"""Bar adapter: judge a lab spec with the project's own judge code (blackbox2 broker + paths, d6q A17 criterion Q),
plus the A50-2 G60-W checkpoint and the A49-2 G-MKT drawdown checks. Nothing is re-implemented: the research code
is imported read-only from /mnt/project-files and only swapped in memory for the duration of a call (the same
technique blackbox2._broker_liq, bb_common.run_common and bb_fx.fx_source use).

HOLDOUT SEAL: every simulation here runs with src_end <= 2014-12-31, passed explicitly. blackbox.Generator is wrapped
at import so that any Generator built in this process (or in forked workers) with a later src_end raises SealError.
The research defaults (d6q / d6l / blackbox2 src_end = '2026-10-07') are never used.

Modes
  quick  '빠른 선별 (기준 아님)': 10y b63 10M only, 400 paths (= the first 400 paths of the bar's 2000-path run,
         same seed 10063), own window, KRWX. A screen, not a bar verdict.
  full   every required version (own/common x KRWX/DEXKOUS, d6q.required_versions) x the 10 Q-suite runs, + G60-W,
         + G-MKT (a)(b)(c), + the prerequisites lab can compute. Output names:
           'REJECT'                   a Q / R check or a prerequisite (D2, A7, causality, version impossible) failed:
                                      fails APPLY-Q, hence APPLY-Q60.
           'REJECT (lab 판정, 미확정)'  the only Q-level failure is a lab port the bar owner has not confirmed (G4_dev).
           'Q60 미달 (Q 미판정)'        only G60-W / G-MKT failed: misses APPLY-Q60 (A50-2: APPLY-Q60 = APPLY-Q + G60-W +
                                      G-MKT); APPLY-Q itself is not decided by lab.
           'PENDING (통합 담당 대기)'    nothing lab computes failed.
         Lab never prints APPLY-Q / APPLY-Q60: PBO, blind A, DSR (trial count N undecided), the G7 stress gates
         (official window is 2015+), valQ, blind B, blind D and the pipeline gates belong to the integrator.

Points marked 'lab interpretation, bar owner not yet confirmed' are choices the coordinator made for lab; they need the
bar owner's ruling (A9-2 identity check) before any lab number is used as a bar result.

Notes for spec writers
  - Warm-up is 300 days on every path (blackbox2): lookbacks longer than 300 days start flat.
  - month() / weekday() read the synthetic path dates (bdate_range from 2026-10-08): calendar rules mean nothing on
    bootstrap paths.
  - Signal names mean the UNDERLYING (as in lab real-data runs): price(TQQQ) = the path's QQQ, price(UPRO) = SPY,
    price(TMF) = TLT. Only QQQ/_NDX, SPY, TLT, IEF families can be judged.
  - The spec's `delay` is not used for the bar (broker delay 0: decide at close t, fill from the t+1 open).
"""
import inspect, math, os, sys, time
import numpy as np, pandas as pd

from . import data as LD, dsl

SEAL = '2014-12-31'
DEEP_LIB = '/mnt/project-files/research/deep/lib'
BB_DIR = '/mnt/project-files/research/signal_research_v3/code'
FX_DIR = '/mnt/project-files/research/data/fx_dexkous'
for _p in (FX_DIR, BB_DIR, DEEP_LIB):        # final order on sys.path: deep/lib, blackbox code, fx_dexkous
    if _p not in sys.path:
        sys.path.insert(0, _p)
import d6q as Q          # noqa: E402
import d6l as L          # noqa: E402
import blackbox2 as B2   # noqa: E402
import blackbox as B     # noqa: E402
import bb_common         # noqa: E402
import bb_fx             # noqa: E402

if not os.path.abspath(sys.modules['engine'].__file__).startswith(BB_DIR):
    raise ImportError(f"top-level 'engine' is {sys.modules['engine'].__file__}, not the blackbox engine; "
                      'import lab.bb in a process that has not imported another engine.py')

ACCT_1M, ACCT_10M = 1_000_000, 10_000_000
GROSS, LEV_CAP = 0.88, 2.64                      # G0: sum(w) <= 0.88, sum(L*w) <= 3 * 0.88
CK_T = (1764, 3024)                              # A50-2: 7y and 12y points (t counted in path days, day 0 = start)
W5, W10 = 1.6 ** 5, 1.6 ** 10
QUICK_N = 400
QUICK_LABEL = '빠른 선별 (기준 아님)'
PENDING_LABEL = 'PENDING (통합 담당 대기)'
PENDING_GATES = ('PBO', 'blind_A', 'DSR', 'stress_cost_x2', 'stress_delay1', 'stress_winner_removal', 'stress_param',
                 'V_validation_ge_QLD', 'B_blindB_ge_max(QLD,QQQM)', 'blind_D (reject-only, A13)',
                 'pipeline_gates(recon_crisis_mdd, deep_dd80, deep_mdd_vs_QQQ, deep_underwater_vs_QQQ)')
