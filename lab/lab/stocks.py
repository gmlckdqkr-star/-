"""US single-stock universe (spec `universe: sp500`): cross-sectional stock strategies on point-in-time S&P 500
members, delisted names included, after costs and Korean overseas-stock tax, with delisting stress rows and a random
basket null.

Panel: research/data/us_stocks/sp500_le2014.npz.xz (env LAB_STOCKS), sealed <= 2014-12-31. Source
github.com/Johnbrick123/sp500-data (no licence published: personal research only, never republish the data).
1503 names = every name that was an S&P 500 member at some point 1968..2014, with point-in-time membership
(start inclusive, end exclusive), split + dividend adjusted closes, dollar volume (mostly missing before 1996) and
no-trade days (`stale`, the source carried the prior close).

Spec (YAML):
    name: stk_mom12_1_top20
    family: stk_mom
    universe: sp500
    stock:
      rebalance: month          # month | quarter | week: decide at the close of the period's first trading day
      score: "ret(252, 21)"     # per-stock expression (higher = better)
      filter: "age() > 252"     # optional boolean per-stock expression
      top: 20                   # or top_pct: 0.1
      weight: equal             # equal | invvol(63) | score
      max_weight: 0.10          # optional cap per name, the excess stays in CASH
      exposure: up              # optional: a signal name or an ETF-DSL expression (bool -> 0/1, number clipped 0..1)
      else: {CASH: 1.0}         # what the unexposed share holds (CASH or US ETF sleeves); default CASH
      exposure_every: daily     # daily (default) | rebalance (sample the exposure on decision rows only)
    signals: {up: "price(_NDX) > sma(_NDX, 200)"}   # optional, the ETF DSL on the ETF panel (cut at 2014-12-31)

Per-stock functions (evaluated on decision rows only, every window ends at the decision close):
  ret(n[, skip])  total return over n days ending `skip` days ago     vol(n)        daily return stdev (n returns)
  sma_ratio(n)    price / n-day mean price                            high_dist(n)  price / n-day max - 1
  dvol(n)         mean dollar volume (>= half the window present)     age()         trading days since the first price
  beta(n)         n-day beta vs the equal-weight member return       rank(x)       cross-sectional percentile 0..1
  csz(x)          cross-sectional z-score                              abs min max log, + - * /, comparisons, and or not
rank / csz rank among the names that are members with a real price on that row. Prices are the adjusted closes carried
forward through days without a price (return 0), from each name's first price on; a window needs a price at its start.

Eligibility at decision close t: member at t, a real (finite, not stale) price at t, filter true, score finite (and
vol(n) finite > 0 for weight invvol(n)). A held name that leaves the index is sold at the next rebalance (target 0).

Returns: adjusted close to close, carried through a pause (an exit gap books its whole change on the next trade day).
After a series' last price (before 2014-12-31) the next day returns -h (delisting haircut), then 0. Execution: lab's
ETF engine (engine.run: delay 2, 0.30% per side, 22% yearly net realized gain tax, final liquidation taxed, cash earns
the T-bill) with one addition for single stocks: on a day without a real price a name cannot be traded (frozen: a pause
or no-trade day, the trade is retried when it trades again) and a name with no price cannot be bought.

Rows: base h=0, CONSERVATIVE h=0.30 (the headline), EXTREME = base + a 6%/year -100% hazard on each held name
(20 seeded draws, median; reference only). Benchmarks on the same engine / costs / tax: equal-weight members (monthly)
and NDX 1x hold (QQQ sleeve of the ETF panel). Annualised after-cost pre-tax Sharpe over the T-bill (G1 non-timing
test, pass >= 1.1). Random-basket null: 200 seeded baskets with the same rebalance dates, eligibility, name count and
name retention (see null_baskets), equal weight, same exposure, engine, costs and tax.
MS1 / G1 (lab/ms1.py, `--std auto`): ms1_stream = the CONSERVATIVE book's daily return after trading cost, before
tax, on the real stock calendar from 1970 (first point-in-time member day; later when an else sleeve or the gate data
starts later), measured on the MS1 bases by ms1.measure_series (re-sampled stream, no path recomputation). G1 = the
Sharpe line above; a spec with an exposure gate also gets gate.test on it (gate_spec: the gate as a QQQ / cash spec on
the G1 real frames).
HOLDOUT SEAL: the panel and every ETF series are cut at 2014-12-31 before anything is computed; asserted below.
"""
import ast, io, json, lzma, math, os, re, time
import numpy as np, pandas as pd
from . import data, dsl, engine, gates

