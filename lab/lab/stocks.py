"""US single-stock universe (spec `universe: sp500`): cross-sectional stock strategies on point-in-time S&P 500
members, delisted names included, after costs and Korean overseas-stock tax, with delisting stress rows and a random
basket null.

Panel: research/data/us_stocks/sp500_le2014_v3.npz.xz (env LAB_STOCKS; its exit gaps in META_v3.json next to it),
sealed <= 2014-12-31. Source github.com/Johnbrick123/sp500-data (no licence published: personal research only, never
republish the data). 1503 names = every name that was an S&P 500 member at some point 1968..2014, with point-in-time
membership (start inclusive, end exclusive), split + dividend adjusted closes, dollar volume (mostly missing before
1996; refused, L1) and no-trade days (`stale`, the source carried the prior close; unread, L2). v2 = v1 without the
post-2014 delisting dates in the ticker strings (tools/build_us_stocks.py: AET-201811 -> AET); every array is identical.
v3 = v2 + divy (every v2 array identical, checked at build and in tests): the cash dividend paid on day t per share /
the previous traded close (raw dividends and closes on one split basis; capped at the distribution the adjusted total
return paid in that day; META_v3 divy), read ONLY by the dividend tax below, never by a score / filter / signal.
The strings are still NOT point in time: they are the source's last-known symbols, so some names print under a
symbol adopted after 2014, and 8 bare symbols shared because one of two names was delisted after 2014 show as X / X_2
(in three pairs both names are members at the same time; names are not listed here). No decision reads a symbol
(only the META exit-gap mapping does) or the panel column order (= the symbols' alphabetical order: a tie at the
top-K boundary is shared by the tied names, top_k, STOCK_VERSION 6), and output never prints one: names print as
point-in-time ids (Panel.label: S0001.. = order of the first membership start, ties by a seeded draw). Seeded draws
(the null baskets, the hazard row, the id ties) are independent of the data; which name a draw lands on follows the
column order like any seed.

Source-dependent leaks (research/indiv_stock/is6 L1-L3, data NOTE_KO.md), closed here:
  L1 dollar volume: 1996-2006 dvol is present 0-4% of days for members that end within 2 years vs 49-86% for the
     rest (the dead-name source has no volume) -> dvol (and volume, dollar_volume) is refused in every expression
     and read by nothing.
  L2 stale: ~49% of the no-trade flags sit within 20 days before a delisted name's last price (member-day rate 0.55%
     for names ending within 2 years vs 0.02%) -> the flag is read by nothing; a stale day is a normal day at the
     carried price.
  L3 history length: pre-membership price history is shorter for later-delisted names (median 476 vs 1382 days; no
     pre-membership price at all for 12.6% of the names first joining in 1990-99 that ended by 2014 vs 5.8% of those
     that did not, 12.5% vs 3.8% for 2000-07) -> age() counts days since the first MEMBERSHIP start (point in time),
     and every per-stock window reads prices from the first membership start on only (WINDOW FLOOR, Panel.wfloor):
     whether a window value exists for a member depends on age() only, never on the pre-membership history. Before
     the floor, a 260-row window existed for 0.77 of recent additions (age() < 260) that later ended within 2 years
     vs 0.89 of the rest (2000-07). Names already members on the first point-in-time day (PIT_FROM = 1970-01-02,
     membership before it unknown) read from their first price (98% of that cohort from the panel's first row
     1968-01-02 in every group). Windows are capped at MAX_WIN = 260 rows (n, n + skip for ret, n of invvol(n)): the
     lab rule since the L3 fix (with the floor the cap is no longer what closes L3).
  L4 price level: adjusted levels differ by source (retroactive adjustment) -> only ratios exist (ret, sma_ratio,
     high_dist); price-level names are refused.
  Dividends (divy): tax input only. div / dividend / yield names are refused in every expression (MSG_DIV): the
     source's distribution records are not checked as a signal (coverage, timing) and lab never needs them to pick.
  Exit gaps (META exit_gaps: documented halts around removal) overlap membership by 2..695 rows in all six gaps, so
  the decision side (eligibility, rank universe, beta market) does not read them; they only freeze trading.

Spec (YAML):
    name: stk_mom12_1_top20
    family: stk_mom
    universe: sp500
    stock:
      rebalance: month          # month | quarter | week: decide at the close of the period's first trading day
      score: "ret(231, 21)"     # per-stock expression (higher = better); 12-1 momentum = P[t-21] / P[t-252] - 1
      filter: "age() > 252"     # optional boolean per-stock expression
      top: 20                   # or top_pct: 0.1
      weight: equal             # equal | invvol(63) | score
      max_weight: 0.10          # optional cap per name, the excess stays in CASH
      exposure: up              # optional: a signal name or an ETF-DSL expression (bool -> 0/1, number clipped 0..1)
      else: {CASH: 1.0}         # what the unexposed share holds (CASH or US ETF sleeves); default CASH
      exposure_every: daily     # daily (default) | rebalance (sample the exposure on decision rows only)
    signals: {up: "price(_NDX) > sma(_NDX, 200)"}   # optional, the ETF DSL on the ETF panel (cut at 2014-12-31)
                                                    # and _SP500EW (below), on the stock calendar

Signals in score / filter (STOCK_VERSION 5): a name defined under `signals:` may appear as a bare name in stock.score
and stock.filter, e.g. "up * rank(ret(231, 21)) + (1 - up) * rank(-vol(252))": it is one number per decision, the
signal's value at the decision close t (the row the stock scores use; boolean -> 1.0 / 0.0), the same for every name.
A signal is INFORMED at t when its value is finite and every indicator call inside it, and inside the signals it reads
(dsl.FUNCS minus the stateful / calendar ones dsl._NO_WARM, as dsl.valid_from), has a value at t: a comparison of an
undefined sma reads False in the DSL, so a boolean alone cannot say it is missing. On a decision where a score / filter
signal is not informed the stock share holds CASH (no name is eligible; the exposure / else part is unchanged), never
"missing = 0"; signal_from = the first informed decision (warm-up, e.g. sma(_SP500EW, 200) -> 1970-10): the 1986
window and the MS1 stream start delay rows after it when it is later (marked (신호 YYYY-MM~), the 1971 row is marked
(신호 YYYY~) when it starts before it), like the gate warm-up. Signal names may not be per-stock function or refused
input names; a window argument is still a number written in the expression (ret(up) is refused) and per-stock
windows stay <= 260 rows (signals are index series: they never compute a per-stock window). Arithmetic is plain:
0 * NaN = NaN, so a name whose unused branch is undefined has no score (put availability in `filter` if it matters),
and a score that is 0 for every name in one regime (`up * rank(..)` alone) ties them all: the tie is shared (Top K
below), the book holds every eligible name that regime. A never-informed signal empties the book; the line says so.
_SP500EW (data.SP500EW, sp500ew): point-in-time equal-weight index of S&P 500 members from this panel: return at t =
mean of adj[t] / adj[t-1] - 1 over the names that were members at t-1 and have a price at t-1 and at t (dividend
adjusted closes; no stale / pause / dvol read; members only, so no pre-membership price; a series end's delisting
return is not in it: whether a price comes back is not known at t); level 1.0 on 1970-01-02 (the first point-in-time
member day), NaN before. Causal: the value at t reads panel rows t-1 and t only. A series in the ETF DSL like _NDX
(price, sma, ret, vol, dd, zscore, ...; the ETF DSL window rules, no 260 cap: it is an index, not a name's history),
so a regime can be measured from 1970 where lab _NDX starts 1985-10. ETF specs may read it too (dev summary only, on
the ETF frame from 1985-10 like any panel key): the bar paths do not have it (REJECT (version impossible)) and MS1
does not (MS1: 해당 없음 (읽는 계열 _SP500EW ...)). A stock spec's exposure gate that reads it gets 'G1 게이트 해당 없음
(읽는 계열 _SP500EW ...)': the G1 frames hold NDX / SPX only (the gate spec carries only the signals the exposure reads).

Per-stock functions (evaluated on decision rows only, every window ends at the decision close and starts on or after
the first membership start (the window floor, L3), n (n + skip) <= 260):
  ret(n[, skip])  total return over n days ending `skip` days ago     vol(n)        daily return stdev (n returns)
  sma_ratio(n)    price / n-day mean price                            high_dist(n)  price / n-day max - 1
  age()           trading days since the first membership start      beta(n)       n-day beta vs the EW member return
  rank(x)         cross-sectional percentile 0..1                      csz(x)        cross-sectional z-score
  abs min max log, + - * /, comparisons, and or not. Refused: dvol / volume (L1), price-level names (L4), first-price
  age (L3), windows above 260 rows.
rank / csz rank among the names that are members with a price on that row. Prices are the adjusted closes carried
forward through days without a price (return 0), from each name's first price on; a window starting before the
name's window floor (first membership start; first price for the 1970-01-02 cohort) is NaN, so for a name that
joined later, whether a value exists depends on age() only (ret(n) / vol(n) / beta(n): age() >= n; sma_ratio(n) /
high_dist(n): age() >= n - 1). age() is censored at the first point-in-time membership day (1970-01-02:
names already members then count from it).

Eligibility at decision close t: member at t, a price at t (stale flags and exit-gap pauses are not read), filter
true, score finite (and vol(n) finite > 0 for weight invvol(n)). A held name that leaves the index is sold at the
next rebalance (target 0).
Top K (STOCK_VERSION 6, top_k): the K eligible names with the highest score; when more names share the K-th best score
than the slots left for them, the tied names SHARE those slots (each gets slots / tied of a name's weight: the expected
book over a uniformly random order of the tied names; exact for equal / score weights, invvol weights the shares by
1 / vol), never the panel column order (alphabetical by the source's last-known symbols, which include post-2014
renames). An all-tied score (`up * rank(ret(231, 21))` while up = 0, a boolean score, high_dist at 0) holds every
eligible name. The line marks it (동점분할 n/m회: decisions in force in the 1986 window); the null basket holds as many
names as the strategy at the same total weight (Targets.unit).

Returns: adjusted close to close, carried through a pause (an exit gap books its whole change on the next trade day).
After a series' last price (before 2014-12-31) the next day returns the delisting return, then 0. Headline rule
(CLASSIFIED, H_CONS): the return over the DL_WIN = 250 rows up to the last price (fewer when the series is shorter,
>= DL_MIN = 20; prices <= the last price only) < -30% -> fail-type, delisting return -50% (between Shumway's NYSE
-30% and Nasdaq -55%); else merger-type, 0 (an acquisition is paid at about the last price). Execution: lab's ETF
engine (engine.run: delay 2 = decided at close t, traded at close t+2, earning from day t+3's return; 0.30% per side,
22% yearly net realized gain tax, final liquidation taxed, cash earns the T-bill) with two additions for single stocks:
inside a recorded exit gap or on a day without a price inside the series a name cannot be traded (frozen, the trade is
retried when it trades again) and a name with no price cannot be bought; DIVIDEND TAX (STOCK_VERSION 7, DIV_TAX =
15.4%, KR resident: US 15% withheld, KR 15.4% with the foreign credit, taken when paid): the adjusted close is a total
return, so on a day a held name pays (divy > 0) the book pays DIV_TAX x (position value at the previous close x divy)
out of that position and adds the other 84.6% to its cost basis (reinvested cash, not a capital gain): the 22% tax
then falls on price gains only. Every book carries it: strategy rows, equal-weight benchmark, null baskets, stress
rows, the MS1 stream. ETF sleeves (else, the NDX hold row) are not taxed on distributions (README: ETF side).

Rows: base h=0, CONSERVATIVE = the classified rule (the headline), ALL30 = every series end -30% (stress; the headline
up to STOCK_VERSION 2), EXTREME = base + a 6%/year -100% hazard on each held name (20 seeded draws, median; reference
only). Benchmarks on the same engine / costs / tax: equal-weight members (monthly) and NDX 1x hold (QQQ sleeve of the
ETF panel). Annualised after-cost PRE-TAX (no 22% tax, no dividend tax) Sharpe over the T-bill (G1 non-timing test,
pass >= 1.1); the same run's CAGR is cagr_pretax in the JSON. cagr_before_liq_tax (JSON) = CAGR of the equity curve:
after cost, the yearly 22% tax and the dividend tax, before only the final liquidation tax (it was cagr_pre up to
STOCK_VERSION 6: not a pre-tax number). Random-basket
null: 200 seeded baskets with the same rebalance dates, eligibility, name count and name retention (see null_baskets),
equal weight, same exposure, engine, costs, tax and delisting rule.
MS1 / G1 (lab/ms1.py, `--std auto`): ms1_stream = the CONSERVATIVE (classified) book's daily return after trading
cost and the dividend tax, before the 22% tax (MS1 applies its own), with the reinvested after-tax dividend of each day
as basis_add (measure_series adds it to the stream's cost basis: not taxed again at 22%), on the real stock calendar from 1970 (first point-in-time member day; later when an else sleeve starts later,
the exposure gate is warmed up later (gate_valid) or the score / filter signals are informed later (signal_row)),
measured on the MS1 bases by ms1.measure_series (re-sampled stream, no path recomputation). The 1986 headline window
also starts at the warmed-up gate / informed signals (marked). G1 = the Sharpe line above; a spec with an exposure gate
also gets gate.test on it (gate_spec: the gate, with only the signals it reads, as a QQQ / cash spec on the G1 real
frames; a gate reading _SP500EW or another series the G1 frames lack: 'G1 게이트 해당 없음 (읽는 계열 ..)'). Signals that
only steer the score are not a timing gate (the book is always invested): G1 = the Sharpe line.
HOLDOUT SEAL: the panel and every ETF series are cut at 2014-12-31 before anything is computed; asserted below.
"""
import ast, io, json, lzma, math, os, re, time
import numpy as np, pandas as pd
from . import data, dsl, engine, gates

