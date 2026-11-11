"""XV1 sealed block evaluator, version 2 (see PREREG_XV1_STRUCTURE.md).

Accounts
  stage A   one continuous account 1986-01-02 .. 2015-12-31 on the calendar CUT at 2015-12-31 (no later row is passed to
            candidate code or to the engine). It scores blocks 0-9.
  own       blocks 10-13 each have their own account for candidate and reference: started on the block's first trading day
            with equity 1 in cash, no position, no tax basis, empty brake memory, zero tax deduction; the ov.WARM rows before
            the block are engine warm-up (only the signal and feature rows are read there). Blocks 11 and 13 are DESIGN.
            Blocks 10 and 12 are SEALED: they are run only inside open_g3().
Score       V = liquidation value of the account (equity minus 22% tax on every realised and unrealised gain not yet taxed);
            x_k = ln(V_k / V_{k-1}) on scored rows (row rank inside its block >= 63).
Outputs     scalars per non-sealed block and per registered set only. No equity level, peak, cumulative figure or array ever
            leaves this module (design-block sub-block means of paired differences are the one exception: they are design
            material and are needed for the family-wise test).
Candidate   make(view) -> dict(B, bfn, bp, fstep[, G, Wt, mode, inc, RB, up, dn]); view.c is the ov.Ctx of the calendar rows, view.x the
            registered extra inputs aligned to those rows. Nothing else may be read (no dates, no row numbers, no files, no
            module-level arrays). The evaluator sets every engine term."""
import os, sys, json, time, hashlib, contextlib, importlib.util
import numpy as np, pandas as pd
from scipy import stats as sps
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_xv1')   # own cache: the shared one collides with other sessions
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std
from std import jp, ov, bk, beng, rx
import mkt, md
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xeng, xdata

CAL_START, ACC_START, CAL_END = '1984-01-03', '1986-01-02', '2026-08-31'
A_END, OLD_END = '2015-12-31', '2014-12-31'
Y0, BLEN, EMB, NB = 1986, 3, 63, 14
SEALED = (10, 12)                      # 2016-18, 2022-24
OWN = (10, 11, 12, 13)                 # blocks with their own account
ACTIVE_MIN = 20                        # active rows that make an active block
FAM_CORR = 0.7                         # |correlation| of design sub-block means at or above which two configurations are one family
DESIGN = (1, 3, 5, 7, 9, 11, 13)
WEAK = (0, 2, 4, 6, 8)
ENGINE = dict(cspr=10.0)               # idle cash earns nothing (owner rule 2026-11-11); everything else = beng.F1
STRESS = dict(base={}, cost2=dict(cost=0.006), delay3=dict(delay=3), delay1=dict(delay=1), tax0=dict(tax=0.0))
G1_STRESS = ('cost2', 'delay3', 'delay1', 'tax0')
OUT = '/mnt/project-files/research/xv1/'
WARM = ov.WARM
assert WARM == xeng.WARM == beng.WARM


def kind_of(b):
    """'D' design, 'W' weak validation (<= 2014, already seen), 'S' sealed."""
    if b % 2 == 1: return 'D'
    return 'S' if b in SEALED else 'W'


def years_of(b): return '%d-%02d' % (Y0 + BLEN * b, (Y0 + BLEN * b + BLEN - 1) % 100)


# ------------------------------------------------------------------------------------------------ calendar and views
_FR = {}
def frame(end=CAL_END):
    """X of the MS1 real-path chain on the calendar rows CAL_START..end."""
    if end not in _FR:
        R, M = jp.calendar(CAL_START, end); _FR[end] = jp.mkX(R, M, 'NDX')
    return _FR[end]


def extras(names, idx):
    """registered extra inputs as full-length arrays aligned to the calendar idx."""
    return {k: np.asarray(xdata.get(k, idx), dtype=np.float64) for k in names}


class View:
    """What candidate code may read: c (ov.Ctx, P = 1), m (the macro levels y10, y3m, cs of the REF chain) and x (dict of
    registered extra inputs), all on the same T rows (WARM warm-up rows, then the account days). The calendar position
    (c.ii) and the dates are removed on purpose."""
    def __init__(s, X, extra=None):
        i0 = int(X.index.searchsorted(pd.Timestamp(ACC_START))) - WARM
        s.c = ov.Ctx(X, ov.flags_hist(X), np.arange(i0, len(X))[None, :]); s.c.ii = None
        s.T = s.c.T
        s.x = {k: np.ascontiguousarray(v[i0:len(X)]) for k, v in (extra or {}).items()}
        s.m = {k: np.ascontiguousarray(X[k].values[i0:len(X)], dtype=np.float64) for k in ('y10', 'y3m', 'cs')}   # macro levels of the REF chain
        s._feat = None; s._shadow = None

    @property
    def feat(s):
        if s._feat is None: s._feat = np.ascontiguousarray(bk.features(s.c)[0])
        return s._feat

    def _sh(s):
        """v1 alone in one continuous shadow account over the view rows (level paths only; warm-up rows are 0)"""
        if s._shadow is None:
            m = _call(ref, s); rec = _run(s, m, 0, s.T)
            pad = lambda a: np.ascontiguousarray(np.r_[np.zeros(WARM), a])
            s._shadow = (pad(rec[:, 2]), pad(np.maximum(rec[:, 1], 0.0)))
        return s._shadow

    @property
    def ref_target(s):
        """level v1 wants after its brake, decided at the close of row t (in force two rows later)"""
        return s._sh()[0]

    @property
    def ref_held(s):
        """level v1 actually holds on row t"""
        return s._sh()[1]