STOCKS = os.environ.get('LAB_STOCKS', '/mnt/project-files/research/data/us_stocks/sp500_le2014.npz.xz')
DEV_END = gates.DEV_END
STOCK_VERSION = 1           # bump when the stock summary changes for an unchanged spec hash (cli recomputes)
BAR_VERDICT = '판정 불가 (개별주)'
WINDOWS = {'w86': pd.Timestamp('1986-01-02'), 'w71': pd.Timestamp('1971-01-04')}   # both end DEV_END
H_CONS = 0.30               # conservative delisting haircut (headline)
HAZARD, N_HAZ, HAZ_SEED = 0.06, 20, 2014
N_NULL, NULL_SEED = 200, 1986
G1_SHARPE = 1.1
N_PIT_CUTS = 3              # runtime causality cuts per spec (the test suite checks PIT in depth)
MS1_FROM = pd.Timestamp('1970-01-02')   # first day with point-in-time members: start of the MS1 return stream
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
    close-to-close return (0 before the first price and through gaps), real = finite price, not stale and not inside
    a recorded exit gap (`pause`, from META.json: the days between last_trade and next_trade, where the source may
    carry the old price without a no-trade flag), frozen = no real price inside the series, no_buy = no real price."""

    def __init__(self, dates, tickers, adj, dvol, member, stale, pause=None):
        dates = pd.DatetimeIndex(dates)
        keep = np.asarray(dates <= DEV_END)
        pause = np.zeros(np.shape(adj), bool) if pause is None else np.asarray(pause, bool)
        if not keep.all():                       # seal: drop later rows before any number is derived
            dates, adj, dvol, member, stale, pause = (dates[keep], adj[keep], dvol[keep], member[keep], stale[keep],
                                                      pause[keep])
        self.idx = _sealed(dates)
        self.tickers = np.asarray(tickers).astype(str)
        self.adj = np.asarray(adj, np.float32)
        self.dvol = np.asarray(dvol, np.float32)
        self.member = np.asarray(member, bool)
        self.stale = np.asarray(stale, bool)
        self.pause = pause
        T, N = self.adj.shape
        assert self.member.shape == self.stale.shape == self.dvol.shape == (T, N) == (len(dates), len(self.tickers))
        fin = np.isfinite(self.adj) & (self.adj > 0)
        self.has = fin
        self.real = fin & ~self.stale & ~self.pause
        anyp = fin.any(0)
        self.first = np.where(anyp, fin.argmax(0), T)
        self.last = np.where(anyp, T - 1 - fin[::-1].argmax(0), -1)
        self.T, self.N = T, N
        self._m = {}

    def cut(self, c):
        """The panel as it was known at the close of row c - 1 (rows [0, c))."""
        return Panel(self.idx[:c], self.tickers, self.adj[:c], self.dvol[:c], self.member[:c], self.stale[:c],
                     self.pause[:c])

    def subset(self, cols):
        cols = np.asarray(cols)
        return Panel(self.idx, self.tickers[cols], self.adj[:, cols], self.dvol[:, cols], self.member[:, cols],
                     self.stale[:, cols], self.pause[:, cols])

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

    def R(self, h):
        """Engine returns: rr inside each series, -h on the day after a last price that is before the panel end
        (delisting haircut), 0 after. Exactly one -h per ended series."""
        def f():
            R = self.rr.copy()
            j = np.flatnonzero((self.last >= 0) & (self.last < self.T - 1))
            R[self.last[j] + 1, j] = -float(h)
            return R
        return self._get(('R', float(h)), f)

    def mkt(self):
        """Equal-weight return of the names that were members the day before and trade that day (for beta)."""
        def f():
            M = np.zeros((self.T, self.N), bool)
            M[1:] = self.member[:-1] & self.real[1:] & (np.arange(1, self.T)[:, None] > self.first)
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
            elif k == 'dv':
                X = np.nan_to_num(self.dvol.astype(np.float64), nan=0.0)
            elif k == 'dvn':
                X = np.isfinite(self.dvol).astype(np.float64)
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
        """Ticker for output. A delisting suffix after 2014 (e.g. AET-201811) is a post-2014 fact: masked as AET*."""
        t = str(self.tickers[j])
        m = re.match(r'^(.*)-(\d{6})$', t)
        return m.group(1) + '*' if m and m.group(2) > '201412' else t


def load(path=None):
    """The sealed stock panel (cached per process). Nothing is dropped except rows after DEV_END. The exit gaps listed
    in META.json next to the panel (if present) become `pause` rows (no trade possible inside)."""
    path = path or STOCKS
    if ('panel', path) not in _cache:
        z = np.load(io.BytesIO(lzma.open(path).read()))
        T = int(z['shape'][0])
        dates = pd.to_datetime(z['dates'], unit='D')
        unpack = lambda a: np.unpackbits(a, axis=0)[:T].astype(bool)
        tick = np.asarray(z['tickers']).astype(str)
        pause = np.zeros((T, len(tick)), bool)
        mp = os.path.join(os.path.dirname(path), 'META.json')
        if os.path.isfile(mp):
            col = {t: i for i, t in enumerate(tick)}
            for g in json.load(open(mp)).get('exit_gaps', []):
                a, b = dates.searchsorted(pd.Timestamp(g['last_trade'])), dates.searchsorted(pd.Timestamp(g['next_trade']))
                if g['ticker'] in col:
                    pause[a + 1:b, col[g['ticker']]] = True
        _cache[('panel', path)] = Panel(dates, tick, z['adj'], z['dvol'], unpack(z['member']), unpack(z['stale']),
                                        pause)
    return _cache[('panel', path)]


# ---------------------------------------------------------------- per-stock expressions
SFUNCS = {'ret': (1, 2), 'vol': (1, 1), 'sma_ratio': (1, 1), 'high_dist': (1, 1), 'dvol': (1, 1), 'age': (0, 0),
          'beta': (1, 1), 'rank': (1, 1), 'csz': (1, 1), 'abs': (1, 1), 'min': (2, 2), 'max': (2, 2), 'log': (1, 1)}
_WINF = {'ret', 'vol', 'sma_ratio', 'high_dist', 'dvol', 'beta'}
_SOK = (ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare, ast.Call, ast.Name, ast.Load, ast.Constant,
        ast.And, ast.Or, ast.Not, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd, ast.Gt, ast.GtE, ast.Lt,
        ast.LtE, ast.Eq, ast.NotEq)


def _int_arg(node, f, lo):
    if not (isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)
            and math.isfinite(node.value) and float(node.value) == int(node.value) and int(node.value) >= lo):
        raise ValueError(f'{f}(): window / skip must be a whole number >= {lo} written as a number, not '
                         f'{ast.unparse(node)!r} (n < {lo} would read rows after the decision close)')
    return int(node.value)


def parse_stock(expr, what='score'):
    """Parse and check a per-stock expression (whitelisted AST; unknown names / functions raise)."""
    if isinstance(expr, bool) or not isinstance(expr, (str, int, float)):
        raise ValueError(f'stock {what} must be an expression string, not {expr!r}')
    try:
        tree = ast.parse(str(expr), mode='eval')
    except SyntaxError as e:
        raise ValueError(f'stock {what}: syntax error in {expr!r}: {e.msg}')
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
                _int_arg(n.args[0], n.func.id, 2 if n.func.id in ('vol', 'beta') else 1)
                if len(n.args) > 1:
                    _int_arg(n.args[1], n.func.id, 0)
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and not any(isinstance(c, ast.Call) and c.func is n for c in ast.walk(tree)):
            raise ValueError(f'stock {what}: unknown name {n.id!r} in {expr!r} (per-stock expressions use only '
                             f'numbers and the functions {", ".join(SFUNCS)})')
    return tree


class _Ctx:
    """Evaluation of per-stock expressions on decision rows D ([nd] row numbers) -> [nd, N] arrays."""

    def __init__(self, P, D):
        self.P, self.D = P, np.asarray(D, np.int64)
        self.E0 = P.member[self.D] & P.real[self.D]          # members with a real price at the decision close
        self.memo = {}

    def _valid(self, start):
        """A window starting at row `start` (per decision) needs a price there: start >= first price, start >= 0."""
        s = np.asarray(start)[:, None]
        return (s >= 0) & (s >= self.P.first[None, :])

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
            if f == 'dvol':
                n = a[0]
                s, c = self._win_sum('dv', n), self._win_sum('dvn', n)
                return np.where(c >= math.ceil(n / 2), s / np.maximum(c, 1), np.nan)
            if f == 'age':
                ag = (D[:, None] - P.first[None, :]).astype(float)
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
        v = self.ev(parse_stock(expr))
        return np.broadcast_to(_f(v), (len(self.D), self.P.N)).astype(float)

    def mask(self, expr):
        v = self.ev(parse_stock(expr, 'filter'))
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
    parse_stock(st['score'], 'score')
    if st.get('filter') is not None:
        parse_stock(st['filter'], 'filter')
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
                els={k: float(v) for k, v in els.items() if k != 'CASH' and float(v) > 0})


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
    c = cfg_of(spec)
    for e in list(sig.values()) + ([c['exposure']] if isinstance(c['exposure'], str) else []):
        names = _gate_names(e, set(sig))
        if 'level' in names['funcs']:
            raise ValueError('universe spec: level(x) is not available (no ETF book is traded by the gate)')
        unk = sorted(names['series'] - _known_series())
        if unk:
            raise ValueError(f'gate expression {e!r}: unknown name(s) {unk} (signal names, ETF sleeves or panel keys)')
    return spec


def _known_series():
    if 'keys' not in _cache:
        _cache['keys'] = set(data.keys()) | set(data.SLEEVES)
    return _cache['keys']


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
def gate_frame(spec, idx):
    """Panel series the gate reads (sleeve names -> their underlying), each cut at DEV_END, on the stock calendar."""
    c = cfg_of(spec)
    sig = spec.get('signals') or {}
    exprs = list(sig.values()) + ([c['exposure']] if isinstance(c['exposure'], str) else [])
    keys = set()
    for e in exprs:
        for nm in _gate_names(e, set(sig))['series']:
            keys.add(data.SLEEVES[nm][1] if nm in data.SLEEVES else nm)
    F = pd.DataFrame(index=idx)
    for k in sorted(keys):
        s = data.series(k)
        s = s[s.index <= DEV_END]                       # seal: nothing after 2014-12-31 enters
        F[k] = s.reindex(idx).ffill() if len(s) else np.nan
    _sealed(F.index)
    return F


def exposure(spec, P, F=None):
    """[T] exposure in [0, 1] decided at each close (1.0 when the spec has no exposure gate)."""
    c = cfg_of(spec)
    if c['exposure'] is None:
        return np.ones(P.T)
    F = gate_frame(spec, P.idx) if F is None else F
    env = dict(dsl._mk(F))
    assets = set(F.columns) | set(data.SLEEVES)
    for name, expr in (spec.get('signals') or {}).items():
        env[name] = dsl._eval(expr, env, assets)
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
    retain[j] (names kept from decision j-1), elig ([nd, N] eligible), e ([T] exposure), els ({sleeve: w})."""

    def __init__(self, dec, picks, wts, K, elig, e, els, cap):
        self.dec, self.picks, self.wts, self.K, self.elig, self.e, self.els, self.cap = dec, picks, wts, K, elig, e, els, cap
        self.retain = np.array([0] + [len(np.intersect1d(picks[j], picks[j - 1])) for j in range(1, len(picks))],
                               np.int64)


