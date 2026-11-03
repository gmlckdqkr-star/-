"""Tests for the single-stock universe (spec `universe: sp500`, lab/stocks.py). Run as a script, in its own process:
    LAB_HOME=<fresh dir> python3 -B tests/test_stocks.py
Prints PASS/FAIL lines and identity / timing results only (no strategy performance numbers), ends with 'FAILS: ...'.
Needs the sealed stock panel (LAB_STOCKS, default research/data/us_stocks/sp500_le2014.npz.xz) and the ETF panel.
"""
import io, json, lzma, math, os, subprocess, sys, tempfile, textwrap, time
LAB = __file__.rsplit('/tests/', 1)[0]
sys.path.insert(0, LAB)
import numpy as np, pandas as pd  # noqa: E402
from lab import dsl, engine, stocks  # noqa: E402

FAILS = []
TMP = tempfile.mkdtemp(prefix='lab_stocks_')
COST, TAX, DELAY = 0.003, 0.22, 2


def check(name, ok, extra=''):
    print(f'{"PASS" if ok else "FAIL"}  {name}{("  " + extra) if extra else ""}', flush=True)
    if not ok:
        FAILS.append(name)


def raises(fn, exc=Exception, text=None):
    try:
        fn()
    except exc as e:
        return text is None or text in str(e)
    return False


def spec(stock, **kw):
    return dict({'name': 't', 'family': 'tst', 'universe': 'sp500', 'stock': stock}, **kw)


