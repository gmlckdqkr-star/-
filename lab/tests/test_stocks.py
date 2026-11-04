"""Tests for the single-stock universe (spec `universe: sp500`, lab/stocks.py). Run as a script, in its own process:
    LAB_HOME=<fresh dir> python3 -B tests/test_stocks.py
Prints PASS/FAIL lines and identity / timing results only (no strategy performance numbers), ends with 'FAILS: ...'.
Needs the sealed stock panel (LAB_STOCKS, default research/data/us_stocks/sp500_le2014_v2.npz.xz) and the ETF panel.
"""
import io, json, lzma, math, os, re, subprocess, sys, tempfile, textwrap, time
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


def err(fn):
    """The message fn raises ('' if it does not raise)."""
    try:
        fn()
    except Exception as e:
        return str(e)
    return ''


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
    'mom': spec({'score': 'ret(231, 21)', 'top': 20}),
    'lowvol_iv': spec({'rebalance': 'quarter', 'score': '-vol(252)', 'filter': 'age() >= 252', 'top': 30,
                       'weight': 'invvol(63)', 'max_weight': 0.05}),
    'mix_pct': spec({'rebalance': 'week', 'score': 'rank(ret(126)) + csz(-beta(126)) + abs(min(sma_ratio(50), 1.2))',
                     'filter': 'high_dist(252) > -0.3 and not (log(age() + 1) < 5) or sma_ratio(20) > 1.3',
                     'top_pct': 0.05, 'weight': 'score', 'max_weight': 0.08}),
    'gate': spec({'score': 'ret(231, 21)', 'top': 10, 'exposure': 'up', 'else': {'CASH': 1.0}},
                 signals={'up': 'price(_NDX) > sma(_NDX, 200)'}),
    'gate_frac': spec({'score': 'max(ret(63), ret(21, 5))', 'top': 15, 'exposure': 'min(1, 0.2 / vol(_GSPC, 20))',
                       'exposure_every': 'rebalance', 'else': {'CASH': 1.0}}),
    # signals in the score (R1) on the point-in-time equal-weight member index (R2), and an _SP500EW exposure gate
    'sig_mix': spec({'score': 'up * rank(ret(231, 21)) + (1 - up) * rank(-vol(252))', 'filter': 'not (calm < 0) or '
                     'age() > 60', 'top': 20}, signals={'up': 'price(_SP500EW) > sma(_SP500EW, 200)',
                                                        'calm': '0.15 - vol(_SP500EW, 63)'}),
    'ew_gate': spec({'score': 'ret(126)', 'top': 15, 'exposure': 'up', 'else': {'CASH': 1.0}},
                    signals={'up': 'price(_SP500EW) > sma(_SP500EW, 200)'}),
}
EW = '_SP500EW'


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
    # refused inputs (source-dependent leaks L1, L3, L4)
    dv = 'dvol 사용 불가: 출처 의존 누출 — 1996~2006 거래대금 유무가 미래 상폐를 드러냄'
    check('(L1) dvol refused with the one-line Korean reason in score, filter, exposure and signals; not a function',
          raises(bad({'score': 'dvol(63)', 'top': 5}), ValueError, dv)
          and raises(bad({'score': 'rank(dvol(10)) + ret(5)', 'top': 5}), ValueError, dv)
          and raises(bad({'score': 'ret(20)', 'filter': 'dvol(20) > 1e7', 'top': 5}), ValueError, dv)
          and raises(bad({'score': 'ret(20)', 'top': 5, 'exposure': 'dvol(_NDX, 20) > 1'}), ValueError, dv)
          and raises(bad({'score': 'ret(20)', 'top': 5, 'exposure': 'up'}, signals={'up': 'dvol > 1'}), ValueError, dv)
          and 'dvol' not in stocks.SFUNCS and '\n' not in stocks.MSG_DVOL)
    vm = {e: err(bad(st, **kw)) for e, (st, kw) in {
        'volume': ({'score': 'ret(20)', 'filter': 'volume(20) > 0', 'top': 5}, {}),
        'dollar_volume': ({'score': 'rank(dollar_volume(5))', 'top': 5}, {}),
        'volume ': ({'score': 'ret(20)', 'top': 5, 'exposure': 'volume(_NDX) > 0'}, {}),
        'dollar_volume ': ({'score': 'ret(20)', 'top': 5, 'exposure': 'up'}, {'signals': {'up': 'dollar_volume > 1'}}),
    }.items()}
    check('(L1) volume / dollar_volume refused with a message that names what the spec wrote (stock and gate), '
          'not dvol', all(m.startswith(f'{e.strip()} 사용 불가: 출처 의존 누출') and 'dvol' not in m and '\n' not in m
                          for e, m in vm.items()), ' | '.join(m[:40] for m in vm.values()))
    check('(L4) price-level names refused (price, close, adj, sma, level), the reason names ratios',
          all(raises(bad({'score': e, 'top': 5}), ValueError, '수정주가 수준') for e in
              ('price()', 'close', 'adj(1)', 'sma(50)', 'level', 'log(price())', 'ret(20) / close')))
    check('(L3) first-price age refused (age() is the membership age)',
          all(raises(bad({'score': 'ret(20)', 'filter': e, 'top': 5}), ValueError, '첫 가격 날짜') for e in
              ('first_price() > 100', 'listing_age() > 1')))
    over = ('ret(261)', 'ret(240, 21)', 'ret(252, 21)', 'vol(261)', 'sma_ratio(261)', 'high_dist(261)', 'beta(261)',
            'rank(ret(300))', 'csz(-vol(500))', 'ret(20) + high_dist(1000)')
    w = '창 261행 > 260 사용 불가'
    check('(L3) a window above 260 rows refused for every function (ret n+skip, vol, sma_ratio, high_dist, beta, '
          'nested, filter, invvol weight) with the Korean reason',
          all(raises(bad({'score': e, 'top': 5}), ValueError, '> 260 사용 불가') for e in over)
          and raises(bad({'score': 'ret(261)', 'top': 5}), ValueError, w)
          and raises(bad({'score': 'ret(20)', 'filter': 'high_dist(300) > -0.2', 'top': 5}), ValueError, '> 260 사용 불가')
          and raises(bad({'score': 'ret(20)', 'top': 5, 'weight': 'invvol(261)'}), ValueError, w)
          and raises(bad({'score': 'ret(240, 21)', 'top': 5}), ValueError, '창 261행'))
    ok260 = ('ret(260)', 'ret(239, 21)', 'ret(1, 259)', 'vol(260)', 'sma_ratio(260)', 'high_dist(260)', 'beta(260)')
    check('(L3) exactly 260 rows accepted (ret(239, 21), vol(260), ..., invvol(260))',
          all(dsl.check_spec(spec({'score': e, 'top': 5})) for e in ok260)
          and dsl.check_spec(spec({'score': 'ret(20)', 'top': 5, 'weight': 'invvol(260)'})))
    # (R1) signals in score / filter: the per-stock rules still hold through them
    up = {'up': f'price({EW}) > sma({EW}, 200)'}
    sg = lambda st, sig=None: (lambda: dsl.check_spec(spec(st, signals=dict(up) if sig is None else sig)))
    check('(R1) a signal name is accepted in score and filter (bare name = one number per decision)',
          dsl.check_spec(spec({'score': 'up * rank(ret(231, 21)) + (1 - up) * rank(-vol(252))', 'top': 5},
                                  signals=up)) is not None
          and dsl.check_spec(spec({'score': 'ret(126)', 'filter': 'up or age() > 500', 'top': 5}, signals=up)))
    check('(R1) the 260-row cap still refuses long per-stock windows next to / multiplied by a signal (score, filter)',
          all(raises(sg({'score': e, 'top': 5}), ValueError, '> 260 사용 불가') for e in
              ('up * ret(300)', 'rank(ret(261)) * up + (1 - up) * rank(-vol(252))', 'up * rank(ret(240, 21))',
               'max(up, vol(500))'))
          and raises(sg({'score': 'ret(20)', 'filter': 'up and high_dist(300) > -0.2', 'top': 5}), ValueError,
                     '> 260 사용 불가')
          and raises(sg({'score': 'up * ret(20)', 'top': 5, 'weight': 'invvol(261)'}), ValueError, '창 261행'))
    check('(R1) a signal is never a window argument: ret(up), ret(231 * up), vol(up + 1) refused (window must be a '
          'number written in the expression)',
          all(raises(sg({'score': e, 'top': 5}), ValueError, 'whole number') for e in
              ('ret(up)', 'ret(231 * up)', 'vol(up + 1)', 'ret(231, up)')))
    check('(R1) dvol / volume refused inside signals read by the score, and next to a signal in the score',
          raises(sg({'score': 'up * ret(20)', 'top': 5}, {'up': f'dvol({EW}, 20) > 1'}), ValueError, dv)
          and raises(sg({'score': 'up * ret(20)', 'top': 5}, {'up': f'price({EW}) > 1 and volume > 0'}), ValueError,
                     'volume 사용 불가')
          and raises(sg({'score': 'up * dvol(20)', 'top': 5}), ValueError, dv)
          and raises(sg({'score': 'ret(20)', 'filter': 'up and dvol(20) > 1e7', 'top': 5}), ValueError, dv))
    nm = {k: err(sg({'score': f'{k} * ret(20)', 'top': 5}, {k: f'price({EW}) > 1'})) for k in
          ('rank', 'age', 'beta', 'close', 'dvol', 'volume', 'adj')}
    check('(R1) a signal named like a per-stock function or a refused input is refused (no name collision)',
          all(('per-stock function or a refused input' in m) or ('사용 불가' in m) for m in nm.values()),
          ' | '.join(f'{k}: {m[:30]}' for k, m in nm.items()))
    e1 = err(sg({'score': 'down * ret(20)', 'top': 5}))
    check('(R1) an undefined name in the score says unknown name and lists the signal names',
          "unknown name 'down'" in e1 and 'signals: up' in e1, e1[:120])
    check('(R1/R2) _SP500EW is a known series for stock signals; level() / unknown series still refused',
          dsl.check_spec(spec({'score': 'ret(20)', 'top': 5, 'exposure': 'up'}, signals=up)) is not None
          and raises(sg({'score': 'up * ret(20)', 'top': 5}, {'up': 'price(_SP500XX) > 1'}), ValueError, 'unknown name')
          and raises(sg({'score': 'up * ret(20)', 'top': 5}, {'up': 'level(QLD) > 1'}), ValueError, 'level(x)'))