def compile_targets(spec, P, F=None):
    """Per-decision picks and weights (point in time: decision row t reads panel rows <= t only)."""
    c = cfg_of(spec)
    D = np.flatnonzero(dsl.reb_rows(P.idx, c['rebalance']))
    cx = _Ctx(P, D)
    S = cx.value(c['score'])
    E = cx.E0 & np.isfinite(S)
    if c['filter'] is not None:
        E = E & cx.mask(c['filter'])
    V = None
    if c['weight'] == 'invvol':
        V = cx.call('vol', [c['wn']])
        E = E & np.isfinite(V) & (V > 0)
    picks, wts, Ks = [], [], []
    Sx = np.where(E, S, -np.inf)
    order = np.argsort(-Sx, axis=1, kind='stable')
    m = E.sum(1)
    for j in range(len(D)):
        K = c['top'] if c['top'] is not None else (max(1, math.ceil(c['top_pct'] * m[j])) if m[j] else 1)
        n = min(K, int(m[j]))
        p = np.sort(order[j, :n])
        if c['weight'] == 'equal' or n == 0:
            w = np.full(n, 1.0 / K)
        else:
            raw = 1.0 / V[j, p] if c['weight'] == 'invvol' else np.maximum(S[j, p], 0.0)
            if not raw.sum() > 0:
                raw = np.ones(n)
            w = raw / raw.sum() * n / K
        if c['cap'] is not None:
            w = np.minimum(w, c['cap'])
        picks.append(p.astype(np.int64)); wts.append(w); Ks.append(K)
    return Targets(D, picks, wts, np.array(Ks), E, exposure(spec, P, F), c['els'], c['cap'])