STOCKS = os.environ.get('LAB_STOCKS', '/mnt/project-files/research/data/us_stocks/sp500_le2014_v3.npz.xz')
DEV_END = gates.DEV_END
STOCK_VERSION = 7           # bump when the stock summary changes for an unchanged spec hash (cli recomputes)
                            # 7: dividend tax (DIV_TAX 15.4% when paid, the rest to cost basis; panel v3 divy) in
                            #    every book and the MS1 stream (basis_add); JSON cagr_pre -> cagr_before_liq_tax,
                            #    + cagr_pretax (the Sharpe run: no 22% tax, no dividend tax)
                            # 6: a tie at the top-K boundary is shared (top_k), not broken by the panel column order;
                            #    the 1971 row keeps its (게이트 / 신호 ..~) mark in the shortest form; an empty book
                            #    with never-informed signals says so
                            # 5: signals in score / filter (informed per decision, signal_from), _SP500EW; the
                            #    gate (warm-up, data start, G1 gate spec) is the exposure + the signals it reads
                            #    only; runtime PIT cuts rebuild the gate frame from the cut panel
                            # 2: the 1986 window and the MS1 stream start once the exposure gate is warmed up
                            #    (gate_from = first decision with every gate indicator defined); empty books say so;
                            #    tickers delisted after 2014 print bare
                            # 3: leaks L1-L4 closed (no dvol / stale / pause on the decision side, membership age,
                            #    windows <= 260 rows); classified delisting rule is the headline (+ ALL30 stress row)
                            # 4: window floor at the first membership start (L3 among recent additions); names print
                            #    as point-in-time ids (source symbols are last-known ones); h_cons merger 0.0 (not -0.0)
BAR_VERDICT = '판정 불가 (개별주)'
WINDOWS = {'w86': pd.Timestamp('1986-01-02'), 'w71': pd.Timestamp('1971-01-04')}   # both end DEV_END
DL_WIN, DL_MIN, DL_FAIL = 250, 20, -0.30   # series-end class: return over DL_WIN rows (>= DL_MIN) to the last price
H_FAIL = 0.50               # fail-type delisting return -50% (between Shumway's NYSE -30% and Nasdaq -55%)
H_CONS = (H_FAIL, 0.0)      # headline rule (h_fail, h_merger): classified, fail-type -50%, merger-type 0
H_ALL = 0.30                # stress row: every series end -30% (the headline rule up to STOCK_VERSION 2)
DIV_TAX = 0.154             # dividend tax of a KR resident on a US stock's dividend, taken when paid: US withholds 15%,
                            # KR taxes foreign dividends at 15.4% with a credit for it -> ~15.4% of each dividend; the
                            # reinvested 84.6% is cost basis (not part of the 22% capital gain)
MAX_WIN = 260               # longest per-stock window in rows (lab rule since the L3 fix; the window floor closes L3)
PIT_FROM = pd.Timestamp('1970-01-02')   # first day with point-in-time members (names members then: membership unknown
                                        # before it; their window floor is the first price, age() counts from it)
ID_SEED = 1970              # output ids: ties in the first membership start are ordered by this seeded draw
HAZARD, N_HAZ, HAZ_SEED = 0.06, 20, 2014
N_NULL, NULL_SEED = 200, 1986
G1_SHARPE = 1.1
N_PIT_CUTS = 3              # runtime causality cuts per spec (the test suite checks PIT in depth)
MS1_FROM = PIT_FROM         # start of the MS1 return stream
CAD = {'month': 'monthly', 'monthly': 'monthly', 'quarter': 'quarterly', 'quarterly': 'quarterly',
       'week': 'weekly', 'weekly': 'weekly'}
STOCK_KEYS = {'rebalance', 'score', 'filter', 'top', 'top_pct', 'weight', 'max_weight', 'exposure', 'else',
              'exposure_every'}
NOT_IN_UNIVERSE = ('rules', 'plugin', 'sleeves', 'inputs', 'params', 'brake', 'band', 'rebalance', 'baseline',
                   'dev_start')
_cache = {}


class SealError(AssertionError):
    pass


def _sealed(idx):
    if len(idx) and idx.max() > DEV_END:
        raise SealError(f'stock data after {DEV_END.date()} reached a computation')
    return idx


# ---------------------------------------------------------------- panel
class Panel:
    """Point-in-time stock panel, rows <= DEV_END only (later rows are dropped before anything is derived).
    Derived arrays ([T, N], built lazily): P = adjusted close carried forward from each name's first price, rr = its
    close-to-close return (0 before the first price and through gaps), has = a finite price (the DECISION side:
    eligibility, the rank universe, the beta market), real = has and not inside a recorded exit gap (`pause`, from
    the panel's META: the days between last_trade and next_trade, where the source may carry the old price), the
    EXECUTION side: frozen = no real price inside the series, no_buy = no real price. fm = first membership row
    (age()), wfloor = the first row a per-stock window may start on (L3: fm, or the first price for names already
    members on PIT_FROM). `dvol` and `stale` are kept as loaded and read by nothing (leaks L1 / L2, module
    docstring). `divy` ([T, N] float, 0 = no dividend; zeros when not given) = the dividend paid on day t per share /
    the previous traded close: read ONLY by the dividend tax of the engines (fast_run, frames), never by a decision.
    `tickers` are the source's last-known symbols (not point in time, module docstring): read only to map the META
    exit gaps; output prints `ids` (label)."""

    def __init__(self, dates, tickers, adj, dvol, member, stale, pause=None, ids=None, divy=None):
        dates = pd.DatetimeIndex(dates)
        keep = np.asarray(dates <= DEV_END)
        pause = np.zeros(np.shape(adj), bool) if pause is None else np.asarray(pause, bool)
        self.div_known = divy is not None        # False: no dividend data (zeros; load() refuses such a file)
        divy = np.zeros(np.shape(adj), np.float32) if divy is None else np.asarray(divy, np.float32)
        if not keep.all():                       # seal: drop later rows before any number is derived
            dates, adj, dvol, member, stale, pause, divy = (dates[keep], adj[keep], dvol[keep], member[keep],
                                                            stale[keep], pause[keep], divy[keep])
        self.idx = _sealed(dates)
        self.tickers = np.asarray(tickers).astype(str)
        self.adj = np.asarray(adj, np.float32)
        self.dvol = np.asarray(dvol, np.float32)
        self.member = np.asarray(member, bool)
        self.stale = np.asarray(stale, bool)
        self.pause = pause
        self.divy = np.where(np.isfinite(divy) & (divy > 0), divy, 0.0).astype(np.float32)   # tax input only
        T, N = self.adj.shape
        assert self.member.shape == self.stale.shape == self.dvol.shape == self.divy.shape == (T, N) \
            == (len(dates), len(self.tickers))
        fin = np.isfinite(self.adj) & (self.adj > 0)
        self.has = fin                           # decision side: never reads stale (L2) or pause
        self.real = fin & ~self.pause            # execution side: a name inside an exit gap cannot trade
        anyp = fin.any(0)
        self.first = np.where(anyp, fin.argmax(0), T)     # read by: a window's "price at its start" check, the
                                                          # series-end class (end_ret), frozen; never a signal (L3)
        self.last = np.where(anyp, T - 1 - fin[::-1].argmax(0), -1)
        anym = self.member.any(0)
        self.fm = np.where(anym, self.member.argmax(0), T)   # first membership row (point in time; age())
        self.f0 = int(self.idx.searchsorted(PIT_FROM))        # row of the first point-in-time day (T if after the end)
        self.wfloor = np.where(self.fm <= self.f0, self.first, np.maximum(self.fm, self.first))   # window floor (L3)
        self.ids = pit_ids(self.fm) if ids is None else np.asarray(ids).astype(str)
        assert len(self.ids) == len(self.tickers)
        self.ended = (self.last >= 0) & (self.last < T - 1)  # the series ends before the panel's last row
        self.T, self.N = T, N
        self._m = {}

    def cut(self, c):
        """The panel as it was known at the close of row c - 1 (rows [0, c))."""
        return Panel(self.idx[:c], self.tickers, self.adj[:c], self.dvol[:c], self.member[:c], self.stale[:c],
                     self.pause[:c], self.ids, self.divy[:c] if self.div_known else None)

    def subset(self, cols):
        cols = np.asarray(cols)
        return Panel(self.idx, self.tickers[cols], self.adj[:, cols], self.dvol[:, cols], self.member[:, cols],
                     self.stale[:, cols], self.pause[:, cols], self.ids[cols],
                     self.divy[:, cols] if self.div_known else None)

    def _get(self, k, f):
        if k not in self._m:
            self._m[k] = f()
        return self._m[k]

    @property
    def P(self):
        return self._get('P', lambda: pd.DataFrame(np.where(self.has, self.adj, np.nan).astype(np.float64))
                         .ffill().values)

    @property
    def rr(self):
        def f():
            P = self.P
            r = np.zeros((self.T, self.N))
            with np.errstate(invalid='ignore', divide='ignore'):
                r[1:] = P[1:] / P[:-1] - 1.0
            r[~np.isfinite(r)] = 0.0
            return r
        return self._get('rr', f)

    @property
    def frozen(self):
        def f():
            rows = np.arange(self.T)[:, None]
            return (rows >= self.first) & (rows <= self.last) & ~self.real
        return self._get('frozen', f)

    @property
    def no_buy(self):
        return ~self.real

    @property
    def end_ret(self):
        """[N] return over the DL_WIN rows up to each ended series' last price (fewer when the series is shorter, NaN
        below DL_MIN rows or for a series that does not end). Reads the name's own prices first..last only, i.e. what
        is known when the series ends (causal at the end)."""
        def f():
            out = np.full(self.N, np.nan)
            j = np.flatnonzero(self.ended)
            w = np.minimum(DL_WIN, self.last[j] - self.first[j])
            ok = w >= DL_MIN
            j, w = j[ok], w[ok]
            L = self.last[j]
            with np.errstate(invalid='ignore', divide='ignore'):
                out[j] = self.adj[L, j].astype(np.float64) / self.P[L - w, j] - 1.0
            return out
        return self._get('end_ret', f)

    @property
    def fail(self):
        """[N] fail-type series end: end_ret < DL_FAIL (-30%). Every other ended series is merger-type."""
        return self._get('fail', lambda: self.ended & (np.nan_to_num(self.end_ret, nan=0.0) < DL_FAIL))

    def R(self, h):
        """Engine returns: rr inside each series; on the day after a last price that is before the panel end (a series
        end) the delisting return, then 0. h = a number: every end returns -h (0 = base, sold at the last price;
        H_ALL = 0.30 = the all-ends stress); h = (h_fail, h_merger): fail-type ends (self.fail) return -h_fail, the
        others -h_merger (H_CONS = the classified headline). Exactly one delisting return per ended series."""
        cls = isinstance(h, (tuple, list))
        hk = tuple(float(x) for x in h) if cls else float(h)

        def f():
            R = self.rr.copy()
            j = np.flatnonzero(self.ended)
            R[self.last[j] + 1, j] = (np.where(self.fail[j], -hk[0], -hk[1]) if cls else -hk) + 0.0
            return R
        return self._get(('R', hk), f)

    def mkt(self):
        """Equal-weight return of the names that were members the day before and have a price that day (for beta;
        decision side: no stale / pause)."""
        def f():
            M = np.zeros((self.T, self.N), bool)
            M[1:] = self.member[:-1] & self.has[1:] & (np.arange(1, self.T)[:, None] > self.first)
            c = M.sum(1)
            return np.where(c > 0, np.where(M, self.rr, 0.0).sum(1) / np.maximum(c, 1), 0.0)
        return self._get('mkt', f)

    def cs(self, k):
        """Cumulative sums with a leading zero row: cs[t] = sum of rows < t."""
        def f():
            if k == 'rr':
                X = self.rr
            elif k == 'rr2':
                X = self.rr ** 2
            elif k == 'P':
                X = np.nan_to_num(self.P, nan=0.0)
            elif k == 'rm':
                X = self.rr * self.mkt()[:, None]
            elif k == 'm':
                X = self.mkt()[:, None]
            elif k == 'm2':
                X = self.mkt()[:, None] ** 2
            else:
                raise KeyError(k)
            out = np.zeros((X.shape[0] + 1, X.shape[1]))
            np.cumsum(X, axis=0, out=out[1:])
            return out
        return self._get(('cs', k), f)

    def label(self, j):
        """Name for output: the point-in-time id (pit_ids), never the source symbol. The symbols are the source's
        last-known ones: a symbol adopted after 2014 or an X / X_2 pair (a name delisted after 2014 freed the symbol)
        tells the reader what happened after 2014."""
        return str(self.ids[j])


def pit_ids(fm):
    """Output ids S0001.. from <= 2014 point-in-time facts only: the order of the first membership start (fm), ties
    (e.g. the 500 names already members on 1970-01-02) by a seeded draw (ID_SEED). Never a source symbol or its
    alphabetical order: an id says when the name first joined, relative to the others, and nothing else."""
    fm = np.asarray(fm)
    order = np.lexsort((np.random.default_rng(ID_SEED).random(len(fm)), fm))
    rank = np.empty(len(fm), np.int64)
    rank[order] = np.arange(1, len(fm) + 1)
    return np.array([f'S{r:04d}' for r in rank])


def meta_path(path=None):
    """The META file next to a panel: sp500_le2014_v3.npz.xz -> META_v3.json, sp500_le2014.npz.xz -> META.json."""
    path = path or STOCKS
    m = re.search(r'(_v\d+)?\.npz(?:\.xz)?$', os.path.basename(path))
    return os.path.join(os.path.dirname(path), f"META{(m.group(1) or '') if m else ''}.json")


class NoDividendError(ValueError):
    pass