REJECT_LAB = 'REJECT (lab 판정, 미확정)'
Q60_MISS = 'Q60 미달 (Q 미판정)'
LAB_PORT = ('real:G4_dev',)                      # Q-level checks that are lab ports, not confirmed by the bar owner
LAB_INTERP = ('real:GMKT_c_real_episodes',)      # Q60-level, episode list is a lab interpretation
N_CUTS = 40                                      # causality: random truncation cuts per path (+ fixed ones)
BAR_VERSION = 2                                  # bump when the adapter logic changes (ledger keys use it)


class SealError(RuntimeError):
    pass


class NotJudgeable(ValueError):
    pass


def _seal(src_end):
    if src_end is None or pd.Timestamp(src_end) > pd.Timestamp(SEAL):
        raise SealError(f'src_end {src_end!r} is after the holdout seal {SEAL}')


def _install_seal():
    """Wrap blackbox.Generator.__init__ (the base of blackbox2.Generator and bb_levels.LevelGenerator) so that no
    path generator in this process can be built on rows after 2014-12-31. Done once; inherited by forked workers."""
    init = B.Generator.__init__
    if getattr(init, '_lab_sealed', False):
        return

    def sealed_init(self, fam, src_end='2026-10-07'):
        _seal(src_end)
        init(self, fam, src_end=src_end)
        if self.cal[-1] > pd.Timestamp(SEAL):
            raise SealError(f'generator calendar ends {self.cal[-1].date()}')
    sealed_init._lab_sealed = True
    B.Generator.__init__ = sealed_init


_install_seal()


# ---------------- candidate ----------------
# lab sleeve -> blackbox ticker (in-path synthesis for QLD TQQQ SSO UPRO TMF; QQQ is held as QQQM, A17 Q-8)
TRADE_MAP = {'QQQ': 'QQQM', 'QLD': 'QLD', 'TQQQ': 'TQQQ', 'SSO': 'SSO', 'UPRO': 'UPRO', 'TMF': 'TMF',
             'SPY': 'SPY', 'TLT': 'TLT', 'IEF': 'IEF'}
# names a signal may read -> blackbox base symbol (the underlying, as lab.data.price_for_signal reads it)
SIG_BASE = {'_NDX': 'QQQ', 'QQQ': 'QQQ', 'QLD': 'QQQ', 'TQQQ': 'QQQ', 'SPY': 'SPY', 'SSO': 'SPY', 'UPRO': 'SPY',
            'TLT': 'TLT', 'TMF': 'TLT', 'IEF': 'IEF'}
BASE_COL = {'QQQ': '_NDX', 'SPY': 'SPY', 'TLT': 'TLT', 'IEF': 'IEF'}       # base -> column name in the DSL frame
LEVER = {'QLD': 2, 'TQQQ': 3, 'SSO': 2, 'UPRO': 3, 'TMF': 3}
NO_PTP = set(TRADE_MAP.values()) | {'QQQ'}     # A7: every instrument lab can trade is a 1940-Act / ETF share, no PTP


def _no_series(*a, **k):
    raise NotJudgeable('the spec reads a panel series that is not on the synthetic path (real history would leak '
                       'onto a bootstrap path)')


def _spec_names(spec):
    """Series names used by the spec's expressions: bare names (minus the DSL functions and the spec's own signal
    names) and every string constant (price('XLK') reads a series just like price(XLK))."""
    import ast
    exprs = list((spec.get('signals') or {}).values())
    for r in spec['rules']:
        if 'when' in r:
            exprs.append(r['when'])
        exprs += list((r.get('hold') or r.get('else') or {}).values())
    fn = set(dsl._mk(pd.DataFrame(index=pd.DatetimeIndex([]))).keys())
    own = set(spec.get('signals') or {})
    out = set()
    for e in exprs:
        if isinstance(e, (int, float)):
            continue
        for n in ast.walk(ast.parse(str(e), mode='eval')):
            if isinstance(n, ast.Name) and n.id not in fn and n.id not in own:
                out.add(n.id)
            elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                out.add(n.value)
    return out