def ew_targets(P, cad='monthly'):
    """Equal-weight members benchmark: every member with a real price at the decision close, 1/m each."""
    D = np.flatnonzero(dsl.reb_rows(P.idx, cad))
    E = P.member[D] & P.real[D]
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
    """DataFrames for engine.run: W (held-ever names + else sleeves + CASH), R, rebal flags, frozen, no_buy."""
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
    return W, R, reb, FZ, NB, names


def run_engine(P, tg, h, start, cost, tax, delay, R_edit=None):
    """engine.run on the spec's targets (the reference engine). R_edit(R) may change the returns (tests: hazard)."""
    W, R, reb, FZ, NB, names = frames(P, tg, h)
    if R_edit is not None:
        R = R_edit(R, names)
    o = engine.run(W, R, start, DEV_END, cost=cost, tax=tax, delay=delay, rebal=reb, frozen=FZ, no_buy=NB)
    _sealed(o['E'].index)
    return o


# ---------------------------------------------------------------- fast path (D books at once)
def _rows(P, start):
    i0 = int(np.searchsorted(P.idx, start)); i1 = int(np.searchsorted(P.idx, DEV_END, side='right')) - 1
    return i0, i1


def fast_run(P, tg, h, start, cost, tax, delay, baskets=None, D=1, hits=None, want_E=False, keep_book=False):
    """engine.run (with frozen / no_buy) vectorised over D books that share the decision rows, exposure and else
    sleeves: the same rules line by line (yearly tax, a trade on a target change / decision row / blocked-trade retry,
    the initial book free of cost). Parity with engine.run is tested (tests/test_stocks.py).
    baskets: None = the spec's own picks in every book, else a list over decisions of (cols [D, n] panel name columns,
    -1 = none; w [D, n]); hits: {panel row: (book idx, name col)} wipes those positions (-100%) after the row's return.
    Returns per-book arrays cagr_at, cagr_pre, final_at, mdd, turn, trades, taxpaid (+ E [D, rows] with want_E;
    + book [rows, k] = book 0's position values after each row's trade, columns names + else + CASH, with keep_book)."""
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
    eq = np.empty((D, nr)) if want_E else None
    book = np.empty((nr, k)) if keep_book else None
    peak = np.full(D, -np.inf); mdd = np.zeros(D)
    years = idx.year.values[i0:i1 + 1]; yr = years[0]
    for i in range(nr):
        if years[i] != yr:
            t = tax * np.maximum(0.0, realized); taxpaid += t
            realized = np.zeros(D); yr = years[i]
            if (t > 0).any():
                s = val.sum(1); f = np.where(t > 0, t / s, 0.0)
                realized = np.where(t > 0, f * (val[:, :cashi] - basis[:, :cashi]).sum(1), 0.0)
                val = val * (1 - f)[:, None]; basis = basis * (1 - f)[:, None]
        if i > 0:
            val *= G[i]
        if i in hit:
            val[hit[i]] = 0.0
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
    out = dict(cagr_at=cg(final), cagr_pre=cg(E), final_at=final, mdd=mdd, turn=turnover / yrs, trades=trades,
               taxpaid=taxpaid, yrs=yrs, names=names)
    if want_E or keep_book:
        out['idx'] = idx[i0:i1 + 1]
    if want_E:
        out['E'] = eq
    if keep_book:
        out['book'] = book; out['cols'] = list(names) + els + ['CASH']
    return out