def load(path=None, allow_nodiv=False):
    """The sealed stock panel (cached per process). Nothing is dropped except rows after DEV_END. The exit gaps listed
    in the META file next to the panel (meta_path, if present) become `pause` rows (no trade possible inside). A file
    without `divy` (v1 / v2) is refused: its books would not pay the dividend tax (allow_nodiv=True: tests that compare
    the shared arrays of the panel versions; divy is then zero)."""
    path = path or STOCKS
    if ('panel', path) not in _cache:
        z = np.load(io.BytesIO(lzma.open(path).read()))
        T = int(z['shape'][0])
        dates = pd.to_datetime(z['dates'], unit='D')
        unpack = lambda a: np.unpackbits(a, axis=0)[:T].astype(bool)
        tick = np.asarray(z['tickers']).astype(str)
        pause = np.zeros((T, len(tick)), bool)
        mp = meta_path(path)
        if os.path.isfile(mp):
            col = {t: i for i, t in enumerate(tick)}
            for g in json.load(open(mp)).get('exit_gaps', []):
                a, b = dates.searchsorted(pd.Timestamp(g['last_trade'])), dates.searchsorted(pd.Timestamp(g['next_trade']))
                if g['ticker'] in col:
                    pause[a + 1:b, col[g['ticker']]] = True
        _cache[('panel', path)] = Panel(dates, tick, z['adj'], z['dvol'], unpack(z['member']), unpack(z['stale']),
                                        pause, divy=z['divy'] if 'divy' in z.files else None)
    P = _cache[('panel', path)]
    if not P.div_known and not allow_nodiv:
        raise NoDividendError(f'{os.path.basename(path)}: 배당 자료(divy) 없음 — 배당세(15.4%)를 못 매겨 세후가 '
                              f'부풀려짐; v3 패널(sp500_le2014_v3.npz.xz)을 씀')
    return P


def sp500ew(P):
    """[T] _SP500EW level on the panel's rows (cached on P): r[t] = mean over the names that were members at t-1 and
    have a price at t-1 and at t (has: finite > 0; stale / pause / dvol are not read) of adj[t] / adj[t-1] - 1
    (= rr there); level 1.0 on the first point-in-time member day P.f0 (1970-01-02), cumprod(1 + r) after it, NaN
    before. A day with no such name (none in the panel after 1970: >= 496 names every day) returns 0. Causal: row t
    reads rows t-1 and t only, and only members' prices (no pre-membership history, L3). A series end's delisting
    return is not in it (no price at t; whether one comes back is not known at t)."""
    def f():
        T = P.T
        lv = np.full(T, np.nan)
        if P.f0 >= T:
            return lv
        M = np.zeros((T, P.N), bool)
        M[1:] = P.member[:-1] & P.has[:-1] & P.has[1:]
        cnt = M.sum(1)
        r = np.where(cnt > 0, np.where(M, P.rr, 0.0).sum(1) / np.maximum(cnt, 1), 0.0)
        r[:P.f0 + 1] = 0.0
        lv[P.f0:] = np.cumprod(1.0 + r[P.f0:])
        return lv
    return P._get('sp500ew', f)


def sp500ew_series(path=None):
    """_SP500EW as a Series on the stock calendar (rows <= DEV_END, from 1970-01-02): data.series('_SP500EW')."""
    P = load(path)
    s = pd.Series(sp500ew(P), index=P.idx).dropna()
    _sealed(s.index)
    return s


# ---------------------------------------------------------------- per-stock expressions
SFUNCS = {'ret': (1, 2), 'vol': (1, 1), 'sma_ratio': (1, 1), 'high_dist': (1, 1), 'age': (0, 0),
          'beta': (1, 1), 'rank': (1, 1), 'csz': (1, 1), 'abs': (1, 1), 'min': (2, 2), 'max': (2, 2), 'log': (1, 1)}
_WINF = {'ret', 'vol', 'sma_ratio', 'high_dist', 'beta'}
_SOK = (ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare, ast.Call, ast.Name, ast.Load, ast.Constant,
        ast.And, ast.Or, ast.Not, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd, ast.Gt, ast.GtE, ast.Lt,
        ast.LtE, ast.Eq, ast.NotEq)
# refused inputs (source-dependent leaks, module docstring): one-line Korean reasons
MSG_DVOL = '{nm} 사용 불가: 출처 의존 누출 — 1996~2006 거래대금 유무가 미래 상폐를 드러냄'
VOL_NAMES = ('dvol', 'volume', 'dollar_volume')
MSG_LEVEL = ('{nm} 사용 불가: 수정주가 수준은 출처(상폐 여부와 엮임)마다 소급 조정이 달라 미래와 엮임 — '
             '비율(ret·sma_ratio·high_dist)만 씀')
MSG_FIRST = ('{nm} 사용 불가: 첫 가격 날짜(가격 이력 길이)는 미래 상폐와 엮임(나중 상폐 종목은 편입 전 이력이 짧음) — '
             '나이는 age()(첫 편입일부터 거래일 수)')
MSG_WIN = ('{what}: {call} 창 {w}행 > ' + str(MAX_WIN) + ' 사용 불가 — lab 창 상한 ' + str(MAX_WIN) + '행(ret는 n+skip, '
           'invvol(n)도; 12-1 모멘텀은 ret(231, 21)). 창은 첫 편입일부터의 가격만 읽음(편입 전 이력은 미래 상폐와 엮임; '
           '1970-01-02에 이미 편입된 종목은 첫 가격부터)')
MSG_DIV = ('{nm} 사용 불가: 배당 자료(divy)는 배당세(15.4%) 계산에만 씀 — 출처의 배당 기록(유무·시점·크기)은 신호로 '
           '검증 안 됨(score·filter·signals 어디서도 못 읽음)')
DIV_NAMES = ('div', 'divs', 'divy', 'dividend', 'dividends', 'div_yield', 'dividend_yield', 'yield', 'yld', 'dy',
             'payout', 'distribution', 'distributions')
_DIV_RE = re.compile(r'(?<![A-Za-z0-9_])(' + '|'.join(sorted(DIV_NAMES, key=len, reverse=True)) + r')(?![A-Za-z0-9_])')
FORBID = dict({k: MSG_DVOL.format(nm=k) for k in VOL_NAMES},
              **{k: MSG_DIV.format(nm=k) for k in DIV_NAMES},
              **{k: MSG_LEVEL.format(nm=k) for k in ('price', 'close', 'adj', 'adj_close', 'level', 'sma', 'ema',
                                                    'high', 'low', 'open', 'mcap')},
              **{k: MSG_FIRST.format(nm=k) for k in ('first_price', 'listed', 'listing_age', 'history', 'price_age',
                                                    'age_price')})


def _int_arg(node, f, lo):
    if not (isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)
            and math.isfinite(node.value) and float(node.value) == int(node.value) and int(node.value) >= lo):
        raise ValueError(f'{f}(): window / skip must be a whole number >= {lo} written as a number, not '
                         f'{ast.unparse(node)!r} (n < {lo} would read rows after the decision close)')
    return int(node.value)


def window_rows(f, args):
    """Rows a window function reaches back (the cap MAX_WIN applies to it): n, n + skip for ret."""
    return int(args[0]) + (int(args[1]) if f == 'ret' and len(args) > 1 else 0)


def _forbid(nm, what, expr):
    if nm in FORBID:
        raise ValueError(f'{FORBID[nm]} (stock {what}: {expr!r})')


def forbid_div_names(spec):
    """Dividend names anywhere in a stock spec (signal names, signal / exposure / score / filter expressions) -> the
    Korean reason. dsl.check_spec calls it before any expression is parsed (`yield` alone is a syntax error)."""
    sig = spec.get('signals') if isinstance(spec.get('signals'), dict) else {}
    for k, e in sig.items():
        if k in DIV_NAMES:
            raise ValueError(f'{MSG_DIV.format(nm=k)} (signal name {k!r})')
        _div_forbid(e, f'signal {k}')
    st = spec.get('stock') if isinstance(spec.get('stock'), dict) else {}
    for k in ('exposure', 'score', 'filter'):
        _div_forbid(st.get(k), f'stock {k}')


def _div_forbid(expr, where):
    """A dividend name anywhere in an expression (also `yield`, a Python keyword that would only give a syntax error):
    the one-line Korean reason (MSG_DIV)."""
    m = _DIV_RE.search(str(expr)) if isinstance(expr, str) else None
    if m:
        raise ValueError(f'{MSG_DIV.format(nm=m.group(1))} ({where}: {expr!r})')


def parse_stock(expr, what='score', sig=()):
    """Parse and check a per-stock expression (whitelisted AST; unknown names / functions raise; refused inputs
    (FORBID) and windows above MAX_WIN raise a one-line Korean reason). sig: the spec's signal names, allowed as bare
    names (one number per decision); a window argument must still be a number (ret(up) is refused)."""
    sig = set(sig)
    if isinstance(expr, bool) or not isinstance(expr, (str, int, float)):
        raise ValueError(f'stock {what} must be an expression string, not {expr!r}')
    _div_forbid(expr, f'stock {what}')
    try:
        tree = ast.parse(str(expr), mode='eval')
    except SyntaxError as e:
        raise ValueError(f'stock {what}: syntax error in {expr!r}: {e.msg}')
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            _forbid(n.id, what, expr)
    for n in ast.walk(tree):
        if not isinstance(n, _SOK):
            raise ValueError(f'stock {what}: {type(n).__name__} not allowed in {expr!r}')
        if isinstance(n, ast.Constant) and (isinstance(n.value, (str, bytes, bool)) or n.value is None):
            raise ValueError(f'stock {what}: only numbers may be constants in {expr!r}')
        if isinstance(n, ast.Call):
            if not isinstance(n.func, ast.Name) or n.func.id not in SFUNCS:
                nm = n.func.id if isinstance(n.func, ast.Name) else ast.unparse(n.func)
                raise ValueError(f'stock {what}: unknown function {nm!r} in {expr!r} '
                                 f'(per-stock functions: {", ".join(SFUNCS)})')
            if n.keywords:
                raise ValueError(f'stock {what}: keyword arguments not allowed in {expr!r}')
            lo, hi = SFUNCS[n.func.id]
            if not lo <= len(n.args) <= hi:
                raise ValueError(f'stock {what}: {n.func.id}() takes {lo}..{hi} arguments in {expr!r}')
            if n.func.id in _WINF:
                a = [_int_arg(n.args[0], n.func.id, 2 if n.func.id in ('vol', 'beta') else 1)]
                if len(n.args) > 1:
                    a.append(_int_arg(n.args[1], n.func.id, 0))
                w = window_rows(n.func.id, a)
                if w > MAX_WIN:
                    raise ValueError(MSG_WIN.format(what=f'stock {what}', call=ast.unparse(n), w=w))
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and n.id not in sig \
                and not any(isinstance(c, ast.Call) and c.func is n for c in ast.walk(tree)):
            raise ValueError(f'stock {what}: unknown name {n.id!r} in {expr!r} (per-stock expressions use only '
                             f'numbers, the functions {", ".join(SFUNCS)} and the names defined under signals: '
                             f'{", ".join(sorted(sig)) or "none"})')
    return tree


def _bare_names(expr):
    """Bare names of a per-stock expression (not called): after parse_stock these are signal names."""
    tree = ast.parse(str(expr), mode='eval')
    fn = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and id(n) not in fn}