class LabCandidate:
    """blackbox2 candidate interface (signal_syms, trade_syms, build(pm)) for a lab spec. The DSL runs on each path's
    synthetic prices. trade_syms/signal_syms override exists for parity fixtures only (F2)."""
    lane = 'LONG'

    def __init__(self, spec, trade_override=None):
        self.spec = dsl.check_spec(spec)
        self.hash = dsl.spec_hash(spec)
        self.name = spec.get('name', self.hash)
        held = sorted({a for r in spec['rules'] for a in (r.get('hold') or r.get('else') or {})} - {'CASH'})
        bad = [s for s in held if s not in TRADE_MAP]
        if bad:
            raise NotJudgeable(f'sleeve(s) {bad} have no common-source proxy (A3-2): version impossible')
        names = _spec_names(spec)
        bad = sorted(n for n in names if n not in SIG_BASE)
        if bad:
            raise NotJudgeable(f'signal series {bad} not on the blackbox path: version impossible')
        self.sleeves = held
        if trade_override:
            self.trade_syms = list(trade_override)
            self._cols = {s: (s if s in held else None) for s in self.trade_syms}
        else:
            self.trade_syms = [TRADE_MAP[s] for s in held] or ['QQQM']   # all-cash spec: one zero column (bsf RefCash)
            self._cols = {TRADE_MAP[s]: s for s in held}
        bases = {SIG_BASE[n] for n in names} | {SIG_BASE[s] for s in held}
        self.signal_syms = sorted(bases)
        self._lev = np.array([LEVER.get(s, 1) for s in self.trade_syms], float)
        # broker cost: the bar's 30 bp, or the spec's own cost if higher. blackbox2.run passes the same cost to the
        # QQQM_100 / QLD_100 buy-and-hold comparators, so a higher spec cost also makes the comparators slightly weaker
        # (not strictly 'stricter'). -- lab interpretation, bar owner not yet confirmed
        self.cost = max(B.COST, float(spec.get('cost', B.COST)))
        self.n_built = 0
        self.n_capped = 0

    def __repr__(self):
        return 'LAB:' + self.hash

    def frame(self, pm):
        F = {}
        for b in self.signal_syms:
            F[BASE_COL[b]] = pm.C[b]
        for s in self.sleeves:                         # each sleeve's own (synthetic) price, by lab sleeve name
            bs = TRADE_MAP[s] if TRADE_MAP[s] in pm.C else s
            if bs in pm.C:
                F.setdefault(s, pm.C[bs])
        return pd.DataFrame(F, index=pm.dates)

    def build(self, pm):
        F = self.frame(pm)
        orig = LD.series
        LD.series = _no_series          # no real panel history on a synthetic path
        try:
            W = dsl.compile_weights(self.spec, F, self.sleeves)
        finally:
            LD.series = orig
        X = np.zeros((len(F), len(self.trade_syms)))
        for j, ts in enumerate(self.trade_syms):
            s = self._cols.get(ts)
            if s is not None and s in W.columns:
                X[:, j] = np.nan_to_num(W[s].values.astype(float))
        X, capped = cap_rows(X, self._lev)
        self.n_built += 1
        self.n_capped += int(capped)
        return X


def cap_rows(X, lev):
    """G0 caps: scale a row so that sum(w) <= 0.88 and sum(L*w) <= 2.64. Scaling (not rejecting) is the
    lab interpretation, bar owner not yet confirmed (plan open item 6)."""
    s = X.sum(1); e = (X * lev).sum(1)
    f = np.ones(len(X))
    over = s > GROSS + 1e-12
    f[over] = GROSS / s[over]
    over2 = e * f > LEV_CAP + 1e-12
    f[over2] = np.minimum(f[over2], LEV_CAP / e[over2])
    capped = bool((f < 1).any())
    return (X * f[:, None] if capped else X), capped


# ---------------- broker with the G60-W checkpoint ----------------
_ANCHOR = '        eq_krw[:, t] = (cash + (sh * c).sum(1)) * fxt'
# value "as if everything were sold at close t", after the year-end tax of t (if any): same formula and the same
# operation order as blackbox2._LIQ, so at t = T-1 it is bit-identical to the liquidated final equity.
# Both CK_T points are year-end days (t % 252 == 0): that year's tax is already paid and `realized` reset, so the as-if
# sale gets a second TAX_FREE (2.5M KRW) exemption in the same tax year (about +0.55M KRW, ~0.5% of the W5 threshold
# at 10M). _LIQ at T-1 does the same, which keeps the identity. -- lab interpretation, bar owner not yet confirmed
# (plan open item 1, including this double exemption)
_INJECT = ('        if t in CK_T:\n'
           '            CK_OUT.setdefault(t, []).append((cash + (sh * c).sum(1) * (1 - cost)) * fxt - TAX_RATE * '
           'np.maximum(realized + ((sh * (c * fxt[:, None] - basis)).sum(1) - (sh * c).sum(1) * cost * fxt) - TAX_FREE, 0.0))\n')