def run1(P, tg, h, start, cost, tax, delay):
    """One book on the fast path (same numbers as run_engine, parity-tested) -> engine.run-like dict."""
    o = fast_run(P, tg, h, start, cost, tax, delay, want_E=True)
    _sealed(o['idx'])
    return dict(E=pd.Series(o['E'][0], index=o['idx']), cagr_at=float(o['cagr_at'][0]), cagr_pre=float(o['cagr_pre'][0]),
                final_at=float(o['final_at'][0]), mdd=float(o['mdd'][0]), turn=float(o['turn'][0]),
                trades=int(o['trades'][0]), taxpaid=float(o['taxpaid'][0]), yrs=o['yrs'])


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
    the strategy's unit 1/K and cap. The chain starts fresh at the decision in force on the window's first row."""
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
        w = np.full((D, n), 1.0 / tg.K[j])
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


def sharpe(o, P):
    """Annualised mean / stdev of daily (pre-tax, after-cost) returns over the T-bill."""
    E = o['E']
    r = E.pct_change().dropna()
    rf = pd.Series(rf_on(P.idx), index=P.idx).reindex(r.index).values
    ex = r.values - rf
    return float(ex.mean() / ex.std(ddof=1) * np.sqrt(252)) if ex.std(ddof=1) > 0 else float('nan')


# ---------------------------------------------------------------- causality (runtime cuts)
def pit_check(spec, P, tg, F=None, n_cuts=N_PIT_CUTS, seed=None):
    """Decisions built on the panel (and gate frame) cut at a row must equal the full-panel decisions before it."""
    if seed is None:
        seed = int.from_bytes(os.urandom(8), 'little')
    rng = np.random.default_rng(seed)
    lo = min(P.T - 1, 300)
    cuts = sorted({int(x) for x in rng.integers(lo, P.T, size=n_cuts)})
    bad = []
    for c in cuts:
        t2 = compile_targets(spec, P.cut(c), None if F is None else F.iloc[:c])
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
    sampled on decision rows only. None when the spec has no exposure gate. Same family (G1 deflation uses its N)."""
    c = cfg_of(spec)
    if c['exposure'] is None:
        return None
    g = dict(name=f"{spec.get('name', 'stock')}:gate", family=str(spec.get('family', 'unset')),
             rules=[{'else': {'QQQ': c['exposure']}}])
    if spec.get('signals'):
        g['signals'] = dict(spec['signals'])
    if c['exposure_every'] == 'rebalance':
        g['rebalance'] = c['rebalance']
    return g


