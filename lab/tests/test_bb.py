"""Tests for lab/bb.py (bar adapter). Run as a script: python -B tests/test_bb.py
Run it in its own process (not together with tests/test_parity.py): both put a different top-level `engine` module
on sys.path. Prints PASS/FAIL lines and identity results only; no strategy figures.

(a) F3 checkpoint broker identity: run_w == blackbox2.run on 'strategy' and 'bench' (every number), and the
    checkpoint at t = T-1 equals the liquidated final equity path by path.
(b) F2 bit-identity: lab spec (QQQ > SMA200 -> QLD 0.88, else cash; trade_syms overridden to QQQ/QLD/TQQQ) vs a numpy
    re-implementation of candidates.TrendLev('QQQ', 200, 2) (candidates.py imports market -> numba), 40 paths, src_end 2014.
(c) seal: every Generator / blackbox2.run / bb_common.run_common call made by quick, real-path replay and the full
    flow (small path count, in-process) sees src_end <= 2014-12-31; later src_end and the research default raise.
(d) F1: deep/checks/test_d6q.py Part A (synthetic suites, d6Q_verdict / combine logic), run unmodified with
    PART_A_ONLY=1 (it imports d6q without numba).
(e) DSL: latch(), band speed-up == the old row loop, G0 row caps, NotJudgeable sleeves / quoted series names,
    window / lag >= 1 (no future rows), delay >= 2, cost clamp in the dev summary, v0 ledger refused.
(f) process-pool plumbing: run_w pickles and returns the same result from a forked worker.
(g) verdict assembly on synthetic inputs: version_checks (W5 / W10 thresholds and keys, G-MKT (b) direction, D2),
    verdict names, G-MKT (c) episode lists, causality catches a weekday-masked look-ahead at random cuts.
"""
import math, os, subprocess, sys, time
LAB = __file__.rsplit('/tests/', 1)[0]
sys.path.insert(0, LAB)
import numpy as np, pandas as pd  # noqa: E402
from lab import bb, dsl  # noqa: E402

B2, B, Q = bb.B2, bb.B, bb.Q
SEAL = '2014-12-31'
FAILS = []


def check(name, ok, extra=''):
    print(f'{"PASS" if ok else "FAIL"}  {name}{("  " + extra) if extra else ""}', flush=True)
    if not ok:
        FAILS.append(name)


def leaves(x, p=''):
    if isinstance(x, dict):
        for k in sorted(x, key=str):
            yield from leaves(x[k], f'{p}/{k}')
    elif isinstance(x, (list, tuple)):
        for i, v in enumerate(x):
            yield from leaves(v, f'{p}[{i}]')
    else:
        yield p, x


def same(a, b, fields=('strategy', 'bench', 'mean_stats', 'source_window', 'n_paths')):
    la = dict(leaves({f: a.get(f) for f in fields})); lb = dict(leaves({f: b.get(f) for f in fields}))
    if la.keys() != lb.keys():
        return False, 0, float('nan')
    n, mx, eq = 0, 0.0, True
    for k in la:
        x, y = la[k], lb[k]
        if isinstance(x, (float, int, np.floating, np.integer)) and not isinstance(x, bool):
            n += 1
            if not (x == y or (math.isnan(x) and math.isnan(y))):
                eq = False; mx = max(mx, abs(float(x) - float(y)))
        elif x != y:
            eq = False
    return eq, n, mx


F2_SPEC = {'name': 'f2_trend_qld', 'rebalance': 'daily', 'signals': {'up': 'price(QQQ) > sma(QQQ, 200)'},
           'rules': [{'when': 'up', 'hold': {'QLD': 0.88}}, {'else': {'CASH': 1.0}}]}