# ---------------------------------------------------------------- per-stock functions vs direct formulas
def test_functions(P):
    print('== per-stock functions vs direct formulas ==')
    D = np.flatnonzero(dsl.reb_rows(P.idx, 'monthly'))
    D = D[D > 400]
    cx = stocks._Ctx(P, D)
    j = col(P, 'AAPL'); q = len(D) // 2; d = D[q]
    Pf, rr = P.P, P.rr
    r1 = cx.value('ret(231, 21)')[q, j]
    check('ret(231, 21) = P[t-21] / P[t-252] - 1 (12-1 momentum)', abs(r1 - (Pf[d - 21, j] / Pf[d - 252, j] - 1)) < 1e-12)
    r2 = cx.value('ret(239, 21)')[q, j]
    check('ret(239, 21) (260 rows, the cap) = P[t-21] / P[t-260] - 1', abs(r2 - (Pf[d - 21, j] / Pf[d - 260, j] - 1)) < 1e-12)
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
    ag = cx.value('age()')
    fm = np.array([np.flatnonzero(P.member[:, k])[0] if P.member[:, k].any() else P.T for k in range(P.N)])
    want = np.where(D[:, None] >= fm[None, :], (D[:, None] - fm[None, :]).astype(float), np.nan)
    gap = np.flatnonzero((fm - P.first > 500) & (fm < P.T))          # names priced long before they joined
    k = gap[0]; dk = np.flatnonzero(D >= fm[k])[0]
    check('age() = trading days since the FIRST MEMBERSHIP start (NaN before it), not since the first price (L3)',
          np.array_equal(ag, want, equal_nan=True) and ag[dk, k] == D[dk] - fm[k] and ag[dk, k] < D[dk] - P.first[k]
          and np.isnan(ag[D < fm[k], k]).all() and len(gap) > 10, f'{len(gap)} names priced > 500 rows before joining')
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
    # (L3) window floor: a window may not start before the first membership start (names joined after 1970-01-02)
    E0 = cx.E0
    late = E0 & (P.fm > P.f0)[None, :]
    want = {'ret(260)': 260, 'ret(239, 21)': 260, 'ret(21)': 21, 'ret(1, 125)': 126, 'vol(252)': 252, 'vol(2)': 2,
            'beta(126)': 126, 'sma_ratio(200)': 199, 'high_dist(252)': 251}
    av = {e: np.array_equal(np.isfinite(cx.value(e))[late], ag[late] >= n) for e, n in want.items()}
    k = gap[np.argmax(fm[gap] > P.f0)]; dk = np.flatnonzero((D >= fm[k]) & (D - fm[k] < 252) & (D - P.first[k] > 252))
    check('(L3) window floor: for every member that joined after 1970-01-02, a window value exists iff age() covers it '
          '(ret / vol / beta n: age() >= n; sma_ratio / high_dist n: age() >= n - 1), however long its price history',
          all(av.values()) and len(dk) > 0 and np.isnan(early[dk, k]).all() and late.sum() > 100000,
          f'{late.sum()} member cells; {P.label(k)}: {len(dk)} decisions with > 252 rows of prices but < 252 of membership')
    coh = E0 & (P.fm <= P.f0)[None, :]
    a252 = np.isfinite(cx.value('ret(252)'))
    check('(L3) names already members on 1970-01-02 (membership before it unknown) read from their first price',
          np.array_equal(a252[coh], (D[:, None] - 252 >= P.first[None, :])[coh]) and P.f0 == row(P, '1970-01-02')
          and int((P.fm <= P.f0).sum()) == 500)