def acc_dates(X):
    i0 = int(X.index.searchsorted(pd.Timestamp(ACC_START))) - WARM
    return X.index[i0 + WARM:]


BLOCK_TABLE = (  # (b, first row, first scored row, last row, rows): part of the registered text, from the calendar dates only
    (0, '1986-01-02', '1986-04-03', '1988-12-30', 759), (1, '1989-01-03', '1989-04-04', '1991-12-31', 758),
    (2, '1992-01-02', '1992-04-01', '1994-12-30', 759), (3, '1995-01-03', '1995-04-03', '1997-12-31', 759),
    (4, '1998-01-02', '1998-04-03', '2000-12-29', 756), (5, '2001-01-02', '2001-04-03', '2003-12-31', 752),
    (6, '2004-01-02', '2004-04-02', '2006-12-29', 755), (7, '2007-01-03', '2007-04-04', '2009-12-31', 756),
    (8, '2010-01-04', '2010-04-06', '2012-12-31', 754), (9, '2013-01-02', '2013-04-04', '2015-12-31', 756),
    (10, '2016-01-04', '2016-04-05', '2018-12-31', 754), (11, '2019-01-02', '2019-04-03', '2021-12-31', 757),
    (12, '2022-01-03', '2022-04-04', '2024-12-31', 753), (13, '2025-01-02', '2025-04-04', '2026-08-31', 416))


def check_calendar(cal, upto=NB):
    """stop if the calendar does not reproduce the registered block table (blocks 0 .. upto-1)"""
    got = {r['b']: (r['first'], r['first_scored'], r['last'], r['rows']) for r in cal.table()}
    for b, f, fs, l, n in BLOCK_TABLE[:upto]:
        if got.get(b) != (f, fs, l, n): raise RuntimeError('calendar does not match the registered block table at block %d' % b)