def _make_broker_ck():
    src = inspect.getsource(B.broker)
    if src.count(_ANCHOR) != 1 or src.count('    return eq_krw,') != 1:
        raise RuntimeError('blackbox.broker source changed: checkpoint injection point not found exactly once')
    ns = vars(B).copy()
    ns['CK_T'] = set(); ns['CK_OUT'] = {}
    exec(src.replace(_ANCHOR, _INJECT + _ANCHOR).replace('    return eq_krw,', B2._LIQ)
         .replace('def broker(', 'def broker_ck('), ns)
    return ns['broker_ck'], ns


BROKER_CK, _CKNS = _make_broker_ck()


def run_w(cand, base='bb2', ck=CK_T, **kw):
    """blackbox2.run (base 'bb2', A3-1 own window) or bb_common.run_common ('common') with the checkpoint broker.
    Module-level so d6l's process pool can pickle it; d6l passes base= through `extra`.
    Adds res['w_check'] = {t: median over paths of value_t / account} and P(value_t / account >= target)."""
    _seal(kw.get('src_end'))
    kw.setdefault('cost', getattr(cand, 'cost', B.COST))
    runner = {'bb2': B2.run, 'common': bb_common.run_common}[base]
    _CKNS['CK_T'] = set(ck); _CKNS['CK_OUT'] = {}
    if hasattr(cand, 'n_built'):
        cand.n_built = cand.n_capped = 0
    old = B2.BROKER_LIQ
    B2.BROKER_LIQ = BROKER_CK
    try:
        res = runner(cand, **kw)
    finally:
        B2.BROKER_LIQ = old
    acct = kw['account']
    out = {int(t): np.concatenate(v) / acct for t, v in _CKNS['CK_OUT'].items()}
    res['w_check'] = {t: float(np.median(v)) for t, v in out.items()}
    res['w_check_p'] = {t: float((v >= (W5 if t == 1764 else W10)).mean()) for t, v in out.items()}
    if hasattr(cand, 'n_built'):
        res['capped_paths'] = [cand.n_capped, cand.n_built]
    res['runner_base'] = base
    return res


# ---------------- checks ----------------
def _key(y, mb, cr, a):
    return B2.key(y, mb, cr, a)


def run_checks(r, main=True):
    """Q / R / G60-W(7y) checks that one 10y run can answer (used by quick mode)."""
    S, Qm, D = r['strategy'], r['bench']['QQQM_100'], r['bench']['QLD_100']
    c = {'Q1': S['log_growth_median'] >= max(D['log_growth_median'], Qm['log_growth_median'] + Q.GROWTH_EDGE),
         'Q2': S['log_growth_p10'] >= max(Qm['log_growth_p10'], D['log_growth_p10']),
         'R1': S['p_ruin_80'] < Q.P_RUIN,
         'R2': S['mdd_p95_worst'] >= Qm['mdd_p95_worst'],
         'R3': S['underwater_p90_days'] <= Qm['underwater_p90_days']}
    if main:
        c['Q3'] = D['p_strategy_beats'] >= Q.P_BEAT and Qm['p_strategy_beats'] >= Q.P_BEAT
    if 1764 in r.get('w_check', {}):
        c['W5'] = r['w_check'][1764] >= W5
    return {k: bool(v) for k, v in c.items()}


def d2_check(hl):
    """Copy of deep/lib/d6.d2_check (d6 imports pipeline -> market -> numba, so it cannot be imported here)."""
    ok = True
    for k, v in hl.items():
        s, q = v['strategy'], v['QQQM_100']
        if k.startswith('10y'):
            ok &= s['p_ruin_80'] < 0.01 and s['mdd_p95_worst'] >= q['mdd_p95_worst'] and s['underwater_p90_days'] <= q['underwater_p90_days']
        else:
            ok &= s['p_ruin_80'] <= q['p_ruin_80']
    return bool(ok)