# ---------------------------------------------------------------- leaks L1-L3: inputs the decisions may not read
def test_leaks(P):
    print('== leaks: dvol / stale / exit-gap pauses not read by any decision; availability checks ==')
    rng = np.random.default_rng(8)
    dv = (rng.random(P.dvol.shape) * 1e9).astype(np.float32); dv[rng.random(dv.shape) < 0.5] = np.nan
    st = rng.random(P.stale.shape) < 0.05
    st[np.flatnonzero(P.member.any(1))[::7]] = True                  # and every name stale on many whole rows
    Pd = stocks.Panel(P.idx, P.tickers, P.adj, dv, P.member, st, P.pause)                       # dvol, stale scrambled
    Pz = stocks.Panel(P.idx, P.tickers, P.adj, P.dvol, P.member, P.stale, np.zeros_like(P.pause))  # no exit gaps
    for k, s in SPECS.items():
        a = stocks.compile_targets(s, P)              # F built from the panel given (_SP500EW: from that panel)
        same = lambda b: (np.array_equal(a.dec, b.dec) and np.array_equal(a.elig, b.elig) and np.array_equal(a.e, b.e)
                          and all(np.array_equal(x, y) and np.array_equal(u, v)
                                  for x, y, u, v in zip(a.picks, b.picks, a.wts, b.wts)))
        check(f'(L) {k}: decisions identical with dvol + stale scrambled, and with every exit-gap pause removed',
              same(stocks.compile_targets(s, Pd)) and same(stocks.compile_targets(s, Pz)))
    ew = stocks.sp500ew(P)
    check('(R2) _SP500EW identical with dvol + stale scrambled and with every exit-gap pause removed (reads none)',
          np.array_equal(ew, stocks.sp500ew(Pd), equal_nan=True) and np.array_equal(ew, stocks.sp500ew(Pz), equal_nan=True))
    # (L3) pre-membership history: delete it, or give every later joiner a full one; no decision may change
    pre = (np.arange(P.T)[:, None] < P.fm[None, :]) & (P.fm > P.f0)[None, :]
    base = {}
    for k, s in SPECS.items():
        base[k] = (None, stocks.compile_targets(s, P))
    res, mk, ewv = {}, [], []
    for v in ('deleted', 'full random'):
        adj = P.adj.copy()
        lvl = np.broadcast_to(P.adj[np.minimum(P.fm, P.T - 1), np.arange(P.N)][None, :], pre.shape)[pre]
        adj[pre] = np.nan if v == 'deleted' else (lvl * np.exp(rng.normal(0, 0.03, lvl.shape))).astype(np.float32)
        Pv = stocks.Panel(P.idx, P.tickers, adj, P.dvol, P.member, P.stale, P.pause)
        for k, s in SPECS.items():
            F, a = base[k]
            b = stocks.compile_targets(s, Pv, F)       # F None: rebuilt from Pv (its _SP500EW too)
            res[k] = res.get(k, True) and (
                np.array_equal(a.dec, b.dec) and np.array_equal(a.elig, b.elig) and np.array_equal(a.e, b.e)
                and all(np.array_equal(x, y) and np.allclose(u, w, rtol=0, atol=1e-12)
                        for x, y, u, w in zip(a.picks, b.picks, a.wts, b.wts)))
        mk.append(np.array_equal(P.mkt(), Pv.mkt()))
        ewv.append(np.array_equal(stocks.sp500ew(P), stocks.sp500ew(Pv), equal_nan=True))
        del Pv, adj
    for k, ok in res.items():
        check(f'(L3) {k}: decisions identical with every later joiner\'s pre-membership prices deleted, and with a full '
              'random pre-membership history for each (window floor)', ok)
    check('(L3) the beta market does not read pre-membership prices either', all(mk) and pre.sum() > 10 ** 6)
    check('(L3/R2) _SP500EW does not read pre-membership prices (members at t-1 only): identical with them deleted / '
          'randomized', all(ewv) and len(ewv) == 2)
    e1, e2, e3 = stocks.ew_targets(P), stocks.ew_targets(Pd), stocks.ew_targets(Pz)
    check('(L) equal-weight benchmark and the beta market do not read stale / pause / dvol',
          all(np.array_equal(x, y) and np.array_equal(x, z) for x, y, z in zip(e1.picks, e2.picks, e3.picks))
          and np.array_equal(P.mkt(), Pd.mkt()) and np.array_equal(P.mkt(), Pz.mkt()))
    tg = stocks.compile_targets(SPECS['mom'], P); w = stocks.WINDOWS['w86']
    a = stocks.fast_run(P, tg, stocks.H_CONS, w, COST, TAX, DELAY)
    b = stocks.fast_run(Pd, stocks.compile_targets(SPECS['mom'], Pd), stocks.H_CONS, w, COST, TAX, DELAY)
    check('(L2) a stale day is a normal day at the carried price: frozen / no_buy never read stale, results identical '
          'with stale scrambled', np.array_equal(P.frozen, Pd.frozen) and np.array_equal(P.no_buy, Pd.no_buy)
          and a['cagr_at'][0] == b['cagr_at'][0] and a['trades'][0] == b['trades'][0])
    # availability: stale flags concentrate on names that end soon (why they are not read)
    end2 = np.zeros(P.stale.shape, bool)
    for j in np.flatnonzero(P.ended):
        end2[max(0, P.last[j] - 504):P.last[j] + 1, j] = True
    r1, r0 = P.stale[P.member & end2].mean(), P.stale[P.member & ~end2].mean()
    check(f'(L2) availability: member-day stale rate {r1:.3%} for names ending within 2 years vs {r0:.3%} for the rest '
          '(flag tied to the future, so unread)', r1 > 5 * r0)
    # exit gaps: documented halts; they overlap membership, so only the execution side reads them
    meta = json.load(open(stocks.meta_path()))
    inside, pz = [], np.zeros_like(P.pause)
    for g in meta['exit_gaps']:
        j = col(P, g['ticker']); a_, b_ = row(P, g['last_trade']), row(P, g['next_trade'])
        inside.append(int(P.member[a_ + 1:b_, j].sum())); pz[a_ + 1:b_, j] = True
    other = P.frozen & ~P.pause
    check(f'(L) exit-gap pauses = the META gaps only; member rows inside them {inside} (the gaps start before removal: '
          'decisions do not read them, above); every other frozen day is a non-member day with no price',
          np.array_equal(pz, P.pause) and not (other & P.member).any() and not (other & P.has).any() and sum(inside) > 0)
    hit = 0
    for k, s in SPECS.items():
        t2 = stocks.compile_targets(s, P)
        hit += sum(int(P.pause[np.minimum(d + DELAY, P.T - 1), p].sum()) for d, p in zip(t2.dec, t2.picks))
    print(f'   info: picks of the {len(SPECS)} test specs whose execution day falls inside an exit gap: {hit} '
          '(bought only when it trades again)')


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
        with np.errstate(over='ignore'):              # the rewritten rows compound to inf: only after t*
            ew, ew2 = stocks.sp500ew(P), stocks.sp500ew(P2)
        check(f'(a/R2) _SP500EW t*={ts}: identical up to t* on the rewritten panel (and different after)',
              np.array_equal(ew[:c + 1], ew2[:c + 1], equal_nan=True) and not np.allclose(ew[c + 1:], ew2[c + 1:]))
        for k, s in SPECS.items():
            F = stocks.gate_frame(s, P.idx, P) if stocks.needs_frame(s) else None
            F2 = None
            if F is not None:                          # the rewritten panel's own frame (_SP500EW from P2), then
                F2 = stocks.gate_frame(s, P2.idx, P2)   # every column after t* scrambled once more
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


# ---------------------------------------------------------------- R1 signals in score / filter, R2 _SP500EW
def _picks_eq(a, b, js=None):
    js = range(len(a.dec)) if js is None else js
    return all(np.array_equal(a.picks[j], b.picks[j]) and np.allclose(a.wts[j], b.wts[j], rtol=0, atol=1e-12)
               for j in js)