class TrendLevNP:
    """numpy copy of research/deep/lib/candidates.TrendLev('QQQ', n, lmax) (sma, map_exposure with GROSS 0.88,
    LEV['QQQ'] = QQQ/QLD/TQQQ)."""
    GROSS = 0.88

    def __init__(self, n=200, lmax=2):
        self.n, self.lmax = n, lmax
        self.signal_syms = ['QQQ']; self.trade_syms = ['QQQ', 'QLD', 'TQQQ']; self.lane = 'LONG'

    def __repr__(self):
        return f'TREND_QQQ_SMA{self.n}_L{self.lmax}'

    def build(self, mkt):
        c = mkt.C['QQQ']
        sma = pd.Series(c).rolling(self.n, min_periods=self.n).mean().values
        e = np.where(c > sma, 1.0, 0.0) * self.lmax * self.GROSS
        W = np.zeros((len(e), 3))
        e = np.clip(np.nan_to_num(e, nan=0.0), 0, 3 * self.GROSS)
        b1 = e <= self.GROSS + 1e-12
        b2 = (~b1) & (e <= 2 * self.GROSS + 1e-12)
        b3 = ~(b1 | b2)
        W[b1, 0] = e[b1]; W[b2, 1] = e[b2] / 2; W[b3, 2] = e[b3] / 3
        return W


RUN = dict(n_paths=40, years=10, mean_block=63, crisis=False, account=10_000_000, src_end=SEAL, seed=10063)


def test_f3():
    print('== (a) F3 checkpoint broker identity ==')
    c = bb.LabCandidate(dsl.load_spec(LAB + '/specs/trend_tqqq_200.yaml'))
    ref = B2.run(c, **RUN, cost=c.cost)
    T = 252 * RUN['years'] + 1
    finals = []
    orig = bb.BROKER_CK

    def spy(*a, **k):
        eq, st = orig(*a, **k)
        finals.append(eq[:, -1].copy())
        return eq, st
    bb.BROKER_CK = spy
    try:
        r = bb.run_w(c, base='bb2', ck=(1764, T - 1), **RUN)
    finally:
        bb.BROKER_CK = orig
    eq_, n, mx = same(ref, r)
    check('F3 run_w == blackbox2.run (strategy, bench, mean_stats)', eq_, f'{n} numbers, max |diff| {mx}')
    ck = np.concatenate(bb._CKNS['CK_OUT'][T - 1]); fin = np.concatenate(finals)
    check('F3 checkpoint at T-1 == liquidated final equity, every path', len(ck) == RUN['n_paths'] and np.array_equal(ck, fin),
          f'{len(ck)} paths, max |diff| {float(np.abs(ck - fin).max())}')
    check('F3 w_check has the 7y point', 1764 in r['w_check'] and np.isfinite(r['w_check'][1764]))
    cc = bb.LabCandidate(dsl.load_spec(LAB + '/specs/trend_tqqq_200.yaml'))
    rc = bb.run_w(cc, base='common', **RUN)
    refc = bb.bb_common.run_common(cc, **RUN, cost=cc.cost)
    eq_, n, mx = same(refc, rc)
    check('F3 run_w(base=common) == bb_common.run_common', eq_ and rc.get('common_window') is True, f'{n} numbers, max |diff| {mx}')


def test_f2():
    print('== (b) F2 bit-identity vs numpy TrendLev(QQQ, 200, 2) ==')
    lab_c = bb.LabCandidate(F2_SPEC, trade_override=['QQQ', 'QLD', 'TQQQ'])
    ref_c = TrendLevNP(200, 2)
    check('F2 same signal_syms / trade_syms', lab_c.signal_syms == ref_c.signal_syms and lab_c.trade_syms == ref_c.trade_syms,
          f'{lab_c.signal_syms} {lab_c.trade_syms}')
    # targets path by path on the bar's own paths
    gen = B2.Generator(B2.base_of(ref_c.trade_syms + ['QLD']), src_end=SEAL)
    allsyms = sorted(set(ref_c.trade_syms) | {'QQQ', 'QQQM', 'QLD'})
    p0 = B2.today_raw_prices(allsyms)
    idx = gen.sample_idx(252 * 10 + 300, 40, 63, False, 10063)
    dates = pd.bdate_range('2026-10-08', periods=252 * 10 + 300 + 1)
    mx = 0.0
    for k in range(40):
        C, O, irx = B2.build_path_prices(gen, idx[k], allsyms, p0)
        pm = B.PathMarket(dates, C, O, irx)
        mx = max(mx, float(np.abs(lab_c.build(pm) - ref_c.build(pm)).max()))
    check('F2 targets identical on 40 paths', mx == 0.0, f'max |diff| {mx}')
    a = B2.run(ref_c, **RUN); b = B2.run(lab_c, **RUN)
    eq_, n, mx2 = same(a, b)
    check('F2 blackbox2.run results identical (strategy, bench, mean_stats)', eq_, f'{n} numbers, max |diff| {mx2}')