def version_checks(suite):
    """Computed checks for one version's 10-run Q suite. None = pending (not computed by lab)."""
    r = Q.d6Q_verdict(suite, {}, valQ=None, blindB=None, blindA_required=True)
    c = {k: v for k, v in r['checks'].items() if k[0] in 'QR'}     # Q1-Q5, R1-R3 (V / B are pending)
    c['G60W_W5_7y'] = all(suite[_key(10, mb, cr, ACCT_10M)]['w_check'][1764] >= W5 for mb, cr in Q.BENEFIT)
    c['G60W_W10_12y'] = all(suite[_key(30, mb, False, ACCT_10M)]['w_check'][3024] >= W10 for mb in (63, 252))
    c['GMKT_a_R2'] = c['R2_mdd95_ge_QQQM']
    c['GMKT_b_crisis_mdd_median'] = all(suite[_key(10, 63, True, a)]['strategy']['mdd_median']
                                        >= suite[_key(10, 63, True, a)]['bench']['QQQM_100']['mdd_median'] for a in Q.ACCTS)
    hl = {k: {'strategy': suite[k]['strategy'], 'QQQM_100': suite[k]['bench']['QQQM_100']}
          for k in (_key(10, 63, False, ACCT_10M), _key(30, 63, False, ACCT_10M))}
    c['blackbox_D2'] = d2_check(hl)
    return {k: bool(v) for k, v in c.items()}


def _numbers(r):
    S, Qm, D = r['strategy'], r['bench']['QQQM_100'], r['bench']['QLD_100']
    f = lambda x: round(float(x), 4)
    out = {'lg_med': f(S['log_growth_median']), 'lg_p10': f(S['log_growth_p10']), 'mdd95': f(S['mdd_p95_worst']),
           'mdd_med': f(S['mdd_median']), 'uw90': f(S['underwater_p90_days']), 'p80': f(S['p_ruin_80']),
           'qqqm_lg_med': f(Qm['log_growth_median']), 'qqqm_lg_p10': f(Qm['log_growth_p10']),
           'qqqm_mdd95': f(Qm['mdd_p95_worst']), 'qqqm_uw90': f(Qm['underwater_p90_days']),
           'qld_lg_med': f(D['log_growth_median']), 'qld_lg_p10': f(D['log_growth_p10']),
           'p_beat_qqqm': f(Qm['p_strategy_beats']), 'p_beat_qld': f(D['p_strategy_beats'])}
    for t, v in r.get('w_check', {}).items():
        out[f'mult_t{t}'] = f(v)
    for t, v in r.get('w_check_p', {}).items():
        out[f'p_target_t{t}'] = f(v)
    if 'capped_paths' in r:
        out['capped_paths'] = r['capped_paths']
    return out


# ---------------- real <=2014 path replay (G-MKT (c), G4_dev, causality) ----------------
def _common_frames(base):
    """bb_common's splice (A3 common window) for the base symbols that start after 1999-03-10; returns the swap."""
    pn = B2.BE._P['panel']
    swap = {}
    for s in base:
        f = bb_common.spliced_frame(s)
        if f is not pn[s]:
            swap[s] = (pn[s], f)
    return swap


def real_path(cand, src_end=SEAL):
    """The ACTUAL <=2014 history as one path (identity row index), through blackbox2's own price construction
    (in-path synthesized QLD/TQQQ, prices start at today's raw levels), on the common window (1999-03-11 start).
    Real dates. -- lab interpretation, bar owner not yet confirmed (plan open item 2)."""
    _seal(src_end)
    B2.install_panel()
    syms = list(cand.trade_syms); sig = [s for s in cand.signal_syms if s not in syms]
    base = B2.base_of(syms + sig + ['QLD'])
    pn = B2.BE._P['panel']
    swap = _common_frames(base)
    try:
        for s, (_, f) in swap.items():
            pn[s] = f
        gen = B2.Generator(base, src_end=src_end)
        start = max(pn[s]['adjclose'].first_valid_index() for s in base)
    finally:
        for s, (o, _) in swap.items():
            pn[s] = o
    allsyms = sorted(set(syms) | set(sig) | {'QQQ', 'QQQM', 'QLD'})
    p0 = B2.today_raw_prices(allsyms)
    C, O, irx = B2.build_path_prices(gen, np.arange(len(gen.cal)), allsyms, p0)
    dates = pd.DatetimeIndex([start]).append(gen.cal)
    assert dates[-1] <= pd.Timestamp(SEAL) and len(dates) == len(C['QQQ'])
    fx0 = float(B2.BE._P['panel']['KRW=X']['adjclose'].dropna().iloc[-1])
    fx = fx0 * np.exp(np.r_[0.0, np.cumsum(gen.fxr)])
    return B.PathMarket(dates, C, O, irx), fx, gen