class Cal:
    """block calendar of the account days"""
    def __init__(s, dates):
        s.dates = dates; s.n = len(dates)
        s.blk = ((dates.year - Y0) // BLEN).astype(int)
        first = np.r_[True, s.blk[1:] != s.blk[:-1]]
        start = np.maximum.accumulate(np.where(first, np.arange(s.n), 0))
        s.rank = np.arange(s.n) - start              # 0-based trading-day number inside the block
        s.scored = s.rank >= EMB                     # the first EMB rows of every block are not scored

    def rows(s, b): return np.flatnonzero(s.blk == b)

    def table(s):
        """block boundaries: dates and counts only"""
        out = []
        for b in range(NB):
            r = s.rows(b)
            if not len(r): continue
            out.append(dict(b=b, kind=kind_of(b), years=years_of(b), first=str(s.dates[r[0]].date()),
                            first_scored=str(s.dates[r[min(EMB, len(r) - 1)]].date()), last=str(s.dates[r[-1]].date()),
                            rows=int(len(r)), scored=int(max(len(r) - EMB, 0))))
        return out


# ------------------------------------------------------------------------------------------------ candidates
def ref(v):
    B, bfn, bp, fs = std.s085(v.c); return dict(B=np.ascontiguousarray(np.asarray(B, dtype=np.float64).reshape(-1)), bfn=bfn, bp=bp, fstep=fs)


def hold3(v): return dict(B=np.full(v.T, 3.0), bfn=std.ident, bp=np.zeros(1), fstep=0.5)


def hold1(v):
    """1x index hold (0.2%/yr cost) as one extra instrument at constant weight 1: bought once, never rebalanced, taxed like the rest."""
    g = v.c.r[0] - 0.002 / 252
    return dict(B=np.zeros(v.T), bfn=std.ident, bp=np.zeros(1), fstep=0.5, G=g[:, None], Wt=np.ones((v.T, 1)), mode=1, inc=0)


def _deny(*a, **k): raise PermissionError('a data reader was called from candidate code')


@contextlib.contextmanager
def _sandbox():
    """while candidate code runs: output streams closed, data readers replaced by functions that raise"""
    spots = [(mkt, '_panel'), (mkt, 'fred'), (md, 'load'), (jp, 'calendar'), (jp, 'build'), (np, 'load'), (np, 'save')]
    old = [getattr(o, n) for o, n in spots]
    with open(os.devnull, 'w') as nul, contextlib.redirect_stdout(nul), contextlib.redirect_stderr(nul):
        for o, n in spots: setattr(o, n, _deny)
        try: yield
        finally:
            for (o, n), f in zip(spots, old): setattr(o, n, f)


def _call(make, v):
    """run candidate code inside the sandbox and normalise what it returns"""
    with _sandbox(): m = make(v)
    T = v.T
    o = dict(B=np.ascontiguousarray(np.asarray(m['B'], dtype=np.float64).reshape(-1)), bfn=m['bfn'],
             bp=np.asarray(m['bp'], dtype=np.float64), fstep=float(m['fstep']), mode=int(m.get('mode', 0)), inc=int(m.get('inc', 0)))
    assert len(o['B']) == T
    G, W = m.get('G'), m.get('Wt')
    if G is None: G = np.zeros((T, 1)); W = np.zeros((T, 1))
    G = np.asarray(G, dtype=np.float64).reshape(T, -1); W = np.asarray(W, dtype=np.float64).reshape(T, -1)
    assert G.shape == W.shape
    W = np.nan_to_num(W, nan=0.0); J = G.shape[1]
    RB = m.get('RB'); RB = np.zeros((T, J)) if RB is None else np.nan_to_num(np.asarray(RB, dtype=np.float64).reshape(T, J))
    o['RB'] = np.ascontiguousarray(RB)
    o['up'] = np.full(J, xeng.OFF) if m.get('up') is None else np.asarray(m['up'], dtype=np.float64).reshape(J)
    o['dn'] = np.full(J, xeng.OFF) if m.get('dn') is None else np.asarray(m['dn'], dtype=np.float64).reshape(J)
    for j in range(G.shape[1]):                         # a weight may never rest on an instrument that does not exist yet
        bad = np.isnan(G[:, j])
        if bad.any():
            on = (W[:, j] != 0).astype(float); held = np.convolve(on, np.ones(5), 'full')[:T] > 0
            if (held & bad).any(): raise ValueError('weight on a missing instrument')
    o['G'] = np.ascontiguousarray(np.nan_to_num(G, nan=0.0)); o['Wt'] = np.ascontiguousarray(W)
    return o


def _run(v, m, a, b, own=False, **stress):
    k = dict(ENGINE); k.update(stress); k['fstep'] = m['fstep']
    if own: k['W0'] = None                             # zero deduction for a block account (conservative, scale-free)
    return xeng.run(v.c.r[0][a:b], v.c.rf[0][a:b], m['B'][a:b], v.feat[a:b], m['bfn'], m['bp'], G=m['G'][a:b], Wt=m['Wt'][a:b],
                    mode=m['mode'], inc=m['inc'], RB=m['RB'][a:b], up=m['up'], dn=m['dn'], **k)


def _x(V):
    x = np.full(len(V), np.nan); x[1:] = np.log(V[1:] / V[:-1]); return x


# ------------------------------------------------------------------------------------------------ accounts (internal)
def _stage_a(make, names=(), **stress):
    """blocks 0-9 from one continuous account on the calendar cut at 2015-12-31"""
    X = frame(A_END); v = View(X, extras(names, X.index)); m = _call(make, v); cal = Cal(acc_dates(X))
    if A_END == '2015-12-31': check_calendar(cal, 10)
    rec = _run(v, m, 0, v.T, **stress); x = _x(rec[:, 4]); out = {}
    for b in range(10):
        r = cal.rows(b); sc = r[cal.rank[r] >= EMB]
        out[b] = dict(x=x[sc], lev=rec[sc, 1], w=rec[sc, 5], date=cal.dates[sc])
    return out


_G3 = object()
def _own(make, names, blocks, _token=None, **stress):
    """blocks with their own account. Sealed blocks need the token that only open_g3() holds."""
    for b in blocks:
        if b not in OWN: raise ValueError('not an own-account block')
        if b in SEALED and _token is not _G3: raise PermissionError('sealed block')
    X = frame(CAL_END); v = View(X, extras(names, X.index)); m = _call(make, v); cal = Cal(acc_dates(X)); check_calendar(cal)
    return {b: _block_account(v, m, cal, b, **stress) for b in blocks}


def _block_account(v, m, cal, b, **stress):
    """own account of block b: view row = account day + WARM, so the WARM view rows before the block are the engine warm-up"""
    r = cal.rows(b); p0, p1 = int(r[0]), int(r[-1])
    rec = _run(v, m, p0, p1 + WARM + 1, own=True, **stress)
    x = _x(rec[:, 4]); sc = np.arange(EMB, len(r))
    return dict(x=x[sc], lev=rec[sc, 1], w=rec[sc, 5], date=cal.dates[r][sc])


def _open_blocks(make, names=(), **stress):
    """all non-sealed blocks: 0-9 (stage A) + 11, 13 (own accounts)"""
    o = _stage_a(make, names, **stress); o.update(_own(make, names, (11, 13), **stress)); return o


# ------------------------------------------------------------------------------------------------ statistics
def ann(xs):
    """annualised log growth of a list of per-block arrays (days pooled)"""
    n = sum(len(x) for x in xs)
    return float(252.0 * sum(float(np.sum(x)) for x in xs) / n) if n else float('nan')


def sub_means(d, L):
    """means of consecutive sub-blocks of L rows; leftover rows join the last sub-block"""
    k = max(len(d) // L, 1); j = np.minimum(np.arange(len(d)) // L, k - 1)
    return np.bincount(j, weights=d, minlength=k) / np.bincount(j, minlength=k)


def test_t(ds, L):
    """test T: one-sided Student t on the sub-block means of the paired daily differences (sub-blocks stay inside a calendar block)"""
    m = np.concatenate([sub_means(d, L) for d in ds if len(d)]); k = len(m)
    sd = float(m.std(ddof=1)) if k > 1 else 0.0
    if sd <= 0: return 0.0, 1.0, k, float(m.mean()), 0.0
    se = sd / np.sqrt(k); t = float(m.mean() / se)
    return t, float(sps.t.sf(t, k - 1)), k, float(m.mean()), se


def p_t(ds): return max(test_t(ds, 63)[1], test_t(ds, 126)[1])


def ci90(ds):
    """two-sided 90% interval of the annualised paired difference (the wider of L = 63 and 126)"""
    best = None
    for L in (63, 126):
        t, p, k, mu, se = test_t(ds, L); h = float(sps.t.ppf(0.95, k - 1)) * se if k > 1 else float('inf')
        c = (252 * (mu - h), 252 * (mu + h))
        if best is None or c[1] - c[0] > best[1] - best[0]: best = c
    return [float(best[0]), float(best[1])]


def te_of(ds):
    d = np.concatenate([x for x in ds if len(x)])
    return float(np.sqrt(252.0) * d.std(ddof=1)) if len(d) > 1 else 0.0


def max_t(M, draws=20000, seed=0):
    """family-wise adjusted p-values (single-step max-t, sign flips of whole sub-blocks, common to all configurations).
    M (k, N): sub-block means of the paired differences of N configurations on the same k design sub-blocks."""
    k, N = M.shape; ssq = (M * M).sum(0)
    def tt(mu):
        var = (ssq - k * mu * mu) / (k - 1); ok = var > 0
        return np.where(ok, mu / np.sqrt(np.where(ok, var, 1.0) / k), 0.0)
    t0 = tt(M.mean(0)); g = np.random.default_rng(seed); cnt = np.zeros(N); done = 0
    while done < draws:
        c = min(2000, draws - done); S = g.integers(0, 2, (c, k)) * 2.0 - 1.0
        mx = tt(S @ M / k).max(1)
        cnt += (mx[None, :] >= t0[:, None]).sum(1); done += c
    return t0, (1 + cnt) / (draws + 1)


# ------------------------------------------------------------------------------------------------ public measurements
_REF = {}
def _ref_blocks(stress='base'):
    if stress not in _REF: _REF[stress] = _open_blocks(ref, (), **STRESS[stress])
    return _REF[stress]


def _levels(o):
    lv = o['lev']; u, n = np.unique(np.round(lv, 2), return_counts=True)
    return dict(share={('%.1f' % a): round(float(c) / len(lv), 4) for a, c in zip(u, n)}, changes=int(np.sum(lv[1:] != lv[:-1])),
                mean_level=round(float(lv.mean()), 4), dd_inblock=round(float(np.expm1(_dd(o['x']))), 4))


def _dd(x):
    """largest drawdown of the curve re-based to 1 on the first scored row of the block"""
    c = np.cumsum(x); return float(np.min(c - np.maximum.accumulate(np.r_[0.0, c])[1:])) if len(c) else 0.0


def reference_table():
    """first measurement: v1, 1x hold and 3x hold on every DESIGN and WEAK block. Scalars only."""
    R = _ref_blocks(); H1 = _open_blocks(hold1); H3 = _open_blocks(hold3); rows = []
    R0 = _ref_blocks('tax0'); H10 = _open_blocks(hold1, **STRESS['tax0']); H30 = _open_blocks(hold3, **STRESS['tax0'])
    for b in sorted(R):
        r = dict(b=b, years=years_of(b), kind=kind_of(b), account='own' if b in OWN else 'continuous', n=int(len(R[b]['x'])),
                 v1=ann([R[b]['x']]), hold1=ann([H1[b]['x']]), hold3=ann([H3[b]['x']]))
        r.update(_levels(R[b])); rows.append(r)
    sets = {}
    post = lambda o, b: o[b]['x'][o[b]['date'] >= pd.Timestamp('2015-01-01')]
    for nm, bl, f in (('design', DESIGN, None), ('weak', WEAK, None), ('design_post2014', (9, 11, 13), post)):
        g = lambda o: [f(o, b) if f else o[b]['x'] for b in bl]
        a, h1, h3 = g(R), g(H1), g(H3)
        dA = [x - y for x, y in zip(a, h3)]; dB = [x - y for x, y in zip(a, h1)]
        a0, h10, h30 = g(R0), g(H10), g(H30)
        dA0 = [x - y for x, y in zip(a0, h30)]; dB0 = [x - y for x, y in zip(a0, h10)]
        sets[nm] = dict(n=int(sum(len(x) for x in a)), v1=ann(a), hold1=ann(h1), hold3=ann(h3),
                        D_A_v1_minus_3x=dict(d=ann(dA), ci90=ci90(dA)), D_B_v1_minus_1x=dict(d=ann(dB), ci90=ci90(dB)),
                        tax0=dict(v1=ann(a0), hold1=ann(h10), hold3=ann(h30),
                                  D_A_v1_minus_3x=dict(d=ann(dA0), ci90=ci90(dA0)), D_B_v1_minus_1x=dict(d=ann(dB0), ci90=ci90(dB0))))
    return dict(blocks=rows, sets=sets)


def model_check():
    """modelled 3x fund against the actual TQQQ on the scored rows of non-sealed blocks where the fund exists. Scalars only."""
    X = frame(CAL_END); idx = X.index; cal = Cal(acc_dates(X)); i0 = len(idx) - cal.n
    a = xdata.get('ret:TQQQ', idx)[i0:]; r = X['r'].values[i0:]; rf = X['rf'].values[i0:]
    m = 3 * r - 2 * rf - beng.F1['er3'] / 252; out = []
    for b in range(NB):
        if b in SEALED: continue
        rr = cal.rows(b); sc = rr[cal.rank[rr] >= EMB]
        if not len(sc) or np.isnan(a[sc]).all(): continue
        miss = int(np.isnan(a[sc]).sum()); big = int(np.nansum(np.abs(a[sc] - m[sc]) > 0.05))
        ok = miss == 0 and big == 0
        gap = float(252 * np.mean(np.log1p(a[sc]) - np.log1p(m[sc]))) if ok else None
        out.append(dict(b=b, years=years_of(b), n=int(len(sc)), rows_without_fund=miss, rows_gap_over_5pp=big, gap_actual_minus_model=gap))
    return out


# ------------------------------------------------------------------------------------------------ configurations, batches, gates
_MOD = {}
class Config:
    """one configuration = candidate source file + function + parameter values + registered inputs + T0"""
    def __init__(s, family, name, file, func, params=None, names=(), t0=None, **_):
        s.family, s.name, s.file, s.func = family, name, os.path.realpath(file), func
        s.params = dict(params or {}); s.names = tuple(names); s.t0 = t0

    @property
    def hash(s):
        body = json.dumps(dict(func=s.func, params=s.params, names=list(s.names), t0=s.t0), sort_keys=True)
        return hashlib.sha256(open(s.file, 'rb').read() + body.encode()).hexdigest()

    def make(s, v):
        if s.file not in _MOD:
            sp = importlib.util.spec_from_file_location('xv1cand_' + hashlib.sha256(s.file.encode()).hexdigest()[:8], s.file)
            m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); _MOD[s.file] = m
        return getattr(_MOD[s.file], s.func)(v, **s.params)

    def to_dict(s):
        return dict(family=s.family, name=s.name, file=s.file, func=s.func, params=s.params, names=list(s.names), t0=s.t0, hash=s.hash)


def register_batch(k, configs):
    """write the batch file and its ledger line. Must happen before any configuration of the batch is scored."""
    os.makedirs(OUT, exist_ok=True); path = OUT + 'BATCH_%d.json' % k
    if os.path.exists(path): raise FileExistsError(path)
    if len(set(c.hash for c in configs)) != len(configs): raise ValueError('duplicate configuration')
    body = json.dumps([c.to_dict() for c in configs], indent=1, sort_keys=True)
    with open(path, 'w') as f: f.write(body)
    sha = hashlib.sha256(body.encode()).hexdigest()
    ledger(dict(kind='batch', batch=k, sha256=sha, n=len(configs)))
    return sha


def load_batch(k):
    body = open(OUT + 'BATCH_%d.json' % k).read(); sha = hashlib.sha256(body.encode()).hexdigest()
    if not any(e.get('kind') == 'batch' and e.get('batch') == k and e.get('sha256') == sha for e in read_ledger()):
        raise PermissionError('batch %d is not registered with this content' % k)
    cfgs = [Config(**d) for d in json.loads(body)]
    for c, d in zip(cfgs, json.loads(body)):
        if c.hash != d['hash']: raise PermissionError('configuration %s changed after registration' % d['name'])
    return cfgs, sha


def _paired(cand, refb, blocks, t0=None):
    ds = []
    for b in blocks:
        d = cand[b]['x'] - refb[b]['x']
        if t0 is not None: d = d[cand[b]['date'] >= pd.Timestamp(t0)]
        ds.append(d)
    return ds


def _active(cand, refb, blocks, t0=None):
    """active rows per block: scored rows on or after T0 on which the candidate holds a different level than the reference
    or holds an extra instrument (a non-zero paired difference alone does not count: after the first divergence the two
    accounts differ slightly on every row)"""
    out = []
    for b in blocks:
        a = (cand[b]['lev'] != refb[b]['lev']) | (cand[b]['w'] != 0) | (refb[b]['w'] != 0)
        if t0 is not None: a = a[cand[b]['date'] >= pd.Timestamp(t0)]
        out.append(int(np.sum(a)))
    return out


def _harm(d, active, k):
    """harm bound of one block: active block (>= 20 active rows) with d_b < -k x TE_b x sqrt(252 / n_b), TE_b from the block's own rows"""
    if active < ACTIVE_MIN or len(d) < 2: return False, 0.0
    lim = -k * te_of([d]) * np.sqrt(252.0 / len(d))
    return bool(ann([d]) < lim), float(lim)


def _gate_stats(ds, act, blocks, harm_k=2.0):
    n = int(sum(len(d) for d in ds)); rows = []; harm = False
    for b, d, a in zip(blocks, ds, act):
        if not len(d): continue
        h, lim = _harm(d, a, harm_k); harm |= h
        rows.append(dict(b=b, n=int(len(d)), active=a, d=ann([d]), te=te_of([d]), harm_limit=lim, harm=h))
    return dict(n=n, d=ann(ds), te=te_of(ds), t63=test_t(ds, 63)[0], p=p_t(ds), active_days=int(sum(act)),
                active_blocks=int(sum(a >= ACTIVE_MIN for a in act)), harm=harm, blocks=rows)


def _corr(a, b):
    """|correlation| of two vectors of design sub-block means (0 when one of them is constant)"""
    if np.std(a) == 0 or np.std(b) == 0: return 0.0
    return abs(float(np.corrcoef(a, b)[0, 1]))


def _sub_of(h):
    """design sub-block means of a scored configuration, from the batch result files"""
    k = 1
    while os.path.exists(OUT + 'results/batch_%d.json' % k):
        sm = json.load(open(OUT + 'results/batch_%d.json' % k))['sub_means']
        if h in sm: return np.asarray(sm[h])
        k += 1
    raise PermissionError('no design sub-block means for this configuration')


def _pre_t0(C, R, t0):
    """before T0 the candidate must equal the reference exactly"""
    if t0 is None: return 0
    return sum(int(np.sum((C[b]['x'] - R[b]['x'])[C[b]['date'] < pd.Timestamp(t0)] != 0)) for b in C)


def _design(c, stress=True):
    """G1 material of one configuration on D7 (scalars) and its L = 63 sub-block means (design material)"""
    C = _open_blocks(c.make, c.names); R = _ref_blocks()
    if _pre_t0(C, R, c.t0): return dict(void='differs from the reference before T0'), None
    ds = _paired(C, R, DESIGN, c.t0); o = _gate_stats(ds, _active(C, R, DESIGN, c.t0), DESIGN)
    o['cand'] = ann([C[b]['x'] for b in DESIGN]); o['ref'] = ann([R[b]['x'] for b in DESIGN])
    o['extra_weight_mean'] = float(np.mean(np.concatenate([C[b]['w'] for b in DESIGN])))
    o['level_mean'] = float(np.mean(np.concatenate([C[b]['lev'] for b in DESIGN])))
    if stress:
        for sname in G1_STRESS:
            Cs = _open_blocks(c.make, c.names, **STRESS[sname]); o['d_' + sname] = ann(_paired(Cs, _ref_blocks(sname), DESIGN, c.t0))
    sub = np.concatenate([sub_means(d, 63) for d in _paired(C, R, DESIGN, None)])   # rows before T0 are exactly 0 (checked above)
    return o, sub


def run_batch(k, stress=True):
    """score every configuration of registered batch k on D7 and apply G1. Scalars only (plus the design sub-block means)."""
    cfgs, sha = load_batch(k); alpha = 0.05 / 2 ** k; seed = int(sha[:8], 16); res = {}; subs = {}
    raw = raw_extras_test([n for c in cfgs for n in c.names], seed=seed)
    for c in cfgs:
        h = c.hash; ledger(dict(kind='score', cfg=h, set='design', batch=k))
        if any(n in raw['failed'] for n in c.names): res[h] = dict(void='raw-level test of an extra input'); res[h].update(family=c.family, name=c.name); continue
        pt = prefix_test(c.make, c.names, n_rand=60, seed=seed)
        if pt['result'] != 'PASS': res[h] = dict(void='prefix test', prefix=pt)
        else:
            o, sub = _design(c, stress); o['prefix'] = pt; res[h] = o
            if sub is not None: subs[h] = sub
        res[h].update(family=c.family, name=c.name)
    live = list(subs)
    if live:
        t0, pf = max_t(np.stack([subs[h] for h in live], axis=1), 20000, seed)
        for h, a, b in zip(live, t0, pf): res[h].update(t63_family=float(a), p_family=float(b))
    for h in live:
        o = res[h]
        o['g1'] = dict(a=bool(o['d'] > 0 and o['active_blocks'] >= 3 and o['n'] >= 1500), b=bool(not o['harm']), c=bool(o['p_family'] <= alpha),
                       d=bool(all(o['d_' + sn] > 0 for sn in G1_STRESS)) if stress else None)
        o['g1_pass'] = all(v for v in o['g1'].values() if v is not None) and stress
    key = lambda h: (res[h]['p_family'], -res[h]['t63_family'], h)
    adv = []                                             # at most one configuration per family goes on
    for h in sorted([h for h in live if res[h]['g1_pass']], key=key):
        if all(res[g]['family'] != res[h]['family'] and _corr(subs[g], subs[h]) < FAM_CORR for g in adv): adv.append(h)
    for h in res:
        res[h]['advance'] = h in adv
        ledger(dict(kind='g1', cfg=h, batch=k, passed=bool(res[h].get('g1_pass', False)), advance=res[h]['advance']))
    out = dict(batch=k, sha256=sha, alpha=alpha, n=len(cfgs), raw_extras_test=raw, results=res, sub_means={h: [float(x) for x in subs[h]] for h in live})
    os.makedirs(OUT + 'results', exist_ok=True); json.dump(out, open(OUT + 'results/batch_%d.json' % k, 'w'), indent=1)
    return out


def weak_eval(c):
    """G2 (old-data no-harm check) on W5: only for a configuration that passed G1 and was selected, and only once."""
    h = c.hash; L = read_ledger()
    if not any(e.get('kind') == 'g1' and e.get('cfg') == h and e.get('passed') and e.get('advance') for e in L):
        raise PermissionError('no G1 pass for this configuration')
    if any(e.get('kind') == 'score' and e.get('cfg') == h and e.get('set') == 'weak' for e in L):
        raise PermissionError('weak blocks already read for this configuration')
    ledger(dict(kind='score', cfg=h, set='weak'))
    C = _open_blocks(c.make, c.names); R = _ref_blocks()
    o = _gate_stats(_paired(C, R, WEAK, c.t0), _active(C, R, WEAK, c.t0), WEAK)
    o['g2_pass'] = bool(o['d'] > 0 and not o['harm'])
    ledger(dict(kind='g2', cfg=h, passed=o['g2_pass']))
    return o


def authorise_g3(c, owner_message_id):
    """record the owner's authorisation of a G3 opening (the id of the owner's own message)"""
    ledger(dict(kind='owner-auth', cfg=c.hash, message=owner_message_id))


def open_g3(c):
    """one G3 opening: blocks 10 and 12 from their own accounts. Output: one word."""
    h = c.hash; L = read_ledger()
    reg = json.load(open(OUT + 'HASHES.json')); now = env_hashes()
    if any(now['data'].get(k) != v for k, v in reg['data'].items()) or any(now['code'].get(k) != v for k, v in reg['code'].items()):
        raise PermissionError('registered hashes changed')
    if not any(e.get('kind') == 'g1' and e.get('cfg') == h and e.get('passed') and e.get('advance') for e in L): raise PermissionError('no G1 pass')
    if not any(e.get('kind') == 'g2' and e.get('cfg') == h and e.get('passed') for e in L): raise PermissionError('no G2 pass')
    if not any(e.get('kind') == 'owner-auth' and e.get('cfg') == h for e in L): raise PermissionError('no owner authorisation')
    opened = [e['cfg'] for e in L if e.get('kind') == 'G3-OPEN']
    if any(e.get('kind') == 'G3-VERDICT' and e.get('cfg') == h for e in L): raise PermissionError('already opened')
    if h in opened:
        if opened.count(h) >= 2: raise PermissionError('retry already used')
    elif len(set(opened)) >= 3: raise PermissionError('the three openings are spent')
    C = _open_blocks(c.make, c.names); R = _ref_blocks(); te = te_of(_paired(C, R, DESIGN, c.t0))
    Xa = frame(A_END); ma = _call(c.make, View(Xa, extras(c.names, Xa.index)))
    fixed = float(np.std(np.concatenate([C[b]['lev'] for b in DESIGN]))) == 0 and float(np.ptp(ma['Wt'], axis=0).max()) == 0 and not ma['RB'].any()
    if te <= 0 or fixed: raise PermissionError('a configuration whose level does not depend on any input may not be opened')
    if h not in opened:
        mine = _sub_of(h)
        if any(_corr(mine, _sub_of(g)) >= FAM_CORR for g in set(opened)): raise PermissionError('same family as an opened configuration')
    ledger(dict(kind='G3-OPEN', cfg=h, retry=h in opened))
    Cs = _own(c.make, c.names, SEALED, _token=_G3); Rs = _own(ref, (), SEALED, _token=_G3)
    ds = _paired(Cs, Rs, SEALED, c.t0); act = _active(Cs, Rs, SEALED, c.t0); d = ann(ds)
    fail = d <= 0 or any(_harm(x, a, 1.0)[0] for x, a in zip(ds, act))
    word = 'FAIL' if fail else ('CONFIRMED' if p_t(ds) <= 0.05 / 3 else 'INCONCLUSIVE')
    ledger(dict(kind='G3-VERDICT', cfg=h, verdict=word))
    return word


# ------------------------------------------------------------------------------------------------ causality test
def _noise(X, E, r, g):
    """copy of X and of the extra inputs with every row after position r replaced by noise"""
    Xn = X.copy(); n = len(X) - r - 1
    if n <= 0: return Xn, E
    Xn.iloc[r + 1:, Xn.columns.get_loc('r')] = np.clip(g.normal(0, 0.03, n), -0.5, 0.5)
    for c in ('rf', 'y10', 'y3m', 'cs', 'vix'):
        last = Xn[c].values[r]; last = 0.0 if np.isnan(last) else last
        Xn.iloc[r + 1:, Xn.columns.get_loc(c)] = last + np.cumsum(g.normal(0, 0.1 if c != 'rf' else 1e-5, n))
    Xn['rb'] = mkt.bond10(Xn); Xn['p'] = (1 + Xn['r']).cumprod()
    En = {}
    for k, a in E.items():
        b = a.copy(); b[r + 1:] = g.normal(0, 0.05, n); En[k] = b
    return Xn, En


def _same(a, b): return int(a.shape != b.shape) if a.shape != b.shape else int(np.sum(~((a == b) | (np.isnan(a) & np.isnan(b)))))


def prefix_test(make, names=(), end=CAL_END, n_rand=60, seed=0, noise=True, step=0, n_event=200):
    """A candidate may not read anything after the row it decides on. For each cut row the calendar is (a) cut after it and
    (b) kept but filled with noise after it; signal, weights, features, level path and account path on the rows up to the cut
    must be bit-identical to the full run. Cuts: the last row of every block and n_rand drawn rows (both variants), and, with
    deletion only, every `step`-th row and the candidate's own event rows (rows on which its signal, a target weight or a
    rebalance flag changes; the row itself and the row before; at most n_event event rows, drawn with the same generator):
    a look-ahead hidden behind a threshold shows only at the rows where it acts. Returns PASS / FAIL and counts only."""
    X = frame(end); E = extras(names, X.index); v = View(X, E); m = _call(make, v); rec = _run(v, m, 0, v.T)
    i0 = len(X) - v.T; cal = Cal(acc_dates(X)); g = np.random.default_rng(seed)
    ends = set([int(cal.rows(b)[-1]) for b in range(NB) if len(cal.rows(b))][:-1])
    drawn = set(int(q) for q in g.integers(260, cal.n - 1, n_rand))
    ev = np.zeros(v.T, dtype=bool)
    for a in (m['B'][:, None], m['Wt'], m['RB']): ev[1:] |= (a[1:] != a[:-1]).any(axis=1)
    evq = np.flatnonzero(ev) - WARM; evq = evq[(evq >= 260) & (evq < cal.n - 1)]
    if len(evq) > n_event: evq = g.choice(evq, n_event, replace=False)
    events = set(int(q) for q in evq) | set(int(q) - 1 for q in evq)
    cuts = sorted(ends | drawn | events | (set(range(260, cal.n - 1, step)) if step else set()))
    cells = 0; bad = 0; ncut = 0
    for q in cuts:
        r = i0 + WARM + q                                # calendar row of the cut
        variants = [(X.iloc[:r + 1], {k: a[:r + 1] for k, a in E.items()})]
        if noise and (q in ends or q in drawn): variants.append(_noise(X, E, r, g))
        for Xc, Ec in variants:
            vc = View(Xc, Ec); mc = _call(make, vc); T = q + WARM + 1; ncut += 1
            n = _same(mc['B'][:T], m['B'][:T]) + _same(mc['G'][:T], m['G'][:T]) + _same(mc['Wt'][:T], m['Wt'][:T]) + \
                _same(mc['RB'][:T], m['RB'][:T]) + _same(mc['up'], m['up']) + _same(mc['dn'], m['dn']) + \
                _same(vc.feat[:T], v.feat[:T]) + _same(mc['bp'], m['bp']) + int(mc['fstep'] != m['fstep']) + \
                int(mc['mode'] != m['mode']) + int(mc['inc'] != m['inc'])
            rc = _run(vc, mc, 0, T)
            n += _same(rc[:, (0, 1, 4, 5)], rec[:q + 1][:, (0, 1, 4, 5)])
            cells += n; bad += int(n > 0)
    return dict(result='PASS' if bad == 0 else 'FAIL', cuts=ncut, failed_cuts=bad, differing_cells=int(cells))


def raw_extras_test(names, end=CAL_END, n_rand=12, seed=0):
    """Raw-level causality of the registered extra inputs. The raw readers behind xdata are wrapped in memory; every raw row
    dated after a cut is (a) deleted and (b) replaced by noise; the aligned arrays up to the cut must be bit-identical.
    Returns PASS / FAIL per name and counts only."""
    names = tuple(sorted(set(names)))
    if not names: return dict(result='PASS', rebuilds=0, failed={})
    X = frame(end); idx = X.index; cal = Cal(acc_dates(X)); i0 = len(idx) - cal.n; g = np.random.default_rng(seed)
    xdata._c.clear(); base = extras(names, idx)
    cuts = set([int(cal.rows(b)[-1]) for b in range(NB) if len(cal.rows(b))][:-1]) | set(int(q) for q in g.integers(260, cal.n - 1, n_rand))
    tr = set()                                           # rows around every start, end or gap of an input (where a fill could reach back)
    for k in names:
        nn = np.isnan(base[k]); t = np.flatnonzero(nn[1:] != nn[:-1]) + 1 - i0
        for o in range(-xdata.CARRY - 1, xdata.CARRY + 1): tr |= set(int(q) + o for q in t)
    tr = sorted(q for q in tr if 0 <= q < cal.n - 1)
    if len(tr) > 600: tr = [int(q) for q in g.choice(tr, 600, replace=False)]
    cuts = sorted(cuts | set(tr))
    st = dict(cut=None, mode='del', g=None)
    def perturb(s):
        c = st['cut']
        if st['mode'] == 'del': return s[s.index <= c]
        s = s.copy(); k = np.asarray(s.index > c); n = int(k.sum())
        if n and isinstance(s, pd.DataFrame): s.iloc[k, :] = st['g'].normal(0, 0.05, (n, s.shape[1]))
        elif n: s[k] = np.abs(s[~k].iloc[-1] if (~k).any() else 1.0) * np.exp(np.cumsum(st['g'].normal(0, 0.05, n)))
        return s
    o_pser, o_chips, o_kf = mkt.pser, xdata.read_chips, xdata.md.kf; bad = {k: 0 for k in names}; runs = 0
    mkt.pser = lambda k, col, f='panel_f32.npz.xz': perturb(o_pser(k, col, f)); xdata.read_chips = lambda: perturb(o_chips())
    xdata.md.kf = lambda: perturb(o_kf())
    try:
        for q in cuts:
            n = i0 + q + 1
            for mode in ('del', 'noise'):
                st.update(cut=cal.dates[q], mode=mode, g=np.random.default_rng(q)); xdata._c.clear(); got = extras(names, idx); runs += 1
                for k in names: bad[k] += int(_same(got[k][:n], base[k][:n]) > 0)
    finally:
        mkt.pser, xdata.read_chips, xdata.md.kf = o_pser, o_chips, o_kf; xdata._c.clear()
    failed = {k: v for k, v in bad.items() if v}
    return dict(result='PASS' if not failed else 'FAIL', rebuilds=runs, failed=failed)


# ------------------------------------------------------------------------------------------------ ledger and hashes
def read_ledger():
    p = OUT + 'LEDGER.jsonl'
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def ledger(entry):
    """append-only, hash-chained"""
    os.makedirs(OUT, exist_ok=True); p = OUT + 'LEDGER.jsonl'
    prev = hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16] if os.path.exists(p) else ''
    entry = dict(entry); entry['ts'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()); entry['prev'] = prev
    with open(p, 'a') as f: f.write(json.dumps(entry, ensure_ascii=False) + '\n'); f.flush(); os.fsync(f.fileno())