def test_signals(P):
    print('== R2 _SP500EW (point-in-time equal-weight members) and R1 signals in score / filter ==')
    from lab import data, ms1, bb
    # (R2) an independent recomputation from the panel file itself (not the Panel's derived arrays)
    t0 = time.time()
    z = np.load(io.BytesIO(lzma.open(stocks.STOCKS).read()))
    T0 = int(z['shape'][0]); d0 = pd.to_datetime(z['dates'], unit='D'); keep = np.asarray(d0 <= stocks.DEV_END)
    adj = z['adj'][keep].astype(np.float64); mem = np.unpackbits(z['member'], axis=0)[:T0].astype(bool)[keep]
    del z
    f0 = int(np.flatnonzero(mem.any(1))[0])
    lv = np.full(len(adj), np.nan); lv[f0] = 1.0; cnt = []
    for t in range(f0 + 1, len(adj)):
        a, b = adj[t - 1], adj[t]
        m = mem[t - 1] & np.isfinite(a) & (a > 0) & np.isfinite(b) & (b > 0)
        cnt.append(int(m.sum()))
        lv[t] = lv[t - 1] * (1.0 + (np.mean(b[m] / a[m] - 1.0) if m.any() else 0.0))
    ew = stocks.sp500ew(P)
    rel = np.nanmax(np.abs(ew[f0:] / lv[f0:] - 1.0))
    s = data.series(EW)
    check('(R2) _SP500EW = an independent per-day recomputation from the panel file (members at t-1 with a price at '
          't-1 and t, mean return, level 1.0 on 1970-01-02, NaN before); data.series gives the same values, <= 2014',
          P.idx[f0] == pd.Timestamp('1970-01-02') and ew[f0] == 1.0 and np.isnan(ew[:f0]).all() and rel < 1e-10
          and np.array_equal(np.isnan(ew), np.isnan(lv)) and s.index[0] == P.idx[f0] and s.index[-1] == stocks.DEV_END
          and np.array_equal(s.values, ew[f0:]) and min(cnt) >= 490,
          f'max rel diff {rel:.1e}, names per day {min(cnt)}..{max(cnt)}, {time.time() - t0:.0f}s')
    del adj, mem
    sp = data.series('_GSPC').reindex(P.idx[f0:]).pct_change(fill_method=None).values[1:]
    er = ew[f0 + 1:] / ew[f0:-1] - 1
    ok = np.isfinite(sp)
    print(f'   info: daily return correlation with _GSPC 1970-2014 {np.corrcoef(er[ok], sp[ok])[0, 1]:.3f} '
          f'({ok.sum()} days)')
    # (R2) causal: rewrite everything after t* (prices, membership, dvol, stale, pauses) in the regime years
    rng = np.random.default_rng(21)
    for ts in ('1973-01-11', '1982-08-12'):
        c = row(P, ts)
        adj2 = P.adj.copy(); mem2 = P.member.copy(); dv = P.dvol.copy(); st = P.stale.copy(); pz = P.pause.copy()
        adj2[c + 1:] = (np.nan_to_num(adj2[c + 1:], nan=10.0) * np.exp(rng.normal(0, 0.3, adj2[c + 1:].shape))
                        ).astype(np.float32)
        adj2[c + 1:][rng.random(adj2[c + 1:].shape) < 0.05] = np.nan
        mem2[c + 1:] = rng.random(mem2[c + 1:].shape) < 0.4
        dv[c + 1:] = 1e9; st[c + 1:] = rng.random(st[c + 1:].shape) < 0.05; pz[c + 1:] = rng.random(pz[c + 1:].shape) < .01
        P2 = stocks.Panel(P.idx, P.tickers, adj2, dv, mem2, st, pz)
        with np.errstate(over='ignore'):              # the rewritten rows compound to inf: only after t*
            e2 = stocks.sp500ew(P2)
        res = [np.array_equal(ew[:c + 1], e2[:c + 1], equal_nan=True) and not np.allclose(ew[c + 1:], e2[c + 1:])]
        for k in ('sig_mix', 'ew_gate'):
            a, b = stocks.compile_targets(SPECS[k], P), stocks.compile_targets(SPECS[k], P2)   # frames from each panel
            nd = int(np.searchsorted(a.dec, c, side='right'))
            res.append(np.array_equal(a.dec, b.dec) and np.array_equal(a.e[:c + 1], b.e[:c + 1]) and _picks_eq(a, b, range(nd))
                       and any(not np.array_equal(a.picks[j], b.picks[j]) for j in range(nd, len(a.dec)))
                       and sum(len(a.picks[j]) for j in range(nd)) > 0)
        check(f'(R2/a) t*={ts}: _SP500EW up to t* identical on a panel rewritten after t*; the signal-mixed score and '
              'the _SP500EW gate give the same decisions <= t* (and later ones change)', all(res), str(res))
        del P2, adj2, mem2, dv, st, pz
    for k in ('sig_mix', 'ew_gate'):
        tg = stocks.compile_targets(SPECS[k], P)
        pc = stocks.pit_check(SPECS[k], P, tg, stocks.gate_frame(SPECS[k], P.idx, P), n_cuts=4, seed=13)
        check(f'(R2/a) runtime cut check on {k} (gate frame rebuilt from each cut panel) passes', pc['ok'] and
              pc['cuts'] >= 3, str(pc))
    # (R1) the value used is the one at the decision close t (not t+1, not t-1)
    sx = spec({'score': 'up * rank(ret(231, 21)) + (1 - up) * rank(-vol(252))', 'top': 20},
              signals={'up': f'price({EW}) > 1'})
    D = np.flatnonzero(dsl.reb_rows(P.idx, 'monthly'))
    fr = lambda rows: pd.DataFrame({EW: np.where(np.isin(np.arange(P.T), rows), 2.0, 0.5)}, index=P.idx)
    hi, lo = stocks.compile_targets(sx, P, fr(np.arange(P.T))), stocks.compile_targets(sx, P, fr([]))
    at, nx, pv = (stocks.compile_targets(sx, P, fr(r)) for r in (D, D + 1, D - 1))
    live = [j for j in range(len(D)) if len(hi.picks[j])]
    differ = sum(not np.array_equal(hi.picks[j], lo.picks[j]) for j in live)
    check('(R1) signal read at the decision close t: up = 1 only on decision rows -> the up picks on every decision; '
          'up = 1 only on t+1 or only on t-1 -> the down picks', _picks_eq(at, hi) and _picks_eq(nx, lo)
          and _picks_eq(pv, lo) and differ > 0.9 * len(live), f'{differ}/{len(live)} decisions differ between regimes')
    F = stocks.gate_frame(SPECS['sig_mix'], P.idx, P)
    up_t = (F[EW] > F[EW].rolling(200, min_periods=200).mean()).values
    s1 = spec({'score': sx['stock']['score'], 'top': 20}, signals={'up': SPECS['sig_mix']['signals']['up']})
    real = stocks.compile_targets(s1, P)
    inf_j = [j for j in range(len(D)) if real.sig_ok[j]]
    flips = sum(up_t[D[j]] != up_t[min(D[j] + 1, P.T - 1)] for j in inf_j)
    check('(R1) real _SP500EW regime: every informed decision holds the up picks when EW > SMA200 at its close, the '
          'down picks otherwise (independent rolling mean)',
          all(np.array_equal(real.picks[j], (hi if up_t[D[j]] else lo).picks[j]) for j in inf_j) and len(inf_j) > 500,
          f'{len(inf_j)} decisions, {int(sum(up_t[D[j]] for j in inf_j))} up; the regime flips the next day on {flips}')
    # (R1) warm-up and NaN: not informed -> no eligible name (CASH), never "missing = 0"
    sv = F[EW].rolling(200, min_periods=200).mean().first_valid_index()
    r0 = int(D[D >= row(P, sv)][0])
    tg = stocks.compile_targets(SPECS['sig_mix'], P)
    check('(R1) warm-up: the first informed decision is the first one with sma(_SP500EW, 200) defined (1970-10); '
          'every decision before it holds no name, the ones after hold 20',
          stocks.signal_row(tg) == r0 and all(len(p) == 0 for j, p in enumerate(tg.picks) if D[j] < r0)
          and all(len(p) == 20 for j, p in enumerate(tg.picks) if D[j] >= r0) and P.idx[r0].year == 1970,
          f'signal_from {P.idx[r0].date()}')
    a_, b_ = row(P, '1990-03-01'), row(P, '1990-08-31')
    Fn = F.copy(); Fn.iloc[a_:b_ + 1, 0] = np.nan                  # a hole in the series
    sn = spec({'score': 'rank(ret(126)) + v', 'top': 20}, signals={'v': f'ret({EW}, 20)'})
    ref = stocks.compile_targets(spec({'score': 'rank(ret(126))', 'top': 20}), P)
    tn = stocks.compile_targets(sn, P, Fn)
    okn = np.isfinite((Fn[EW] / Fn[EW].shift(20) - 1).values)[D]          # independent: the 20-day return exists
    bad = (D >= a_) & (D <= b_ + 20)
    check('(R1) a numeric signal that is NaN at t (hole + its 20-row window): those decisions hold no name; every '
          'other decision is the plain score\'s (a signal shared by all names leaves the ranking)',
          all(len(tn.picks[j]) == 0 for j in range(len(D)) if not okn[j]) and np.array_equal(tn.sig_ok, okn)
          and np.array_equal(~okn & (D > row(P, '1971-01-04')), bad) and bad.sum() >= 6
          and _picks_eq(tn, ref, [j for j in range(len(D)) if okn[j]]), f'{int(bad.sum())} decisions not informed')
    sb = spec({'score': 'ret(126)', 'filter': 'not up', 'top': 20}, signals={'up': f'price({EW}) > sma({EW}, 20)'})
    tb = stocks.compile_targets(sb, P, Fn)
    pu = Fn[EW]; ups = (pu > pu.rolling(20, min_periods=20).mean()).values
    want = np.isfinite(pu.values) & np.isfinite(pu.rolling(20, min_periods=20).mean().values)
    check('(R1) a boolean signal over an undefined input (price / sma NaN reads False in the DSL): `not up` does NOT '
          'pass every name there; those decisions hold no name, informed ones follow up at t',
          np.array_equal(tb.sig_ok, want[D]) and all(len(tb.picks[j]) == 0 for j in range(len(D)) if not want[D[j]])
          and all((len(tb.picks[j]) == 0) == bool(ups[D[j]]) for j in range(len(D)) if want[D[j]] and len(ref.picks[j]))
          and (~want[D] & (D > row(P, '1971-01-04'))).sum() >= 6)
    # (R1) the warm-up marker and the window start, like the gate's (a TLT regime: data from 2002-07)
    stl = spec({'score': 'up * rank(ret(231, 21)) + (1 - up) * rank(-vol(252))', 'top': 20},
               signals={'up': 'price(TLT) > sma(TLT, 200)'})
    se = stocks.evaluate(stl, P, null=False, pit=False)
    tl = data.series('TLT').reindex(P.idx).ffill().rolling(200, min_periods=200).mean().first_valid_index()
    rt = int(D[D >= row(P, tl)][0])
    a86 = se['windows']['w86']
    ms = stocks.ms1_stream(stl, P)
    check('(R1) a late signal (TLT SMA200, 2003): signal_from = its first informed decision, the 1986 window and the '
          'MS1 stream start delay rows later, marked (신호 2003-06~) / (신호03-06~), the 1971 row (신호 2003~)',
          se['signal_from'] == str(P.idx[rt].date()) and a86['start'] == str(P.idx[rt + DELAY].date())
          and a86['start_by'] == 'signal' and f"(신호 {se['signal_from'][:7]}~)" in stocks.dev_part(se)
          and f"(신호 {se['signal_from'][:4]}~)" in stocks.dev_part(se)
          and f"(신호{se['signal_from'][2:7]}~)" in stocks.dev_part(se, compact=2) and ms['start'] == a86['start']
          and se['signals']['gaps'] == 0 and '게이트' not in stocks.dev_part(se), f"{se['signal_from']} -> {a86['start']}")
    # (R1) ETF-DSL window rules on the index; a series name is not a value
    bw = {e: err(lambda e=e: stocks.compile_targets(spec({'score': 'up * ret(20)', 'top': 5}, signals={'up': e}), P, F))
          for e in (f'sma({EW}, 0) > 1', f'ret({EW}, -5) > 0', f'lag(price({EW}), -1) > 1')}
    check('(R2) the ETF DSL window rules on _SP500EW: window / lag 0 or negative refused; a long index window is an '
          'ETF-DSL window (allowed, not a per-stock one)',
          all('integer >= 1' in m for m in bw.values())
          and len(stocks.compile_targets(spec({'score': 'up * ret(20)', 'top': 5}, signals={'up': f'price({EW}) > '
                                              f'sma({EW}, 400)'}), P, F).dec) == len(D), str(list(bw.values()))[:160])
    e2 = err(lambda: stocks.compile_targets(spec({'score': 'x * ret(20)', 'top': 5}, signals={'x': EW}), P))
    check('(R1) a signal that is only a series name (x: _SP500EW) is refused in a score with a readable reason',
          'is the series name' in e2, e2[:100])
    # (R2) where it may go: ETF specs (dev only), bar, MS1, G1
    es = dict(name='etf_ew', family='tst', signals={'up': f'price({EW}) > sma({EW}, 200)'},
              rules=[{'when': 'up', 'hold': {'QLD': 1.0}}, {'else': {'CASH': 1.0}}])
    Fe, Re, _, _ = data.build(['QLD', 'QQQ']); Fe = Fe[Fe.index <= stocks.DEV_END]; Re = Re[Re.index <= stocks.DEV_END]
    We = dsl.compile_weights(es, Fe, ['QLD', 'QQQ'], Re)
    pe = data.price_for_signal(Fe, EW)
    want = (pe > pe.rolling(200, min_periods=200).mean()).astype(float).values
    tc = dsl.truncation_check(es, Fe, ['QLD', 'QQQ'], Re, n_cuts=2, seed=3)
    check('(R2) ETF spec (dev only): _SP500EW on the ETF frame = the stock-calendar series carried onto it (from '
          '1985-10 like any panel key), weights follow it, dev truncation check passes',
          np.array_equal(pe.values, pd.Series(ew, P.idx).reindex(Fe.index).ffill().values, equal_nan=True)
          and np.array_equal(We['QLD'].values, want) and tc['ok'], f'frame from {Fe.index[0].date()}')
    jb = bb.judge(es, 'quick'); el = ms1.eligibility(es)
    check('(R2) ETF spec reading _SP500EW: bar -> REJECT (version impossible), MS1 -> 해당 없음 (읽는 계열 _SP500EW)',
          jb['verdict'] == 'REJECT (version impossible)' and EW in jb['reason'] and el[0] is False
          and el[1].startswith(f'읽는 계열 {EW}'), f"{jb['reason'][:60]} | {el[1]}")
    gok, gi = ms1._stock_gate(SPECS['ew_gate'])
    gt = ms1.fmt_gate(dict(gate=True, na=gi), 1)[0]
    mix = spec({'score': 'up * ret(126) + (1 - up) * ret(21)', 'top': 15, 'exposure': 'g'},
               signals={'up': SPECS['ew_gate']['signals']['up'], 'g': 'price(_NDX) > sma(_NDX, 200)'})
    mok, mg = ms1._stock_gate(mix)
    check('(R2) stock gate reading _SP500EW -> G1 게이트 해당 없음 (읽는 계열 _SP500EW ..); an NDX gate next to a score-only '
          '_SP500EW signal keeps its G1 (the gate spec carries only the signals the exposure reads)',
          gok is False and gt.startswith(f'G1 게이트 해당 없음 (읽는 계열 {EW}') and mok is True
          and mg['signals'] == {'g': mix['signals']['g']}, gt)
    m2 = spec({'score': 'up * ret(126) + (1 - up) * ret(21)', 'top': 15, 'exposure': 'g'},
              signals={'up': 'price(TLT) > sma(TLT, 200)', 'g': 'price(_NDX) > sma(_NDX, 200)'})
    F2 = stocks.gate_frame(m2, P.idx, P)
    rg, _ = stocks.gate_valid(m2, P, F2)
    nd = data.series('_NDX').reindex(P.idx).ffill().rolling(200, min_periods=200).mean().first_valid_index()
    check('(R1) the gate is the exposure + the signals it reads: a score-only TLT signal moves signal_from (2003), '
          'not the NDX gate\'s warm-up (1986-07) or its data columns',
          P.idx[rg] == nd and stocks.gate_cols(m2, F2) == ['_NDX'] and sorted(F2.columns) == ['TLT', '_NDX']
          and stocks.signal_row(stocks.compile_targets(m2, P, F2)) == rt, f'gate {P.idx[rg].date()}')


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
        ok_mem = P.member[rows_abs - DELAY, names].all() and P.has[rows_abs - DELAY, names].all()
        first_mem = np.array([np.flatnonzero(P.member[:, j])[0] for j in names])
        ok_first = (rows_abs >= first_mem + DELAY).all()
        # a name bought while not yet a member would also show in the decisions: none outside membership
        dec_ok = all(P.member[tg.dec[j], p].all() and P.has[tg.dec[j], p].all() for j, p in enumerate(tg.picks))
        check(f'(b) {k}: {len(starts)} holding spells start >= membership start + delay, bought on member rows',
              len(starts) > 50 and ok_mem and ok_first and dec_ok)
    # a name removed from the index is sold at the next decision: no pick outside membership
    tg = stocks.compile_targets(SPECS['mom'], P)
    left = [(j, p) for j, p in enumerate(tg.picks) if not P.member[tg.dec[j], p].all()]
    check('(b) no decision picks a non-member (removed names drop out at the next rebalance)', not left)