def _episodes_ath(qc):
    """QQQ peak->trough falls deeper than -20% with all-time-high peaks: the same logic as blackbox.Generator.bear
    (L73-85). Returns [(peak_index, trough_index)] on qc's index."""
    peak = np.maximum.accumulate(qc)
    newhigh = np.r_[True, qc[1:] >= peak[:-1]]
    starts = np.flatnonzero(newhigh)
    out = []
    for a, b in zip(starts, np.r_[starts[1:], len(qc)]):
        seg = qc[a:b]
        tr = int(np.argmin(seg))
        if seg[tr] / qc[a] - 1 < -0.20:
            out.append((int(a), int(a + tr)))
    return out


def _episodes_local(qc, fall=0.20, rally=0.20):
    """QQQ falls deeper than -20% from LOCAL peaks: the peak is the highest close since the last trough; a decline
    starts when the close is more than 20% below that peak; its trough is the lowest close until the close rises more
    than 20% above it (or the series ends). Covers 2000-02 and 2007-09 on the <=2014 history."""
    out, pk, tr, down = [], 0, None, False
    for i in range(1, len(qc)):
        if not down:
            if qc[i] > qc[pk]:
                pk = i
            elif qc[i] / qc[pk] - 1 < -fall:
                down, tr = True, i
        else:
            if qc[i] < qc[tr]:
                tr = i
            elif qc[i] / qc[tr] - 1 > rally:
                out.append((int(pk), int(tr))); down, pk = False, i
    if down:
        out.append((int(pk), int(tr)))
    return out


def _episodes_recover(qc, peaks):
    """For each local peak: peak -> lowest close before the close regains that peak (or the series ends), if that
    fall is deeper than -20% (e.g. 2007-10-31 -> 2008-11-20, which the 20%-rally rule splits in two)."""
    out = []
    for pk in peaks:
        above = np.flatnonzero(qc[pk + 1:] >= qc[pk])
        j = pk + 1 + int(above[0]) if len(above) else len(qc)
        tr = pk + int(np.argmin(qc[pk:j]))
        if qc[tr] / qc[pk] - 1 < -0.20:
            out.append((int(pk), int(tr)))
    return out


def _episodes(qc):
    """A49-2(c) 'every stretch where QQQ fell more than 20% from a peak': the union of the all-time-high reading
    (Generator.bear), the local-peak reading (20% fall / 20% rally) and, for each local peak, the fall to the lowest
    close before that peak is regained. A PASS then holds under each reading. -- lab interpretation, bar owner not yet
    confirmed."""
    loc = _episodes_local(qc)
    return sorted(set(_episodes_ath(qc)) | set(loc) | set(_episodes_recover(qc, sorted({a for a, _ in loc}))))


def causality(cand, pm, n_cuts=N_CUTS, fixed=(), seed=None):
    """Targets built on the path truncated at a cut must equal the full-path targets up to the cut. Cuts: the fixed
    dates (if any) + n_cuts random rows drawn from a fresh OS seed (recorded), so a spec cannot know them in advance.
    Returns (ok, violations, seed)."""
    if seed is None:
        seed = int.from_bytes(os.urandom(8), 'little')
    rng = np.random.default_rng(seed)
    tg = np.asarray(cand.build(pm), float)
    N = len(pm.dates)
    cuts = [int(np.searchsorted(pm.dates.values, np.datetime64(pd.Timestamp(c)), side='right')) for c in fixed]
    cuts += sorted(int(x) for x in rng.integers(2, N, size=n_cuts))
    bad = []
    for n in cuts:
        if n < 2:
            continue
        pt = B.PathMarket(pm.dates[:n], {k: v[:n] for k, v in pm.C.items()},
                          {k: v[:n] for k, v in pm.O.items()}, pm.irx[:n])
        d = float(np.max(np.abs(np.asarray(cand.build(pt), float) - tg[:n])))
        if not d <= 1e-9:
            bad.append((str(pm.dates[n - 1].date()), d))
    return not bad, bad, seed


def boot_paths(cand, n=2, years=10, mean_block=63, seed=10063):
    """The first n bootstrap paths of blackbox2.run(n_paths>=n, years, mean_block, seed, src_end=2014) as PathMarkets
    (same generator, index draw, price construction and synthetic dates as blackbox2.run)."""
    B2.install_panel()
    syms = list(cand.trade_syms); sig = [s for s in cand.signal_syms if s not in syms]
    gen = B2.Generator(B2.base_of(syms + sig + ['QLD']), src_end=SEAL)
    allsyms = sorted(set(syms) | set(sig) | {'QQQ', 'QQQM', 'QLD'})
    p0 = B2.today_raw_prices(allsyms)
    warm = 300; nd = 252 * years
    idx = gen.sample_idx(nd + warm, n, mean_block, False, seed)
    dates = pd.bdate_range('2026-10-08', periods=warm + nd + 1)
    out = []
    for k in range(n):
        C, O, irx = B2.build_path_prices(gen, idx[k], allsyms, p0)
        out.append(B.PathMarket(dates, C, O, irx))
    return out