def ms1_stream(spec, P=None):
    """MS1 input of a stock spec (ms1.measure_series): the CONSERVATIVE book's (h = 0.30) daily return after trading
    cost and BEFORE tax (MS1 applies its own tax), on the real stock calendar, from MS1_FROM (1970-01-02, the first
    point-in-time member day) or the later start of an else sleeve or of the gate data (before it the gate is all
    cash), to 2014-12-31. turnover = min(1, one-way yearly turnover) = measure_series' realized share.
    -> dict(dates, ret, label, turnover, start, min_cover)."""
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
        F = gate_frame(spec, P.idx) if c['exposure'] is not None else None
        tg = compile_targets(spec, P, F)
    st = [MS1_FROM] + [pd.Timestamp(v) for v in else_returns(tg.els, P.idx)[1].values()]
    if F is not None and F.shape[1]:
        fv = [F[k].first_valid_index() for k in F.columns]
        st += [pd.Timestamp(v) for v in fv if v is not None]
    st = max(st)
    o = fast_run(P, tg, H_CONS, st, cost, 0.0, delay, want_E=True)
    _sealed(o['idx'])
    E = o['E'][0]
    r = E[1:] / E[:-1] - 1.0
    one_way = float(o['turn'][0]) / 2.0
    return dict(dates=[d.strftime('%Y-%m-%d') for d in o['idx'][1:]], ret=[float(x) for x in r],
                label=f"{spec.get('name', h)} 보수 h={H_CONS:.2f} 비용후 세전 {o['idx'][0].year}~2014",
                turnover=min(1.0, one_way), start=str(o['idx'][0].date()), min_cover=0.95)