DATA_FILES = ['/mnt/project-files/research/data/' + f for f in (
    'panel_f32.npz.xz', 'panel_ext_f32.npz.xz', 'macro_n/raw/DBAA.csv', 'macro_n/raw/DAAA.csv', 'macro_n/raw/BAA.csv',
    'macro_n/raw/AAA.csv', 'deep_history/raw/TB3MS.csv', 'macro_regime/raw/SHILLER_ie_data_current.xls',
    'deep_history/clean/SPX_TR_daily_1927_2014.csv', 'deep_history/clean/TBILL_daily_1927_2014.csv')] + [
    '/mnt/project-files/research/c3_multi/data/kf_sel.bin.xz', '/mnt/project-files/research/c3_brake/code/agents/alt/fin_params.json', xdata.CHIPS]


def env_hashes():
    """sha256 of every data file of the chain and of every project code file loaded so far, plus package versions"""
    def h(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
    code = sorted(set(os.path.realpath(m.__file__) for m in list(sys.modules.values())
                      if getattr(m, '__file__', None) and ('/project-files/' in os.path.realpath(m.__file__) or '/research_xv1/' in os.path.realpath(m.__file__))))
    import numba, scipy
    return dict(data={p: h(p) for p in DATA_FILES}, code={p: h(p) for p in code},
                packages=dict(python=sys.version.split()[0], numpy=np.__version__, pandas=pd.__version__, numba=numba.__version__, scipy=scipy.__version__))