# ---------------------------------------------------------------- (c) exit gaps
def test_exit_gap(P):
    print('== (c) exit gaps: the price is carried through the pause, the held name books the whole change ==')
    meta = json.load(open(stocks.meta_path()))
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
def _held_through(P, j, h):
    """Hold name j and JNJ half / half from 60 rows before j's last price, sell j at the first decision after it.
    -> (value ratio of j's position the day after its last price, flat after and sold at the next decision)."""
    l = P.last[j]; x = col(P, 'JNJ')
    d0 = l - 60
    nxt = np.flatnonzero(dsl.reb_rows(P.idx, 'monthly'))
    d1 = int(nxt[nxt > l + 1][0])
    tg = mk_targets(P, [d0, d1], [[j, x], [x]], [[0.5, 0.5], [1.0]])
    st = P.idx[d0 - 20]
    f = stocks.fast_run(P, tg, h, st, COST, TAX, DELAY, keep_book=True)
    i0, _ = stocks._rows(P, st)
    v = f['book'][:, list(f['cols']).index(j)]
    return v[l + 1 - i0] / v[l - i0], bool(np.allclose(v[l + 1 - i0:d1 + DELAY - i0], v[l + 1 - i0])
                                           and v[d1 + DELAY - i0] == 0)


def test_series_end(P):
    print('== (d) series end: one delisting return the day after the last price, then 0 (classified headline: '
          'fail-type -50%, merger-type 0; stress: every end -30%) ==')
    R0 = P.R(0.0)
    ended = np.flatnonzero(P.ended)
    L = P.last[ended]
    below = np.arange(P.T)[:, None] <= L
    for nm, h in (('all-30', stocks.H_ALL), ('classified', stocks.H_CONS)):
        R = P.R(h)
        want = (np.where(P.fail[ended], -h[0], -h[1]) if isinstance(h, tuple) else np.full(len(ended), -h)) + 0.0
        on = np.array_equal(R[L + 1, ended], want)
        after = all(np.all(R[l + 2:, j] == 0) for j, l in zip(ended, L))
        inside = np.array_equal(R[:, ended][below], R0[:, ended][below])
        exact = {tuple(x) for x in np.argwhere(R != R0)} == {(l + 1, j) for j, l, w in zip(ended, L, want) if w != 0}
        check(f'(d) {nm}: {len(ended)} ended series, one delisting return each on last+1 ({int((want != 0).sum())} '
              'non-zero), 0 after, unchanged before, nothing else differs from h=0', on and after and inside and exact)
    nf = int(P.fail.sum()); er = P.end_ret[ended]
    check(f'(d) classification: {nf} fail-type (return over the 250 rows to the last price < -30%), '
          f'{len(ended) - nf} merger-type; every ended series has >= 20 rows to classify',
          np.isfinite(er).all() and np.array_equal(P.fail[ended], er < -0.30) and not P.fail[~P.ended].any()
          and np.isnan(P.end_ret[~P.ended]).all())
    j = ended[np.flatnonzero(P.fail[ended])[0]]; l = P.last[j]; w = min(250, l - P.first[j])
    check('(d) end_ret = P[last] / P[last - min(250, last - first)] - 1 (prices <= the last price only)',
          abs(P.end_ret[j] - (P.adj[l, j] / P.P[l - w, j] - 1)) < 1e-9)
    check('(d) a series ending on the last panel row (2014-12-31) gets no delisting return',
          all(np.array_equal(P.R(h)[:, P.last == P.T - 1], R0[:, P.last == P.T - 1]) for h in (stocks.H_ALL, stocks.H_CONS)))
    # the classification is causal at the end: the panel cut right after a series end classifies it the same
    rng = np.random.default_rng(4)
    samp = list(rng.choice(ended[P.fail[ended]], 5, replace=False)) + list(rng.choice(ended[~P.fail[ended]], 5, replace=False))
    ok = True
    for j in samp:
        Ps = P.subset([j, col(P, 'JNJ')]); c = int(P.last[j]) + 2
        Pc = Ps.cut(c)
        ok &= bool(Pc.ended[0] and Pc.fail[0] == P.fail[j] and Pc.end_ret[0] == P.end_ret[j]
                   and Pc.R(stocks.H_CONS)[c - 1, 0] == P.R(stocks.H_CONS)[c - 1, j])
    check('(d) causal: 10 ended series (5 fail, 5 merger) classified the same on the panel cut the day after their '
          'last price', ok)
    # held names through their end: the position changes by the delisting return exactly once, sold next decision
    okj = lambda j: (P.idx[P.last[j]].year >= 1975 and P.member[P.last[j] - 60, j] and P.real[P.last[j] - 58, j]
                     and P.has[P.last[j] - 60, j])
    jf = [j for j in ended if P.fail[j] and okj(j)][0]
    jm = [j for j in ended if not P.fail[j] and okj(j) and P.idx[P.last[j]].year in (2005, 2006)][0]
    rf, sf = _held_through(P, jf, stocks.H_CONS)
    rm, sm = _held_through(P, jm, stocks.H_CONS)
    r30, s30 = _held_through(P, jm, stocks.H_ALL)
    r0, s0 = _held_through(P, jf, 0.0)
    check(f'(d) held fail-type {P.label(jf)}: x{rf:.4f} (= 0.5) the day after its last price (x{r0:.0f} at h=0); held '
          f'merger-type {P.label(jm)}: x{rm:.4f} (= 1; all-30 stress x{r30:.2f}); flat after, sold at the next decision',
          abs(rf - 0.5) < 1e-12 and abs(rm - 1.0) < 1e-12 and abs(r30 - 0.7) < 1e-12 and abs(r0 - 1.0) < 1e-12
          and sf and sm and s30 and s0)
    l = P.last[jf]
    check('(d) after the series end the name is not frozen (sellable) but cannot be bought',
          not P.frozen[l + 1:, jf].any() and P.no_buy[l + 1:, jf].all())