class _Ctx:
    """Evaluation of per-stock expressions on decision rows D ([nd] row numbers) -> [nd, N] arrays. sig: {signal
    name: [nd] value at each decision close} (a bare signal name reads it, the same for every name)."""

    def __init__(self, P, D, sig=None):
        self.P, self.D = P, np.asarray(D, np.int64)
        self.E0 = P.member[self.D] & P.has[self.D]           # members with a price at the decision close (no stale)
        self.sig = {k: np.asarray(v, float).reshape(len(self.D)) for k, v in (sig or {}).items()}
        self.memo = {}

    def _valid(self, start):
        """A window starting at row `start` (per decision) must start on or after the name's window floor (wfloor: the
        first membership start; the first price for names already members on PIT_FROM) and at a row >= 0. L3: the
        pre-membership price history (its length, its existence) is tied to later delisting, so no window reads it
        and whether a member's window value exists depends on age() only. Windows are <= MAX_WIN rows."""
        assert (self.D - np.asarray(start)).max(initial=0) <= MAX_WIN, 'window above MAX_WIN reached _Ctx'
        s = np.asarray(start)[:, None]
        return (s >= 0) & (s >= self.P.wfloor[None, :])

    def _win_sum(self, k, n):
        cs = self.P.cs(k)
        a = self.D + 1; b = np.maximum(self.D + 1 - n, 0)
        return cs[a] - cs[b]

    def call(self, f, a):
        P, D = self.P, self.D
        with np.errstate(invalid='ignore', divide='ignore', over='ignore'):
            if f == 'ret':
                n, s = a[0], (a[1] if len(a) > 1 else 0)
                x, y = D - s, D - s - n
                out = P.P[np.maximum(x, 0)] / P.P[np.maximum(y, 0)] - 1.0
                return np.where(self._valid(y) & (x >= 0)[:, None], out, np.nan)
            if f == 'vol':
                n = a[0]
                S1, S2 = self._win_sum('rr', n), self._win_sum('rr2', n)
                v = np.sqrt(np.maximum((S2 - S1 * S1 / n) / (n - 1), 0.0))
                return np.where(self._valid(D - n), v, np.nan)
            if f == 'sma_ratio':
                n = a[0]
                out = P.P[D] / (self._win_sum('P', n) / n)
                return np.where(self._valid(D - n + 1), out, np.nan)
            if f == 'high_dist':
                n = a[0]
                Pf = P.P
                mx = np.stack([Pf[max(0, d - n + 1): d + 1].max(0) for d in D]) if len(D) else np.zeros((0, P.N))
                return np.where(self._valid(D - n + 1), Pf[D] / mx - 1.0, np.nan)
            if f == 'age':                                     # days since the first membership start (PIT, L3)
                ag = (D[:, None] - P.fm[None, :]).astype(float)
                return np.where(ag >= 0, ag, np.nan)
            if f == 'beta':
                n = a[0]
                Srm, Sr = self._win_sum('rm', n), self._win_sum('rr', n)
                Sm, Smm = self._win_sum('m', n), self._win_sum('m2', n)
                vm = Smm - Sm * Sm / n
                b = (Srm - Sr * Sm / n) / np.where(vm > 0, vm, np.nan)
                return np.where(self._valid(D - n), b, np.nan)
            if f in ('rank', 'csz'):
                x = np.where(self.E0 & np.isfinite(a[0]), a[0], np.nan)
                if f == 'rank':
                    r = pd.DataFrame(x).rank(axis=1, method='average').values
                    m = np.isfinite(x).sum(1, keepdims=True)
                    return np.where(m > 1, (r - 1.0) / np.maximum(m - 1, 1), 0.5) * np.where(np.isfinite(x), 1, np.nan)
                m = np.isfinite(x).sum(1, keepdims=True)
                mu = np.nanmean(np.where(m > 0, x, 0.0), 1, keepdims=True)
                sd = np.nanstd(np.where(m > 1, x, 0.0), 1, ddof=1, keepdims=True) if x.shape[1] > 1 else np.nan
                return np.where((m > 1) & (sd > 0), (x - mu) / np.where(sd > 0, sd, 1.0), np.nan)
            if f == 'abs':
                return np.abs(a[0])
            if f == 'min':
                return np.minimum(a[0], a[1])
            if f == 'max':
                return np.maximum(a[0], a[1])
            if f == 'log':
                return np.where(np.asarray(a[0]) > 0, np.log(np.where(np.asarray(a[0]) > 0, a[0], 1.0)), np.nan)
        raise ValueError(f)

    def ev(self, node):
        if isinstance(node, ast.Expression):
            return self.ev(node.body)
        if isinstance(node, ast.Constant):
            return float(node.value)
        if isinstance(node, ast.Name):                         # a signal: [nd, 1], broadcast over the names
            return self.sig[node.id][:, None]
        if isinstance(node, ast.UnaryOp):
            v = self.ev(node.operand)
            if isinstance(node.op, ast.Not):
                return ~_b(v)
            return -v if isinstance(node.op, ast.USub) else v
        if isinstance(node, ast.BoolOp):
            vs = [_b(self.ev(v)) for v in node.values]
            out = vs[0]
            for v in vs[1:]:
                out = (out & v) if isinstance(node.op, ast.And) else (out | v)
            return out
        if isinstance(node, ast.BinOp):
            l, r = _f(self.ev(node.left)), _f(self.ev(node.right))
            with np.errstate(invalid='ignore', divide='ignore', over='ignore'):
                if isinstance(node.op, ast.Add):
                    return l + r
                if isinstance(node.op, ast.Sub):
                    return l - r
                if isinstance(node.op, ast.Mult):
                    return l * r
                return np.where(r != 0, l / np.where(r != 0, r, 1.0), np.nan)
        if isinstance(node, ast.Compare):
            out, left = None, _f(self.ev(node.left))
            for op, c in zip(node.ops, node.comparators):
                right = _f(self.ev(c))
                with np.errstate(invalid='ignore'):
                    v = {ast.Gt: np.greater, ast.GtE: np.greater_equal, ast.Lt: np.less, ast.LtE: np.less_equal,
                         ast.Eq: np.equal, ast.NotEq: np.not_equal}[type(op)](left, right)
                out = v if out is None else (out & v)
                left = right
            return out
        if isinstance(node, ast.Call):
            f = node.func.id
            if f in _WINF:
                a = [int(x.value) for x in node.args]
            else:
                a = [_f(self.ev(x)) for x in node.args]
            key = ast.dump(node)
            if key not in self.memo:
                self.memo[key] = self.call(f, a)
            return self.memo[key]
        raise ValueError(f'cannot evaluate {type(node).__name__}')

    def value(self, expr):
        v = self.ev(parse_stock(expr, 'score', self.sig))
        return np.broadcast_to(_f(v), (len(self.D), self.P.N)).astype(float)

    def mask(self, expr):
        v = self.ev(parse_stock(expr, 'filter', self.sig))
        return np.broadcast_to(_b(v), (len(self.D), self.P.N))


def _f(v):
    return v.astype(float) if isinstance(v, np.ndarray) and v.dtype == bool else v


def _b(v):
    if isinstance(v, np.ndarray):
        return v if v.dtype == bool else (np.nan_to_num(v, nan=0.0) != 0)
    return bool(v) if np.isfinite(v) else False


# ---------------------------------------------------------------- spec
def _weight_cfg(w):
    if w in (None, 'equal'):
        return ('equal', None)
    if w == 'score':
        return ('score', None)
    m = re.fullmatch(r'\s*invvol\s*\(\s*(\d+)\s*\)\s*', str(w))
    if m and int(m.group(1)) > MAX_WIN:
        raise ValueError(MSG_WIN.format(what='stock weight', call=str(w).strip(), w=int(m.group(1))))
    if m and int(m.group(1)) >= 2:
        return ('invvol', int(m.group(1)))
    raise ValueError(f"stock weight must be equal | score | invvol(n) (n >= 2), not {w!r}")


def cfg_of(spec):
    """Checked stock block -> dict (raises ValueError with a readable message)."""
    st = spec.get('stock')
    if not isinstance(st, dict):
        raise ValueError('universe spec needs a `stock:` mapping (score, top, ...)')
    bad = sorted(set(st) - STOCK_KEYS)
    if bad:
        raise ValueError(f'unknown stock key(s) {bad} (allowed: {sorted(STOCK_KEYS)})')
    reb = st.get('rebalance', 'month')
    if reb not in CAD:
        raise ValueError(f'stock rebalance must be month | quarter | week, not {reb!r}')
    if st.get('score') is None:
        raise ValueError('stock needs `score:` (a per-stock expression, higher = picked first)')
    sg = spec.get('signals') or {}
    sg = set(sg) if isinstance(sg, dict) else set()
    parse_stock(st['score'], 'score', sg)
    used = _bare_names(st['score'])
    if st.get('filter') is not None:
        parse_stock(st['filter'], 'filter', sg)
        used |= _bare_names(st['filter'])
    if ('top' in st) == ('top_pct' in st):
        raise ValueError('stock needs exactly one of `top: K` or `top_pct: x`')
    top, pct = st.get('top'), st.get('top_pct')
    if top is not None and (isinstance(top, bool) or not isinstance(top, int) or top < 1):
        raise ValueError(f'stock top must be an integer >= 1, not {top!r}')
    if pct is not None and (isinstance(pct, bool) or not isinstance(pct, (int, float)) or not 0 < pct <= 1):
        raise ValueError(f'stock top_pct must be in (0, 1], not {pct!r}')
    wk, wn = _weight_cfg(st.get('weight', 'equal'))
    cap = st.get('max_weight')
    if cap is not None and (isinstance(cap, bool) or not isinstance(cap, (int, float)) or not 0 < cap <= 1):
        raise ValueError(f'stock max_weight must be in (0, 1], not {cap!r}')
    els = st.get('else', {'CASH': 1.0})
    if not isinstance(els, dict) or not els:
        raise ValueError('stock else must be a mapping {CASH or ETF sleeve: weight}')
    for k, v in els.items():
        if k != 'CASH' and (k not in data.SLEEVES or k in data.KR_SLEEVES):
            raise ValueError(f'stock else: {k!r} is not CASH or a US ETF sleeve ({", ".join(sorted(set(data.SLEEVES) - set(data.KR_SLEEVES)))})')
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 1:
            raise ValueError(f'stock else weights must be numbers in [0, 1], not {v!r}')
    if sum(float(v) for v in els.values()) > 1 + 1e-9:
        raise ValueError('stock else weights sum to more than 1')
    ex = st.get('exposure')
    if ex is not None and (isinstance(ex, bool) or not isinstance(ex, (str, int, float))):
        raise ValueError(f'stock exposure must be a signal name or an expression, not {ex!r}')
    if ex is None and any(k != 'CASH' for k in els):
        raise ValueError('stock else is only used with `exposure:` (the unexposed share)')
    ee = st.get('exposure_every', 'daily')
    if ee not in ('daily', 'rebalance'):
        raise ValueError(f"stock exposure_every must be daily | rebalance, not {ee!r}")
    return dict(rebalance=CAD[reb], score=st['score'], filter=st.get('filter'), top=top, top_pct=pct, weight=wk,
                wn=wn, cap=None if cap is None else float(cap), exposure=ex, exposure_every=ee,
                els={k: float(v) for k, v in els.items() if k != 'CASH' and float(v) > 0}, sig=sorted(used))


def check_spec(spec):
    """Universe spec checks (dsl.check_spec calls this after its delay / cost / grid checks)."""
    if spec.get('universe') != 'sp500':
        raise ValueError(f"universe must be 'sp500' (the only stock universe), not {spec.get('universe')!r}")
    bad = [k for k in NOT_IN_UNIVERSE if spec.get(k) is not None]
    if bad:
        raise ValueError(f'{bad} not used in a universe spec (stock picks come from `stock:`; an exposure gate is '
                         '`signals:` + `stock.exposure` / `stock.else`)')
    if spec.get('account', 'us') != 'us':
        raise ValueError('universe spec: account must be us (US stocks: 0.30%/side, 22% yearly net gain tax)')
    sig = spec.get('signals') or {}
    if not isinstance(sig, dict):
        raise ValueError('signals must be a mapping {name: expression}')
    for k in sig:
        if not isinstance(k, str) or not k.isidentifier() or k.startswith('_') or k in dsl.FUNCS:
            raise ValueError(f'signal name {k!r} must be an identifier that is not a DSL function (YAML on/off/yes/no '
                             'are booleans) and does not start with _')
        if k in DIV_NAMES:                         # a dividend name: the Korean reason, whatever the signal holds
            raise ValueError(f'{MSG_DIV.format(nm=k)} (signal name {k!r})')
        if k in SFUNCS or k in FORBID:            # a score / filter reads signal names: no per-stock name collisions
            raise ValueError(f'signal name {k!r} is a per-stock function or a refused input name: rename it '
                             '(e.g. up, calm)')
    c = cfg_of(spec)
    for e in list(sig.values()) + ([c['exposure']] if isinstance(c['exposure'], str) else []):
        _gate_forbid(e)
        names = _gate_names(e, set(sig))
        if 'level' in names['funcs']:
            raise ValueError('universe spec: level(x) is not available (no ETF book is traded by the gate)')
        unk = sorted(names['series'] - _known_series())
        if unk:
            raise ValueError(f'gate expression {e!r}: unknown name(s) {unk} (signal names, ETF sleeves or panel keys)')
    return spec


def _known_series():
    if 'keys' not in _cache:
        _cache['keys'] = set(data.signal_keys()) | set(data.SLEEVES)      # panel keys, _SP500EW, sleeves
    return _cache['keys']


def _gate_forbid(expr):
    """Gate expressions (signals / exposure, the ETF DSL) may not name dollar volume (L1) or dividends either."""
    _div_forbid(expr, 'gate')
    try:
        tree = ast.parse(str(expr), mode='eval')
    except SyntaxError:
        return                                        # dsl._parse reports the syntax error
    for n in ast.walk(tree):
        nm = n.id if isinstance(n, ast.Name) else n.value if isinstance(n, ast.Constant) else None
        if isinstance(nm, str) and nm in VOL_NAMES:
            raise ValueError(f'{MSG_DVOL.format(nm=nm)} (gate: {expr!r})')


def _gate_names(expr, own):
    tree = dsl._parse(expr)
    funcs = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    flag = {id(a) for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == 'macro' for a in n.args}      # macro(k): k is a flag key (dsl.check_spec checks it)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and id(n) not in flag} - funcs - set(own) \
        - set(dsl.FUNCS)
    names |= {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
              and id(n) not in flag}
    bad = funcs - set(dsl.FUNCS)
    if bad:
        raise ValueError(f'gate expression {expr!r}: unknown function(s) {sorted(bad)}')
    keys = {n.id if isinstance(n, ast.Name) else n.value if isinstance(n, ast.Constant) else '?'
            for n in ast.walk(tree) if id(n) in flag}
    badm = sorted(str(k) for k in keys if k not in data.MACRO_KEYS)
    if badm:
        raise ValueError(f'gate expression {expr!r}: macro(k): k must be one of {", ".join(data.MACRO_KEYS)}, '
                         f'not {badm}')
    return dict(funcs=funcs, series=names)


# ---------------------------------------------------------------- gate (ETF DSL on the stock calendar)
def needs_frame(spec):
    """The spec reads the ETF DSL on the stock calendar: an exposure gate, or signals in its score / filter."""
    c = cfg_of(spec)
    return c['exposure'] is not None or bool(c['sig'])


def gate_frame(spec, idx, P=None):
    """Series the signals / exposure read (sleeve names -> their underlying), each cut at DEV_END, on the stock
    calendar idx. _SP500EW is built from the stock panel P (default: the loaded panel), so a cut or rewritten panel
    gives its own (causal) index."""
    c = cfg_of(spec)
    sig = spec.get('signals') or {}
    exprs = list(sig.values()) + ([c['exposure']] if isinstance(c['exposure'], str) else [])
    keys = set()
    for e in exprs:
        for nm in _gate_names(e, set(sig))['series']:
            keys.add(data.SLEEVES[nm][1] if nm in data.SLEEVES else nm)
    F = pd.DataFrame(index=idx)
    for k in sorted(keys):
        if k == data.SP500EW:                           # derived from the (sealed) stock panel, not the ETF panel
            Pk = load() if P is None else P
            F[k] = pd.Series(sp500ew(Pk), index=Pk.idx).reindex(idx).ffill()
            continue
        s = data.series(k)
        s = s[s.index <= DEV_END]                       # seal: nothing after 2014-12-31 enters
        F[k] = s.reindex(idx).ffill() if len(s) else np.nan
    _sealed(F.index)
    return F