def causality_all(cand, real_pm=None):
    """Causality on the real <=2014 path (3 fixed cuts + N_CUTS random) and on 2 bootstrap paths (N_CUTS random each)."""
    res = {'violations': [], 'seeds': []}
    pms = ([('real', real_pm, ('2008-06-30', '2012-03-30', SEAL))] if real_pm is not None else []) + \
          [(f'boot{k}', pm, ()) for k, pm in enumerate(boot_paths(cand))]
    for tag, pm, fixed in pms:
        ok, bad, seed = causality(cand, pm, fixed=fixed)
        res['seeds'].append((tag, seed))
        res['violations'] += [(tag,) + b for b in bad]
    res['ok'] = not res['violations']
    return res


def _metrics(x):
    r = x[1:] / x[:-1] - 1
    sd = r.std()
    return {'log_growth': float(np.log1p(np.maximum(r, -0.999999)).mean() * 252),
            'sharpe': float(r.mean() / sd * math.sqrt(252)) if sd > 0 else 0.0,
            'mdd': float((x / np.maximum.accumulate(x) - 1).min())}


def real_checks(cand, account=ACCT_10M):
    """G-MKT (c), G4_dev, causality, A7 on the actual <=2014 path, + dev-window stress figures (info only)."""
    pm, fx, gen = real_path(cand)
    tg = np.asarray(cand.build(pm), float)
    syms = list(cand.trade_syms)
    Cs = np.stack([pm.C[s] for s in syms], 1)[None]; Os = np.stack([pm.O[s] for s in syms], 1)[None]

    def replay(delay=0, cost=cand.cost):
        eq, st = B2.BROKER_LIQ(tg[None], Cs, Os, fx[None], account, delay=delay, cost=cost)
        return eq[0]
    E = replay()
    q = pm.C['QQQ']
    # G-MKT (c): candidate loss over each QQQ episode (peak -> trough dates) <= QQQ loss. Both sides in KRW: the broker
    # holds USD, so the FX factor is the same on both sides and this equals the USD comparison.
    # -- lab interpretation, bar owner not yet confirmed (episode list = union of all-time-high and local-peak readings)
    qk = q * fx
    eps = [(a + 1, b + 1) for a, b in _episodes(q[1:])]
    ep = [{'peak': str(pm.dates[a].date()), 'trough': str(pm.dates[b].date()),
           'cand': float(E[b] / E[a]), 'qqq': float(qk[b] / qk[a])} for a, b in eps]
    gmkt_c = all(e['cand'] >= e['qqq'] for e in ep)
    # G4_dev: Sharpe > 0.5, >= 30 entries, log growth > QQQ, on the dev path (USD view: KRW equity / FX).
    # Entries counted on the targets (flat -> invested). -- lab port of the plan's G4 text, bar owner not yet confirmed
    us = E / fx
    ms, mq = _metrics(us), _metrics(q)
    on = tg.sum(1) > 1e-12
    entries = int(np.sum(on[1:] & ~on[:-1]) + on[0])
    g4 = ms['sharpe'] > 0.5 and entries >= 30 and ms['log_growth'] > mq['log_growth']
    # causality: truncation test at fixed + random cuts on the real path and on 2 bootstrap paths
    caus = causality_all(cand, pm)
    bad = caus['violations']
    a7 = all(s in NO_PTP for s in syms)
    # dev-window stress (INFO ONLY: pipeline.stress, the G7 gate, runs on 2015+ actual data, which lab cannot open)
    r = E[1:] / E[:-1] - 1
    r2 = r.copy(); r2[np.argsort(r)[-10:]] = 0.0
    info = {'cost_x2_lg': _metrics(replay(cost=2 * cand.cost) / fx)['log_growth'],
            'delay1_lg': _metrics(replay(delay=1) / fx)['log_growth'],
            'winner_removed_top10d_lg': float(np.log1p(r2).mean() * 252)}
    return {'window': [str(pm.dates[0].date()), str(pm.dates[-1].date())], 'source_window': gen.src,
            'checks': {'GMKT_c_real_episodes': bool(gmkt_c), 'G4_dev': bool(g4), 'causality': not bad,
                       'A7_no_PTP': bool(a7)},
            'episodes': ep, 'g4': {'sharpe': ms['sharpe'], 'entries': entries, 'lg': ms['log_growth'],
                                   'qqq_lg': mq['log_growth'], 'mdd': ms['mdd'], 'qqq_mdd': mq['mdd']},
            'episode_rule': 'union(all-time-high peaks = Generator.bear; local peaks, 20% fall / 20% rally; '
                            'local peak -> low before the peak is regained)',
            'causality_violations': bad, 'causality_seeds': caus['seeds'], 'dev_stress_info': info}