def test_seal():
    print('== (c) holdout seal ==')
    seen = []
    o_init, o_run, o_common = B.Generator.__init__, B2.run, bb.bb_common.run_common

    def rec_init(self, fam, src_end='2026-10-07'):
        seen.append(('Generator', src_end))
        o_init(self, fam, src_end=src_end)
        seen.append(('Generator.cal_end', str(self.cal[-1].date())))

    def rec_run(cand, *a, **kw):
        seen.append(('blackbox2.run', kw.get('src_end', a[9] if len(a) > 9 else '2026-10-07(default)')))
        return o_run(cand, *a, **kw)

    def rec_common(cand, **kw):
        seen.append(('run_common', kw.get('src_end', '2026-10-07(default)')))
        return o_common(cand, **kw)
    o_runw = bb.run_w

    def small_run_w(cand, **kw):      # the full flow with 20 paths per run (mechanics only)
        kw['n_paths'] = 20
        return o_runw(cand, **kw)
    B.Generator.__init__, B2.run, bb.bb_common.run_common, bb.run_w = rec_init, rec_run, rec_common, small_run_w
    t0 = time.time()
    try:
        c = bb.LabCandidate(dsl.load_spec(LAB + '/specs/trend_tqqq_200.yaml'))
        q = bb.quick(c, n_paths=20)
        f = bb.full(c, workers=1, early_stop=False)
    finally:
        B.Generator.__init__, B2.run, bb.bb_common.run_common, bb.run_w = o_init, o_run, o_common, o_runw
    gens = [s for k, s in seen if k == 'Generator']
    ends = [s for k, s in seen if k == 'Generator.cal_end']
    runs = [s for k, s in seen if k in ('blackbox2.run', 'run_common')]
    check('seal: every Generator src_end <= 2014-12-31', bool(gens) and all(pd.Timestamp(s) <= pd.Timestamp(SEAL) for s in gens),
          f'{len(gens)} generators')
    check('seal: every Generator calendar ends <= 2014-12-31', bool(ends) and all(e <= SEAL for e in ends))
    check('seal: every run / run_common call passes src_end <= 2014-12-31',
          bool(runs) and all(not str(s).endswith('(default)') and pd.Timestamp(s) <= pd.Timestamp(SEAL) for s in runs),
          f'{len(runs)} calls')
    nv = sum(1 for v in f['versions'].values() if 'checks' in v)
    check('seal: full flow ran all 4 versions x 10 runs in-process (mechanics)', nv == 4 and
          all(len(v['numbers']) == 10 for v in f['versions'].values()), f'{nv} versions, {time.time() - t0:.0f}s')
    check('full flow output name is REJECT / Q60 미달 / PENDING only (never APPLY)',
          f['verdict'] in ('REJECT', bb.REJECT_LAB, bb.Q60_MISS, bb.PENDING_LABEL) and 'APPLY' not in str(f['verdict']) and 'APPLY' not in q['label'])
    for what, fn in (('run_w src_end 2015-01-01', lambda: bb.run_w(c, base='bb2', **dict(RUN, src_end='2015-01-01'))),
                     ('run_w without src_end', lambda: bb.run_w(c, base='bb2', **{k: v for k, v in RUN.items() if k != 'src_end'})),
                     ('blackbox2.run research default src_end', lambda: B2.run(c, n_paths=2)),
                     ('d6Q_suite research default src_end', lambda: Q.d6Q_suite(c, runner=bb.run_w, workers=1,
                                                                               keys=[Q.Q_KEYS[0]], extra={'base': 'bb2'},
                                                                               log=lambda *a: None)),
                     ('Generator src_end 2015-01-02', lambda: B2.Generator(['QQQ'], src_end='2015-01-02'))):
        try:
            fn(); check(f'seal: {what} -> SealError', False)
        except bb.SealError:
            check(f'seal: {what} -> SealError', True)