def _gate_env(spec, F):
    env = dict(dsl._mk(F))
    assets = set(F.columns) | set(data.SLEEVES)
    for name, expr in (spec.get('signals') or {}).items():
        env[name] = dsl._eval(expr, env, assets)
    return env, assets


def gate_exprs(spec):
    """The exposure gate's expressions: the signals the exposure reads (sig_closure, in order) and the exposure."""
    c = cfg_of(spec)
    ex = c['exposure']
    if not isinstance(ex, str):
        return []
    sig = spec.get('signals') or {}
    return [sig[k] for k in sig_closure(spec, _dsl_refs(ex, set(sig)))] + [ex]


def gate_cols(spec, F):
    """Columns of the gate frame F that the exposure gate reads (gate_exprs)."""
    sig = spec.get('signals') or {}
    keys = set()
    for e in gate_exprs(spec):
        for nm in _gate_names(e, set(sig))['series']:
            keys.add(data.SLEEVES[nm][1] if nm in data.SLEEVES else nm)
    return [k for k in F.columns if k in keys]


def _dsl_refs(expr, own):
    """Signal names (of `own`) an ETF-DSL expression reads (bare names; a macro(k) key is not one)."""
    if isinstance(expr, (int, float)) or not dsl._parses(expr):
        return set()
    tree = dsl._parse(expr)
    skip = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    skip |= {id(a) for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == 'macro' for a in n.args}
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and id(n) not in skip and n.id in own}


def sig_closure(spec, names):
    """The signals `names` read, directly or through other signals, in spec order (they are evaluated in order)."""
    sig = spec.get('signals') or {}
    need, todo = set(), list(names)
    while todo:
        k = todo.pop()
        if k in need or k not in sig:
            continue
        need.add(k)
        todo += sorted(_dsl_refs(sig[k], set(sig) - {k}))
    return [k for k in sig if k in need]


def _ind_calls(expr):
    """Indicator calls inside an ETF-DSL expression whose value can be undefined (dsl.valid_from's set)."""
    if isinstance(expr, (int, float)) or not dsl._parses(expr):
        return []
    return [ast.unparse(n) for n in ast.walk(dsl._parse(expr)) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name) and n.func.id in dsl.FUNCS and n.func.id not in dsl._NO_WARM]


def _sig_array(k, v, idx):
    """A signal's value on idx as floats (boolean -> 1.0 / 0.0; NaN kept)."""
    if isinstance(v, str):
        raise ValueError(f'signal {k!r} is the series name {v!r}, not a value: a stock score / filter reads a signal '
                         f'as a number or a boolean (write e.g. price({v}) > sma({v}, 200))')
    if isinstance(v, pd.Series):
        v = v.reindex(idx)
        try:
            return v.astype(float).values
        except (TypeError, ValueError):
            raise ValueError(f'signal {k!r} is not a number or a boolean series')
    a = np.asarray(v, dtype=float)
    if a.ndim == 0:
        return np.full(len(idx), float(a))
    if a.shape != (len(idx),):
        raise ValueError(f'signal {k!r}: unexpected shape {a.shape}')
    return a.copy()


def signal_values(spec, P, F=None):
    """Signals read by stock.score / stock.filter on the stock calendar -> ({name: [T] float at each close (boolean ->
    1 / 0)}, informed [T] bool or None, [indicator calls never defined]). Informed at t = every used signal is finite
    at t and every indicator call inside it and inside the signals it reads (sig_closure) has a value at t
    (dsl.valid_from's calls, row by row: before sma(_SP500EW, 200) exists the comparison reads False, which is not a
    regime). Causal: the ETF DSL reads rows <= t."""
    c = cfg_of(spec)
    if not c['sig']:
        return {}, None, []
    F = gate_frame(spec, P.idx, P) if F is None else F
    env, assets = _gate_env(spec, F)
    vals = {k: _sig_array(k, env[k], P.idx) for k in c['sig']}
    ok = np.ones(P.T, bool)
    for v in vals.values():
        ok &= np.isfinite(v)
    never, sig = [], spec.get('signals') or {}
    for k in sig_closure(spec, c['sig']):
        for call in _ind_calls(sig[k]):
            try:
                v = dsl._eval(call, env, assets)
            except Exception:                           # evaluated inside the signal already; nothing to add
                continue
            if not isinstance(v, pd.Series) or v.dtype == bool:
                continue
            try:
                fin = np.isfinite(v.reindex(P.idx).astype(float).values)
            except (TypeError, ValueError):
                continue
            ok &= fin
            if not fin.any():
                never.append(call)
    return vals, ok, never


def signal_row(tg):
    """First decision row on which every score / filter signal is informed (None: no such signals, or never)."""
    if tg.sig_ok is None or not tg.sig_ok.any():
        return None
    return int(tg.dec[int(np.argmax(tg.sig_ok))])


def gate_valid(spec, P, F):
    """First decision row at which the exposure gate is informed: every indicator call of the gate (the exposure and
    the signals it reads, gate_exprs; a score-only signal is not the gate's) has a value (dsl.valid_from: sma(_NDX,
    200) on the stock calendar -> its 200th row after _NDX starts; before it a comparison reads False = the gate is
    forced to the else share). With exposure_every: rebalance, the first rebalance row on or after it. -> (row or
    None, [never-valid calls])."""
    c = cfg_of(spec)
    if c['exposure'] is None or F is None:
        return None, []
    env, assets = _gate_env(spec, F)
    fv, never = dsl.valid_from(gate_exprs(spec), env, assets)
    if fv is None:
        return None, never
    r = int(np.searchsorted(P.idx, fv))
    if c['exposure_every'] == 'rebalance':
        rows = np.flatnonzero(dsl.reb_rows(P.idx, c['rebalance']))
        rows = rows[rows >= r]
        r = int(rows[0]) if len(rows) else P.T - 1
    return r, never


def gate_start(P, row, delay):
    """First engine row whose target was decided on an informed gate row (decision row + delay), as a date."""
    return None if row is None else P.idx[min(row + delay, P.T - 1)]


def exposure(spec, P, F=None):
    """[T] exposure in [0, 1] decided at each close (1.0 when the spec has no exposure gate)."""
    c = cfg_of(spec)
    if c['exposure'] is None:
        return np.ones(P.T)
    F = gate_frame(spec, P.idx, P) if F is None else F
    env, assets = _gate_env(spec, F)
    ex = c['exposure']
    v = env[ex] if isinstance(ex, str) and ex in (spec.get('signals') or {}) else dsl._eval(ex, env, assets)
    if isinstance(v, pd.Series):
        v = v.reindex(P.idx).values
    v = np.broadcast_to(np.asarray(v, dtype=float) if not (isinstance(v, np.ndarray) and v.dtype == bool)
                        else v.astype(float), (P.T,)).copy()
    v = np.clip(np.nan_to_num(v, nan=0.0), 0.0, 1.0)
    if c['exposure_every'] == 'rebalance':
        rows = dsl.reb_rows(P.idx, c['rebalance'])
        v, _ = dsl._ffill_rows(v[:, None], rows)
        v = v[:, 0]
    return v


# ---------------------------------------------------------------- targets
class Targets:
    """Decisions of one spec: dec (decision rows), picks[j] (name columns), wts[j] (weights), K[j] (the 1/K unit),
    retain[j] (names kept from decision j-1), elig ([nd, N] eligible), e ([T] exposure), els ({sleeve: w}),
    sig_ok ([nd] score / filter signals informed, None without such signals), sig_never (calls never defined),
    tie ([nd] the top-K boundary was a tie, shared: top_k), unit ([nd] the equal weight per held name for the null:
    min(K, eligible) / K / names held = 1/K without a shared tie)."""

    def __init__(self, dec, picks, wts, K, elig, e, els, cap, sig_ok=None, sig_never=(), tie=None, unit=None):
        self.dec, self.picks, self.wts, self.K, self.elig, self.e, self.els, self.cap = dec, picks, wts, K, elig, e, els, cap
        self.sig_ok, self.sig_never = sig_ok, list(sig_never)
        self.tie = np.zeros(len(dec), bool) if tie is None else np.asarray(tie, bool)
        self.unit = 1.0 / np.asarray(K, float) if unit is None else np.asarray(unit, float)
        self.retain = np.array([0] + [len(np.intersect1d(picks[j], picks[j - 1])) for j in range(1, len(picks))],
                               np.int64)


def top_k(sx, n):
    """The top n of one decision's scores sx ([N], -inf = not eligible; n <= the eligible count) -> (columns, inclusion
    share f). A tie at the boundary (more names with the n-th best score than the slots left for them) is SHARED: every
    tied name gets f = slots / tied names (the expected book over a uniformly random order of the tied names), never
    an order of the panel columns (the source's last-known symbols in alphabetical order, not point in time). An
    all-tied score (e.g. `up * rank(ret(231, 21))` while up = 0) holds every eligible name at n / K / m. -> (cols
    sorted, f, tie)."""
    if n <= 0:
        return np.zeros(0, np.int64), np.zeros(0), False
    fin = np.isfinite(sx)
    if n >= int(fin.sum()):
        p = np.flatnonzero(fin)
        return p, np.ones(len(p)), False
    s_n = np.partition(sx, len(sx) - n)[len(sx) - n]                 # the n-th best score (finite: n <= eligible)
    above, at = sx > s_n, sx == s_n
    r, g = n - int(above.sum()), int(at.sum())
    if g <= r:                                                       # the boundary is not shared: every tie fits
        p = np.flatnonzero(above | at)
        return p, np.ones(len(p)), False
    p = np.flatnonzero(above | at)
    return p, np.where(at[p], r / g, 1.0), True


def compile_targets(spec, P, F=None):
    """Per-decision picks and weights (point in time: decision row t reads panel rows <= t only). F: the gate frame
    (gate_frame; built from P when None and the spec needs one). A decision whose score / filter signals are not all
    informed (signal_values) has no eligible name: the stock share holds CASH."""
    c = cfg_of(spec)
    D = np.flatnonzero(dsl.reb_rows(P.idx, c['rebalance']))
    if F is None and needs_frame(spec):
        F = gate_frame(spec, P.idx, P)
    ok, never, sv = None, [], {}
    if c['sig']:
        vals, ok, never = signal_values(spec, P, F)
        sv = {k: np.where(ok, v, np.nan)[D] for k, v in vals.items()}      # not informed -> NaN, never 0
    cx = _Ctx(P, D, sv)
    S = cx.value(c['score'])
    E = cx.E0 & np.isfinite(S)
    if c['filter'] is not None:
        E = E & cx.mask(c['filter'])
    if ok is not None:
        E = E & ok[D][:, None]                         # `not up` of a missing up is not True: no name, CASH
    V = None
    if c['weight'] == 'invvol':
        V = cx.call('vol', [c['wn']])
        E = E & np.isfinite(V) & (V > 0)
    picks, wts, Ks, ties, units = [], [], [], np.zeros(len(D), bool), np.zeros(len(D))
    Sx = np.where(E, S, -np.inf)
    m = E.sum(1)
    for j in range(len(D)):
        K = c['top'] if c['top'] is not None else (max(1, math.ceil(c['top_pct'] * m[j])) if m[j] else 1)
        n = min(K, int(m[j]))
        p, f, ties[j] = top_k(Sx[j], n)             # a tie at the top-K boundary is shared (no column order)
        if c['weight'] == 'equal' or n == 0:
            w = f / K
        else:
            raw = (1.0 / V[j, p] if c['weight'] == 'invvol' else np.maximum(S[j, p], 0.0)) * f
            if not raw.sum() > 0:
                raw = f.copy()
            w = raw / raw.sum() * n / K
        if c['cap'] is not None:
            w = np.minimum(w, c['cap'])
        units[j] = n / K / len(p) if len(p) else 1.0 / K
        picks.append(p.astype(np.int64)); wts.append(w); Ks.append(K)
    return Targets(D, picks, wts, np.array(Ks), E, exposure(spec, P, F), c['els'], c['cap'],
                   None if ok is None else ok[D], never, ties, units)


def ew_targets(P, cad='monthly'):
    """Equal-weight members benchmark: every member with a price at the decision close, 1/m each."""
    D = np.flatnonzero(dsl.reb_rows(P.idx, cad))
    E = P.member[D] & P.has[D]
    picks = [np.flatnonzero(E[j]) for j in range(len(D))]
    wts = [np.full(len(p), 1.0 / max(len(p), 1)) for p in picks]
    return Targets(D, picks, wts, np.array([max(len(p), 1) for p in picks]), E, np.ones(P.T), {}, None)


# ---------------------------------------------------------------- sleeves on the stock calendar
def rf_on(idx):
    """T-bill daily return on the stock calendar (lab rule: _IRX / 100 / 252, carried forward), _IRX cut at DEV_END."""
    key = ('rf', len(idx), idx[0] if len(idx) else None, idx[-1] if len(idx) else None)
    if key not in _cache:
        irx = data.series('_IRX', 3)
        irx = irx[irx.index <= DEV_END] / 100.0           # seal
        _cache[key] = (irx.reindex(idx).ffill().fillna(0.0) / 252.0).values
    return _cache[key]