def test_classified_synthetic():
    print('== (d) classified delisting rule on a constructed panel ==')
    T = 700
    idx = pd.bdate_range('1990-01-01', periods=T)
    nm = ['FAIL', 'MERGE', 'SHORT', 'YOUNG', 'ALIVE', 'EDGE_IN', 'EDGE_OUT']
    t = np.arange(T, dtype=float)
    adj = np.full((T, len(nm)), np.nan)
    adj[:401, 0] = 100 * np.where(t[:401] < 150, 1.0, 0.5 ** ((t[:401] - 150) / 250))   # -50% over its last 250 rows
    adj[:401, 1] = 100 * (1 + 0.001 * t[:401])            # rising into its end (an acquisition)
    adj[390:401, 2] = np.linspace(50, 20, 11)             # -60% but only 10 rows of prices: not classified -> 0
    adj[300:451, 3] = np.linspace(80, 48, 151)            # 150 rows of prices, -40%: fail-type on the shorter window
    adj[:, 4] = 10.0                                      # alive to the panel end: no delisting return
    adj[:501, 5] = np.where(t[:501] <= 250, 100.0, 70.5)  # -29.5% over the window: merger-type
    adj[:501, 6] = np.where(t[:501] <= 250, 100.0, 69.5)  # -30.5%: fail-type
    adj = adj.astype(np.float32)
    mem = np.ones((T, len(nm)), bool)
    Q = stocks.Panel(idx, np.array(nm), adj, np.full(adj.shape, np.nan, np.float32), mem, np.zeros_like(mem))
    want = np.array([True, False, False, True, False, False, True])
    check('(d) synthetic: fail-type = return over 250 rows (or what exists, >= 20) to the last price < -30%',
          np.array_equal(Q.fail, want) and np.isnan(Q.end_ret[2]) and abs(Q.end_ret[3] + 0.4) < 1e-6
          and abs(Q.end_ret[0] + 0.5) < 1e-6, ' '.join(f'{a}:{b:.3f}' for a, b in zip(nm, Q.end_ret)))
    lastrow = np.array([400, 400, 400, 450, -1, 500, 500])
    ok = np.array_equal(Q.last, np.where(lastrow < 0, T - 1, lastrow))
    for h, vals in ((stocks.H_CONS, [-0.5, 0, 0, -0.5, None, 0, -0.5]), (stocks.H_ALL, [-0.3] * 4 + [None, -0.3, -0.3]),
                    (0.0, [0, 0, 0, 0, None, 0, 0])):
        R = Q.R(h)
        for k, v in enumerate(vals):
            if v is None:
                ok &= bool(np.all(R[1:, k] == 0))
            else:
                l = lastrow[k]
                ok &= bool(R[l + 1, k] == v and np.all(R[l + 2:, k] == 0) and np.array_equal(R[:l + 1, k], Q.rr[:l + 1, k]))
    check('(d) synthetic: R(classified) -50% on last+1 for fail-type, 0 for merger-type / unclassified; all-30 -30% '
          'for every end; once each, 0 after, nothing before changes', ok)
    adj2 = adj.copy(); adj2[401:, [4]] = 1e6                     # rewrite everything after FAIL's end
    adj2[:150, 0] = 1.0                                           # and FAIL's prices before its 250-row window
    Q2 = stocks.Panel(idx, np.array(nm), adj2, np.full(adj.shape, np.nan, np.float32), mem, np.zeros_like(mem))
    Qc = Q.cut(402)
    check('(d) synthetic: the class reads only the own prices of the name in the window up to its last price (cut after '
          'the end and rewritten other rows give the same class and return)',
          Q2.fail[0] and Q2.end_ret[0] == Q.end_ret[0] and np.array_equal(Qc.fail[:3], Q.fail[:3])
          and np.array_equal(Qc.R(stocks.H_CONS)[401, :3], Q.R(stocks.H_CONS)[401, :3]))
    tg = mk_targets(Q, [100], [[0, 1]], [[0.5, 0.5]])
    st = idx[50]
    i0, _ = stocks._rows(Q, st)
    res = {}
    for k, h in (('cls', stocks.H_CONS), ('all30', stocks.H_ALL)):
        f = stocks.fast_run(Q, tg, h, st, COST, TAX, DELAY, keep_book=True)
        e = stocks.run_engine(Q, tg, h, st, COST, TAX, DELAY)
        v = f['book'][:, :2]
        res[k] = (v[401 - i0] / v[400 - i0], abs(f['final_at'][0] - e['final_at']))
    check('(d) synthetic book holding FAIL and MERGE through their end: classified x0.5 / x1.0, all-30 x0.7 / x0.7 '
          '(fast path == engine.run)', np.allclose(res['cls'][0], [0.5, 1.0], rtol=0, atol=1e-12)
          and np.allclose(res['all30'][0], [0.7, 0.7], rtol=0, atol=1e-12) and max(res['cls'][1], res['all30'][1]) < 1e-12)


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
    for k, s in (('mom', spec({'score': 'ret(231, 21)', 'top': 5})),
                 ('week_iv', spec({'rebalance': 'week', 'score': '-vol(63)', 'top': 8, 'weight': 'invvol(63)'})),
                 ('gate', spec({'score': 'ret(126)', 'top': 6, 'exposure': 'up', 'else': {'QQQ': 0.5}},
                               signals={'up': 'price(_NDX) > sma(_NDX, 100)'})),
                 ('frac', spec({'score': 'ret(63)', 'top_pct': 0.3, 'weight': 'score', 'max_weight': 0.15,
                                'exposure': 'min(1, 0.15 / vol(_GSPC, 20))', 'else': {'CASH': 1.0}}))):
        tg = stocks.compile_targets(s, Ps)
        for h in (0.0, stocks.H_ALL, stocks.H_CONS):
            for tax in (0.0, TAX):
                f = stocks.fast_run(Ps, tg, h, st, COST, tax, DELAY, want_E=True)
                e = stocks.run_engine(Ps, tg, h, st, COST, tax, DELAY)
                worst = max(worst, _cmp(f, e))
    blocked = int(Ps.frozen[row(P, '1986-01-02'):].sum())
    check(f'(f) 30-name subset, 4 specs x (base, all-30, classified) x tax: fast path == engine.run (max abs diff '
          f'{worst:.1e} < 1e-9)',
          worst < 1e-9, f'{blocked} frozen name-days in the subset')
    # full universe, the strategy itself
    tg = stocks.compile_targets(SPECS['mom'], P)
    t0 = time.time(); e = stocks.run_engine(P, tg, stocks.H_CONS, stocks.WINDOWS['w86'], COST, TAX, DELAY); te = time.time() - t0
    t0 = time.time(); f = stocks.fast_run(P, tg, stocks.H_CONS, stocks.WINDOWS['w86'], COST, TAX, DELAY, want_E=True); tf = time.time() - t0
    check(f'(f) full universe momentum: fast path == engine.run ({_cmp(f, e):.1e})', _cmp(f, e) < 1e-9,
          f'engine {te:.1f}s fast {tf:.2f}s')
    # null draws and the hazard draws vs engine.run, one book at a time
    st = stocks.WINDOWS['w86']
    nb = stocks.null_baskets(P, tg, st, DELAY, D=200)
    fn = stocks.fast_run(P, tg, stocks.H_CONS, st, COST, TAX, DELAY, baskets=nb, D=200, want_E=True)
    dmax = 0.0
    for b in (0, 77, 199):
        tb = stocks.Targets(tg.dec, [c[b][c[b] >= 0] for c, _ in nb], [w[b][c[b] >= 0] for c, w in nb], tg.K, tg.elig,
                            tg.e, tg.els, tg.cap)
        e = stocks.run_engine(P, tb, stocks.H_CONS, st, COST, TAX, DELAY)
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
    s = spec({'score': 'ret(231, 21)', 'top': 3})
    a = stocks.fast_run(Ps, stocks.compile_targets(s, Ps), stocks.H_CONS, stocks.WINDOWS['w86'], COST, TAX, DELAY)
    b = stocks.fast_run(P2, stocks.compile_targets(s, P2), stocks.H_CONS, stocks.WINDOWS['w86'], COST, TAX, DELAY)
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
          score: "ret(231, 21)"
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
    num = lambda x, pat: (lambda m: m and next(g for g in m.groups() if g is not None))(re.search(pat, x))
    got = sorted((num(x, r'세후 ?보수 (-?\d+\.\d)%'), num(x, r'일괄-30% (-?\d+\.\d)%|일괄30 (-?\d+\.\d)')) for x in one)
    js = sorted((f"{100 * x['dev_summary']['windows']['w86']['cons']['cagr_at']:.1f}",
                 f"{100 * x['dev_summary']['windows']['w86']['all30']['cagr_at']:.1f}") for x in sd)
    check("(k) the line's headline (세후 보수) = the classified row in the detail JSON, 일괄-30% = its all-30 row",
          got == js and all(x['dev_summary']['h_cons']['rule'] == 'classified' and x['dev_summary']['h_cons']['fail'] == -0.5
                            and x['dev_summary']['h_cons']['merger'] == 0 for x in sd), f'{got} vs {js}')
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
          score: "ret(231, 21)"
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
    keys = ('cons', 'base', 'all30', 'extreme', 'ew_cons', 'ew_base', 'ndx', 'sharpe', 'g1_pass', 'null', 'held_ends')
    check('report: every row present (cons = classified, base, all30, extreme, ew, ndx, sharpe, null, held ends), '
          'w71 too',
          all(k in a for k in keys) and 'cons' in s['windows']['w71'] and len(a['null']['cagrs']) == 200
          and len(a['extreme']['draws']) == 20, f'{dt:.1f}s for one spec (panel loaded)')
    check('report: one spec <= 60 s after the panel load', dt <= 60)
    check('report: gate data start recorded (NDX from 1985)', s['gate_from'] is not None and s['gate_from'] >= '1985')
    nm = s['last_decision']['names']
    check('report: last-decision names are point-in-time ids (S####), never source symbols',
          len(nm) > 0 and all(re.fullmatch(r'S\d{4}', n) for n in nm) and not set(nm) & set(P.tickers)
          and 'point-in-time ids' in s['last_decision']['names_are'])
    check('report: h_cons stores the merger-type return as 0.0, not -0.0',
          s['h_cons']['merger'] == 0 and math.copysign(1.0, s['h_cons']['merger']) == 1.0
          and s['h_cons']['fail'] == -stocks.H_FAIL and '-0.0' not in json.dumps(s['h_cons']))
    line = stocks.dev_part(s)
    check('report: dev line has the headline parts', all(x in line for x in ('세후 보수', '기본', '일괄-30%', '극단', '동일가중',
                                                                          'NDX보유', '무작위 바구니', 'Sharpe', 'G1 1.1'))
          and len(line.encode()) < 360, f'{len(line.encode())} bytes')