# ---------------------------------------------------------------- report
def _row(o, names):
    return dict(cagr_at=float(o['cagr_at']), cagr_pre=float(o['cagr_pre']), mdd=float(o['mdd']), turn=float(o['turn']),
                trades=int(o['trades']), names=names, yrs=float(o['yrs']))


def evaluate(spec, P=None, null=True, pit=True):
    """Dev summary of a universe spec (every number <= 2014-12-31). See the module docstring for the rows."""
    t0 = time.time()
    dsl.check_spec(spec)
    P = load() if P is None else P
    c = cfg_of(spec)
    cost = max(dsl.MIN_COST, float(spec.get('cost', dsl.MIN_COST)))
    delay = int(spec.get('delay', dsl.MIN_DELAY)); tax = dsl.ACCOUNTS['us']['tax']
    F = gate_frame(spec, P.idx) if c['exposure'] is not None else None
    tg = compile_targets(spec, P, F)
    _cache['last_tg'] = (dsl.spec_hash(spec), id(P), tg, F)    # ms1_stream reuses it (one spec at a time)
    _, efirst = else_returns(tg.els, P.idx)
    gate_from = None
    if F is not None and F.shape[1]:
        fv = [F[k].first_valid_index() for k in F.columns]
        gate_from = None if any(v is None for v in fv) else str(max(fv).date())
    out = dict(kind='stock', universe='sp500', stock_version=STOCK_VERSION, dev_end=str(DEV_END.date()),
               label='개별주 S&P500 시점편입·상폐포함 (개발 요약, 기준 아님)', cost=cost, delay=delay, tax=tax,
               h_cons=H_CONS, gate_from=gate_from, windows={})
    for w, st0 in WINDOWS.items():
        st = max([st0] + [pd.Timestamp(v) for v in efirst.values()])
        nm = avg_names(P, tg, st, delay)
        cons = run1(P, tg, H_CONS, st, cost, tax, delay)
        base = run1(P, tg, 0.0, st, cost, tax, delay)
        row = dict(start=str(st.date()), cons=_row(cons, nm), base=_row(base, nm),
                   ew_cons=ew_row(P, H_CONS, st, cost, tax, delay))
        if w == 'w86':
            row['ew_base'] = ew_row(P, 0.0, st, cost, tax, delay)
            row['ndx'] = ndx_hold(st, cost, tax, delay)
            pre = run1(P, tg, H_CONS, st, cost, 0.0, delay)
            row['sharpe'] = sharpe(pre, P)
            row['g1_pass'] = bool(row['sharpe'] >= G1_SHARPE)
            ex = fast_run(P, tg, 0.0, st, cost, tax, delay, D=N_HAZ, hits=hazard_hits(P, tg, st))
            row['extreme'] = dict(cagr_at=float(np.median(ex['cagr_at'])), mdd=float(np.median(ex['mdd'])),
                                  draws=[round(float(x), 6) for x in ex['cagr_at']], n=N_HAZ, seed=HAZ_SEED,
                                  hazard=HAZARD)
            if null:
                nb = null_baskets(P, tg, st, delay)
                nr = fast_run(P, tg, H_CONS, st, cost, tax, delay, baskets=nb, D=N_NULL)
                x = np.sort(nr['cagr_at']); s = row['cons']['cagr_at']
                below = float(np.mean(x < s) + 0.5 * np.mean(x == s))
                row['null'] = dict(kind='matched_retention', n=N_NULL, seed=NULL_SEED, h=H_CONS, pct=below,
                                   top=1.0 - below, median=float(np.median(x)), p95=float(np.percentile(x, 95)),
                                   p99=float(np.percentile(x, 99)), beat95=bool(s > np.percentile(x, 95)),
                                   beat99=bool(s > np.percentile(x, 99)), turn_med=float(np.median(nr['turn'])),
                                   cagrs=[round(float(v), 6) for v in x])
        out['windows'][w] = row
    if pit:
        pc = pit_check(spec, P, tg, F)
        out['causality'] = pc
    j = int(np.searchsorted(tg.dec, P.T - 1, side='right')) - 1
    out['last_decision'] = dict(date=str(P.idx[tg.dec[j]].date()) if j >= 0 else None,
                                names=[P.label(x) for x in tg.picks[j][:30]] if j >= 0 else [],
                                exposure=float(tg.e[-1]))
    out['n_decisions'] = int(len(tg.dec))
    out['screen_pass'] = bool(out['windows']['w86'].get('g1_pass')) and (out.get('causality') or {}).get('ok', True)
    out['elapsed_s'] = round(time.time() - t0, 1)
    return out