# ---------------- modes ----------------
def quick(cand, n_paths=QUICK_N):
    """'빠른 선별 (기준 아님)': 10y b63 10M, own window, KRWX, src_end 2014, seed = the bar's (10063), + causality on 2
    bootstrap paths (random cuts)."""
    t0 = time.time()
    caus = causality_all(cand)
    with bb_fx.fx_source('KRWX'):
        r = run_w(cand, base='bb2', ck=(1764,), n_paths=n_paths, years=10, mean_block=63, crisis=False,
                  account=ACCT_10M, src_end=SEAL, seed=L.seed_of(10, 63, False))
    c = dict(run_checks(r), causality=caus['ok'])
    fails = [k for k, v in c.items() if not v]
    return {'mode': 'quick', 'label': QUICK_LABEL, 'src_end': SEAL, 'n_paths': n_paths, 'key': _key(10, 63, False, ACCT_10M),
            'source_window': r['source_window'], 'checks': c, 'failed': fails, 'causality': caus,
            'screen': 'pass' if not fails else 'fail', 'numbers': _numbers(r), 'elapsed_s': time.time() - t0}


def _is_q60(name):
    g = name.split(':', 1)[-1]
    return g.startswith(('G60W_', 'GMKT_'))


def verdict_of(failed):
    """Name for a list of failed check names (see the module doc). Q-level = everything that is not G60-W / G-MKT."""
    q = [f for f in failed if not _is_q60(f)]
    if q:
        return 'REJECT' if any(f not in LAB_PORT for f in q) else REJECT_LAB
    return Q60_MISS if failed else PENDING_LABEL


def full(cand, workers=4, early_stop=True, log=None):
    """Every required version x the 10 Q runs. With early_stop the remaining versions are skipped once a check that
    is final fails: any version-level check, causality, A7 or version-impossible. A failure of a real-path lab port
    (G4_dev) or lab interpretation (G-MKT (c) episodes) does not stop the run, so the official Q checks still decide."""
    t0 = time.time()
    quiet = log or (lambda *a, **k: None)
    real = real_checks(cand)
    out = {'mode': 'full', 'src_end': SEAL, 'label': f'src_end {SEAL}, design side', 'real_path': real,
           'versions': {}, 'pending': list(PENDING_GATES)}
    failed = []
    for k, v in real['checks'].items():
        if v is False:
            n = f'real:{k}'
            failed.append(n)
    stop = lambda: early_stop and any(f not in LAB_PORT + LAB_INTERP for f in failed)
    for v in Q.required_versions():
        src, fx = v.split('_')
        if stop():
            out['versions'][v] = {'not_run': 'skipped: a final check already failed'}
            continue
        try:
            suite = Q.d6Q_suite(cand, runner=run_w, fx=fx, workers=workers, src_end=SEAL,
                                extra={'base': 'bb2' if src == 'own' else 'common'}, log=quiet)
        except bb_common.NoProxyError as e:
            out['versions'][v] = {'impossible': str(e)}
            failed.append(f'{v}:version_impossible')
            continue
        c = version_checks(suite)
        out['versions'][v] = {'checks': c, 'numbers': {k: _numbers(r) for k, r in suite.items()},
                              'source_window': suite[Q.Q_KEYS[0]]['source_window']}
        failed += [f'{v}:{k}' for k, x in c.items() if x is False]
    out['failed'] = [f + ('(lab port)' if f in LAB_PORT else '') for f in failed]
    out['failed_q'] = [f for f in failed if not _is_q60(f)]
    out['failed_q60'] = [f for f in failed if _is_q60(f)]
    out['verdict'] = verdict_of(failed)
    out['elapsed_s'] = time.time() - t0
    return out


def judge(spec, mode='quick', **kw):
    """mode 'quick' | 'full'. A spec that cannot be put on the blackbox paths -> REJECT (version impossible)."""
    try:
        cand = LabCandidate(spec)
    except NotJudgeable as e:
        return {'mode': mode, 'verdict': 'REJECT (version impossible)', 'failed': ['version_impossible'],
                'reason': str(e), 'screen': 'fail'}
    if mode == 'quick':
        return quick(cand, **kw)
    if mode == 'full':
        return full(cand, **kw)
    raise ValueError(mode)