def test_review(P):
    print('== review fixes: gate warm-up window, empty book, ticker labels ==')
    from lab import data
    import warnings
    # output names: point-in-time ids. The source symbols are last-known ones (not point in time): some were adopted
    # after 2014, and an X / X_2 pair exists because one of the two was delisted after 2014 (in v2 three pairs are
    # members at the same time), so no output prints them
    ids = [P.label(j) for j in range(P.N)]
    rk = np.array([int(x[1:]) for x in ids])
    late = [t for t in P.tickers if any(int(y) > 2014 for y in re.findall(r'(?:19|20)\d\d', t))]
    check('labels: point-in-time ids S0001..S1503, unique, in the order of the first membership start, none is a '
          'source symbol; the panel cut and subset keep them',
          all(re.fullmatch(r'S\d{4}', x) for x in ids) and sorted(rk) == list(range(1, P.N + 1))
          and bool(np.all(np.diff(P.fm[np.argsort(rk)]) >= 0)) and not set(ids) & set(P.tickers)
          and np.array_equal(P.cut(row(P, '1990-01-02')).ids, P.ids) and np.array_equal(P.subset([5, 9]).ids, P.ids[[5, 9]]))
    if 'AET-201811' not in P.tickers:      # v2: no post-2014 delisting date in a string (but see above)
        check('tickers (v2 panel): no ticker string holds a year after 2014 (AET-201811 is AET)', not late and 'AET' in P.tickers)
    v1 = os.path.join(os.path.dirname(stocks.STOCKS), 'sp500_le2014.npz.xz')
    if stocks.STOCKS.endswith('_v2.npz.xz') and os.path.isfile(v1):
        P1 = stocks.load(v1)
        same = (np.array_equal(P.idx, P1.idx) and np.array_equal(P.adj, P1.adj, equal_nan=True)
                and np.array_equal(P.dvol, P1.dvol, equal_nan=True) and np.array_equal(P.member, P1.member)
                and np.array_equal(P.stale, P1.stale) and np.array_equal(P.pause, P1.pause))
        ch = [(x, y) for x, y in zip(P1.tickers, P.tickers) if x != y]
        okt = all(y == x[:-7] or (re.fullmatch(r'.+_\d', y) and (y[:-2] == x or y[:-2] == x[:-7])) for x, y in ch)
        check(f'panel v2 == v1 except {len(ch)} ticker strings (adj, dvol, member, stale, dates, exit gaps identical); '
              'changed ones only lose a post-2014 suffix or take _2 by first membership start; output ids identical '
              '(they never read a string)', same and okt and ch and np.array_equal(P1.ids, P.ids))
        stocks._cache.pop(('panel', v1), None); del P1
    # gate warm-up: the 1986 window and the MS1 stream start at the first decision with sma(_NDX, 200) defined (+ delay)
    g = SPECS['gate']
    nd = data.series('_NDX').reindex(P.idx).ffill()
    sv = nd.rolling(200, min_periods=200).mean().first_valid_index()
    s = stocks.evaluate(g, P, null=False, pit=False)
    a = s['windows']['w86']
    want = P.idx[row(P, sv) + DELAY]
    check('gate warm-up: gate_from = first day sma(_NDX, 200) exists on the stock calendar (1986-07), the 1986 window '
          'starts delay rows later and is marked (게이트 1986-07~)',
          s['gate_from'] == str(sv.date()) and s['gate_from'].startswith('1986-07') and a['start'] == str(want.date())
          and a['start_by'] == 'gate' and '(게이트 1986-07~)' in stocks.dev_part(s)
          and '(게이트86-07~)' in stocks.dev_part(s, compact=2), f"{s['gate_from']} -> {a['start']}")
    m = stocks.ms1_stream(g, P)
    check('gate warm-up: MS1 stream starts with the 1986 window (no forced-cash months in it)', m['start'] == a['start'])
    sm = dsl.check_spec(dict(SPECS['mom']))
    ms = stocks.ms1_stream(sm, P); tgm = stocks.compile_targets(sm, P); stm = pd.Timestamp(ms['start'])
    gr = float(np.prod(1 + np.asarray(ms['ret'])))
    eq = {k: stocks.fast_run(P, tgm, h, stm, COST, 0.0, DELAY, want_E=True)['E'][0] for k, h in
          (('cls', stocks.H_CONS), ('all30', stocks.H_ALL))}
    ends = stocks.run1(P, tgm, stocks.H_CONS, stm, COST, 0.0, DELAY, ends=True)['ends']
    check(f"MS1 stream = the classified (headline) book after cost before tax, not the all-30 book (the book holds "
          f"{ends['merger']} merger-type / {ends['fail']} fail-type ends)", abs(gr - eq['cls'][-1] / eq['cls'][0]) < 1e-9
          and abs(gr - eq['all30'][-1] / eq['all30'][0]) > 1e-6 and '상폐 분류' in ms['label'] and ends['merger'] > 0)
    gr = dict(g, stock=dict(g['stock'], exposure_every='rebalance'))
    r, _ = stocks.gate_valid(gr, P, stocks.gate_frame(gr, P.idx))
    rows = np.flatnonzero(dsl.reb_rows(P.idx, 'monthly'))
    check('gate warm-up with exposure_every: rebalance = first month-start row on or after it',
          r == int(rows[rows >= row(P, sv)][0]))
    gt = spec({'score': 'ret(126)', 'top': 30, 'exposure': 'price(TLT) > sma(TLT, 200)'})
    rt, _ = stocks.gate_valid(gt, P, stocks.gate_frame(gt, P.idx))
    tl = data.series('TLT').reindex(P.idx).ffill().rolling(200, min_periods=200).mean().first_valid_index()
    check('gate warm-up: a TLT gate (data from 2002-07) is informed only from its 200th row (2003)',
          P.idx[rt] == tl and tl.year == 2003)
    # a book that never holds a stock says so, computes no null / Sharpe, emits no numpy warnings
    e = spec({'score': 'ret(252)', 'filter': 'age() > 100000', 'top': 10})
    with warnings.catch_warnings(record=True) as wl:
        warnings.simplefilter('always')
        se = stocks.evaluate(e, P, pit=False)
    ae = se['windows']['w86']
    check('empty book: flagged, no null basket, no Sharpe, G1 not passed, line says 종목 0 (filter/게이트 확인)',
          ae['empty'] and 'null' not in ae and ae['sharpe'] is None and not ae['g1_pass'] and not se['screen_pass']
          and all('종목 0 (filter/게이트 확인)' in stocks.dev_part(se, c) for c in (False, True, 2)))
    one = stocks.compile_targets(spec({'score': 'ret(252)', 'top': 1}), P)     # a one-name book the hazard wipes out
    st = pd.Timestamp('1986-01-02')
    with warnings.catch_warnings(record=True) as w2:
        warnings.simplefilter('always')
        stocks.fast_run(P, one, 0.0, st, COST, TAX, DELAY, D=stocks.N_HAZ, hits=stocks.hazard_hits(P, one, st))
    rw = [w for w in wl + w2 if issubclass(w.category, RuntimeWarning)]
    check('engine: no RuntimeWarning (divide by zero / invalid) for an empty book or a book wiped to 0 (one name, '
          'hazard hit)', not rw, str([str(w.message) for w in rw][:2]))
    tg = stocks.compile_targets(e, P)
    o = stocks.run1(P, tg, stocks.H_CONS, pd.Timestamp('1986-01-02'), COST, 0.0, DELAY)
    check('Sharpe of an all-T-bill book (excess stdev ~1e-15) is nan, not float noise', math.isnan(stocks.sharpe(o, P)))