def _pp(x):
    return f'{x:.1%}' if x is not None and np.isfinite(x) else '-'


def dev_part(s, compact=False):
    """The one-line dev part (Korean, every number <= 2014). compact drops names / turnover and the 95% line;
    compact=2 = the same numbers in the shortest wording (the CLI steps down while the whole line, with the MS1 / G1
    parts, would pass 400 bytes)."""
    a, b = s['windows']['w86'], s['windows']['w71']
    nl = a.get('null')
    yn = lambda x: '통과' if x else '미달'
    if compact == 2:
        q = lambda x: f'{100 * x:.1f}' if x is not None and np.isfinite(x) else '-'
        if nl:
            top = nl['top'] * 100
            npart = f"무작위 상위{'<0.5' if top < 0.5 else f'{top:.0f}'}%(99%선 {yn(nl['beat99'])})"
        else:
            npart = '무작위 미계산'
        g71 = f"(게이트{s['gate_from'][2:4]}~)" if s.get('gate_from') and s['gate_from'] > b['start'] else ''
        cz = '' if (s.get('causality') or {}).get('ok', True) else ' 인과성위반'
        return (f"개별주PIT·상폐포함 {a['start'][2:4]}~14 세후보수 {_pp(a['cons']['cagr_at'])}"
                f"(기본 {q(a['base']['cagr_at'])}·극단 {q(a['extreme']['cagr_at'])}) 낙폭{a['cons']['mdd']:.0%} | "
                f"EW {q(a['ew_cons']['cagr_at'])}·NDX {q(a['ndx']['cagr_at'])} | {b['start'][2:4]}~14 "
                f"{_pp(b['cons']['cagr_at'])}{g71} | {npart} | 샤프 {a['sharpe']:.2f} G1 1.1 {yn(a['g1_pass'])}" + cz)
    if nl:
        top = nl['top'] * 100
        tp = '<0.5' if top < 0.5 else f'{top:.0f}'
        npart = f"무작위 바구니 상위 {tp}% (" + ('' if compact else f"95%선 {yn(nl['beat95'])}·") + \
            f"99%선 {yn(nl['beat99'])})"
    else:
        npart = '무작위 바구니 미계산'
    y86, y71 = a['start'][:4], b['start'][:4]
    g71 = ''
    if s.get('gate_from') and s['gate_from'] > b['start']:
        g71 = f"(게이트 {s['gate_from'][:4]}~)"
    cz = '' if (s.get('causality') or {}).get('ok', True) else ' 개발 인과성 위반'
    return (f"개별주 S&P500(시점편입·상폐포함) {y86}~2014 세후 보수 {_pp(a['cons']['cagr_at'])} "
            f"(기본 {_pp(a['base']['cagr_at'])}·극단 {_pp(a['extreme']['cagr_at'])}) 낙폭 {a['cons']['mdd']:.0%} "
            + ('' if compact else f"평균 {a['cons']['names']:.0f}종목 회전 {a['cons']['turn']:.1f}x ")
            + f"| 동일가중 {_pp(a['ew_cons']['cagr_at'])} · "
            f"NDX보유 {_pp(a['ndx']['cagr_at'])} | {y71}~2014 {_pp(b['cons']['cagr_at'])}{g71} | {npart} | "
            f"Sharpe {a['sharpe']:.2f} (G1 1.1 {'통과' if a['g1_pass'] else '미달'})" + cz)