def write(name, txt):
    p = os.path.join(TMP, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as fh:
        fh.write(textwrap.dedent(txt))
    return p


def row(P, d):
    return int(P.idx.get_loc(pd.Timestamp(d)))


def col(P, t):
    return int(np.flatnonzero(P.tickers == t)[0])


def mk_targets(P, dec, picks, wts, e=None, els=None):
    """Hand-made decisions (tests only)."""
    dec = np.asarray(dec, np.int64)
    picks = [np.asarray(p, np.int64) for p in picks]
    wts = [np.asarray(w, float) for w in wts]
    return stocks.Targets(dec, picks, wts, np.array([max(len(p), 1) for p in picks]),
                          np.zeros((len(dec), P.N), bool), np.ones(P.T) if e is None else e, els or {}, None)


SPECS = {   # every per-stock function, filter, weights, top_pct, cap, cadences
    'mom': spec({'score': 'ret(252, 21)', 'top': 20}),
    'lowvol_iv': spec({'rebalance': 'quarter', 'score': '-vol(252)', 'filter': 'age() >= 252', 'top': 30,
                       'weight': 'invvol(63)', 'max_weight': 0.05}),
    'mix_pct': spec({'rebalance': 'week', 'score': 'rank(ret(126)) + csz(-beta(126)) + abs(min(sma_ratio(50), 1.2))',
                     'filter': 'high_dist(252) > -0.3 and not (log(age() + 1) < 5) or dvol(63) > 1e9',
                     'top_pct': 0.05, 'weight': 'score', 'max_weight': 0.08}),
    'gate': spec({'score': 'ret(252, 21)', 'top': 10, 'exposure': 'up', 'else': {'CASH': 1.0}},
                 signals={'up': 'price(_NDX) > sma(_NDX, 200)'}),
    'gate_frac': spec({'score': 'max(ret(63), ret(21, 5))', 'top': 15, 'exposure': 'min(1, 0.2 / vol(_GSPC, 20))',
                       'exposure_every': 'rebalance', 'else': {'CASH': 1.0}}),
}


# ---------------------------------------------------------------- (j) spec errors
def test_errors():
    print('== (j) spec checks ==')
    bad = lambda st, **kw: (lambda: dsl.check_spec(spec(st, **kw)))
    check('(j) unknown function in score raises and names it',
          raises(bad({'score': 'foo(10) + ret(5)', 'top': 5}), ValueError, "unknown function 'foo'"))
    check('(j) unknown bare name raises', raises(bad({'score': 'x + ret(5)', 'top': 5}), ValueError, "unknown name 'x'"))
    check('(j) window 0 / negative / non-constant refused',
          raises(bad({'score': 'ret(0)', 'top': 5}), ValueError) and raises(bad({'score': 'ret(-5)', 'top': 5}), ValueError)
          and raises(bad({'score': 'ret(5 * 2)', 'top': 5}), ValueError) and raises(bad({'score': 'ret(5, -1)', 'top': 5}), ValueError))
    check('(j) attributes / subscripts / strings refused',
          raises(bad({'score': 'ret(5).real', 'top': 5}), ValueError) and raises(bad({'score': "ret('a')", 'top': 5}), ValueError)
          and raises(bad({'score': '[1][0]', 'top': 5}), ValueError))
    check('(j) unknown filter function raises', raises(bad({'score': 'ret(5)', 'filter': 'pe() < 10', 'top': 5}),
                                                       ValueError, "unknown function 'pe'"))
    check('(j) stock block shape: top xor top_pct, weight, else, unknown key, universe',
          raises(bad({'score': 'ret(5)'})) and raises(bad({'score': 'ret(5)', 'top': 5, 'top_pct': 0.1}))
          and raises(bad({'score': 'ret(5)', 'top': 5, 'weight': 'invvol(1)'}))
          and raises(bad({'score': 'ret(5)', 'top': 5, 'else': {'TQQQ': 1.0}}))
          and raises(bad({'score': 'ret(5)', 'top': 5, 'weights': 'equal'}))
          and raises(lambda: dsl.check_spec(dict(spec({'score': 'ret(5)', 'top': 5}), universe='nasdaq'))))
    check('(j) ETF-spec keys refused in a universe spec (rules, plugin, rebalance, brake)',
          raises(bad({'score': 'ret(5)', 'top': 5}, rules=[{'else': {'CASH': 1}}]), ValueError)
          and raises(bad({'score': 'ret(5)', 'top': 5}, rebalance='monthly'), ValueError)
          and raises(bad({'score': 'ret(5)', 'top': 5}, brake={'dd': -0.2}), ValueError))
    check('(j) gate: unknown series / level() refused, delay < 2 refused',
          raises(bad({'score': 'ret(5)', 'top': 5, 'exposure': 'up'}, signals={'up': 'price(NOPE) > 1'}), ValueError)
          and raises(bad({'score': 'ret(5)', 'top': 5, 'exposure': 'up'}, signals={'up': 'level(QLD) > 1'}), ValueError)
          and raises(bad({'score': 'ret(5)', 'top': 5}, delay=1), ValueError))
    for k, s in SPECS.items():
        dsl.check_spec(s)
    check('(j) every test spec passes the checks', True)


# ---------------------------------------------------------------- per-stock functions vs direct formulas
def test_functions(P):
    print('== per-stock functions vs direct formulas ==')
    D = np.flatnonzero(dsl.reb_rows(P.idx, 'monthly'))
    D = D[D > 400]
    cx = stocks._Ctx(P, D)
    j = col(P, 'AAPL'); q = len(D) // 2; d = D[q]
    Pf, rr = P.P, P.rr
    r1 = cx.value('ret(252, 21)')[q, j]
    check('ret(252, 21) = P[t-21] / P[t-273] - 1', abs(r1 - (Pf[d - 21, j] / Pf[d - 273, j] - 1)) < 1e-12)
    v = cx.value('vol(63)')[q, j]
    check('vol(63) = stdev of the 63 daily returns ending t (ddof 1)', abs(v - np.std(rr[d - 62:d + 1, j], ddof=1)) < 1e-12)
    s = cx.value('sma_ratio(50)')[q, j]
    check('sma_ratio(50) = P / mean(P[t-49..t])', abs(s - Pf[d, j] / Pf[d - 49:d + 1, j].mean()) < 1e-10)
    hd = cx.value('high_dist(252)')[q, j]
    check('high_dist(252) = P / max(P[t-251..t]) - 1', abs(hd - (Pf[d, j] / Pf[d - 251:d + 1, j].max() - 1)) < 1e-12)
    m = P.mkt()
    b = cx.value('beta(126)')[q, j]
    x, y = rr[d - 125:d + 1, j], m[d - 125:d + 1]
    check('beta(126) = cov(r, m) / var(m) over 126 days', abs(b - np.cov(x, y)[0, 1] / np.var(y, ddof=1)) < 1e-9)
    dv = cx.value('dvol(63)')[q, j]
    w = P.dvol[d - 62:d + 1, j].astype(float)
    check('dvol(63) = mean of the present dollar volumes', abs(dv - np.nanmean(w)) < 1e-6 * abs(dv) if np.isfinite(w).sum() >= 32
          else not np.isfinite(dv))
    ag = cx.value('age()')[q, j]
    check('age() = trading days since the first price', ag == d - P.first[j])
    rk = cx.value('rank(ret(126))')
    e0 = P.member[D[q]] & P.real[D[q]]
    raw = cx.value('ret(126)')[q]
    ok = e0 & np.isfinite(raw)
    ref = pd.Series(raw[ok]).rank().values
    check('rank(x) = (rank - 1) / (m - 1) among members with a real price, NaN elsewhere',
          np.allclose(rk[q, ok], (ref - 1) / (ok.sum() - 1)) and np.isnan(rk[q, ~ok]).all())
    z = cx.value('csz(ret(126))')[q]
    check('csz(x) = (x - mean) / stdev among the same names', np.allclose(z[ok], (raw[ok] - raw[ok].mean()) / raw[ok].std(ddof=1)))
    early = cx.value('ret(252)')
    jj = col(P, 'GOOGL') if 'GOOGL' in P.tickers else col(P, 'AABA')
    dd = np.flatnonzero(D - 252 < P.first[jj])
    check('a window with no price at its start is NaN (history must exist)', len(dd) and np.isnan(early[dd, jj]).all())


# ---------------------------------------------------------------- (a) PIT
def test_pit(P):
    print('== (a) point in time: rewriting everything after t* leaves decisions <= t* unchanged ==')
    rng = np.random.default_rng(5)
    tested = 0
    for ts in ('1987-10-16', '1999-12-31', '2008-09-12'):
        c = row(P, ts)
        adj = P.adj.copy(); dv = P.dvol.copy(); mem = P.member.copy(); st = P.stale.copy()
        adj[c + 1:] = (np.nan_to_num(adj[c + 1:], nan=10.0) * np.exp(rng.normal(0, 0.3, adj[c + 1:].shape))).astype(np.float32)
        adj[c + 1:][rng.random(adj[c + 1:].shape) < 0.05] = np.nan
        dv[c + 1:] = rng.random(dv[c + 1:].shape).astype(np.float32) * 1e10
        mem[c + 1:] = rng.random(mem[c + 1:].shape) < 0.4
        st[c + 1:] = rng.random(st[c + 1:].shape) < 0.05
        pz = P.pause.copy(); pz[c + 1:] = rng.random(pz[c + 1:].shape) < 0.01
        P2 = stocks.Panel(P.idx, P.tickers, adj, dv, mem, st, pz)
        for k, s in SPECS.items():
            F = stocks.gate_frame(s, P.idx) if s['stock'].get('exposure') else None
            F2 = None
            if F is not None:
                F2 = F.copy()
                F2.iloc[c + 1:] = F2.iloc[c + 1:].values * np.exp(rng.normal(0, 0.5, F2.iloc[c + 1:].shape))
            a, b = stocks.compile_targets(s, P, F), stocks.compile_targets(s, P2, F2)
            nd = int(np.searchsorted(a.dec, c, side='right'))
            same = np.array_equal(a.dec, b.dec) and np.array_equal(a.e[:c + 1], b.e[:c + 1]) and all(
                np.array_equal(a.picks[j], b.picks[j]) and np.array_equal(a.wts[j], b.wts[j]) for j in range(nd))
            changed = any(not np.array_equal(a.picks[j], b.picks[j]) for j in range(nd, len(a.dec)))
            check(f'(a) {k} t*={ts}: {nd} decisions <= t* identical (and later ones do change)', same and changed)
            tested += 1
    s = SPECS['mom']; tg = stocks.compile_targets(s, P)
    pc = stocks.pit_check(s, P, tg, n_cuts=4, seed=11)
    check('(a) runtime cut check (pit_check) passes on the real panel', pc['ok'] and pc['cuts'] >= 3, str(pc))


# ---------------------------------------------------------------- (b) membership start + delay
def test_membership(P):
    print('== (b) never held before membership (decision row member, held from decision + delay) ==')
    for k in ('mom', 'mix_pct'):
        tg = stocks.compile_targets(SPECS[k], P)
        st = stocks.WINDOWS['w86']
        o = stocks.fast_run(P, tg, 0.3, st, COST, TAX, DELAY, keep_book=True)
        i0, _ = stocks._rows(P, st)
        B = o['book'][:, :len(o['names'])] > 0
        starts = np.argwhere(B[1:] & ~B[:-1]) + [1, 0]
        rows_abs = starts[:, 0] + i0; names = o['names'][starts[:, 1]]
        ok_mem = P.member[rows_abs - DELAY, names].all() and P.real[rows_abs - DELAY, names].all()
        first_mem = np.array([np.flatnonzero(P.member[:, j])[0] for j in names])
        ok_first = (rows_abs >= first_mem + DELAY).all()
        # a name bought while not yet a member would also show in the decisions: none outside membership
        dec_ok = all(P.member[tg.dec[j], p].all() and P.real[tg.dec[j], p].all() for j, p in enumerate(tg.picks))
        check(f'(b) {k}: {len(starts)} holding spells start >= membership start + delay, bought on member rows',
              len(starts) > 50 and ok_mem and ok_first and dec_ok)
    # a name removed from the index is sold at the next decision: no pick outside membership
    tg = stocks.compile_targets(SPECS['mom'], P)
    left = [(j, p) for j, p in enumerate(tg.picks) if not P.member[tg.dec[j], p].all()]
    check('(b) no decision picks a non-member (removed names drop out at the next rebalance)', not left)


# ---------------------------------------------------------------- (c) exit gaps
def test_exit_gap(P):
    print('== (c) exit gaps: the price is carried through the pause, the held name books the whole change ==')
    meta = json.load(open(os.path.join(os.path.dirname(stocks.STOCKS), 'META.json')))
    R0 = P.R(0.0)
    ok = True
    for g in meta['exit_gaps']:
        j = col(P, g['ticker']); a, b = row(P, g['last_trade']), row(P, g['next_trade'])
        chg = P.adj[b, j] / P.adj[a, j] - 1
        ok &= abs(R0[b, j] - chg) < 1e-6 and np.all(R0[a + 1:b, j] == 0) and P.frozen[a + 1:b, j].all() \
            and abs(np.prod(1 + R0[a + 1:b + 1, j]) - 1 - g['change']) < 1e-3
    check('(c) every META exit gap: return 0 inside, whole change on next_trade, frozen inside (incl. carried prices '
          'the source did not flag, e.g. MAT 1974-09-06)', ok)
    # a book that wants to sell EHC inside its pause cannot: the sale waits for the next trade, the loss is booked
    j, x = col(P, 'EHC'), col(P, 'JNJ')
    a, b = row(P, '2003-03-18'), row(P, '2003-03-26')
    tg = mk_targets(P, [row(P, '2003-02-03'), a - 1], [[j, x], [x]], [[0.5, 0.5], [0.5]])
    st = pd.Timestamp('2003-01-02')
    f = stocks.fast_run(P, tg, 0.0, st, COST, TAX, DELAY, want_E=True, keep_book=True)
    e = stocks.run_engine(P, tg, 0.0, st, COST, TAX, DELAY)
    W, R, reb, FZ, NB, _ = stocks.frames(P, tg, 0.0)
    esc = engine.run(W, R, st, stocks.DEV_END, cost=COST, tax=TAX, delay=DELAY, rebal=reb)     # no frozen: escapes
    i0, _ = stocks._rows(P, st)
    cj = list(o for o in f['cols']).index(j)
    held = f['book'][:, cj]
    # inside the pause the stuck position only pays its proportional share of the other names' trade cost
    check('(c) EHC sale decided before the pause is blocked inside it and done on next_trade, after the -97%',
          held[a + 1 - i0] > 0 and held[b - 1 - i0] > 0 and held[b - i0] == 0
          and abs(held[b - 1 - i0] / held[a - i0] - 1) < 2e-3 and P.frozen[a + 1:b, j].all() and P.real[b, j]
          and f['trades'][0] >= 3)
    check('(c) fast path == engine.run on the gap (frozen honoured), the frozen-free run escapes the -97%',
          abs(f['final_at'][0] - e['final_at']) < 1e-12 and e['final_at'] < 0.8 * esc['final_at'],
          f"held final/escape {e['final_at'] / esc['final_at']:.3f}")


# ---------------------------------------------------------------- (d) series end
def test_series_end(P):
    print('== (d) series end: the day after the last price returns -h exactly once, then 0 ==')
    h = 0.3
    R = P.R(h); R0 = P.R(0.0)
    ended = np.flatnonzero((P.last >= 0) & (P.last < P.T - 1))
    L = P.last[ended]
    once = np.all(R[L + 1, ended] == -h)
    after = all(np.all(R[l + 2:, j] == 0) for j, l in zip(ended, L))
    inside = np.array_equal(np.delete(R, [], 0)[:, ended][np.arange(P.T)[:, None] <= L], R0[:, ended][np.arange(P.T)[:, None] <= L])
    n_h = int(np.sum(R == -h))
    check(f'(d) {len(ended)} ended series: one -h each on last+1, 0 after, unchanged before', once and after and inside
          and n_h == len(ended))
    check('(d) a series ending on the last panel row (2014-12-31) gets no haircut',
          not np.any(R[:, P.last == P.T - 1] == -h))
    # a held name through its end: the position drops by exactly (1 - h) once, is sold at the next decision
    cand = [j for j in ended if P.idx[P.last[j]].year in (2005, 2006) and P.member[P.last[j], j]
            and P.member[P.last[j] - 60, j] and P.real[P.last[j] - 60, j]]
    j = cand[0]; l = P.last[j]; x = col(P, 'JNJ')
    d0 = l - 60
    nxt = np.flatnonzero(dsl.reb_rows(P.idx, 'monthly'))
    d1 = int(nxt[nxt > l + 1][0])
    tg = mk_targets(P, [d0, d1], [[j, x], [x]], [[0.5, 0.5], [1.0]])
    st = P.idx[d0 - 20]
    f = stocks.fast_run(P, tg, h, st, COST, TAX, DELAY, keep_book=True)
    i0, _ = stocks._rows(P, st)
    cj = list(f['cols']).index(j); v = f['book'][:, cj]
    r1 = v[l + 1 - i0] / v[l - i0]
    flat = np.allclose(v[l + 1 - i0:d1 + DELAY - i0], v[l + 1 - i0])
    check(f'(d) held {P.label(j)}: value x{r1:.4f} (= 1 - h) the day after its last price, flat after, sold at the '
          'next decision', abs(r1 - (1 - h)) < 1e-12 and flat and v[d1 + DELAY - i0] == 0)
    check('(d) after the series end the name is not frozen (sellable) but cannot be bought',
          not P.frozen[l + 1:, j].any() and P.no_buy[l + 1:, j].all())


# ---------------------------------------------------------------- (e) costs and tax
def test_cost_tax(P):
    print('== (e) cost and tax are applied ==')
    tg = stocks.compile_targets(SPECS['mom'], P)
    st = stocks.WINDOWS['w86']
    r = {(c, t): stocks.fast_run(P, tg, 0.3, st, c, t, DELAY) for c in (0.0, COST) for t in (0.0, TAX)}
    g = lambda c, t: float(r[(c, t)]['cagr_at'][0])
    check('(e) zero-cost zero-tax > cost only, tax only > cost and tax', g(0, 0) > g(COST, 0) > g(COST, TAX)
          and g(0, 0) > g(0, TAX) > g(COST, TAX))
    check('(e) tax paid > 0 with tax, = 0 without; pre-tax CAGR unchanged by the final tax only when tax = 0',
          r[(COST, TAX)]['taxpaid'][0] > 0 and r[(COST, 0.0)]['taxpaid'][0] == 0
          and abs(r[(COST, 0.0)]['cagr_at'][0] - r[(COST, 0.0)]['cagr_pre'][0]) < 1e-15)
    s2 = dict(SPECS['mom'], cost=0.001)
    check('(e) spec cost below 0.30% is clamped up (cost only raised)',
          stocks.evaluate(s2, P, null=False, pit=False)['cost'] == dsl.MIN_COST)


# ---------------------------------------------------------------- (f) parity
def _cmp(f, e, b=0):
    E = f['E'][b] if 'E' in f else None
    dE = float(np.max(np.abs(E - e['E'].values))) if E is not None else 0.0
    return max(dE, abs(f['final_at'][b] - e['final_at']), abs(f['cagr_at'][b] - e['cagr_at']),
               abs(f['mdd'][b] - e['mdd']), abs(f['turn'][b] - e['turn']), abs(int(f['trades'][b]) - e['trades']))


def test_parity(P):
    print('== (f) fast path vs engine.run ==')
    # 30-name subset: EHC (exit gap), names that end while members, a stale-day name, big names
    ended = [j for j in np.flatnonzero((P.last > row(P, '1990-01-02')) & (P.last < P.T - 1)) if P.member[P.last[j], j]][:12]
    stale = [j for j in np.flatnonzero(P.stale[row(P, '1986-01-02'):].any(0))][:4]
    big = [col(P, t) for t in ('AAPL', 'JNJ', 'XOM', 'GE', 'IBM', 'KO', 'PG', 'MRK', 'PFE', 'WMT', 'MSFT', 'INTC', 'T')]
    cols = sorted(set([col(P, 'EHC')] + ended + stale + big))[:30]
    Ps = P.subset(cols)
    st = pd.Timestamp('1986-01-02')
    worst = 0.0
    for k, s in (('mom', spec({'score': 'ret(252, 21)', 'top': 5})),
                 ('week_iv', spec({'rebalance': 'week', 'score': '-vol(63)', 'top': 8, 'weight': 'invvol(63)'})),
                 ('gate', spec({'score': 'ret(126)', 'top': 6, 'exposure': 'up', 'else': {'QQQ': 0.5}},
                               signals={'up': 'price(_NDX) > sma(_NDX, 100)'})),
                 ('frac', spec({'score': 'ret(63)', 'top_pct': 0.3, 'weight': 'score', 'max_weight': 0.15,
                                'exposure': 'min(1, 0.15 / vol(_GSPC, 20))', 'else': {'CASH': 1.0}}))):
        tg = stocks.compile_targets(s, Ps)
        for h in (0.0, 0.3):
            for tax in (0.0, TAX):
                f = stocks.fast_run(Ps, tg, h, st, COST, tax, DELAY, want_E=True)
                e = stocks.run_engine(Ps, tg, h, st, COST, tax, DELAY)
                worst = max(worst, _cmp(f, e))
    blocked = int(Ps.frozen[row(P, '1986-01-02'):].sum())
    check(f'(f) 30-name subset, 4 specs x h x tax: fast path == engine.run (max abs diff {worst:.1e} < 1e-9)',
          worst < 1e-9, f'{blocked} frozen name-days in the subset')
    # full universe, the strategy itself
    tg = stocks.compile_targets(SPECS['mom'], P)
    t0 = time.time(); e = stocks.run_engine(P, tg, 0.3, stocks.WINDOWS['w86'], COST, TAX, DELAY); te = time.time() - t0
    t0 = time.time(); f = stocks.fast_run(P, tg, 0.3, stocks.WINDOWS['w86'], COST, TAX, DELAY, want_E=True); tf = time.time() - t0
    check(f'(f) full universe momentum: fast path == engine.run ({_cmp(f, e):.1e})', _cmp(f, e) < 1e-9,
          f'engine {te:.1f}s fast {tf:.2f}s')
    # null draws and the hazard draws vs engine.run, one book at a time
    st = stocks.WINDOWS['w86']
    nb = stocks.null_baskets(P, tg, st, DELAY, D=200)
    fn = stocks.fast_run(P, tg, 0.3, st, COST, TAX, DELAY, baskets=nb, D=200, want_E=True)
    dmax = 0.0
    for b in (0, 77, 199):
        tb = stocks.Targets(tg.dec, [c[b][c[b] >= 0] for c, _ in nb], [w[b][c[b] >= 0] for c, w in nb], tg.K, tg.elig,
                            tg.e, tg.els, tg.cap)
        e = stocks.run_engine(P, tb, 0.3, st, COST, TAX, DELAY)
        dmax = max(dmax, _cmp(fn, e, b))
    check(f'(f) null draws 0, 77, 199: fast (200 books at once) == engine.run ({dmax:.1e}; bar 0.05pp CAGR)', dmax < 1e-9)
    hz = stocks.hazard_hits(P, tg, st, D=3)
    fh = stocks.fast_run(P, tg, 0.0, st, COST, TAX, DELAY, D=3, hits=hz, want_E=True)
    dmax = 0.0
    for b in range(3):
        def edit(R, names, b=b):
            R = R.copy()
            for r_, (dd, cc) in hz.items():
                for d_, c_ in zip(dd, cc):
                    if d_ == b:
                        R.iloc[r_, R.columns.get_loc(f'S{c_}')] = -1.0
            return R
        e = stocks.run_engine(P, tg, 0.0, st, COST, TAX, DELAY, R_edit=edit)
        dmax = max(dmax, _cmp(fh, e, b))
    nh = sum(len(v[0]) for v in hz.values())
    check(f'(f) hazard draws (-100% hits) fast == engine.run with the hits in R ({dmax:.1e})', dmax < 1e-9, f'{nh} hits')


# ---------------------------------------------------------------- (g) null
def test_null(P):
    print('== (g) random-basket null ==')
    tg = stocks.compile_targets(SPECS['mom'], P)
    st = stocks.WINDOWS['w86']
    a = stocks.null_baskets(P, tg, st, DELAY)
    b = stocks.null_baskets(P, tg, st, DELAY)
    same = all(np.array_equal(x[0], y[0]) and np.array_equal(x[1], y[1]) for x, y in zip(a, b))
    c = stocks.null_baskets(P, tg, st, DELAY, seed=7)
    diff = any(not np.array_equal(x[0], y[0]) for x, y in zip(a, c))
    check('(g) null baskets deterministic for a seed (and a different seed differs)', same and diff)
    j0 = int(stocks._daily_pos(P, tg)[stocks._rows(P, st)[0] - DELAY])
    okE = all(tg.elig[j][x[0]].all() and x[0].shape[1] == len(tg.picks[j]) and
              all(len(set(r)) == len(r) for r in x[0]) for j, x in enumerate(a) if j >= j0)
    check('(g) each null basket: the strategy\'s name count, distinct names, all from its eligible set', okE)
    kept = np.array([np.mean([len(np.intersect1d(a[j][0][d], a[j - 1][0][d])) for d in range(0, 200, 10)])
                     for j in range(j0 + 1, len(a))])
    check('(g) null keeps the strategy\'s retained-name count (turnover matched)',
          np.abs(kept - tg.retain[j0 + 1:]).max() < 1.0, f'mean |diff| {np.abs(kept - tg.retain[j0 + 1:]).mean():.2f} names')
    f1 = stocks.fast_run(P, tg, 0.0, st, 0.0, 0.0, DELAY, baskets=a, D=200)
    f2 = stocks.fast_run(P, tg, 0.0, st, 0.0, 0.0, DELAY, baskets=b, D=200)
    ew = stocks.fast_run(P, stocks.ew_targets(P), 0.0, st, 0.0, 0.0, DELAY)
    med, e = float(np.median(f1['cagr_at'])), float(ew['cagr_at'][0])
    check('(g) null CAGRs deterministic; zero-cost null median within 1pp of equal-weight members (no-skill baseline)',
          np.array_equal(f1['cagr_at'], f2['cagr_at']) and abs(med - e) < 0.01, f'|diff| {abs(med - e) * 100:.2f}pp')


# ---------------------------------------------------------------- (h) seal
def test_seal(P):
    print('== (h) holdout seal: nothing after 2014-12-31 is ever indexed ==')
    sub = [col(P, t) for t in ('AAPL', 'JNJ', 'XOM', 'GE', 'IBM', 'KO', 'PG', 'MRK', 'PFE', 'WMT', 'EHC')]
    Ps = P.subset(sub)
    extra = pd.bdate_range('2015-01-02', periods=30)
    idx2 = Ps.idx.append(extra)
    rng = np.random.default_rng(3)
    big = lambda a, f: np.concatenate([a, f((30, a.shape[1]))])
    P2 = stocks.Panel(idx2, Ps.tickers, big(Ps.adj, lambda s: (rng.random(s) * 1e6).astype(np.float32)),
                      big(Ps.dvol, lambda s: (rng.random(s) * 1e12).astype(np.float32)),
                      big(Ps.member, lambda s: rng.random(s) < 0.5), big(Ps.stale, lambda s: np.zeros(s, bool)),
                      big(Ps.pause, lambda s: rng.random(s) < 0.5))
    check('(h) a panel with post-2014 rows is cut at load (same rows, same arrays)',
          P2.T == Ps.T and P2.idx.max() <= stocks.DEV_END and np.array_equal(P2.adj, Ps.adj, equal_nan=True))
    s = spec({'score': 'ret(252, 21)', 'top': 3})
    a = stocks.fast_run(Ps, stocks.compile_targets(s, Ps), 0.3, stocks.WINDOWS['w86'], COST, TAX, DELAY)
    b = stocks.fast_run(P2, stocks.compile_targets(s, P2), 0.3, stocks.WINDOWS['w86'], COST, TAX, DELAY)
    check('(h) results identical with or without the post-2014 rows', a['cagr_at'][0] == b['cagr_at'][0])
    # the file loader too
    buf = io.BytesIO()
    T2 = len(idx2)
    np.savez(buf, dates=idx2.values.astype('datetime64[D]').astype(np.int64), tickers=P2.tickers,
             adj=big(Ps.adj, lambda s: np.full(s, 5.0, np.float32)), dvol=big(Ps.dvol, lambda s: np.ones(s, np.float32)),
             member=np.packbits(big(Ps.member, lambda s: np.ones(s, bool)), axis=0),
             stale=np.packbits(big(Ps.stale, lambda s: np.zeros(s, bool)), axis=0), shape=np.array([T2, len(sub)]))
    fp = os.path.join(TMP, 'late.npz.xz')
    with lzma.open(fp, 'wb') as fh:
        fh.write(buf.getvalue())
    L = stocks.load(fp)
    check('(h) loader drops rows after 2014-12-31 from a file that has them', L.T == Ps.T and L.idx[-1] == Ps.idx[-1])
    check('(h) the seal guard raises on a later index', raises(lambda: stocks._sealed(idx2), stocks.SealError))
    F = stocks.gate_frame(SPECS['gate'], P.idx)
    Re, first = stocks.else_returns({'QQQ': 0.5}, P.idx)
    check('(h) gate frame, T-bill and ETF sleeve series on the stock calendar end <= 2014-12-31',
          F.index.max() <= stocks.DEV_END and Re.index.max() <= stocks.DEV_END and len(stocks.rf_on(P.idx)) == P.T
          and P.idx.max() == stocks.DEV_END)
    src = open(stocks.__file__).read()
    check('(h) every ETF series stocks.py reads is cut at DEV_END in code',
          src.count('<= DEV_END]') >= 4 and '_sealed(' in src)


# ---------------------------------------------------------------- (i) bar, (k) grid + CLI
def test_cli(P):
    print('== (i) bar answers 판정 불가 (개별주); (k) grid over top counts N; CLI line ==')
    from lab import bb
    s = SPECS['mom']
    check('(i) bb.judge quick and full -> 판정 불가 (개별주)', bb.judge(s, 'quick')['verdict'] == '판정 불가 (개별주)'
          and bb.judge(s, 'full', workers=1)['verdict'] == '판정 불가 (개별주)')
    check('(i) LabCandidate refuses a universe spec (never put on bar paths)',
          raises(lambda: bb.LabCandidate(s), bb.NotJudgeable))
    home = os.path.join(TMP, 'home'); os.makedirs(home, exist_ok=True)
    d = os.path.join(TMP, 'grid')
    write('grid/g.yaml', """
        name: g_top
        family: stk_grid
        universe: sp500
        grid: {K: [10, 20]}
        stock:
          score: "ret(252, 21)"
          top: "{K}"
        """)
    write('grid/z_etf.yaml', """
        name: etf_hold
        family: hold
        rules:
          - else: {QLD: 0.5}
        """)
    env = dict(os.environ, LAB_HOME=home, PYTHONDONTWRITEBYTECODE='1')
    run = lambda *a: subprocess.run([sys.executable, '-B', '-m', 'lab', 'run', *a], cwd=LAB, env=env,
                                    capture_output=True, text=True, timeout=1200)
    t0 = time.time()
    p = run(d, '--bar', 'quick')
    one = [x for x in p.stdout.splitlines() if x.startswith('[g_top')]
    ns = [x.split(' N=')[1].split()[0] for x in one]
    check('(k) grid over top: 2 points, own lines, N = 1, 2; batch with an ETF spec runs', p.returncode == 0
          and len(one) == 2 and ns == ['1', '2'] and any(x.startswith('[etf_hold') for x in p.stdout.splitlines()),
          p.stderr[-300:])
    check('(i) CLI line ends with 기준: 판정 불가 (개별주), every line <= 400 bytes',
          all('기준: 판정 불가 (개별주)' in x for x in one) and all(len(x.encode()) <= 400 for x in p.stdout.splitlines()
                                                         if x.startswith('[')), f'{time.time() - t0:.0f}s')
    check('(k) summary table lists the stock rows in their own block', '-- 개별주 2/2' in p.stdout)
    hs = sorted(f for f in os.listdir(os.path.join(home, 'out')) if f.endswith('_quick.json'))
    det = [json.load(open(os.path.join(home, 'out', f))) for f in hs]
    sd = [x for x in det if x['spec'].get('universe')]
    check('(k) two distinct hashes, detail JSON in LAB_HOME/out with the stock summary',
          len(sd) == 2 and sd[0]['hash'] != sd[1]['hash'] and all(x['dev_summary']['kind'] == 'stock' for x in sd))
    p2 = run(os.path.join(d, 'g.yaml'), '--bar', 'none')
    one2 = [x for x in p2.stdout.splitlines() if x.startswith('[')]
    check('(k) rerun: same hashes -> (중복), family N stays 2', len(one2) == 2 and all('(중복)' in x and 'N=2' in x
                                                                                for x in one2))
    from lab import ledger
    os.environ['LAB_HOME'] = home
    check('(k) ledger counts both points in the family', subprocess.run(
        [sys.executable, '-B', '-m', 'lab', 'ledger'], cwd=LAB, env=env, capture_output=True, text=True).stdout.count(
        'stk_grid: N=2') == 1)
    # a long name falls back to the compact line (still <= 400 bytes, the bar part kept)
    write('long/l.yaml', """
        name: stk_a_very_long_spec_name_that_would_push_the_line_past_four_hundred_bytes
        family: stk_grid2
        universe: sp500
        stock:
          score: "ret(252, 21)"
          top: 20
        """)
    p3 = run(os.path.join(TMP, 'long', 'l.yaml'), '--bar', 'quick')
    ln = [x for x in p3.stdout.splitlines() if x.startswith('[')]
    check('(i) long spec name: compact line <= 400 bytes keeps 기준 and the null 99% flag',
          len(ln) == 1 and len(ln[0].encode()) <= 400 and '판정 불가 (개별주)' in ln[0] and '99%선' in ln[0],
          f'{len(ln[0].encode()) if ln else 0} bytes')


def test_report(P):
    print('== report shape and speed ==')
    t0 = time.time()
    s = stocks.evaluate(SPECS['gate'], P)
    dt = time.time() - t0
    a = s['windows']['w86']
    keys = ('cons', 'base', 'extreme', 'ew_cons', 'ew_base', 'ndx', 'sharpe', 'g1_pass', 'null')
    check('report: every row present (cons, base, extreme, ew, ndx, sharpe, null), w71 too',
          all(k in a for k in keys) and 'cons' in s['windows']['w71'] and len(a['null']['cagrs']) == 200
          and len(a['extreme']['draws']) == 20, f'{dt:.1f}s for one spec (panel loaded)')
    check('report: one spec <= 60 s after the panel load', dt <= 60)
    check('report: gate data start recorded (NDX from 1985)', s['gate_from'] is not None and s['gate_from'] >= '1985')
    check('report: post-2014 delisting suffixes are masked in names', all(not (n.rsplit('-', 1)[-1].isdigit()
          and n.rsplit('-', 1)[-1] > '201412') for n in s['last_decision']['names']))
    line = stocks.dev_part(s)
    check('report: dev line has the headline parts', all(x in line for x in ('세후 보수', '기본', '극단', '동일가중',
                                                                          'NDX보유', '무작위 바구니', 'Sharpe', 'G1 1.1'))
          and len(line.encode()) < 360, f'{len(line.encode())} bytes')


if __name__ == '__main__':
    t0 = time.time()
    test_errors()
    P = stocks.load()
    test_functions(P)
    test_pit(P)
    test_membership(P)
    test_exit_gap(P)
    test_series_end(P)
    test_cost_tax(P)
    test_parity(P)
    test_null(P)
    test_seal(P)
    test_report(P)
    test_cli(P)
    print(f'{time.time() - t0:.0f}s')
    print('FAILS:', ', '.join(FAILS) if FAILS else 'none')
    sys.exit(1 if FAILS else 0)