def else_returns(els, idx):
    """ETF sleeve returns of the lab ETF panel (data.build, cut at DEV_END), carried onto the stock calendar as a
    level (nothing lost on a calendar mismatch). Returns (DataFrame, {sleeve: first return date})."""
    if not els:
        return pd.DataFrame(index=idx), {}
    key = ('else', tuple(sorted(els)), len(idx), idx[0], idx[-1])
    if key not in _cache:
        _, R, _, _ = data.build(sorted(els))
        R = R[R.index <= DEV_END]                         # seal
        out, first = {}, {}
        for s in sorted(els):
            r = R[s].values.astype(float); ok = np.isfinite(r)
            if not ok.any():
                raise ValueError(f'stock else: {s} has no returns <= {DEV_END.date()}')
            f = int(np.argmax(ok)); base = max(f - 1, 0)
            lv = np.cumprod(1.0 + np.where(ok & (np.arange(len(r)) > base), r, 0.0))
            lv = pd.Series(np.where(np.arange(len(r)) >= base, lv, np.nan), index=R.index)
            out[s] = lv.reindex(idx).ffill().pct_change(fill_method=None)
            first[s] = out[s].first_valid_index()
        _cache[key] = (pd.DataFrame(out, index=idx), first)
    return _cache[key]


# ---------------------------------------------------------------- engine frames (engine.run)
def _daily_pos(P, tg):
    """Row -> index of the decision in force at that close (-1 before the first)."""
    pos = np.full(P.T, -1, np.int64)
    pos[tg.dec] = np.arange(len(tg.dec))
    return np.maximum.accumulate(pos)


def frames(P, tg, h):
    """DataFrames for engine.run: W (held-ever names + else sleeves + CASH), R, rebal flags, frozen, no_buy, DV (the
    names' dividend yields divy; else sleeves and CASH 0)."""
    names = np.unique(np.concatenate(list(tg.picks) + [np.zeros(0, np.int64)])).astype(np.int64)
    k = len(names); ci = np.full(P.N, -1); ci[names] = np.arange(k)
    B = np.zeros((len(tg.dec), k))
    for j, (p, w) in enumerate(zip(tg.picks, tg.wts)):
        B[j, ci[p]] = w
    pos = _daily_pos(P, tg)
    Bd = np.where((pos >= 0)[:, None], B[np.maximum(pos, 0)], 0.0) * tg.e[:, None]
    labels = [f'S{j}' for j in names]
    W = pd.DataFrame(Bd, index=P.idx, columns=labels)
    Re = else_returns(tg.els, P.idx)[0]
    for s, w in tg.els.items():
        W[s] = (1.0 - tg.e) * w
    W['CASH'] = 1.0 - W.sum(1)
    R = pd.DataFrame(P.R(h)[:, names], index=P.idx, columns=labels)
    for s in tg.els:
        R[s] = Re[s].values
    R['CASH'] = rf_on(P.idx)
    reb = pd.Series(False, index=P.idx); reb.iloc[tg.dec] = True
    FZ = pd.DataFrame(P.frozen[:, names], index=P.idx, columns=labels)
    NB = pd.DataFrame(P.no_buy[:, names], index=P.idx, columns=labels)
    DV = pd.DataFrame(P.divy[:, names].astype(np.float64), index=P.idx, columns=labels)
    return W, R, reb, FZ, NB, names, DV


def run_engine(P, tg, h, start, cost, tax, delay, R_edit=None, dtax=DIV_TAX):
    """engine.run on the spec's targets (the reference engine), with the dividend tax (div = the names' divy, div_tax =
    dtax). R_edit(R) may change the returns (tests: hazard)."""
    W, R, reb, FZ, NB, names, DV = frames(P, tg, h)
    if R_edit is not None:
        R = R_edit(R, names)
    o = engine.run(W, R, start, DEV_END, cost=cost, tax=tax, delay=delay, rebal=reb, frozen=FZ, no_buy=NB, div=DV,
                   div_tax=dtax)
    _sealed(o['E'].index)
    return o


# ---------------------------------------------------------------- fast path (D books at once)
def _rows(P, start):
    i0 = int(np.searchsorted(P.idx, start)); i1 = int(np.searchsorted(P.idx, DEV_END, side='right')) - 1
    return i0, i1


def fast_run(P, tg, h, start, cost, tax, delay, baskets=None, D=1, hits=None, want_E=False, keep_book=False,
             dtax=DIV_TAX):
    """engine.run (with frozen / no_buy / div) vectorised over D books that share the decision rows, exposure and else
    sleeves: the same rules line by line (yearly tax, the dividend tax, a trade on a target change / decision row /
    blocked-trade retry, the initial book free of cost). Parity with engine.run is tested (tests/test_stocks.py).
    baskets: None = the spec's own picks in every book, else a list over decisions of (cols [D, n] panel name columns,
    -1 = none; w [D, n]); hits: {panel row: (book idx, name col)} wipes those positions (-100%) after the row's return
    (a wiped position gets no dividend that row). dtax: dividend tax rate (DIV_TAX; 0 = dividends untaxed but still
    cost basis): on a row where a held name pays, dividend cash dc = its value at the previous close x divy; its value
    after the row's total return loses dtax x dc, its cost basis gains (1 - dtax) x dc.
    Returns per-book arrays cagr_at, cagr_before_liq_tax (CAGR of E: after cost, the yearly tax and the dividend tax,
    before only the final liquidation tax), final_at, mdd, turn, trades, taxpaid (22% tax), divtax (dividend tax)
    (+ E [D, rows] and dnet [D, rows] = the reinvested after-tax dividend cash of each row, with want_E; + book
    [rows, k] = book 0's position values after each row's trade, columns names + else + CASH, with keep_book)."""
    idx = P.idx
    i0, i1 = _rows(P, start)
    assert i0 >= delay and idx[i1] <= DEV_END
    if baskets is None:
        baskets = [(np.broadcast_to(p, (D, len(p))), np.broadcast_to(w, (D, len(w)))) for p, w in zip(tg.picks, tg.wts)]
    pos = _daily_pos(P, tg)
    rows = np.arange(i0, i1 + 1); nr = len(rows)
    src = rows - delay                                    # decision-time row of each engine row's target
    dpos = pos[src]
    used = sorted(set(dpos[dpos >= 0].tolist()))
    names = np.unique(np.concatenate([np.asarray(baskets[j][0]).ravel() for j in used] + [np.zeros(0, np.int64)]))
    names = names[names >= 0].astype(np.int64)
    kn = len(names); ci = np.full(P.N, -1); ci[names] = np.arange(kn)
    els = sorted(tg.els); ke = len(els); k = kn + ke + 1; cashi = k - 1
    Re = else_returns(tg.els, idx)[0]
    G = np.empty((nr, k))
    G[:, :kn] = P.R(h)[i0:i1 + 1][:, names]
    for q, s in enumerate(els):
        G[:, kn + q] = np.nan_to_num(Re[s].values[i0:i1 + 1], nan=0.0)
    G[:, cashi] = rf_on(idx)[i0:i1 + 1]
    G += 1.0
    DY = np.zeros((nr, k))                                # dividend yields of the names (else sleeves, CASH: 0)
    DY[:, :kn] = P.divy[i0:i1 + 1][:, names]
    pays = DY.any(1)
    FZ = np.zeros((nr, k), bool); NB = np.zeros((nr, k), bool)
    FZ[:, :kn] = P.frozen[i0:i1 + 1][:, names]; NB[:, :kn] = P.no_buy[i0:i1 + 1][:, names]
    e_sh = tg.e[src]
    isdec = np.zeros(P.T, bool); isdec[tg.dec] = True
    force = isdec[src]
    elsew = np.array([tg.els[s] for s in els])
    cand = np.zeros(nr, bool); cand[0] = True
    cand[1:] = (dpos[1:] != dpos[:-1]) | (e_sh[1:] != e_sh[:-1])
    cand |= force
    hit = {}
    for r_, (dd_, cc_) in (hits or {}).items():
        if i0 <= r_ <= i1:
            cc_ = ci[np.asarray(cc_)]; ok = cc_ >= 0
            if ok.any():
                hit[r_ - i0] = (np.asarray(dd_)[ok], cc_[ok])
    bd = np.arange(D)

    def target(i):
        Wt = np.zeros((D, k))
        j = dpos[i]
        if j >= 0:
            c, w = np.asarray(baskets[j][0]), np.asarray(baskets[j][1])
            if c.size:
                cc = np.where(c >= 0, ci[np.maximum(c, 0)], -1)
                ok = cc >= 0
                Wt[np.broadcast_to(bd[:, None], c.shape)[ok], cc[ok]] = w[ok] * e_sh[i]
        Wt[:, kn:kn + ke] = (1.0 - e_sh[i]) * elsew
        Wt[:, cashi] = 1.0 - Wt[:, :cashi].sum(1)
        return Wt

    Wt = target(0)
    val = Wt.copy(); basis = val.copy()
    pend = np.zeros((D, k), bool)
    realized = np.zeros(D); turnover = np.zeros(D); taxpaid = np.zeros(D); trades = np.zeros(D, np.int64)
    divtax = np.zeros(D)
    eq = np.empty((D, nr)) if want_E else None
    dnet = np.zeros((D, nr)) if want_E else None
    book = np.empty((nr, k)) if keep_book else None
    peak = np.full(D, -np.inf); mdd = np.zeros(D)
    years = idx.year.values[i0:i1 + 1]; yr = years[0]
    with np.errstate(divide='ignore', invalid='ignore'):     # a book wiped to 0 / an empty book divides 0 / 0
        for i in range(nr):
            if years[i] != yr:
                t = tax * np.maximum(0.0, realized); taxpaid += t
                realized = np.zeros(D); yr = years[i]
                if (t > 0).any():
                    s = val.sum(1); f = np.where(t > 0, t / s, 0.0)
                    realized = np.where(t > 0, f * (val[:, :cashi] - basis[:, :cashi]).sum(1), 0.0)
                    val = val * (1 - f)[:, None]; basis = basis * (1 - f)[:, None]
            dv = i > 0 and pays[i]
            if dv:
                dc = val * DY[i]                          # dividend cash: value at the previous close x divy
            if i > 0:
                val *= G[i]
            if i in hit:
                val[hit[i]] = 0.0
                if dv:
                    dc[hit[i]] = 0.0                      # a wiped position (-100% row) gets no dividend
            if dv:                                        # tax when paid; the rest is reinvested cash = cost basis
                val -= dtax * dc; basis += (1.0 - dtax) * dc
                ds = dc.sum(1); divtax += dtax * ds
                if want_E:
                    dnet[:, i] = (1.0 - dtax) * ds
            go = np.zeros(D, bool)
            if cand[i]:
                Wn = target(i)
                go = np.full(D, bool(i == 0 or force[i])) | np.any(Wn != Wt, axis=1)
                Wt = Wn
            if pend.any():
                go |= np.any(pend & ~FZ[i], axis=1)
            if go.any():
                V = val.sum(1)
                tgt, blk = engine.limit_target(Wt * V[:, None], val, FZ[i], NB[i], cashi, V)
                do = go & (np.abs(tgt - val).sum(1) > 1e-9 * V)
                if do.any():
                    d = tgt - val
                    ad = np.abs(d[:, :cashi]).sum(1)
                    c = cost * ad
                    sell = (d[:, :cashi] < 0) & (val[:, :cashi] > 0)
                    vs = val[:, :cashi]
                    f = np.where(sell, np.minimum(1.0, -d[:, :cashi] / np.where(vs > 0, vs, 1.0)), 0.0)
                    g = (f * (vs - basis[:, :cashi])).sum(1)
                    bn = np.where(sell, basis[:, :cashi] * (1 - f), basis[:, :cashi])
                    bn = bn + np.where(d[:, :cashi] > 0, d[:, :cashi], 0.0)
                    dm = do[:, None]
                    realized = realized + np.where(do, g, 0.0)
                    basis[:, :cashi] = np.where(dm, bn, basis[:, :cashi])
                    turnover = turnover + np.where(do, ad / V, 0.0); trades += do
                    val = np.where(dm, tgt * (V - c)[:, None] / V[:, None], val)
                    pend = np.where(dm, blk, pend)
            E = val.sum(1)
            if want_E:
                eq[:, i] = E
            if keep_book:
                book[i] = val[0]
            peak = np.maximum(peak, E); mdd = np.minimum(mdd, E / peak - 1)
    unreal = (val[:, :cashi] - basis[:, :cashi]).sum(1)
    t = tax * np.maximum(0.0, realized + unreal)
    final = E - t
    yrs = (idx[i1] - idx[i0]).days / 365.25
    cg = lambda x: np.where(x > 0, np.abs(x) ** (1 / yrs), 0.0) - 1
    out = dict(cagr_at=cg(final), cagr_before_liq_tax=cg(E), final_at=final, mdd=mdd, turn=turnover / yrs,
               trades=trades, taxpaid=taxpaid, divtax=divtax, yrs=yrs, names=names)
    if want_E or keep_book:
        out['idx'] = idx[i0:i1 + 1]
    if want_E:
        out['E'] = eq; out['dnet'] = dnet
    if keep_book:
        out['book'] = book; out['cols'] = list(names) + els + ['CASH']
    return out


def run1(P, tg, h, start, cost, tax, delay, ends=False, dtax=DIV_TAX):
    """One book on the fast path (same numbers as run_engine, parity-tested) -> engine.run-like dict. ends: also
    count the series ends the book holds into (a position > 0 after the last price's row), {'fail': n, 'merger': m}."""
    o = fast_run(P, tg, h, start, cost, tax, delay, want_E=True, keep_book=ends, dtax=dtax)
    _sealed(o['idx'])
    out = dict(E=pd.Series(o['E'][0], index=o['idx']), cagr_at=float(o['cagr_at'][0]),
               cagr_before_liq_tax=float(o['cagr_before_liq_tax'][0]), final_at=float(o['final_at'][0]),
               mdd=float(o['mdd'][0]), turn=float(o['turn'][0]), trades=int(o['trades'][0]),
               taxpaid=float(o['taxpaid'][0]), divtax=float(o['divtax'][0]), yrs=o['yrs'])
    if ends:
        i0, i1 = _rows(P, start)
        nm = o['names']; L = P.last[nm]
        q = np.flatnonzero(P.ended[nm] & (L >= i0) & (L < i1))
        held = np.zeros(len(nm), bool)
        held[q] = o['book'][L[q] - i0, q] > 0
        out['ends'] = dict(fail=int((held & P.fail[nm]).sum()), merger=int((held & ~P.fail[nm]).sum()))
    return out


