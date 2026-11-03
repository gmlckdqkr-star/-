"""Tests for the v2 spec language (rotate, cross-asset functions, brake, grid, batch summary, plugin, non-resampled
inputs). Run as a script, in its own process: python -B tests/test_dsl2.py
(like tests/test_bb.py it imports lab.bb, which puts the blackbox `engine` module on sys.path).
Prints PASS/FAIL lines and identity / timing results only; dev numbers printed by the CLI checks stay <= 2014 and are
not printed here.
"""
import json, math, os, subprocess, sys, tempfile, textwrap, time
LAB = __file__.rsplit('/tests/', 1)[0]
sys.path.insert(0, LAB)
import numpy as np, pandas as pd  # noqa: E402
from lab import bb, cli, data, dsl  # noqa: E402

FAILS = []
TMP = tempfile.mkdtemp(prefix='lab_dsl2_')


def check(name, ok, extra=''):
    print(f'{"PASS" if ok else "FAIL"}  {name}{("  " + extra) if extra else ""}', flush=True)
    if not ok:
        FAILS.append(name)


def raises(fn, exc=Exception):
    try:
        fn()
    except exc:
        return True
    return False


def frame(n=1500, seed=0, cols=('_NDX', 'SPY', 'TLT', 'IEF')):
    """Synthetic price frame on a business-day calendar (DSL column names: _NDX = QQQ family, SPY, TLT, IEF)."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range('2001-01-02', periods=n)
    out = {}
    for j, c in enumerate(cols):
        mu, sd = (3e-4, 0.018) if c in ('_NDX', 'SPY') else (1e-4, 0.008)
        reg = np.where((np.arange(n) // 200) % 3 == j % 3, -2.5e-3, 0.0)         # rotating bad spells
        out[c] = 100 * np.exp(np.cumsum(rng.normal(mu, sd, n) + reg))
    return pd.DataFrame(out, index=idx)


def write(name, txt):
    p = os.path.join(TMP, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as fh:
        fh.write(textwrap.dedent(txt))
    return p


# ---------------------------------------------------------------- functions
def test_functions():
    print('== (1) cross-asset functions ==')
    F = frame()
    fn = dsl._mk(F)
    lr = lambda c: np.log(F[c]).diff()
    c1 = fn['corr']('QQQ', 'SPY', 60)
    ref = lr('_NDX').rolling(60, min_periods=60).corr(lr('SPY'))
    check('corr(QQQ, SPY, 60) == rolling corr of the underlyings\' log returns', np.allclose(c1, ref, equal_nan=True, rtol=0, atol=1e-12)
          and c1.iloc[:60].isna().all())
    z = fn['zscore']('TLT', 50)
    r = F['TLT'].rolling(50, min_periods=50)
    check('zscore(TLT, 50) == (p - mean) / std', np.allclose(z, (F['TLT'] - r.mean()) / r.std(), equal_nan=True, atol=1e-12))
    zs = fn['zscore'](fn['ret']('QQQ', 20), 100)
    check('zscore accepts a series (ret(QQQ, 20))', np.isfinite(zs.iloc[-1]))
    ev = fn['ewvol']('QQQ', 20)
    check('ewvol(QQQ, 20) == ewm(halflife 20, adjust False) std x sqrt(252)',
          np.allclose(ev, lr('_NDX').ewm(halflife=20, adjust=False, min_periods=20).std() * np.sqrt(252), equal_nan=True, atol=1e-12))
    idx = pd.bdate_range('2020-01-01', periods=10)
    c = pd.Series([0, 1, 0, 0, 1, 1, 0, 0, 0, 0], index=idx).astype(bool)
    s = dsl._mk(pd.DataFrame(index=idx))['since'](c)
    check('since(): inf before the first true, 0 on true days, days since the last true after',
          s.tolist() == [math.inf, 0, 1, 2, 0, 0, 1, 2, 3, 4])
    h = dsl._mk(pd.DataFrame(index=idx))['hold_min'](c, 3).astype(int).tolist()
    check('hold_min(c, 3): on for >= 3 days from each turn-on, then while c holds', h == [0, 1, 1, 1, 1, 1, 0, 0, 0, 0], str(h))
    c2 = pd.Series([1, 1, 1, 1, 1, 0, 1, 0, 0, 0], index=idx).astype(bool)
    h2 = dsl._mk(pd.DataFrame(index=idx))['hold_min'](c2, 2).astype(int).tolist()
    check('hold_min: a long run stays on, a short re-entry gets its minimum', h2 == [1, 1, 1, 1, 1, 0, 1, 1, 0, 0], str(h2))
    iv = fn['invvol']('QLD', ['QLD', 'TLT'], 60)
    vq = 2 * lr('_NDX').rolling(60, min_periods=60).std(); vt = lr('TLT').rolling(60, min_periods=60).std()
    check('invvol(QLD, [QLD, TLT], 60) == (1 / (2 vol_NDX)) / sum (leverage-scaled)',
          np.allclose(iv.iloc[60:], ((1 / vq) / (1 / vq + 1 / vt)).iloc[60:], atol=1e-12) and (iv.iloc[:60] == 0).all())
    s3 = fn['invvol']('QLD', ['QLD', 'SSO', 'TLT'], 60) + fn['invvol']('SSO', ['QLD', 'SSO', 'TLT'], 60) \
        + fn['invvol']('TLT', ['QLD', 'SSO', 'TLT'], 60)
    check('invvol weights over a list sum to 1', np.allclose(s3.iloc[60:], 1.0))
    A = ['QQQ', 'SPY', 'TLT']
    w = np.stack([fn['rp'](a, A, 120).values for a in A], 1)[200:]
    X = np.stack([lr(c).values for c in ('_NDX', 'SPY', 'TLT')], 1)
    C = dsl._roll_cov(X, 120)[200:]
    rc = w * np.einsum('tij,tj->ti', C, w)
    spread = np.max(np.abs(rc / rc.sum(1, keepdims=True) - 1 / 3))
    check('rp(x, [QQQ, SPY, TLT], 120): equal risk contributions, weights sum to 1', spread < 1e-6 and np.allclose(w.sum(1), 1),
          f'max |RC share - 1/3| {spread:.1e}')
    bad = ["corr(QQQ, SPY, 0) > 0", "zscore(QQQ, -5) > 0", "ewvol(QQQ, 0) > 0", "hold_min(price(QQQ) > 0, 0)",
           "invvol(QLD, [QLD, TLT], 0) > 0", "rp(QLD, [QLD, TLT], -1) > 0", "corr(QQQ, SPY, 2.5) > 0",
           "invvol(QLD, QLD, 20) > 0", "[QLD][0] > 0", "price(QQQ).shift(-1) > 0"]
    n = 0
    for e in bad:
        n += raises(lambda: dsl.compile_weights({'signals': {'up': e}, 'rules': [{'when': 'up', 'hold': {'QLD': 0.5}}]}, F, ['QLD']),
                    (ValueError, TypeError))
    check('windows <= 0 / non-integer, non-list asset arg, subscripts, attributes refused', n == len(bad), f'{n}/{len(bad)}')
    check("star(): '*' placeholder vs multiplication",
          dsl.star('ret(*, 126) * 2 + price(*)*sma(*,20)', 'QLD') == 'ret(QLD, 126) * 2 + price(QLD)*sma(QLD,20)'
          and dsl.star('corr(*, SPY, 60)', 'TLT') == 'corr(TLT, SPY, 60)')
    sp = {'signals': {'a': 'zscore(ret(QQQ, 20), 100) > 0', 'b': 'hold_min(a, 10)', 'c': 'since(a) < 5',
                      'k': 'corr(QQQ, TLT, 60) < 0', 'v': 'ewvol(QQQ, 20) < 0.3'},
          'rules': [{'when': 'b and k', 'hold': {'QLD': '0.88 * invvol(QLD, [QLD, TLT], 60)', 'TLT': '0.88 * invvol(TLT, [QLD, TLT], 60)'}},
                    {'when': 'c or v', 'hold': {'SSO': 'min(0.88, 0.2 / ewvol(SSO, 20))'}}, {'else': {'CASH': 1.0}}]}
    W = dsl.compile_weights(sp, F, ['QLD', 'TLT', 'SSO'])
    tc = dsl.truncation_check(sp, F, ['QLD', 'TLT', 'SSO'], n_cuts=8)
    check('weights may use invvol / ewvol; spec with all new functions is causal (8 random cuts)',
          W['QLD'].max() > 0 and W['SSO'].max() > 0 and tc['ok'], f"{tc['violations'][:2]}")


# ---------------------------------------------------------------- rotate
def rot_ref(F, ro):
    """Plain per-row loop of the rotate rule (reference for the vectorised dsl._rotate)."""
    fn = dsl._mk(F); idx = F.index; n = len(idx)
    A = ro['assets']; top = ro.get('top', 1 if ro.get('score') else len(A)); tot = ro.get('total', 1.0)
    wm = ro.get('weight', 'equal'); nl = ro.get('n', 60)
    ev = lambda e, a: dsl._eval(dsl.star(e, a), fn, set(data.SLEEVES) | set(F.columns))
    S = {a: (ev(ro['score'], a).reindex(idx).values if ro.get('score') else np.zeros(n)) for a in A}
    Fl = {a: (ev(ro['filter'], a).reindex(idx).fillna(False).astype(bool).values if ro.get('filter') else np.ones(n, bool))
          for a in A}
    V = {a: (dsl._lev(a) * np.log(data.price_for_signal(F, a)).diff()).rolling(nl, min_periods=nl).std().values * np.sqrt(252)
         for a in A}
    rows = dsl.reb_rows(idx, ro.get('every', 'monthly'))
    W = np.zeros((n, len(A))); fill = np.zeros(n); cur = None; dropped = set()
    for t in range(n):
        if rows[t]:
            ok = [i for i, a in enumerate(A) if Fl[a][t] and np.isfinite(S[a][t])
                  and (wm not in ('invvol', 'rp') or (np.isfinite(V[a][t]) and V[a][t] > 0))]
            ok.sort(key=lambda i: (-S[A[i]][t], i))
            pk = ok[:top]; cur = np.zeros(len(A)); dropped = set()
            if pk:
                if wm == 'equal':
                    for i in pk:
                        cur[i] = tot / top
                else:
                    raw = {i: (max(S[A[i]][t], 0.0) if wm == 'score' else 1 / V[A[i]][t]) for i in pk}
                    if sum(raw.values()) <= 0:
                        raw = {i: 1.0 for i in pk}
                    sm = sum(raw.values())
                    for i in pk:
                        cur[i] = raw[i] / sm * tot * len(pk) / top
        if cur is None:
            continue
        if ro.get('exit') == 'daily':
            for i, a in enumerate(A):
                if not Fl[a][t]:
                    dropped.add(i)
        row = cur.copy()
        for i in dropped:
            row[i] = 0.0
        W[t] = row; fill[t] = max(tot - row.sum(), 0.0)
    return W, fill


def test_rotate():
    print('== (2) rotate rule ==')
    F = frame(seed=4)
    cases = [dict(assets=['QLD', 'SSO', 'TLT'], score='ret(*, 126)', filter='price(*) > sma(*, 200)', top=1, every='monthly',
                  exit='daily', total=0.88),
             dict(assets=['QQQ', 'SPY', 'TLT', 'IEF'], score='ret(*, 63) - vol(*, 63) / 4', top=2, every='weekly', total=1.0),
             dict(assets=['QLD', 'SSO', 'TLT', 'IEF'], score='ret(*, 126)', filter='ret(*, 126) > 0', top=3, weight='score',
                  every=21, fill='SHY', total=0.9),
             dict(assets=['QLD', 'SSO', 'TLT'], score='zscore(*, 60)', filter='price(*) > sma(*, 100)', top=2,
                  weight='invvol', n=40, every='quarterly', exit='daily', fill='IEF'),
             dict(assets=['QQQ', 'SPY', 'TLT'], filter='price(*) > sma(*, 150)', weight='equal', every='daily', total=0.88)]
    for k, ro in enumerate(cases):
        A, fill, Wd, fw = dsl._rotate(ro, dsl._mk(F), set(data.SLEEVES) | set(F.columns), F)
        Wr, fr = rot_ref(F, ro)
        d = max(float(np.abs(Wd - Wr).max()), float(np.abs(fw - fr).max()))
        sp = {'rules': [{'rotate': ro}]}
        tc = dsl.truncation_check(sp, F, dsl.held_sleeves(sp), n_cuts=6)
        W = dsl.compile_weights(sp, F, dsl.held_sleeves(sp))
        check(f"rotate case {k} ({ro.get('weight', 'equal')}, top {ro.get('top', len(ro['assets']))}, every {ro['every']}"
              f"{', exit daily' if ro.get('exit') else ''}) == per-row reference; causal; sums <= 1",
              d < 1e-12 and tc['ok'] and (W.drop(columns='CASH').sum(axis=1) <= 1 + 1e-12).all() and W.values.min() >= -1e-12
              and Wd.max() > 0, f'max |diff| {d:.1e}')
    ro = cases[0]
    A, fill, Wd, fw = dsl._rotate(ro, dsl._mk(F), set(data.SLEEVES) | set(F.columns), F)
    rows = dsl.reb_rows(F.index, 'monthly')
    held = (Wd > 0).sum(1)
    chg = np.flatnonzero(np.any(Wd[1:] != Wd[:-1], 1)) + 1
    up_off_month = [t for t in chg if not rows[t] and Wd[t].sum() > Wd[t - 1].sum()]
    check('rotate monthly + exit daily: at most 1 asset held; no pick added between decision rows (exits only)',
          held.max() <= 1 and not up_off_month)
    rp = dict(assets=['QQQ', 'SPY', 'TLT'], top=3, weight='rp', n=60, every='monthly')
    A, fill, Wd, fw = dsl._rotate(rp, dsl._mk(F), set(data.SLEEVES) | set(F.columns), F)
    ri = np.flatnonzero(dsl.reb_rows(F.index, 'monthly'))[5:]
    X = np.stack([np.log(F[c]).diff().values for c in ('_NDX', 'SPY', 'TLT')], 1)
    C = dsl._roll_cov(X, 60)[ri]; w = Wd[ri]
    rc = w * np.einsum('tij,tj->ti', C, w)
    check('rotate weight: rp gives equal risk contributions on decision rows',
          np.max(np.abs(rc / rc.sum(1, keepdims=True) - 1 / 3)) < 1e-6)
    bad = [dict(assets=['QLD'], score='ret(QLD, 20)'), dict(assets=['QLD', 'QLD']), dict(assets=['QLD', 'TLT'], top=3),
           dict(assets=['QLD', 'TLT'], weight='x'), dict(assets=['QLD', 'TLT'], exit='daily'),
           dict(assets=['QLD', 'TLT'], fill='TLT'), dict(assets=['QLD', 'TLT'], every='yearly'), dict(assets=['QLD'], total=1.5),
           dict(assets=['QLD', 'TLT'], weight='score')]
    n = sum(raises(lambda b=b: dsl.check_spec({'rules': [{'rotate': b}]}), ValueError) for b in bad)
    check('rotate config errors refused (no *, duplicates, top > k, weight, exit without filter, fill, every, total)',
          n == len(bad), f'{n}/{len(bad)}')
    w = dsl.reb_rows(pd.bdate_range('2021-01-01', periods=15), 'weekly')
    m = dsl.reb_rows(pd.bdate_range('2021-01-27', periods=10), 'monthly')
    check('cadence rows = first row of each period (row 0 included); N = every N-th row',
          np.flatnonzero(w).tolist() == [0, 1, 6, 11] and np.flatnonzero(m).tolist() == [0, 3]
          and np.flatnonzero(dsl.reb_rows(pd.bdate_range('2021-01-01', periods=10), 4)).tolist() == [0, 4, 8])


# ---------------------------------------------------------------- brake
def brake_ref(raw, rr, risk, br, floor=None):
    """Reference: re-simulate the paper equity from the FINAL (braked) weights row by row."""
    cfg = dsl._brake_levels(br)
    n = len(raw); W = raw.copy(); E = Er = pk = 1.0; on = [False] * len(cfg['levels']); braked = 0
    for t in range(n):
        if t:
            E *= 1 + float(np.sum(W[t - 1, risk] * rr[t]))
            Er *= 1 + float(np.sum(raw[t - 1, risk] * rr[t]))
        e = E if cfg['basis'] == 'own' else Er
        pk = max(pk, e); d = e / pk - 1
        if cfg['knee']:
            a, b, f = cfg['knee']
            s = 1.0 if d >= a else (f if d <= b else max(f, 1 - (a - d) / (a - b) * (1 - f)))
        else:
            s = 1.0
            for i, (l, sc, rc) in enumerate(cfg['levels']):
                on[i] = (d < rc) if on[i] else (d <= l)
                if on[i]:
                    s = min(s, sc)
        if s < 1:
            braked += 1
            if cfg['cooldown'] and braked > cfg['cooldown']:
                on = [False] * len(on); pk = e; braked = 0; s = 1.0
        else:
            braked = 0
        if floor is not None:
            s = max(s, floor[t])
        W[t, risk] = raw[t, risk] * s
    W[:, ~risk] = 0; W[:, list(~risk).index(True)] = 1 - W[:, risk].sum(1)
    return W


def test_brake():
    print('== (3) brake on the strategy\'s own paper equity ==')
    F = frame(2600, seed=7)
    base = {'signals': {'up': 'price(QQQ) > sma(QQQ, 100)'},
            'rules': [{'when': 'up', 'hold': {'QLD': 0.6, 'TLT': 0.3}}, {'else': {'TLT': 0.5}}]}
    sl = ['QLD', 'TLT']
    raw = dsl.compile_weights(base, F, sl)
    cols = list(raw.columns); risk = np.array([c != 'CASH' for c in cols])
    rr = dsl.sleeve_returns(F, [c for c in cols if c != 'CASH'])
    R = pd.DataFrame({'QLD': 2 * F['_NDX'].pct_change(), 'TLT': F['TLT'].pct_change()}, index=F.index)
    brakes = [{'dd': -0.15, 'scale': 0.5, 'recover': -0.05},
              {'dd': -0.15, 'scale': 0.0, 'recover': -0.05, 'cooldown': 40},
              {'ladder': [[-0.10, 0.75], [-0.20, 0.4], [-0.30, 0.0, -0.12]], 'recover': -0.04},
              {'knee': [-0.10, -0.30], 'floor': 0.2},
              {'dd': -0.15, 'scale': 0.3, 'basis': 'raw'},
              {'dd': -0.12, 'scale': 0.0, 'recover': -0.06, 'floor_when': {'when': 'up', 'scale': 0.5}}]
    for k, br in enumerate(brakes):
        sp = dict(base, brake=br)
        W = dsl.compile_weights(sp, F, sl)
        fl = None
        if 'floor_when' in br:
            fl = np.where(dsl._boolv(dsl._eval('up', dict(dsl._mk(F), up=dsl._eval(base['signals']['up'], dsl._mk(F), set(data.SLEEVES))),
                                               set(data.SLEEVES)), F.index), br['floor_when']['scale'], 0.0)
        ref = brake_ref(raw.values, rr, risk, br, fl)
        d = float(np.abs(W.values - ref).max())
        tc = dsl.truncation_check(sp, F, sl, n_cuts=6)
        bound = (W[sl].values <= raw[sl].values + 1e-12).all()
        check(f'brake {k} {json.dumps(br)}: == row-by-row re-simulation from the final weights; causal; never above raw',
              d < 1e-12 and tc['ok'] and bound and (W[sl].values < raw[sl].values - 1e-9).any(), f'max |diff| {d:.1e}')
    sp = dict(base, brake=brakes[0])
    a = dsl.compile_weights(sp, F, sl, R); b = dsl.compile_weights(sp, F, sl)
    check('brake: dev path takes sleeve returns from R (same result when R equals the frame returns)',
          float(np.abs(a.values - b.values).max()) < 1e-12)
    R2 = R.copy(); R2['QLD'] = R2['QLD'] * 1.5
    check('brake: R really used (different R -> different scale)', float(np.abs(dsl.compile_weights(sp, F, sl, R2).values - a.values).max()) > 0)
    # crash path: engage at dd <= -20%, release at >= -10%
    idx = pd.bdate_range('2010-01-01', periods=300)
    px = np.r_[np.full(50, 100.0), np.linspace(100, 70, 30), np.linspace(70, 70, 40), np.linspace(70, 115, 60), np.full(120, 115.0)]
    Fc = pd.DataFrame({'_NDX': px}, index=idx)
    spc = {'rules': [{'else': {'QQQ': 1.0}}], 'brake': {'dd': -0.20, 'scale': 0.5, 'recover': -0.10}}
    Wc = dsl.compile_weights(spc, Fc, ['QQQ'])['QQQ'].values
    E = np.cumprod(np.r_[1.0, 1 + Wc[:-1] * np.diff(px) / px[:-1]]); dd = E / np.maximum.accumulate(E) - 1
    on_i = int(np.argmax(Wc < 1)); off_i = on_i + int(np.argmax(Wc[on_i:] == 1))
    check('brake crash path: halves on the first day dd <= -20%, back to full on the first day dd >= -10%',
          dd[on_i] <= -0.20 and dd[on_i - 1] > -0.20 and dd[off_i] >= -0.10 and dd[off_i - 1] < -0.10 and Wc[on_i] == 0.5)
    bad = [{'dd': 0.1}, {'dd': -0.2, 'scale': 1.5}, {'dd': -0.2, 'recover': -0.3}, {'knee': [-0.5, -0.2]},
           {'dd': -0.2, 'basis': 'x'}, {'dd': -0.2, 'cooldown': 0}, {'ladder': [[-0.1]]}, 'x']
    n = sum(raises(lambda b=b: dsl.check_spec(dict(base, brake=b)), ValueError) for b in bad)
    check('brake config errors refused', n == len(bad), f'{n}/{len(bad)}')
    # timing on a bar path (10y + 300 warm-up rows)
    cand = bb.LabCandidate({'name': 'bk', 'rules': [{'else': {'QLD': 0.88}}],
                            'brake': {'ladder': [[-0.15, 0.6], [-0.30, 0.2, -0.15]], 'recover': -0.08}})
    pm = bb.boot_paths(cand, n=1)[0]
    cand.build(pm)
    ts = []
    for _ in range(20):
        t0 = time.perf_counter(); cand.build(pm); ts.append(time.perf_counter() - t0)
    g = np.random.default_rng(0).normal(0, 0.02, len(pm.dates))
    cfg = dsl._brake_levels({'ladder': [[-0.15, 0.6], [-0.30, 0.2, -0.15]], 'recover': -0.08, 'cooldown': 60})
    t0 = time.perf_counter()
    for _ in range(20):
        dsl.brake_scale(g, cfg)
    tb = (time.perf_counter() - t0) / 20
    check('brake: per-path build < 10 ms on a 10y bar path', np.median(ts) < 0.010,
          f'{len(pm.dates)} rows: build median {np.median(ts) * 1e3:.1f} ms, brake loop alone {tb * 1e3:.1f} ms')
    ok, badc, seed = bb.causality(cand, pm)
    check('brake: bar truncation test (40 random cuts) passes on a bootstrap path', ok)


# ---------------------------------------------------------------- grid + batch + CLI
def test_grid_batch():
    print('== (4) grid, batch run, summary ==')
    g = {'name': 'g', 'family': 'fam_g', 'grid': {'N': [100, 200, 300], 'D': [-0.2, -0.3]},
         'signals': {'up': 'price(QQQ) > sma(QQQ, {N})'}, 'rules': [{'when': 'up', 'hold': {'QLD': 0.88}}, {'else': {'CASH': 1.0}}],
         'brake': {'dd': '{D}', 'scale': 0.5}}
    ex = dsl.expand_grid(g)
    hs = {dsl.spec_hash(s) for s in ex}
    check('grid: 3 x 2 points, names base[N=..,D=..], distinct hashes, {D} whole-string keeps the number type',
          len(ex) == 6 and len(hs) == 6 and ex[0]['name'] == 'g[N=100,D=-0.2]' and ex[0]['brake']['dd'] == -0.2
          and ex[0]['signals']['up'] == 'price(QQQ) > sma(QQQ, 100)' and all('grid' not in s for s in ex)
          and all(dsl.check_spec(s) for s in ex))
    check('grid: unexpanded spec refused by check_spec; unused key / empty / too many points refused',
          raises(lambda: dsl.check_spec(g), ValueError)
          and raises(lambda: dsl.expand_grid(dict(g, grid={'Z': [1]})), ValueError)
          and raises(lambda: dsl.expand_grid(dict(g, grid={'N': []})), ValueError)
          and raises(lambda: dsl.expand_grid(dict(g, grid={'N': list(range(300)), 'D': [0]})), ValueError))
    # CLI batch on a directory: grid (3) + a plain spec, --bar none, fresh LAB_HOME
    d = os.path.join(TMP, 'batch'); home = os.path.join(TMP, 'home'); os.makedirs(d)
    write('batch/a_grid.yaml', '''\
        name: cli_grid
        family: cli_fam
        grid: {N: [150, 200, 250]}
        signals:
          up: price(QQQ) > sma(QQQ, {N})
        rules:
          - when: up
            hold: {QLD: 0.88}
          - else: {CASH: 1.0}
        ''')
    write('batch/b_rot.yaml', '''\
        name: cli_rot
        family: cli_fam
        rules:
          - rotate: {assets: [QLD, SSO, TLT], score: 'ret(*, 126)', filter: 'price(*) > sma(*, 200)', top: 1, every: monthly, exit: daily, total: 0.88}
        brake: {dd: -0.25, scale: 0.5, recover: -0.10}
        ''')
    env = dict(os.environ, LAB_HOME=home, PYTHONDONTWRITEBYTECODE='1')
    run = lambda *a: subprocess.run([sys.executable, '-B', '-m', 'lab', 'run', *a], cwd=LAB, env=env, capture_output=True,
                                    text=True, timeout=900)
    p = run(d, '--bar', 'none')
    lines = p.stdout.splitlines()
    one = [x for x in lines if x.startswith('[')]
    summ = p.stdout[p.stdout.index('== 요약'):] if '== 요약' in p.stdout else ''
    check('CLI batch: dir -> 4 one-line results (grid x3 + rotate/brake), N counts 1..4, all lines <= 400 bytes',
          p.returncode == 0 and len(one) == 4 and [x.split(' N=')[1].split()[0] for x in one] == ['1', '2', '3', '4']
          and all(len(x.encode()) <= 400 for x in one), p.stderr[-300:])
    check('CLI batch: ranked summary follows, <= 1.5 KB, lists all 4', bool(summ) and len(summ.encode()) <= 1500
          and summ.count('\n') >= 5, f'{len(summ.encode())} bytes')
    bj = [f for f in os.listdir(os.path.join(home, 'out')) if f.startswith('batch_')]
    check('CLI batch: full JSON written to LAB_HOME/out/batch_*.json', len(bj) == 1 and
          len(json.load(open(os.path.join(home, 'out', bj[0])))['records']) == 4)
    p2 = run(os.path.join(d, 'a_grid.yaml'), '--bar', 'none')
    one2 = [x for x in p2.stdout.splitlines() if x.startswith('[')]
    check('CLI grid rerun: same hashes -> (중복), family N unchanged at 4',
          len(one2) == 3 and all('(중복)' in x and 'N=4' in x for x in one2))
    # summary unit: 25 records, long names, mixed verdicts, errors
    recs = [dict(name='x' * 60 + str(i), hash=f'{i:012d}', lg=0.01 * i, qld=0.1, qqqm=0.08, dev_y12=2.0, dev_screen=False,
                 verdict='빠른 선별 (기준 아님) fail', failed=['Q1', 'Q2', 'R1', 'R2', 'R3', 'Q3', 'W5', 'causality'], mode='quick@2')
            for i in range(25)]
    recs += [dict(name='vi', hash='a' * 12, dev_y12=9.0, dev_screen=True, verdict='REJECT (version impossible)',
                  failed=['version_impossible'], mode='quick@2'), dict(name='bad', error='ValueError: x')]
    t = cli.summary(recs, 'quick')
    body = t.splitlines()[2:]
    check('summary(): <= 1500 bytes, top 10 by lg (descending), errors counted, not listed',
          len(t.encode()) <= 1500 and len(body) == 10 and '0.240/' in body[0] and '0.230/' in body[1] and '0.150/' in body[9]
          and '오류 1' in t and 'bad' not in t, f'{len(t.encode())} bytes')


# ---------------------------------------------------------------- plugin
PLUG_OK = '''\
    import numpy as np
    import pandas as pd


    def trend(F, sleeves, params):
        n = int(params['n'])
        up = F['QQQ'] > F['QQQ'].rolling(n, min_periods=n).mean()
        return pd.DataFrame({sleeves[0]: np.where(up, 0.88, 0.0)}, index=F.index)


    def peek(F, sleeves, params):
        up = F['QQQ'].shift(-1) > F['QQQ']          # tomorrow's close: look-ahead
        return pd.DataFrame({sleeves[0]: np.where(up, 0.88, 0.0)}, index=F.index)


    def badcol(F, sleeves, params):
        return pd.DataFrame({'TQQQ': 1.0}, index=F.index)
    '''


def test_plugin():
    print('== (5) plugin escape hatch ==')
    pf = write('plug/p.py', PLUG_OK)
    sp_p = dsl.load_spec(write('plug/p.yaml', 'name: pt\nplugin: p.py:trend\nsleeves: [QLD]\ninputs: [QQQ]\nparams: {n: 200}\n'))
    check('plugin path resolved relative to the spec file', sp_p['plugin'] == pf + ':trend')
    sp_d = {'signals': {'up': 'price(QQQ) > sma(QQQ, 200)'}, 'rules': [{'when': 'up', 'hold': {'QLD': 0.88}}, {'else': {'CASH': 1.0}}]}
    Fd, R, _, _ = data.build(['QLD', 'QQQ'])
    Fd = Fd[Fd.index <= '2014-12-31']; R = R[R.index <= '2014-12-31']
    a = dsl.compile_weights(sp_p, Fd, ['QLD'], R); b = dsl.compile_weights(sp_d, Fd, ['QLD'], R)
    check('plugin in the dev summary == the same rule in the DSL (real <= 2014 frame, bit-identical)',
          a.index.equals(b.index) and np.array_equal(a.values, b.values))
    ca, cb = bb.LabCandidate(sp_p), bb.LabCandidate(sp_d)
    pm = bb.boot_paths(ca, n=1)[0]
    check('plugin on a bar path == the DSL rule (bit-identical), signal/trade syms derived from inputs / sleeves',
          np.array_equal(ca.build(pm), cb.build(pm)) and ca.signal_syms == ['QQQ'] and ca.trade_syms == ['QLD'])
    okc, badc, _ = bb.causality(ca, pm)
    check('plugin: bar truncation test passes for the causal plugin', okc)
    sp_k = dict(sp_p, plugin=pf + ':peek')
    ck = bb.LabCandidate(sp_k)
    okk, badk, _ = bb.causality(ck, pm)
    tck = dsl.truncation_check(sp_k, Fd, ['QLD'], R)
    check('plugin look-ahead caught: bar truncation test (random cuts) and dev truncation test both fail',
          not okk and not tck['ok'], f'{len(badk)} bar violations, {len(tck["violations"])} dev')
    q = bb.quick(ck, n_paths=20)
    check('plugin look-ahead: quick screen lists causality as failed', 'causality' in q['failed'])
    h0 = dsl.spec_hash(sp_p)
    pf2 = write('plug/p2.py', PLUG_OK.replace("0.88, 0.0", "0.87, 0.0"))
    check('plugin hash follows the plugin file content (not its path)',
          dsl.spec_hash(dict(sp_p, plugin=pf2 + ':trend')) != h0 and dsl.spec_hash(dict(sp_p)) == h0)
    check('plugin returning a column outside sleeves + CASH refused',
          raises(lambda: dsl.compile_weights(dict(sp_p, plugin=pf + ':badcol'), Fd, ['QLD'], R), dsl.PluginError))
    srcs = {'open': "def f(F, s, p):\n    x = open('/etc/hosts').read()\n",
            'np.load': "import numpy as np\ndef f(F, s, p):\n    z = np.load('x.npz')\n",
            'lab.data': "import lab.data\ndef f(F, s, p):\n    pass\n",
            'data.series': "from lab import data\ndef f(F, s, p):\n    x = data.series('QQQ')\n",
            'os': "import os\ndef f(F, s, p):\n    pass\n",
            '/mnt': "P = '/mnt/project-files/research/data'\ndef f(F, s, p):\n    pass\n"}
    n = 0
    for k, s in srcs.items():
        f = write(f'plug/bad_{k.replace("/", "_").replace(".", "_")}.py', s)
        n += raises(lambda f=f: dsl.load_plugin(f + ':f'), dsl.PluginError)
    check('plugin source scan refuses file / panel / system access (open, np.load, lab.data, data.series, os, /mnt)',
          n == len(srcs), f'{n}/{len(srcs)}')
    # runtime isolation: code the scan lets through runs in a forked child that cannot open files or keep state
    sneak = write('plug/sneak.py', '''\
        import pandas as pd
        _N = []


        def via_open(F, sleeves, params):
            o = open
            o('/etc/hostname')
            return pd.DataFrame({sleeves[0]: 0.0}, index=F.index)


        def count(F, sleeves, params):
            _N.append(1)
            return pd.DataFrame({sleeves[0]: 0.1 * len(_N)}, index=F.index)


        def bye(F, sleeves, params):
            raise SystemExit(0)
        ''')
    ro = raises(lambda: dsl.compile_weights(dict(sp_p, plugin=sneak + ':via_open'), Fd, ['QLD'], R), dsl.PluginError)
    cs = bb.LabCandidate(dict(sp_p, plugin=sneak + ':via_open'))
    rb = raises(lambda: cs.build(pm), dsl.PluginError)
    w1 = dsl.compile_weights(dict(sp_p, plugin=sneak + ':count'), Fd, ['QLD'], R)['QLD'].iloc[-1]
    w2 = dsl.compile_weights(dict(sp_p, plugin=sneak + ':count'), Fd, ['QLD'], R)['QLD'].iloc[-1]
    rx = raises(lambda: dsl.compile_weights(dict(sp_p, plugin=sneak + ':bye'), Fd, ['QLD'], R), dsl.PluginError)
    check('plugin isolation: open() fails in the child (dev and bar path), module state does not survive between '
          'builds, SystemExit in the plugin is a PluginError (lab keeps running)',
          ro and rb and w1 == w2 == 0.1 and rx, f'{w1} {w2}')
    memo = write('plug/memo.py', '''\
        import numpy as np
        import pandas as pd
        _SEEN = []


        def weights(F, sleeves, params):
            v = F.values
            for fv, w in _SEEN:
                if len(fv) >= len(v) and np.array_equal(fv[:len(v)], v, equal_nan=True):
                    return pd.DataFrame({sleeves[0]: w[:len(v)]}, index=F.index)
            px = F.iloc[:, 0].values
            nxt = np.r_[px[1:], np.nan]
            w = np.where(nxt > px, 0.88, 0.0)
            _SEEN.append((v.copy(), w))
            return pd.DataFrame({sleeves[0]: w}, index=F.index)
        ''')
    cm = bb.LabCandidate(dict(sp_p, plugin=memo + ':weights'))
    okm, badm, _ = bb.causality(cm, pm)
    tcm = dsl.truncation_check(dict(sp_p, plugin=memo + ':weights'), Fd, ['QLD'], R)
    check('memo look-ahead plugin (replays a stored full-length answer on cuts) caught by bar and dev truncation tests',
          not okm and not tcm['ok'], f'{len(badm)} bar, {len(tcm["violations"])} dev violations')
    reach = write('plug/reach.py', 'from lab import (data as D)\nimport blackbox2\ndef f(F, s, p):\n    pass\n')
    check('plugin imports outside numpy / pandas / math / small stdlib refused (lab, blackbox2, parenthesised form)',
          raises(lambda: dsl.load_plugin(reach + ':f'), dsl.PluginError))
    check('plugin spec shape: needs sleeves; plugin + rules refused; missing file refused',
          raises(lambda: dsl.check_spec({'plugin': pf + ':trend'}), ValueError)
          and raises(lambda: dsl.check_spec(dict(sp_p, rules=[{'else': {'QLD': 1}}])), ValueError)
          and raises(lambda: dsl.check_spec(dict(sp_p, plugin='/nope.py:f')), ValueError))
    # plugin with brake + weekly rebalance on a path: post-processing applies, still causal
    cpb = bb.LabCandidate(dict(sp_p, brake={'dd': -0.2, 'scale': 0.5}, rebalance='weekly'))
    okb, _, _ = bb.causality(cpb, pm)
    check('plugin + brake + weekly rebalance: bar truncation test passes', okb)


# ---------------------------------------------------------------- inputs blackbox2 does not resample
def test_not_resampled():
    print('== (6) inputs the bar paths do not resample (macro, KR, FX) ==')
    Fd, R, _, _ = data.build(['QLD', 'QQQ'])
    Fd = Fd[Fd.index <= '2014-12-31']; R = R[R.index <= '2014-12-31']
    specs = {'_IRX': {'signals': {'up': 'price(_IRX) < sma(_IRX, 100)'}, 'rules': [{'when': 'up', 'hold': {'QLD': 0.88}}, {'else': {'CASH': 1.0}}]},
             'KRW_X': {'signals': {'up': "ret('KRW_X', 20) < 0"}, 'rules': [{'when': 'up', 'hold': {'QLD': 0.88}}, {'else': {'CASH': 1.0}}]},
             '069500.KS': {'signals': {'up': "price('069500.KS') > sma('069500.KS', 200)"},
                           'rules': [{'when': 'up', 'hold': {'QLD': 0.88}}, {'else': {'CASH': 1.0}}]},
             'rotate score': {'rules': [{'rotate': {'assets': ['QLD', 'TLT'], 'score': "ret(*, 60) - ret('KRW_X', 60)"}}]},
             'invvol list': {'signals': {'w': 'invvol(QLD, [QLD, GLD], 60)'}, 'rules': [{'else': {'QLD': 'w'}}]},
             'brake floor_when': {'rules': [{'else': {'QLD': 0.88}}],
                                  'brake': {'dd': -0.2, 'scale': 0.0, 'floor_when': {'when': 'price(_IRX) < 2', 'scale': 0.5}}},
             'rotate SHY sleeve': {'rules': [{'rotate': {'assets': ['QLD', 'SHY'], 'score': 'ret(*, 60)'}}]}}
    pf = write('plug/irx.py', PLUG_OK)
    specs['plugin inputs'] = {'plugin': pf + ':trend', 'sleeves': ['QLD'], 'inputs': ['QQQ', '_IRX'], 'params': {'n': 50}}
    for k, sp in specs.items():
        sl = sorted(set(dsl.held_sleeves(sp)) | {'QQQ'})
        F2, R2, _, _ = data.build(sl)
        F2 = F2[F2.index <= '2014-12-31']; R2 = R2[R2.index <= '2014-12-31']
        W = dsl.compile_weights(sp, F2, sl, R2)
        dev_ok = W.index[-1] <= pd.Timestamp('2014-12-31') and np.isfinite(W.values).all() and W.drop(columns='CASH').values.max() > 0
        nj = raises(lambda: bb.LabCandidate(sp), bb.NotJudgeable)
        r = bb.judge(sp, 'quick')
        check(f'{k}: dev summary computes (<= 2014); bar -> NotJudgeable -> REJECT (version impossible)',
              dev_ok and nj and r['verdict'] == 'REJECT (version impossible)' and r['failed'] == ['version_impossible'],
              r.get('reason', '')[:90])
    # CLI line for such a spec
    home = os.path.join(TMP, 'home6')
    p = write('ni/irx.yaml', 'name: irx\nfamily: macro\nsignals:\n  up: price(_IRX) < sma(_IRX, 100)\nrules:\n  - when: up\n'
                             '    hold: {QLD: 0.88}\n  - else: {CASH: 1.0}\n')
    o = subprocess.run([sys.executable, '-B', '-m', 'lab', 'run', p, '--bar', 'quick'], cwd=LAB, capture_output=True, text=True,
                       env=dict(os.environ, LAB_HOME=home), timeout=600)
    check('CLI --bar quick on a macro-input spec: dev part present, bar part says 기준: REJECT (version impossible)',
          o.returncode == 0 and '개발(' in o.stdout and '기준: REJECT (version impossible)' in o.stdout, o.stderr[-200:])


# ---------------------------------------------------------------- review fixes (phase-2 verifier findings)
def test_review_fixes():
    print('== (8) review fixes ==')
    from lab import engine, gates
    Fd, R, _, _ = data.build(['TQQQ', 'TMF', 'QQQ', 'QLD', 'TLT', 'IEF'])
    Fd = Fd[Fd.index <= '2014-12-31']; R = R[R.index <= '2014-12-31']
    fn = dsl._mk(Fd, R)
    a = fn['rp']('TQQQ', ['TQQQ', 'TMF'], 60).values; b = fn['invvol']('TQQQ', ['TQQQ', 'TMF'], 60).values
    lr = lambda c: np.log(data.price_for_signal(Fd, c)).diff()
    cr = lr('TQQQ').rolling(60, min_periods=60).corr(lr('TMF')).values
    m = (a > 0) & (b > 0)
    check('rp == invvol for two assets, incl. strongly negative correlation (TQQQ/TMF <= 2014)',
          m.sum() > 2000 and np.abs(a - b)[m].max() < 1e-10 and np.nanmin(cr[m]) < -0.6 and ((a > 0) == (b > 0)).all(),
          f'max diff {np.abs(a - b)[m].max():.1e}, min corr {np.nanmin(cr[m]):.2f}')
    A = ['TQQQ', 'TMF', 'QQQ', 'IEF']
    W = np.stack([fn['rp'](x, A, 60).values for x in A], 1)
    X = np.stack([dsl._lev(x) * lr(x).values for x in A], 1)
    C = dsl._roll_cov(X, 60); rows = np.flatnonzero(W.sum(1) > 0)
    rc = W[rows] * np.einsum('tij,tj->ti', C[rows], W[rows])
    sp_ = np.abs(rc / rc.sum(1, keepdims=True) - 0.25).max()
    check('rp over 4 assets with negative correlations: equal risk contributions (all rows)', sp_ < 1e-8, f'{sp_:.1e}')
    iv = fn['invvol']('TQQQ', ['TQQQ', 'TMF'], 60)
    first_tmf = data.price_for_signal(Fd, 'TMF').first_valid_index()
    check('invvol: 0 until every listed asset has an n-day vol (no full weight on the one that has)',
          (iv[iv.index < first_tmf] == 0).all() and (iv[iv > 0].index.min() > first_tmf))
    # static weights + quarterly rebalance: the dev engine trades the drift back on the sampled rows
    st = {'rebalance': 'quarterly', 'rules': [{'else': {'QLD': 0.5, 'TLT': 0.2, 'IEF': 0.18}}], 'dev_start': '2003-01-01'}
    sl = ['IEF', 'QLD', 'QQQ', 'TLT']
    F2, R2, _, _ = data.build(sl); F2 = F2[F2.index <= '2014-12-31']; R2 = R2[R2.index <= '2014-12-31']
    Ws = dsl.compile_weights(st, F2, sl, R2)
    e0 = engine.run(Ws, R2, pd.Timestamp('2003-01-02'), gates.DEV_END)
    e1 = engine.run(Ws, R2, pd.Timestamp('2003-01-02'), gates.DEV_END,
                    rebal=pd.Series(dsl.reb_rows(Ws.index, 'quarterly'), index=Ws.index))
    s_q = gates.evaluate(Ws, R2, st); s_d = gates.evaluate(Ws, R2, dict(st, rebalance='daily'))
    check('static mix, rebalance quarterly: dev engine trades on each quarter start (was 0 trades); daily unchanged',
          e0['trades'] == 0 and e1['trades'] >= 45 and s_q['dev']['trades'] >= 45 and s_d['dev']['trades'] == 0,
          f"{e0['trades']} -> {e1['trades']}")
    # YAML booleans as signal names, else + hold, grid placeholder in family, huge constants
    ysp = dsl.yaml.safe_load('signals:\n  on: price(QQQ) > sma(QQQ, 200)\n  off: price(QQQ) < sma(QQQ, 100)\n'
                             '  st: latch(on, off)\nrules:\n  - when: st\n    hold: {QLD: 0.88}\n')
    try:
        dsl.check_spec(ysp); msg = ''
    except ValueError as e:
        msg = str(e)
    check('signal names on / off (YAML booleans) refused with a clear message', 'YAML boolean' in msg, msg[:80])
    check('rule with both hold and else refused',
          raises(lambda: dsl.check_spec({'rules': [{'else': {'QLD': "0.5 * (price('KRW_X') > 0)"}, 'hold': {'QLD': 0.4}}]}),
                 ValueError))
    g = {'name': 'g', 'family': 'trend_{N}', 'grid': {'N': [150, 200]}, 'signals': {'up': 'price(QQQ) > sma(QQQ, {N})'},
         'rules': [{'when': 'up', 'hold': {'QLD': 0.88}}]}
    check('grid placeholder in family / name refused (the family N must count every point)',
          raises(lambda: dsl.expand_grid(g), ValueError)
          and raises(lambda: dsl.expand_grid(dict(g, family='t', name='g{N}')), ValueError)
          and len(dsl.expand_grid(dict(g, family='t'))) == 2)
    t0 = time.time(); r1 = raises(lambda: dsl._eval('10**10**9', {}, set()), (OverflowError, ValueError))
    r2 = raises(lambda: dsl._eval("'a' * 10**9", {}, set()), (TypeError, ValueError))
    check('constant arithmetic cannot stall a batch (10**10**9, string x 1e9 fail at once)',
          r1 and r2 and time.time() - t0 < 0.5, f'{time.time() - t0:.3f}s')
    # level(x): the traded sleeve level
    lv = fn['level']('TQQQ'); ref = (1 + R['TQQQ'].fillna(0.0)).cumprod()
    ok_dev = np.allclose(lv.dropna().values, ref.reindex(lv.dropna().index).values, rtol=1e-12)
    spl = {'signals': {'tp': 'level(TQQQ) >= 1.3 * low(level(TQQQ), 126)', 'st': 'hold_min(not tp, 20)'},
           'rules': [{'when': 'st', 'hold': {'TQQQ': 0.88}}, {'else': {'QQQ': 0.88}}]}
    cl = bb.LabCandidate(spl)
    pm = bb.boot_paths(cl, n=1)[0]
    Fp = cl.frame(pm)
    ok_bar = np.array_equal(dsl._mk(Fp)['level']('TQQQ').values, pm.C['TQQQ'])
    okc, _, _ = bb.causality(cl, pm)
    tcl = dsl.truncation_check(spl, Fd, ['QQQ', 'TQQQ'], R)
    check('level(TQQQ): dev = cumprod(1 + R), bar = path TQQQ price; level inside sma/low; causal on dev and bar',
          ok_dev and ok_bar and okc and tcl['ok'])
    check('level(x) of a sleeve the spec does not hold refused',
          raises(lambda: dsl.check_spec({'signals': {'a': 'level(TMF) > 0'}, 'rules': [{'when': 'a', 'hold': {'QLD': 0.5}}]}),
                 ValueError))
    # plugin input as an expression (level of the held sleeve)
    pf = write('plug/lvl.py', 'import pandas as pd\ndef f(F, s, p):\n    x = F["level(TQQQ)"]\n'
                              '    return pd.DataFrame({"TQQQ": (x > x.rolling(50, min_periods=50).mean()) * 0.88}, index=F.index)\n')
    spi = {'plugin': pf + ':f', 'sleeves': ['TQQQ'], 'inputs': ['level(TQQQ)']}
    spd = {'signals': {'u': 'level(TQQQ) > sma(level(TQQQ), 50)'}, 'rules': [{'when': 'u', 'hold': {'TQQQ': 0.88}}]}
    wa = dsl.compile_weights(spi, Fd, ['TQQQ'], R).values; wb = dsl.compile_weights(spd, Fd, ['TQQQ'], R).values
    ca = bb.LabCandidate(spi)
    check("plugin inputs may be expressions ('level(TQQQ)'): dev and bar weights == the DSL form",
          np.array_equal(wa, wb) and np.array_equal(ca.build(pm), bb.LabCandidate(spd).build(pm)))
    # month-end look-ahead (needs the next row's date): caught with the plugin cut count
    me = write('plug/me.py', '''\
        import numpy as np
        import pandas as pd


        def f(F, sleeves, params):
            s0 = F.index.to_series()
            last = (s0.groupby(F.index.to_period('M')).transform('max') == s0).values
            px = F.iloc[:, 0].values
            sm = pd.Series(px).rolling(200, min_periods=200).mean().values
            pick = np.where(last, (px > sm).astype(float), np.nan)
            w = pd.Series(pick).ffill().fillna(0.0).values * 0.88
            return pd.DataFrame({sleeves[0]: w}, index=F.index)
        ''')
    spm = {'plugin': me + ':f', 'sleeves': ['QLD'], 'inputs': ['QQQ']}
    caught = sum(not dsl.truncation_check(spm, Fd, ['QLD'], R, seed=s_)['ok'] for s_ in range(5))
    cmb = bb.LabCandidate(spm)
    cb = sum(not bb.causality(cmb, pm, seed=s_)[0] for s_ in range(3))
    check(f'month-end sampling plugin (look-ahead on a few days a year) caught with the plugin cut count '
          f'({dsl.N_CUTS_PLUGIN} + boundaries): dev 5/5 seeds, bar 3/3', caught == 5 and cb == 3, f'dev {caught}/5, bar {cb}/3')
    # batch robustness: a non-string name, an interrupted batch still writes the summary JSON
    d = os.path.join(TMP, 'rf_batch'); home = os.path.join(TMP, 'home_rf'); os.makedirs(d)
    write('rf_batch/a.yaml', 'name: 123\nfamily: rf\nrules:\n  - else: {QLD: 0.5}\n')
    write('rf_batch/b.yaml', 'name: b\nfamily: rf\nrules:\n  - else: {QLD: 0.6}\n')
    write('rf_batch/c.yaml', 'name: c\nfamily: rf\nplugin: ../plug/sneak.py:bye\nsleeves: [QLD]\ninputs: [QQQ]\n')
    o = subprocess.run([sys.executable, '-B', '-m', 'lab', 'run', d, '--bar', 'none'], cwd=LAB, capture_output=True,
                       text=True, env=dict(os.environ, LAB_HOME=home), timeout=600)
    bj = [f for f in os.listdir(os.path.join(home, 'out')) if f.startswith('batch_')] if os.path.isdir(os.path.join(home, 'out')) else []
    check('batch: name 123 works, a plugin raising SystemExit is an error line, summary + batch JSON written',
          '[123]' in o.stdout and '[c] 오류: PluginError' in o.stdout and '== 요약' in o.stdout and len(bj) == 1
          and o.returncode == 1, (o.stdout + o.stderr)[-200:])


# ---------------------------------------------------------------- compatibility
def test_compat():
    print('== (7) v1 compatibility ==')
    import hashlib

    def v1_hash(spec):
        core = {k: spec.get(k) for k in ('signals', 'rules', 'rebalance', 'cost', 'delay')}
        if spec.get('band'):
            core['band'] = spec.get('band')
        return hashlib.sha256(json.dumps(core, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    s1 = dsl.load_spec(LAB + '/specs/trend_tqqq_200.yaml'); s2 = dsl.load_spec(LAB + '/specs/qld_088_hold.yaml')
    s3 = dsl.load_spec(LAB + '/specs/voltarget_qld.yaml')
    check('daily v1 specs keep their hash (ledger rows stay valid)', dsl.spec_hash(s1) == v1_hash(s1) and dsl.spec_hash(s2) == v1_hash(s2))
    check('weekly / monthly v1 specs get a new hash (sampling rule changed to period start)', dsl.spec_hash(s3) != v1_hash(s3))
    ok = True
    for reb in ('weekly', 'monthly', 'quarterly', 10):
        c = bb.LabCandidate({'rebalance': reb, 'signals': {'up': 'price(QQQ) > sma(QQQ, 200)'},
                             'rules': [{'when': 'up', 'hold': {'QLD': 0.88}}, {'else': {'CASH': 1.0}}]})
        o, b_, _ = bb.causality(c, bb.boot_paths(c, n=1)[0])
        ok &= o
    check('rebalance weekly / monthly / quarterly / N passes the bar truncation test (v1 period-end sampling failed it)', bool(ok))


def test_kr_account():
    """account: kr_etf = 13bp/side + 15.4% withheld per sale (no loss offset); dev only, bar refuses."""
    from lab import engine, gates
    idx = pd.bdate_range('2001-01-02', periods=600)
    r = np.zeros(600); r[50:150] = -0.004; r[150:400] = 0.006; r[400:] = 0.001
    R = pd.DataFrame({'X': r, 'CASH': 0.0}, index=idx)
    Wh = pd.DataFrame({'X': 1.0, 'CASH': 0.0}, index=idx)
    a = engine.run(Wh, R, idx[0], idx[-1], cost=0.0013, tax=0.154, tax_mode='yearly')
    b = engine.run(Wh, R, idx[0], idx[-1], cost=0.0013, tax=0.154, tax_mode='per_sale')
    check('kr per_sale: buy-and-hold one sleeve = yearly rule (only the final liquidation is taxed)',
          abs(a['final_at'] - b['final_at']) < 1e-12)
    # same calendar year: sell at a loss (row 140), re-buy (160), sell at a gain (240): yearly nets, per_sale does not
    w = np.ones(600); w[140:160] = 0.0; w[240:] = 0.0
    Wt = pd.DataFrame({'X': w, 'CASH': 1 - w}, index=idx)
    a = engine.run(Wt, R, idx[0], idx[-1], cost=0.0013, tax=0.154, tax_mode='yearly')
    b = engine.run(Wt, R, idx[0], idx[-1], cost=0.0013, tax=0.154, tax_mode='per_sale')
    check('kr per_sale: no loss offset -> final wealth < yearly-netting rule', b['final_at'] < a['final_at'] - 1e-6,
          f"{b['final_at']:.6f} <= {a['final_at']:.6f}")
    # manual: per_sale tax on a single round trip with a gain
    w = np.ones(600); w[500:] = 0.0
    Wt = pd.DataFrame({'X': w, 'CASH': 1 - w}, index=idx)
    b = engine.run(Wt, R, idx[0], idx[-1], cost=0.0, tax=0.154, tax_mode='per_sale')
    g = np.prod(1 + r[3:503]) - 1              # bought at row 2 (delay 2), earns rows 3..502, sold at row 502
    check('kr per_sale: one round trip pays 15.4% of its gain at the sale', abs(b['taxpaid'] - 0.154 * g) < 1e-9,
          f"{b['taxpaid']:.6f} vs {0.154 * g:.6f}")
    sp = {'name': 'kr', 'account': 'kr_etf', 'signals': {'up': 'price(QLD) > sma(QLD, 200)'},
          'rules': [{'when': 'up', 'hold': {'QLD': 0.88}}, {'else': {'CASH': 1.0}}]}
    us = dict(sp); us.pop('account')
    check('kr account changes the hash; a us spec keeps its old hash', dsl.spec_hash(sp) != dsl.spec_hash(us)
          and dsl.spec_hash(dict(us, account='us')) == dsl.spec_hash(us))
    check('unknown account refused', raises(lambda: dsl.check_spec(dict(us, account='jp'))))
    check('kr account: bar answers 판정 불가, never a pass', bb.judge(sp, 'quick')['verdict'].startswith('판정 불가'))
    F, R2, _, _ = data.build(['QLD', 'QQQ'])
    F = F[F.index <= gates.DEV_END]; R2 = R2[R2.index <= gates.DEV_END]
    W = dsl.compile_weights(sp, F, ['QLD', 'QQQ'], R2)
    if True:
        sk = gates.evaluate(W, R2, sp); su = gates.evaluate(W, R2, us)
        kr = {'name': 'kr2', 'account': 'kr_etf', 'baseline': 'KR200', 'signals': {'up': 'price(KR200) > sma(KR200, 200)'},
              'rules': [{'when': 'up', 'hold': {'KRLEV': 0.88}}, {'else': {'CASH': 1.0}}]}
        check('KR domestic ETF in a us account is refused', raises(lambda: dsl.check_spec(dict(kr, account='us'))))
        check('KR domestic ETF spec: bar answers 판정 불가', bb.judge(kr, 'quick')['verdict'].startswith('판정 불가'))
        F3, R3, _, _ = data.build(['KR200', 'KRLEV'])
        R3 = R3[R3.index <= gates.DEV_END]
        ok = True
        for n in ('KR200', 'KRLEV', 'KRINV', 'KRSEMI'):
            _, Rn, _, _ = data.build([n]); Rn = Rn[Rn.index <= gates.DEV_END]; r = Rn[n]
            fv = r.first_valid_index(); ok &= fv is not None and not r[r.index >= fv].isna().any()
            raw = data.kr_clean(data.series(data.KR_SLEEVES[n])); lv = (1 + r.fillna(0)).cumprod()
            c = raw.index.intersection(lv.index); c = c[(c > fv) & (c <= gates.DEV_END)]
            q = lv[c] / raw[c]; ok &= float(q.max() / q.min() - 1) < 1e-9
        check('KR sleeves: no missing returns after start, traded level = raw KR close on shared dates (<= 2014)', bool(ok))
        Wk = pd.DataFrame({'KR200': 1.0, 'CASH': 0.0}, index=R3.index)
        fv = R3['KR200'].first_valid_index()
        e = engine.run(Wk, R3, fv, gates.DEV_END, cost=0.0013, tax=0.154, tax_mode='per_sale', tax_by_col=dict(data.KR_TAX))
        check('KR domestic-equity ETF: gains not taxed (final = equity)', abs(e['final_at'] - e['E'].iloc[-1]) < 1e-12 and e['taxpaid'] == 0)
        check('kr account dev summary runs, labelled, and dev end <= 2014', sk['account'] == 'kr_etf'
              and sk['dev_end'] <= '2014-12-31' and su['account'] == 'us')


if __name__ == '__main__':
    t0 = time.time()
    for f in (test_functions, test_rotate, test_brake, test_grid_batch, test_plugin, test_not_resampled, test_compat,
              test_review_fixes, test_kr_account):
        try:
            f()
        except Exception as e:  # a crash is a failure, keep going
            import traceback; traceback.print_exc()
            check(f'{f.__name__} crashed: {type(e).__name__}: {e}', False)
    print(f'FAILS: {FAILS or "none"}  ({time.time() - t0:.0f}s)')
    sys.exit(1 if FAILS else 0)