def test_f1():
    print('== (d) F1 deep/checks/test_d6q.py Part A ==')
    T = '/mnt/project-files/research/deep/checks/test_d6q.py'
    # lab.bb is imported first so that the Generator seal is installed in the subprocess too: if PART_A_ONLY were
    # ignored, Part B (research default src_end 2026-10-07) would raise SealError instead of running.
    code = (f'import sys, runpy; sys.path.insert(0, {LAB!r}); import lab.bb; sys.argv = [{T!r}]; '
            f'runpy.run_path({T!r}, run_name="__main__")')
    p = subprocess.run([sys.executable, '-B', '-c', code],
                       env=dict(os.environ, PART_A_ONLY='1', PYTHONDONTWRITEBYTECODE='1'),
                       capture_output=True, text=True, cwd='/tmp', timeout=600)
    lines = [x for x in p.stdout.splitlines() if x.startswith(('PASS', 'FAIL'))]
    for x in lines:
        print('     ' + x)
    partb = 'Part B' in p.stdout or any(x.split()[1].startswith('B') for x in lines if len(x.split()) > 1)
    check('F1 test_d6q.py Part A exit 0, FAILS: none, sealed, Part B never started',
          p.returncode == 0 and 'FAILS: none' in p.stdout and not partb and
          not any(x.startswith('FAIL  ') for x in lines), f'{len(lines)} checks, rc {p.returncode} {p.stderr[-300:]}')