# ---------------------------------------------------------------- stress rows and the null
def hazard_hits(P, tg, start, D=N_HAZ, seed=HAZ_SEED, p=HAZARD):
    """EXTREME row: for each book d, year y and name ever picked, with probability p a -100% day drawn uniformly among
    the window's trading days of y (it only bites while the name is held). Seeded per book: default_rng([seed, d])."""
    names = np.unique(np.concatenate(list(tg.picks) + [np.zeros(0, np.int64)])).astype(np.int64)
    i0, i1 = _rows(P, start)
    years = P.idx.year.values[i0:i1 + 1]
    hits = {}
    for d in range(D):
        rng = np.random.default_rng([seed, d])
        for y in np.unique(years):
            ry = np.flatnonzero(years == y) + i0
            u = rng.random(len(names)); day = rng.integers(0, len(ry), size=len(names))
            for j in np.flatnonzero(u < p):
                hits.setdefault(int(ry[day[j]]), []).append((d, int(names[j])))
    return {r: (np.array([a for a, _ in v]), np.array([b for _, b in v])) for r, v in hits.items()}


def null_baskets(P, tg, start, delay, D=N_NULL, seed=NULL_SEED):
    """Random-basket null, one chain per book (deviation from a fully re-drawn basket, see README: a basket re-drawn
    every period turns over ~95% of its names and pays costs and taxes the strategy does not, which would flatter any
    strategy). On every decision a book holds as many names as the strategy picked, drawn from the strategy's own
    eligible set (eligibility, filter, finite score), and keeps as many of its previous names as the strategy kept
    from its previous basket (random ones among those still eligible), so name turnover matches. Equal weight with
    the strategy's unit 1/K (tg.unit: on a decision whose top-K boundary tie is shared, the same total min(K, m) / K
    spread over the names it holds) and cap. The chain starts fresh at the decision in force on the window's first
    row."""
    rng = np.random.default_rng(seed)
    pos = _daily_pos(P, tg)
    i0, _ = _rows(P, start)
    j0 = int(pos[i0 - delay])
    nd = len(tg.dec)
    empty = (np.zeros((D, 0), np.int64), np.zeros((D, 0)))
    out = [empty] * nd
    prev = None
    q = None
    for j in range(max(j0, 0), nd):
        n = len(tg.picks[j])
        if n == 0:
            out[j] = empty; prev = empty[0]
            continue
        E = np.flatnonzero(tg.elig[j]); m = len(E)
        kept = np.full((D, n), -1, np.int64); nk = np.zeros(D, np.int64)
        r = int(tg.retain[j]) if j > j0 else 0
        if prev is not None and prev.shape[1] and r > 0:
            el = (prev >= 0) & tg.elig[j][np.maximum(prev, 0)]
            key = np.where(el, rng.random(prev.shape), np.inf)
            o = np.argsort(key, 1, kind='stable')[:, :r]
            nk = np.minimum(r, el.sum(1))
            take = np.take_along_axis(prev, o, 1)
            kept[:, :r] = np.where(np.arange(r)[None, :] < nk[:, None], take, -1)
        posE = np.full(P.N, -1); posE[E] = np.arange(m)
        key = rng.random((D, m))
        kr, kc = np.nonzero(kept >= 0)
        key[kr, posE[kept[kr, kc]]] = np.inf
        sel = np.argpartition(key, n - 1, axis=1)[:, :n] if n < m else np.broadcast_to(np.arange(m), (D, m)).copy()
        sel = np.take_along_axis(sel, np.argsort(np.take_along_axis(key, sel, 1), 1, kind='stable'), 1)
        fill = E[sel]
        qq = np.arange(n)[None, :]
        res = np.where(qq < nk[:, None], np.take_along_axis(kept, np.minimum(qq, n - 1).repeat(D, 0), 1),
                       np.take_along_axis(fill, np.maximum(qq - nk[:, None], 0), 1))
        w = np.full((D, n), tg.unit[j])                 # 1/K; less when a shared tie holds more names (top_k)
        if tg.cap is not None:
            w = np.minimum(w, tg.cap)
        out[j] = (res, w); prev = res
    return out


# ---------------------------------------------------------------- benchmarks
def ndx_hold(start, cost, tax, delay):
    """NDX 1x hold = the lab QQQ sleeve (_NDX before QQQ lists), lab ETF engine, same costs and tax."""
    key = ('ndx', start, cost, tax, delay)
    if key not in _cache:
        _, R, _, _ = data.build(['QQQ'])
        R = R[R.index <= DEV_END]                         # seal
        Wb = pd.DataFrame({'QQQ': 1.0, 'CASH': 0.0}, index=R.index)
        o = engine.run(Wb, R, start, DEV_END, cost=cost, tax=tax, delay=delay)
        _sealed(o['E'].index)
        _cache[key] = dict(cagr_at=o['cagr_at'], mdd=o['mdd'], start=str(o['E'].index[0].date()))
    return _cache[key]


def ew_row(P, h, start, cost, tax, delay):
    key = ('ew', id(P), h, start, cost, tax, delay)
    if key not in _cache:
        if ('ewtg', id(P)) not in _cache:
            _cache[('ewtg', id(P))] = ew_targets(P)
        tg = _cache[('ewtg', id(P))]
        o = run1(P, tg, h, start, cost, tax, delay)
        _cache[key] = dict(cagr_at=o['cagr_at'], mdd=o['mdd'], turn=o['turn'], names=avg_names(P, tg, start, delay))
    return _cache[key]


def avg_names(P, tg, start, delay):
    """Average number of names in the book the engine targets over the window (0 on unexposed days)."""
    i0, i1 = _rows(P, start)
    src = np.arange(i0, i1 + 1) - delay
    pos = _daily_pos(P, tg)[src]
    cnt = np.array([len(p) for p in tg.picks] + [0])[np.where(pos >= 0, pos, -1)]
    return float(np.mean(np.where(tg.e[src] > 0, cnt, 0)))


def tie_count(P, tg, start, delay):
    """(decisions whose top-K boundary tie was shared, decisions) among the ones in force inside the window."""
    i0, i1 = _rows(P, start)
    pos = _daily_pos(P, tg)[np.arange(i0, i1 + 1) - delay]
    js = np.unique(pos[pos >= 0])
    return int(tg.tie[js].sum()), int(len(js))


def sharpe(o, P):
    """Annualised mean / stdev of daily returns over the T-bill (evaluate passes the pre-tax book: after cost, no 22%
    tax, no dividend tax)."""
    E = o['E']
    r = E.pct_change().dropna()
    rf = pd.Series(rf_on(P.idx), index=P.idx).reindex(r.index).values
    ex = r.values - rf
    sd = ex.std(ddof=1) if len(ex) > 1 else 0.0
    return float(ex.mean() / sd * np.sqrt(252)) if sd > 1e-12 else float('nan')   # all T-bill: 0 / float noise


# ---------------------------------------------------------------- causality (runtime cuts)
def pit_check(spec, P, tg, F=None, n_cuts=N_PIT_CUTS, seed=None):
    """Decisions built on the panel cut at a row must equal the full-panel decisions before it. The gate frame of a
    cut is rebuilt from the cut panel (gate_frame: _SP500EW from the cut rows, ETF series on the cut calendar), so the
    derived index is cut-tested too."""
    if seed is None:
        seed = int.from_bytes(os.urandom(8), 'little')
    rng = np.random.default_rng(seed)
    lo = min(P.T - 1, 300)
    cuts = sorted({int(x) for x in rng.integers(lo, P.T, size=n_cuts)})
    bad = []
    for c in cuts:
        Pc = P.cut(c)
        t2 = compile_targets(spec, Pc, None if F is None else gate_frame(spec, Pc.idx, Pc))
        nd = int(np.searchsorted(tg.dec, c))
        ok = len(t2.dec) == nd and np.array_equal(t2.dec, tg.dec[:nd]) and np.array_equal(t2.e, tg.e[:c])
        ok = ok and all(np.array_equal(t2.picks[j], tg.picks[j]) and np.allclose(t2.wts[j], tg.wts[j], rtol=0,
                                                                                    atol=1e-12) for j in range(nd))
        if not ok:
            bad.append(str(P.idx[c - 1].date()))
    return dict(ok=not bad, cuts=len(cuts), violations=bad[:3], seed=seed)


# ---------------------------------------------------------------- MS1 / G1 inputs (lab/ms1.py)
def gate_spec(spec):
    """The exposure gate as an ETF spec for G1 (gate.test): hold QQQ with the exposure as its weight, else cash
    (in market = exposure > 0, the stock book's own rule), `rebalance:` = the stock cadence when the exposure is
    sampled on decision rows only. None when the spec has no exposure gate. Same family (G1 deflation uses its N).
    Only the signals the exposure reads (sig_closure) go with it: a score-only signal (e.g. on _SP500EW) does not take
    the gate off the G1 frames."""
    c = cfg_of(spec)
    if c['exposure'] is None:
        return None
    g = dict(name=f"{spec.get('name', 'stock')}:gate", family=str(spec.get('family', 'unset')),
             rules=[{'else': {'QQQ': c['exposure']}}])
    sig = spec.get('signals') or {}
    keep = sig_closure(spec, _dsl_refs(c['exposure'], set(sig))) if sig else []
    if keep:
        g['signals'] = {k: sig[k] for k in keep}             # = gate_exprs
    if c['exposure_every'] == 'rebalance':
        g['rebalance'] = c['rebalance']
    return g


def ms1_stream(spec, P=None):
    """MS1 input of a stock spec (ms1.measure_series): the CONSERVATIVE book's (H_CONS: the classified delisting rule,
    the headline) daily return after trading cost and the dividend tax (DIV_TAX, paid when the dividend is), BEFORE the
    22% tax (MS1 applies its own), with basis_add = each day's reinvested after-tax dividend / the book's value at the
    previous close (measure_series adds it to the stream's cost basis, so MS1's 22% tax does not fall on dividends
    again), on the real stock calendar, from MS1_FROM (1970-01-02, the first
    point-in-time member day) or the later start of an else sleeve, of the warmed-up gate (gate_start: before it
    the gate is forced to the else share) or of the informed score / filter signals (signal_row + delay: before it the
    stock share is CASH), to 2014-12-31. turnover = min(1, one-way yearly turnover) = measure_series' realized share.
    -> dict(dates, ret, basis_add, label, turnover, start, min_cover)."""
    spec = dsl.check_spec(spec)
    P = load() if P is None else P
    c = cfg_of(spec)
    cost = max(dsl.MIN_COST, float(spec.get('cost', dsl.MIN_COST)))
    delay = int(spec.get('delay', dsl.MIN_DELAY))
    h = dsl.spec_hash(spec)
    hit = _cache.get('last_tg')
    if hit is not None and hit[0] == h and hit[1] == id(P):
        tg, F = hit[2], hit[3]
    else:
        F = gate_frame(spec, P.idx, P) if needs_frame(spec) else None
        tg = compile_targets(spec, P, F)
    st = [MS1_FROM] + [pd.Timestamp(v) for v in else_returns(tg.els, P.idx)[1].values()]
    if c['exposure'] is not None and F is not None and F.shape[1]:
        fv = [F[k].first_valid_index() for k in gate_cols(spec, F)]
        st += [pd.Timestamp(v) for v in fv if v is not None]
        g = gate_start(P, gate_valid(spec, P, F)[0], delay)     # before it the gate is forced to the else share
        st += [g] if g is not None else []
    g = gate_start(P, signal_row(tg), delay)                     # before it the stock share is CASH (not informed)
    st += [g] if g is not None else []
    st = max(st)
    o = fast_run(P, tg, H_CONS, st, cost, 0.0, delay, want_E=True, dtax=DIV_TAX)
    _sealed(o['idx'])
    E = o['E'][0]
    r = E[1:] / E[:-1] - 1.0
    q = np.where(E[:-1] > 0, o['dnet'][0][1:] / np.where(E[:-1] > 0, E[:-1], 1.0), 0.0)
    one_way = float(o['turn'][0]) / 2.0
    return dict(dates=[d.strftime('%Y-%m-%d') for d in o['idx'][1:]], ret=[float(x) for x in r],
                basis_add=[float(x) for x in q],
                label=f"{spec.get('name', h)} 보수(상폐 분류: 실패형 -{H_FAIL:.0%}·인수형 0) 비용·배당세 "
                      f"{DIV_TAX:.1%} 후, 22% 양도세 전 {o['idx'][0].year}~2014",
                turnover=min(1.0, one_way), start=str(o['idx'][0].date()), min_cover=0.95)


# ---------------------------------------------------------------- report
def _row(o, names):
    """cagr_at = after cost and every tax (dividend tax when paid, 22% yearly, final liquidation); cagr_before_liq_tax =
    the same before only the final liquidation tax (NOT pre-tax); taxpaid / divtax = 22% / dividend tax paid (units of
    the starting value)."""
    return dict(cagr_at=float(o['cagr_at']), cagr_before_liq_tax=float(o['cagr_before_liq_tax']), mdd=float(o['mdd']),
                turn=float(o['turn']), trades=int(o['trades']), names=names, yrs=float(o['yrs']),
                taxpaid=float(o['taxpaid']), divtax=float(o['divtax']))