def test_docs():
    print('== docs: refused inputs are not listed as usable data; no claim that ticker strings are point in time ==')
    use = open(os.path.join(LAB, 'USAGE_FOR_THREADS_KO.md')).read().splitlines()
    dl = [x for x in use if '거래대금' in x]
    check('usage brief: every line naming 거래대금 (dollar volume) says it is refused / not to be used',
          dl and all(any(m in x for m in ('거부', '쓰지 않', '안 됨', '못 씀')) for x in dl), f'{len(dl)} lines')
    src = open(stocks.__file__).read() + open(os.path.join(LAB, 'README.md')).read() \
        + open(os.path.join(LAB, 'tools', 'build_us_stocks.py')).read()
    check('docs: no claim that the ticker strings hold no post-2014 fact; the last-known-symbol limit is stated',
          'no post-2014 fact in a ticker' not in src and 'NOT point in time' in src and '시점 사실이 아님' in src)


if __name__ == '__main__':
    t0 = time.time()
    test_errors()
    P = stocks.load()
    test_functions(P)
    test_pit(P)
    test_signals(P)
    test_membership(P)
    test_exit_gap(P)
    test_series_end(P)
    test_classified_synthetic()
    test_leaks(P)
    test_cost_tax(P)
    test_parity(P)
    test_null(P)
    test_seal(P)
    test_report(P)
    test_review(P)
    test_cli(P)
    test_docs()
    print(f'{time.time() - t0:.0f}s')
    print('FAILS:', ', '.join(FAILS) if FAILS else 'none')
    sys.exit(1 if FAILS else 0)