def test_dsl():
    print('== (e) DSL / adapter units ==')
    idx = pd.bdate_range('2020-01-01', periods=10)
    on = pd.Series([0, 1, 0, 0, 0, 0, 1, 1, 0, 0], index=idx).astype(bool)
    off = pd.Series([0, 0, 0, 1, 0, 0, 0, 1, 0, 1], index=idx).astype(bool)
    check('latch: on/off/keep, starts False, off wins on a tie', dsl._latch(on, off, idx).astype(int).tolist() == [0, 1, 1, 0, 0, 0, 1, 0, 0, 0])
    px = np.r_[100 * 1.005 ** np.arange(300), 100 * 1.005 ** 299 * 0.99 ** np.arange(1, 101)]
    F = pd.DataFrame({'_NDX': px}, index=pd.bdate_range('2000-01-03', periods=400))
    sp = {'signals': {'on': 'price(QQQ) > sma(QQQ, 50) * 1.02', 'off': 'price(QQQ) < sma(QQQ, 50) * 0.98', 'up': 'latch(on, off)'},
          'rules': [{'when': 'up', 'hold': {'QLD': 0.88}}, {'else': {'CASH': 1.0}}]}
    W = dsl.compile_weights(sp, F, ['QLD'])
    check('latch in a spec compiles and switches', W['QLD'].max() == 0.88 and W['QLD'].iloc[-1] == 0.0)
    rng = np.random.default_rng(1); ok = True
    for _ in range(100):
        n = int(rng.integers(2, 300)); Wv = np.repeat(np.round(rng.random((n, 3)), 1), rng.integers(1, 5, n), axis=0)[:n]
        old = Wv.copy()
        for i in range(1, len(old)):
            if np.abs(old[i] - old[i - 1]).max() < 0.1:
                old[i] = old[i - 1]
        ok &= np.array_equal(old, dsl._band(Wv, 0.1))
    check('band: change-row loop == old row loop (100 random cases)', bool(ok))
    X, capped = bb.cap_rows(np.array([[1.0, 0.0], [0.5, 0.5], [0.44, 0.0]]), np.array([3.0, 1.0]))
    check('G0 caps: sum <= 0.88 and sum(L*w) <= 2.64, untouched rows kept', capped and np.all(X.sum(1) <= 0.88 + 1e-12)
          and np.all((X * [3, 1]).sum(1) <= 2.64 + 1e-12) and X[2, 0] == 0.44)
    for sp_, what in ((dsl.load_spec(LAB + '/specs/voltarget_qld.yaml'), 'SHY sleeve'),
                      ({'signals': {'up': 'price(XLK) > 0'}, 'rules': [{'when': 'up', 'hold': {'QLD': 0.5}}]}, 'XLK signal')):
        try:
            bb.LabCandidate(sp_); check(f'NotJudgeable: {what}', False)
        except bb.NotJudgeable:
            check(f'NotJudgeable: {what}', True)
    r = bb.judge(dsl.load_spec(LAB + '/specs/voltarget_qld.yaml'), 'quick')
    check('judge: voltarget_qld -> REJECT (version impossible)', r['verdict'] == 'REJECT (version impossible)')
    for e in ("price('_GSPC') > sma('_GSPC', 200)", "price('XLK') > 0"):
        try:
            bb.LabCandidate({'signals': {'up': e}, 'rules': [{'when': 'up', 'hold': {'QLD': 0.5}}]})
            check(f'NotJudgeable at construction: quoted name {e}', False)
        except bb.NotJudgeable:
            check(f'NotJudgeable at construction: quoted name {e}', True)
    # windows / lags: integer >= 1 only (n <= 0 reads future rows)
    bad = ['lag(price(QQQ), -1) > price(QQQ)', 'lag(price(QQQ), 0) > 0', 'ret(QQQ, -5) > 0', 'ret(QQQ, 0) > 0',
           'sma(QQQ, -200) > 0', 'ema(QQQ, 0) > 0', 'vol(QQQ, -20) > 0', 'high(QQQ, -5) > 0', 'low(QQQ, 0) > 0',
           'dd(QQQ, -5) > 0', 'rsi(QQQ, -14) > 0', 'sma(QQQ, 2.5) > 0', 'lag(price(QQQ), 1.5) > 0']
    refused = 0
    for e in bad:
        try:
            dsl.compile_weights({'signals': {'up': e}, 'rules': [{'when': 'up', 'hold': {'QLD': 0.5}}, {'else': {'CASH': 1.0}}]},
                                F, ['QLD'])
        except ValueError:
            refused += 1
    check('DSL: window / lag <= 0 or non-integer refused (lag, ret, sma, ema, vol, high, low, dd, rsi)',
          refused == len(bad), f'{refused}/{len(bad)}')
    okw = dsl.compile_weights({'signals': {'up': 'lag(price(QQQ), 1) > sma(QQQ, 50.0) and ret(QQQ, 5) > -1'},
                               'rules': [{'when': 'up', 'hold': {'QLD': 0.5}}, {'else': {'CASH': 1.0}}]}, F, ['QLD'])
    check('DSL: positive integer windows (incl. 50.0) still compile', okw['QLD'].max() == 0.5)
    refused = 0
    for d in (-1, 0, 1, 1.5, 'x', True):
        try:
            dsl.check_spec({'delay': d, 'rules': []})
        except ValueError:
            refused += 1
    okd = all(dsl.check_spec({'delay': d, 'rules': []}) for d in (2, 3, 2.0)) and dsl.check_spec({'rules': []})
    check('spec: delay < 2 / non-integer refused, delay >= 2 or absent accepted', refused == 6 and bool(okd))
    try:
        bb.LabCandidate({'delay': 0, 'rules': [{'else': {'QLD': 0.88}}]}); check('LabCandidate refuses delay 0', False)
    except ValueError:
        check('LabCandidate refuses delay 0', True)
    from lab import gates
    ix = pd.bdate_range('1990-01-01', '2014-12-31')
    rr = np.random.default_rng(3)
    R = pd.DataFrame({'QQQ': rr.normal(4e-4, 0.015, len(ix)), 'CASH': 1e-4}, index=ix)
    W = pd.DataFrame({'QQQ': (np.arange(len(ix)) // 40 % 2).astype(float)}, index=ix); W['CASH'] = 1 - W['QQQ']
    sp0 = {'rules': [], 'dev_start': '1990-01-01'}
    a0, a3 = gates.evaluate(W, R, dict(sp0, cost=0.0)), gates.evaluate(W, R, dict(sp0, cost=0.003))
    a9 = gates.evaluate(W, R, dict(sp0, cost=0.01))
    check('dev summary: cost clamped to >= 0.003 (0.0 == 0.003, 0.01 differs)',
          a0['dev'] == a3['dev'] and a9['dev']['cagr_at'] < a3['dev']['cagr_at'])
    try:
        gates.evaluate(W, R, dict(sp0, delay=-1)); check('dev summary refuses delay -1', False)
    except ValueError:
        check('dev summary refuses delay -1', True)
    import sqlite3, tempfile
    from lab import ledger
    os.makedirs(ledger.HOME, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ledger.HOME) as td:
        c0 = sqlite3.connect(os.path.join(td, 'ledger.sqlite'))
        c0.execute('create table runs(hash text primary key, name text, family text, known int, ts text, summary text, '
                   'holdout text)'); c0.commit(); c0.close()
        old = ledger.HOME; ledger.HOME = td
        try:
            ledger.get('x'); check('ledger: v0 ledger (holdout column) refused', False)
        except RuntimeError:
            check('ledger: v0 ledger (holdout column) refused', True)
        finally:
            ledger.HOME = old


def test_verdict():
    print('== (g) verdict assembly on synthetic inputs ==')
    W5, W10 = bb.W5, bb.W10
    S = {'log_growth_median': 0.20, 'log_growth_p10': 0.10, 'mdd_p95_worst': -0.40, 'underwater_p90_days': 500,
         'p_ruin_80': 0.0, 'cagr_median': 0.65, 'mdd_median': -0.30}
    QM = {'log_growth_median': 0.12, 'log_growth_p10': 0.02, 'mdd_p95_worst': -0.60, 'underwater_p90_days': 900,
          'p_ruin_80': 0.0, 'mdd_median': -0.35}
    QL = {'log_growth_median': 0.15, 'log_growth_p10': -0.05, 'mdd_p95_worst': -0.85, 'underwater_p90_days': 1500,
          'p_ruin_80': 0.05, 'mdd_median': -0.55}

    def suite(mod=lambda y, mb, cr, a, e: None):
        out = {}
        for (y, n, mb, cr, a), k in zip(Q.Q_SUITE, Q.Q_KEYS):
            e = {'strategy': dict(S), 'bench': {'QQQM_100': dict(QM, p_strategy_beats=0.7), 'QLD_100': dict(QL, p_strategy_beats=0.7)},
                 'w_check': {1764: W5 * 1.000001, 3024: W10 * 1.000001}}
            mod(y, mb, cr, a, e)
            out[k] = e
        return out
    bad = lambda c: sorted(k for k, v in c.items() if not v)
    c = bb.version_checks(suite())
    check('V1 all good -> every computed check True (Q1-Q5, R1-R3, G60W, GMKT, D2)', not bad(c) and
          {'G60W_W5_7y', 'G60W_W10_12y', 'GMKT_a_R2', 'GMKT_b_crisis_mdd_median', 'blackbox_D2'} <= set(c), str(bad(c)))
    lo5, lo10 = W5 * (1 - 1e-9), W10 * (1 - 1e-9)
    ok = True
    for mb_, cr_ in Q.BENEFIT:
        def m(y, mb, cr, a, e, mb_=mb_, cr_=cr_):
            if y == 10 and mb == mb_ and cr == cr_ and a == bb.ACCT_10M:
                e['w_check'][1764] = lo5
        ok &= bad(bb.version_checks(suite(m))) == ['G60W_W5_7y']
    check('V2 W5: 7y multiple just below 1.6^5 on each 10y BENEFIT 10M run -> G60W_W5_7y only', bool(ok))
    def m(y, mb, cr, a, e):
        if y == 10 and (a == bb.ACCT_1M or mb == 20):
            e['w_check'][1764] = 1.0
    check('V3 W5 reads 10M benefit runs only (1M and b20 below target -> pass)', not bad(bb.version_checks(suite(m))))
    def m(y, mb, cr, a, e):
        if y == 10 and mb == 63 and not cr and a == bb.ACCT_10M:
            e['w_check'][1764] = W5
    check('V4 W5: exactly 1.6^5 passes (>=)', not bad(bb.version_checks(suite(m))))
    ok = True
    for mb_ in (63, 252):
        def m(y, mb, cr, a, e, mb_=mb_):
            if y == 30 and mb == mb_:
                e['w_check'][3024] = lo10
        ok &= bad(bb.version_checks(suite(m))) == ['G60W_W10_12y']
    check('V5 W10: 12y multiple just below 1.6^10 on 30y b63 / b252 10M -> G60W_W10_12y only', bool(ok))
    def m(y, mb, cr, a, e):
        if y == 10:
            e['w_check'][3024] = 1.0
    check('V6 W10 reads the 30y runs only', not bad(bb.version_checks(suite(m))))
    ok = True
    for a_ in Q.ACCTS:
        def m(y, mb, cr, a, e, a_=a_):
            if y == 10 and mb == 63 and cr and a == a_:
                e['strategy']['mdd_median'] = QM['mdd_median'] - 0.001
        ok &= bad(bb.version_checks(suite(m))) == ['GMKT_b_crisis_mdd_median']
    def m(y, mb, cr, a, e):
        if y == 10 and mb == 63 and cr:
            e['strategy']['mdd_median'] = QM['mdd_median']
        if not (y == 10 and mb == 63 and cr):
            e['strategy']['mdd_median'] = -0.99
    check('V7 G-MKT (b): crisis mdd_median worse than QQQM on either account -> fail; equal passes; other runs not read',
          bool(ok) and not bad(bb.version_checks(suite(m))))
    def m(y, mb, cr, a, e):
        if y == 30 and mb == 63:
            e['strategy']['p_ruin_80'] = 0.001
            e['bench']['QQQM_100']['p_ruin_80'] = 0.0
    check('V8 D2: 30y b63 P(-80%) above QQQM -> blackbox_D2 False', 'blackbox_D2' in bad(bb.version_checks(suite(m))))
    def m(y, mb, cr, a, e):
        if y == 10 and mb == 63 and cr and a == bb.ACCT_1M:
            e['strategy']['mdd_p95_worst'] = -0.61
    b8 = bad(bb.version_checks(suite(m)))
    check('V9 G-MKT (a) == R2 (crisis 1M MDD95 worse than QQQM)', 'GMKT_a_R2' in b8 and 'R2_mdd95_ge_QQQM' in b8)
    vo = bb.verdict_of
    check('V10 verdict names: none -> PENDING; G60W / GMKT only -> Q60 미달; G4_dev only -> REJECT (lab); any Q -> REJECT',
          vo([]) == bb.PENDING_LABEL and vo(['own_KRWX:G60W_W5_7y']) == bb.Q60_MISS
          and vo(['real:GMKT_c_real_episodes', 'common_DEXKOUS:GMKT_b_crisis_mdd_median']) == bb.Q60_MISS
          and vo(['real:G4_dev']) == bb.REJECT_LAB and vo(['real:G4_dev', 'own_KRWX:G60W_W5_7y']) == bb.REJECT_LAB
          and vo(['real:G4_dev', 'own_KRWX:Q1_median_ge_max(QLD,QQQM+3pp)']) == 'REJECT'
          and vo(['real:causality']) == 'REJECT' and vo(['own_KRWX:blackbox_D2']) == 'REJECT')
    # episodes: 100 -> 75 -> 92 (+22.7%) -> 50 -> 110: ATH gives (0 -> 50); local 20%/20% gives (0 -> 75), (92 -> 50);
    # peak-to-low-before-regain gives (0 -> 50)
    seg = lambda a, b, n: np.linspace(a, b, n + 1)[1:]
    qc = np.r_[100.0, seg(100, 75, 20), seg(75, 92, 10), seg(92, 50, 30), seg(50, 110, 40)]
    i75, i92, i50 = 20, 30, 60
    check('E1 episodes ATH reading', bb._episodes_ath(qc) == [(0, i50)], str(bb._episodes_ath(qc)))
    check('E2 episodes local-peak reading', bb._episodes_local(qc) == [(0, i75), (i92, i50)], str(bb._episodes_local(qc)))
    check('E3 episodes union (A49-2(c) list)', bb._episodes(qc) == [(0, i75), (0, i50), (i92, i50)], str(bb._episodes(qc)))
    qc2 = np.r_[100.0, seg(100, 85, 10), seg(85, 100, 10), seg(100, 81, 10), seg(81, 120, 10)]
    check('E4 falls of -15% / -19% are not episodes', bb._episodes(qc2) == [])
    # causality: a look-ahead masked to Tue/Wed (cannot be written in the DSL any more) is caught at random cuts
    c = bb.LabCandidate(F2_SPEC)
    pm = bb.boot_paths(c, n=1)[0]

    class Peek:
        def __init__(self, k):
            self.k = k

        def build(self, pm):
            q = pm.C['QQQ']
            ref = np.r_[q[self.k:], np.full(self.k, np.nan)] if self.k > 0 else np.r_[np.full(-self.k, np.nan), q[:self.k]]
            wd = pm.dates.weekday.values
            return (((ref > q) & ((wd == 1) | (wd == 2))).astype(float) * 0.88)[:, None]
    okp, badp, seedp = bb.causality(Peek(1), pm)
    okh, badh, _ = bb.causality(Peek(-1), pm)
    check('C1 causality: weekday-masked 1-day look-ahead caught at random cuts; the lagged version passes',
          not okp and okh, f'{len(badp)} violations, seed {seedp}')


def test_pool():
    print('== (f) process pool plumbing (d6l runs run_w in forked workers) ==')
    import pickle
    from concurrent.futures import ProcessPoolExecutor
    c = bb.LabCandidate(dsl.load_spec(LAB + '/specs/qld_088_hold.yaml'))
    pickle.dumps((c, bb.run_w))
    kws = [dict(RUN, n_paths=12, base='bb2'), dict(RUN, n_paths=12, base='common', mean_block=252, seed=10252)]
    with ProcessPoolExecutor(2) as ex:
        par = list(ex.map(_pool_one, [(c, k) for k in kws]))
    ser = [_pool_one((c, k)) for k in kws]
    ok = all(same(a, b)[0] and a['w_check'] == b['w_check'] for a, b in zip(par, ser))
    check('pool: run_w in worker processes == in-process (pickles, w_check comes back)', ok)


def _pool_one(a):
    c, kw = a
    return bb.run_w(c, **kw)


if __name__ == '__main__':
    t0 = time.time()
    test_dsl()
    test_f1()
    test_f3()
    test_f2()
    test_seal()
    test_pool()
    test_verdict()
    print(f'FAILS: {FAILS or "none"}  ({time.time() - t0:.0f}s)')
    sys.exit(1 if FAILS else 0)