def evaluate(spec, P=None, null=True, pit=True):
    """Dev summary of a universe spec (every number <= 2014-12-31). See the module docstring for the rows."""
    t0 = time.time()
    dsl.check_spec(spec)
    P = load() if P is None else P
    c = cfg_of(spec)
    cost = max(dsl.MIN_COST, float(spec.get('cost', dsl.MIN_COST)))
    delay = int(spec.get('delay', dsl.MIN_DELAY)); tax = dsl.ACCOUNTS['us']['tax']
    F = gate_frame(spec, P.idx, P) if needs_frame(spec) else None
    tg = compile_targets(spec, P, F)
    _cache['last_tg'] = (dsl.spec_hash(spec), id(P), tg, F)    # ms1_stream reuses it (one spec at a time)
    _, efirst = else_returns(tg.els, P.idx)
    gate_data_from, grow, gnever = None, None, []
    if c['exposure'] is not None and F is not None and F.shape[1]:
        fv = [F[k].first_valid_index() for k in gate_cols(spec, F)]
        gate_data_from = None if not fv or any(v is None for v in fv) else str(max(fv).date())
        grow, gnever = gate_valid(spec, P, F)
    gate_from = None if grow is None else str(P.idx[grow].date())    # first informed gate decision
    gst = gate_start(P, grow, delay)
    srow = signal_row(tg)                                  # first decision with every score / filter signal informed
    sst = gate_start(P, srow, delay)
    sig_info = None
    if c['sig']:
        after = tg.sig_ok[tg.dec >= srow] if srow is not None else tg.sig_ok
        sig_info = dict(names=c['sig'], closure=sig_closure(spec, c['sig']),
                        signal_from=None if srow is None else str(P.idx[srow].date()),
                        gaps=int((~after).sum()) if srow is not None else int(len(tg.dec)),
                        never=tg.sig_never[:3], rule='not informed -> no eligible name (stock share CASH)')
    out = dict(kind='stock', universe='sp500', stock_version=STOCK_VERSION, dev_end=str(DEV_END.date()),
               label='개별주 S&P500 시점편입·상폐포함 (개발 요약, 기준 아님)', cost=cost, delay=delay, tax=tax,
               div_tax=DIV_TAX, tax_rule=f'세후 = 비용·배당세 {DIV_TAX:.1%}(지급일, 나머지는 취득가)·연 22% 순실현이익·마지막 '
                                         f'청산세 뒤; cagr_before_liq_tax = 청산세만 빼기 전(세전 아님); cagr_pretax = '
                                         f'비용 뒤 세금 전부 전(Sharpe와 같은 장부)',
               h_cons=dict(rule='classified', fail_if=f'return over {DL_WIN} rows (>= {DL_MIN}) to the last price < '
                           f'{DL_FAIL:.0%}', fail=0.0 - H_CONS[0], merger=0.0 - H_CONS[1]), h_all=H_ALL, gate_from=gate_from, gate_data_from=gate_data_from, gate_never=gnever[:3],
               signal_from=None if sig_info is None else sig_info['signal_from'], signals=sig_info, windows={})
    for w, st0 in WINDOWS.items():
        st = max([st0] + [pd.Timestamp(v) for v in efirst.values()])
        by = 'else' if st > st0 else None
        late = [(x, b_) for x, b_ in ((gst, 'gate'), (sst, 'signal')) if x is not None and x > st]
        if w == 'w86' and late:                          # headline window: no forced-cash warm-up years inside
            st, by = max(late, key=lambda z: z[0])
        nm = avg_names(P, tg, st, delay)
        cons = run1(P, tg, H_CONS, st, cost, tax, delay, ends=w == 'w86')
        base = run1(P, tg, 0.0, st, cost, tax, delay)
        row = dict(start=str(st.date()), start_by=by, cons=_row(cons, nm), base=_row(base, nm),
                   ew_cons=ew_row(P, H_CONS, st, cost, tax, delay))
        if w == 'w86':
            row['all30'] = _row(run1(P, tg, H_ALL, st, cost, tax, delay), nm)     # stress: every end -30%
            row['held_ends'] = cons['ends']                    # series ends held into, by class
            row['empty'] = empty = not nm > 0                  # never holds a stock (filter / gate / units typo)
            row['ew_base'] = ew_row(P, 0.0, st, cost, tax, delay)
            row['ndx'] = ndx_hold(st, cost, tax, delay)
            if empty:
                row['sharpe'], row['g1_pass'] = None, False
                row['cons']['cagr_pretax'] = None
            else:
                pre = run1(P, tg, H_CONS, st, cost, 0.0, delay, dtax=0.0)    # truly pre-tax: no 22%, no dividend tax
                row['sharpe'] = sharpe(pre, P)
                row['g1_pass'] = bool(row['sharpe'] >= G1_SHARPE)
                row['cons']['cagr_pretax'] = float(pre['cagr_at'])
            ex = fast_run(P, tg, 0.0, st, cost, tax, delay, D=N_HAZ, hits=hazard_hits(P, tg, st))
            row['extreme'] = dict(cagr_at=float(np.median(ex['cagr_at'])), mdd=float(np.median(ex['mdd'])),
                                  draws=[round(float(x), 6) for x in ex['cagr_at']], n=N_HAZ, seed=HAZ_SEED,
                                  hazard=HAZARD)
            if null and not empty:
                nb = null_baskets(P, tg, st, delay)
                nr = fast_run(P, tg, H_CONS, st, cost, tax, delay, baskets=nb, D=N_NULL)
                x = np.sort(nr['cagr_at']); s = row['cons']['cagr_at']
                below = float(np.mean(x < s) + 0.5 * np.mean(x == s))
                row['null'] = dict(kind='matched_retention', n=N_NULL, seed=NULL_SEED, h='classified', pct=below,
                                   top=1.0 - below, median=float(np.median(x)), p95=float(np.percentile(x, 95)),
                                   p99=float(np.percentile(x, 99)), beat95=bool(s > np.percentile(x, 95)),
                                   beat99=bool(s > np.percentile(x, 99)), turn_med=float(np.median(nr['turn'])),
                                   cagrs=[round(float(v), 6) for v in x])
        row['ties'], row['decisions'] = tie_count(P, tg, st, delay)   # shared top-K boundary ties (top_k)
        out['windows'][w] = row
    if pit:
        pc = pit_check(spec, P, tg, F)
        out['causality'] = pc
    j = int(np.searchsorted(tg.dec, P.T - 1, side='right')) - 1
    lp = sorted(zip(-tg.wts[j], P.ids[tg.picks[j]], tg.picks[j]))[:30] if j >= 0 else []   # by weight, then id
    out['last_decision'] = dict(date=str(P.idx[tg.dec[j]].date()) if j >= 0 else None,
                                names=[P.label(x) for _, _, x in lp], held=len(tg.picks[j]) if j >= 0 else 0,
                                tie=bool(tg.tie[j]) if j >= 0 else False,
                                names_are='point-in-time ids (S0001.. = order of the first membership start, ties '
                                          'by a seeded draw), by weight then id, at most 30; source symbols are '
                                          'last-known ones and are not printed',
                                exposure=float(tg.e[-1]))
    out['ties'] = dict(w86=out['windows']['w86']['ties'], of=out['windows']['w86']['decisions'],
                       all=int(tg.tie.sum()), n_dec=int(len(tg.dec)),
                       rule='a tie at the top-K boundary is shared: the tied names split the slots left equally '
                            '(no panel column / symbol order)')
    out['n_decisions'] = int(len(tg.dec))
    out['screen_pass'] = bool(out['windows']['w86'].get('g1_pass')) and (out.get('causality') or {}).get('ok', True)
    out['elapsed_s'] = round(time.time() - t0, 1)
    return out


def _pp(x):
    return f'{x:.1%}' if x is not None and np.isfinite(x) else '-'


def dev_part(s, compact=False):
    """The one-line dev part (Korean, every number <= 2014). 세후 보수 = the CONSERVATIVE row (classified delisting
    rule: fail-type -50%, merger-type 0), in parentheses 기본 = h 0, 일괄-30% = every end -30%, 극단 = the hazard row.
    compact drops names / turnover and the 95% line;
    compact=2 = the same numbers in the shortest wording (the CLI steps down while the whole line, with the MS1 / G1
    parts, would pass 400 bytes). Warm-up marks: (게이트 ..~) = the exposure gate's first informed decision, (신호 ..~) =
    the score / filter signals' (signal_from): on the 1986 window when it starts there, on the 1971 row when later
    than its start (in every form, compact=2 too). 동점분할 n/m회 = n of the m decisions in force in the 1986 window
    had a shared top-K boundary tie (top_k; shown only when n > 0). An empty book whose score / filter signals are
    never informed says so (and names the never-defined calls) instead of 'filter/게이트 확인'."""
    a, b = s['windows']['w86'], s['windows']['w71']
    a30 = (a.get('all30') or {}).get('cagr_at')          # stress row: every series end -30%
    nl = a.get('null')
    yn = lambda x: '통과' if x else '미달'
    sh = lambda x: f'{x:.2f}' if x is not None and np.isfinite(x) else '-'
    gf = s.get('gate_from') or ''
    sf = s.get('signal_from') or ''
    by = a.get('start_by')                             # the headline window starts once the gate / signals are informed
    w86 = ('게이트', gf) if by == 'gate' and gf else ('신호', sf) if by == 'signal' and sf else None
    late71 = [(wd, x) for wd, x in (('게이트', gf), ('신호', sf)) if x and x > b['start']]
    cz = '' if (s.get('causality') or {}).get('ok', True) else (' 인과성위반' if compact == 2 else ' 개발 인과성 위반')
    nt, ndc = a.get('ties') or 0, a.get('decisions') or 0       # shared top-K boundary ties (top_k)
    if a.get('empty'):                                 # no stock is ever held: say it instead of a normal-looking line
        y = f"{a['start'][2:4]}~14" if compact == 2 else f"{a['start'][:4]}~2014"
        sg = s.get('signals') or {}
        if sg and not sg.get('signal_from'):           # the score / filter signals are never informed (<= 2014)
            nv = ', '.join(sg.get('never') or [])
            why = (f"신호 정보 없음{': ' + nv if nv else ''}" if compact == 2 else
                   f"score·filter 신호가 2014년까지 한 번도 정보 없음{': ' + nv + ' 값 없음' if nv else ''}")
        else:
            why = 'filter/게이트 확인'
        return ((f"개별주PIT {y} 종목 0 ({why}) 현금만 세후 {_pp(a['cons']['cagr_at'])} | 무작위·샤프 안 함"
                 if compact == 2 else
                 f"개별주 S&P500(시점편입·상폐포함) {y} 종목 0 ({why}): 현금(T-bill)만 세후 "
                 f"{_pp(a['cons']['cagr_at'])} | 무작위 바구니·Sharpe 계산 안 함 (G1 1.1 미달)") + cz)
    if compact == 2:
        q = lambda x: f'{100 * x:.1f}' if x is not None and np.isfinite(x) else '-'
        if nl:
            top = nl['top'] * 100
            npart = f"무작위 상위{'<0.5' if top < 0.5 else f'{top:.0f}'}%(99%선 {yn(nl['beat99'])})"
        else:
            npart = '무작위 미계산'
        g71 = ''.join(f"({wd}{x[2:4]}~)" for wd, x in late71)     # the 1971 row is cash before it: always marked
        return (f"개별주PIT·상폐포함 {a['start'][2:4]}~14{f'({w86[0]}{w86[1][2:7]}~)' if w86 else ''} "
                f"세후보수 {_pp(a['cons']['cagr_at'])}"
                f"(기본 {q(a['base']['cagr_at'])}·일괄30 {q(a30)}·극단 {q(a['extreme']['cagr_at'])}) "
                f"낙폭{a['cons']['mdd']:.0%}{f' 동점분할{nt}/{ndc}' if nt else ''} | "
                f"EW {q(a['ew_cons']['cagr_at'])}·NDX {q(a['ndx']['cagr_at'])} | {b['start'][2:4]}~14 "
                f"{_pp(b['cons']['cagr_at'])}{g71} | {npart} | 샤프 {sh(a['sharpe'])} G1 1.1 {yn(a['g1_pass'])}" + cz)
    if nl:
        top = nl['top'] * 100
        tp = '<0.5' if top < 0.5 else f'{top:.0f}'
        npart = f"무작위 바구니 상위 {tp}% (" + ('' if compact else f"95%선 {yn(nl['beat95'])}·") + \
            f"99%선 {yn(nl['beat99'])})"
    else:
        npart = '무작위 바구니 미계산'
    y86, y71 = a['start'][:4], b['start'][:4]
    g71 = ''.join(f"({wd} {x[:4]}~)" for wd, x in late71)
    return (f"개별주 S&P500(시점편입·상폐포함) {y86}~2014{f'({w86[0]} {w86[1][:7]}~)' if w86 else ''} "
            f"세후 보수 {_pp(a['cons']['cagr_at'])} "
            f"(기본 {_pp(a['base']['cagr_at'])}·일괄-30% {_pp(a30)}·극단 {_pp(a['extreme']['cagr_at'])}) "
            f"낙폭 {a['cons']['mdd']:.0%} " + (f"동점분할 {nt}/{ndc}회 " if nt else '')
            + ('' if compact else f"평균 {a['cons']['names']:.0f}종목 회전 {a['cons']['turn']:.1f}x ")
            + f"| 동일가중 {_pp(a['ew_cons']['cagr_at'])} · "
            f"NDX보유 {_pp(a['ndx']['cagr_at'])} | {y71}~2014 {_pp(b['cons']['cagr_at'])}{g71} | {npart} | "
            f"Sharpe {sh(a['sharpe'])} (G1 1.1 {'통과' if a['g1_pass'] else '미달'})" + cz)
