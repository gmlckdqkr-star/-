"""Strategy spec -> daily target weights.

A spec is a short YAML (or JSON) file. Example:

    name: trend_tqqq_200
    family: price_trend        # family tag: multiple-testing count N is kept per family
    known: 3                   # how known the idea is, 0 (new) .. 3 (textbook)
    idea: NDX above 200-day average -> TQQQ, else cash
    rebalance: daily           # daily | weekly | monthly | quarterly | N (every N rows)
    signals:                   # evaluated in order; later lines may use earlier names
      up: price(TQQQ) > sma(TQQQ, 200)
    rules:                     # first rule whose `when` is true wins
      - when: up
        hold: {TQQQ: 1.0}
      - else: {CASH: 1.0}

Weights may be expressions, e.g. {TQQQ: "min(1, 0.3 / vol(TQQQ, 20))"}; the rest goes to CASH.
State signal: latch(on, off) is True from a day `on` holds, False from a day `off` holds, else keeps the previous
state; it starts False and `off` wins on a tie.
Expressions are checked with an AST whitelist (no attributes, no subscripts, no imports; list literals of names are
allowed for invvol / rp). Every indicator only uses data up to the decision close; the engine adds the execution delay.

v2 additions (see README for the cheat-sheet):
  rule `rotate:`   rank a sleeve list by a score expression ('*' = the asset), filter, top-k, equal / score / invvol /
                   rp weights, own cadence, optional daily exit.
  functions        corr(x, y, n), zscore(s, n), ewvol(x, halflife), since(cond), hold_min(cond, n),
                   invvol(x, [a, b, ..], n), rp(x, [a, b, ..], n).
  `brake:`         scale the weights by a drawdown rule on the strategy's own paper equity (applied after the rules).
  `grid:`          {X: [..]} with {X} placeholders: expand_grid() gives one spec per point (each its own hash / trial).
  `plugin:`        path.py:func, func(F, sleeves, params) -> weights, for shapes the DSL cannot express. Runs out of
                   process (lab/sandbox.py: fresh forked child per session, no files, no panel, no lab state).
  level(x)         traded level of a held sleeve (dev: cumprod(1 + R[x]); bar: the path's sleeve price).
Post-processing order: rules (or plugin) -> sum <= 1 -> `rebalance` sampling -> brake -> band.
"""
import ast, copy, hashlib, io, itertools, json, math, os, re, tokenize
import numpy as np, pandas as pd
from . import data, sandbox

try:
    import yaml
except ImportError:  # JSON specs still work
    yaml = None


def load_spec(path):
    txt = open(path, encoding='utf-8').read()
    spec = json.loads(txt) if (path.endswith('.json') or yaml is None) else yaml.safe_load(txt)
    if isinstance(spec, dict) and isinstance(spec.get('plugin'), str):
        f, _, fn = spec['plugin'].rpartition(':')
        if f and not os.path.isabs(f):          # plugin path is relative to the spec file
            spec['plugin'] = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(path)), f)) + ':' + fn
    return spec


def _plugin_ref(ref):
    f, _, fn = str(ref).rpartition(':')
    if not f or not fn.isidentifier():
        raise ValueError(f"plugin must be 'path/to/file.py:func', not {ref!r}")
    return f, fn


def _file_sha(f):
    with open(f, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def spec_hash(spec):
    core = {k: spec.get(k) for k in ('signals', 'rules', 'rebalance', 'cost', 'delay')}
    if spec.get('band'):  # band changes the weights; added only when set so older hashes stay the same
        core['band'] = spec.get('band')
    if spec.get('rebalance') not in (None, 'daily'):
        core['reb_rule'] = 'period_first'      # v2: period-start sampling (v1 period-end sampling was not causal)
    for k in ('brake', 'params', 'inputs', 'sleeves'):
        if spec.get(k) is not None:
            core[k] = spec.get(k)
    if spec.get('account', 'us') != 'us':     # added only when not the default so older hashes stay the same
        core['account'] = spec.get('account')
    if spec.get('plugin'):
        f, fn = _plugin_ref(spec['plugin'])
        core['plugin'] = {'file': os.path.basename(f), 'func': fn, 'sha': _file_sha(f)}
    if spec.get('universe') is not None:      # single-stock spec (lab/stocks.py); added only when set
        core['universe'] = spec.get('universe')
        core['stock'] = spec.get('stock')
    return hashlib.sha256(json.dumps(core, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def is_universe(spec):
    """A single-stock spec (`universe: sp500`, lab/stocks.py) rather than an ETF-sleeve spec."""
    return isinstance(spec, dict) and spec.get('universe') is not None


MIN_DELAY = 2          # engine delay 2 = decide at close t, trade at close t+1 (delay < 2 would fill at or before the decision close)
MIN_COST = 0.003       # 0.25% fee + 0.05% spread; a spec may only raise it
# account: which broker/tax the dev engine models. 'us' = Kiwoom US-listed ETFs (0.30%/side, 22% yearly net CGT).
# 'kr_etf' = KR-listed ETFs tracking overseas/leveraged indices: 13bp/side, 15.4% withheld on each sale's gain, no
# loss offset across sales (conservative; ignores the 과표기준가 rule and ISA). Sleeve returns are the same series
# (no KRW FX, no KR-listing ER/tracking gap). The bar (bb.py) is calibrated to the US broker only -> kr_etf is dev only.
ACCOUNTS = {'us': dict(min_cost=0.003, tax=0.22, tax_mode='yearly'),
            'kr_etf': dict(min_cost=0.0013, tax=0.154, tax_mode='per_sale')}


def account_of(spec):
    a = spec.get('account', 'us')
    if a not in ACCOUNTS:
        raise ValueError(f'account must be one of {sorted(ACCOUNTS)}, not {a!r}')
    return a, ACCOUNTS[a]
MAX_GRID = 256


def check_spec(spec):
    """Refuse spec settings that would let a back-test see or trade on information it could not have had.
    delay must be an integer >= MIN_DELAY; cost must be a finite number (it is clamped up to MIN_COST where used).
    Also checks the shape of the v2 blocks (grid must be expanded first, plugin needs declared sleeves)."""
    d = spec.get('delay', MIN_DELAY)
    if isinstance(d, bool) or not isinstance(d, (int, float)) or not np.isfinite(d) or float(d) != int(d) \
            or int(d) < MIN_DELAY:
        raise ValueError(f'delay must be an integer >= {MIN_DELAY} (same-bar or earlier fills are look-ahead), not {d!r}')
    c = spec.get('cost', MIN_COST)
    if isinstance(c, bool) or not isinstance(c, (int, float)) or not np.isfinite(c):
        raise ValueError(f'cost must be a finite number, not {c!r}')
    acct, _ = account_of(spec)
    if spec.get('grid') is not None:
        raise ValueError('spec has a grid: expand it first (dsl.expand_grid; `lab run` does this)')
    if is_universe(spec):                     # single stocks: own checks (stock block, gate signals)
        from . import stocks
        return stocks.check_spec(spec)
    if spec.get('plugin'):
        if spec.get('rules') or spec.get('signals'):
            raise ValueError('plugin spec: give either plugin (+ sleeves, inputs, params) or signals/rules, not both')
        if not spec.get('sleeves'):
            raise ValueError('plugin spec needs `sleeves: [..]` (the sleeves its weights may hold)')
        f, _ = _plugin_ref(spec['plugin'])
        if not os.path.isfile(f):
            raise ValueError(f'plugin file not found: {f}')
    elif not isinstance(spec.get('rules'), list):
        raise ValueError('spec needs `rules: [..]` (or `plugin:`)')
    _cadence(spec.get('rebalance', 'daily'), 'rebalance')
    from . import data as _data
    kr = sorted(set(held_sleeves(spec) + [spec.get('baseline', 'QQQ')]) & set(_data.KR_SLEEVES))
    if kr and acct != 'kr_etf':
        raise ValueError(f'{kr} are KR-listed ETFs: set `account: kr_etf` (KR costs and tax)')
    if spec.get('brake') is not None:
        _brake_levels(spec['brake'])
    sig = spec.get('signals') or {}
    if not isinstance(sig, dict):
        raise ValueError('signals must be a mapping {name: expression}')
    for k in sig:
        if isinstance(k, bool):
            raise ValueError(f'signal name {k!r} is a YAML boolean (on / off / yes / no / true / false are read as '
                             'True / False): rename it, e.g. go / stop')
        if not isinstance(k, str) or not k.isidentifier() or k.startswith('_') or k in FUNCS:
            raise ValueError(f'signal name {k!r} must be an identifier that is not a DSL function and does not start '
                             'with _')
    for r in spec.get('rules') or []:
        if not isinstance(r, dict):
            raise ValueError(f'each rule must be a mapping, not {r!r}')
        if 'else' in r and ({'when', 'hold', 'rotate'} & set(r)):
            raise ValueError("a rule with `else` takes nothing else (no when / hold / rotate): write "
                             "`- else: {..}` or `- when: .. / hold: {..}`")
        for k in ('hold', 'else'):
            if k in r and not isinstance(r[k], dict):
                raise ValueError(f'rule {k} must be a mapping {{SLEEVE: weight}}, not {r[k]!r}')
        if 'rotate' in r:
            _rot_cfg(r['rotate'])
    lv = level_names(spec)
    held = set(held_sleeves(spec))
    bad = sorted(lv - held)
    if bad:
        raise ValueError(f'level(x) reads the traded level of a held sleeve; {bad} is not held by this spec')
    return spec


def held_sleeves(spec):
    """Sleeves a spec can hold (without CASH): hold / else keys, rotate assets and fill, plugin `sleeves`."""
    out = set(spec.get('sleeves') or [])
    for r in spec.get('rules') or []:
        out |= set(r.get('else') if 'else' in r else (r.get('hold') or {}))
        if 'rotate' in r:
            out |= set(r['rotate'].get('assets') or [])
            out.add(r['rotate'].get('fill', 'CASH'))
    return sorted(out - {'CASH'})


# ---------------- grid ----------------
def _subst(x, point):
    if isinstance(x, dict):
        return {_subst(k, point): _subst(v, point) for k, v in x.items()}
    if isinstance(x, list):
        return [_subst(v, point) for v in x]
    if isinstance(x, str):
        for k, v in point.items():
            if x == '{' + k + '}':
                return v                                   # whole-string placeholder keeps the value's type
        for k, v in point.items():
            x = x.replace('{' + k + '}', str(v))
        return x
    return x


def expand_grid(spec):
    """grid: {X: [0.25, 0.30], N: [100, 200]} + {X} / {N} placeholders anywhere in the spec -> one spec per point
    (cartesian product, key order as written). Each point is its own spec: own hash, own ledger row, counted in the
    family N. Name = 'base[X=0.25,N=100]'. A spec without grid -> [spec]."""
    g = spec.get('grid')
    if g is None:
        return [spec]
    if not isinstance(g, dict) or not g:
        raise ValueError('grid must be a mapping {NAME: [values..]}')
    for k, v in g.items():
        if not str(k).isidentifier() or not isinstance(v, list) or not v:
            raise ValueError(f'grid {k!r}: name must be an identifier and values a non-empty list')
    body = {k: v for k, v in spec.items() if k != 'grid'}
    for k in ('name', 'family', 'known', 'baseline', 'grid_of'):
        t = json.dumps(body.get(k), ensure_ascii=False)
        used = [g_ for g_ in g if '{' + str(g_) + '}' in t]
        if used:
            raise ValueError(f'grid placeholder {used} in `{k}`: every grid point must share the base spec\'s {k} '
                             '(the family N counts each point)')
    txt = json.dumps(body, ensure_ascii=False)
    unused = [k for k in g if '{' + k + '}' not in txt]
    if unused:
        raise ValueError(f'grid key(s) {unused} not used as {{NAME}} anywhere in the spec')
    n = int(np.prod([len(v) for v in g.values()]))
    if n > MAX_GRID:
        raise ValueError(f'grid has {n} points (> {MAX_GRID})')
    base = spec.get('name', 'grid')
    out = []
    for vals in itertools.product(*g.values()):
        point = dict(zip(g.keys(), vals))
        s = _subst(copy.deepcopy(body), point)
        s['name'] = f"{base}[{','.join(f'{k}={v}' for k, v in point.items())}]"
        s['grid_of'] = base; s['grid_point'] = point; s['grid_n'] = n
        out.append(s)
    return out


def _win(n, f):
    """Window / lag argument: a plain integer >= 1. Zero or negative values (lag(x, -1), ret(x, -5)) read rows after
    the decision row, i.e. the future, and are refused."""
    if isinstance(n, (bool, np.bool_)) or not isinstance(n, (int, float, np.integer, np.floating)) \
            or not np.isfinite(n) or float(n) != int(n) or int(n) < 1:
        raise ValueError(f'{f}(): window / lag must be an integer >= 1, not {n!r} (n <= 0 would read future rows)')
    return int(n)


def _pos(x, f):
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, float, np.integer, np.floating)) \
            or not np.isfinite(x) or x <= 0:
        raise ValueError(f'{f}(): needs a positive number, not {x!r}')
    return float(x)


def _lev(a):
    return float(data.SLEEVES[a][2]) if a in data.SLEEVES else 1.0


def _boolv(x, idx):
    if isinstance(x, pd.Series):
        return x.reindex(idx).fillna(False).astype(bool).values
    if isinstance(x, np.ndarray):
        return np.nan_to_num(x.astype(float)).astype(bool)
    return np.full(len(idx), bool(x))


# ---- indicator library (all causal: every window / lag is checked to be an integer >= 1) ----
def _mk(F, R=None):
    """Function table for one frame. R (dev summary): lab sleeve returns, used by level(); on a bar path R is None and
    level() reads the path's own sleeve price column (LabCandidate.frame puts it in F under the sleeve name)."""
    P = lambda x: x.astype(float) if isinstance(x, pd.Series) else data.price_for_signal(F, x)
    lr = lambda x: np.log(P(x)).diff()
    idx = F.index
    memo = {}

    def level(x):
        if not isinstance(x, str) or x not in data.SLEEVES:
            raise ValueError(f'level(x): x must be a sleeve name (e.g. TQQQ), not {x!r}')
        if R is not None:
            if x not in R.columns:
                raise ValueError(f'level({x}): {x} must be one of the spec\'s held sleeves')
            r = R[x].reindex(idx).astype(float)
            ok = np.flatnonzero(r.notna().values)
            lv = (1.0 + r.fillna(0.0)).cumprod()        # 1.0 on the row before the first return, NaN before that
            return lv.where(np.arange(len(idx)) >= ok[0] - 1) if len(ok) else lv * np.nan
        if x not in F.columns:
            raise ValueError(f'level({x}): {x} must be one of the spec\'s held sleeves')
        return F[x].astype(float)

    def ser(x, ret=False):
        """name -> its price (ret=True: daily log return); Series -> as is; number -> constant Series."""
        if isinstance(x, str):
            return lr(x) if ret else P(x)
        if isinstance(x, pd.Series):
            return x
        return pd.Series(float(x), index=idx)

    def rsi(x, n=14):
        n = _win(n, 'rsi')
        d = P(x).diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
        dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
        return 100 - 100 / (1 + up / dn)

    def corr(x, y, n):
        n = _win(n, 'corr')
        return ser(x, True).rolling(n, min_periods=n).corr(ser(y, True))

    def zscore(s, n):
        n = _win(n, 'zscore'); s = ser(s)
        r = s.rolling(n, min_periods=n)
        return (s - r.mean()) / r.std()

    def ewvol(x, halflife):
        hl = _pos(halflife, 'ewvol')
        return ser(x, True).ewm(halflife=hl, adjust=False, min_periods=max(2, int(math.ceil(hl)))).std() * np.sqrt(252)

    def since(cond):
        b = _boolv(cond, idx); ar = np.arange(len(b))
        last = np.maximum.accumulate(np.where(b, ar, -1))
        return pd.Series(np.where(last >= 0, ar - last, np.inf), index=idx)

    def hold_min(cond, n):
        return pd.Series(_hold_min(_boolv(cond, idx), _win(n, 'hold_min')), index=idx)

    def _assets(lst, f):
        if not isinstance(lst, (list, tuple)) or not lst or not all(isinstance(a, str) for a in lst):
            raise ValueError(f'{f}(): second argument must be a list of sleeve names, e.g. [QLD, TLT]')
        return tuple(lst)

    def invvol(x, lst, n):
        A = _assets(lst, 'invvol'); n = _win(n, 'invvol')
        k = ('iv', A, n)
        if k not in memo:            # 0 until EVERY listed asset has an n-day vol (like rp: no full weight on one)
            V = np.stack([_lev_vol(P, a, n) for a in A], 1)
            ok = np.all(np.isfinite(V) & (V > 0), 1)[:, None] & np.ones(len(A), bool)
            memo[k] = _iv_weights(V, ok)
        return pd.Series(memo[k][:, A.index(x)], index=idx)

    def rp(x, lst, n):
        A = _assets(lst, 'rp'); n = _win(n, 'rp')
        k = ('rp', A, n)
        if k not in memo:
            C = _roll_cov(np.stack([_lev(a) * lr(a).values for a in A], 1), n)
            memo[k] = _erc(C, np.all(np.isfinite(C.reshape(len(C), -1)), 1)[:, None] & np.ones(len(A), bool))
        return pd.Series(memo[k][:, A.index(x)], index=idx)

    fn = {
        'price': lambda x: P(x),
        'sma': lambda x, n: P(x).rolling(_win(n, 'sma'), min_periods=_win(n, 'sma')).mean(),
        'ema': lambda x, n: P(x).ewm(span=_win(n, 'ema'), adjust=False, min_periods=_win(n, 'ema')).mean(),
        'ret': lambda x, n: P(x) / P(x).shift(_win(n, 'ret')) - 1,
        'vol': lambda x, n: lr(x).rolling(_win(n, 'vol'), min_periods=_win(n, 'vol')).std() * np.sqrt(252),
        'high': lambda x, n: P(x).rolling(_win(n, 'high'), min_periods=1).max(),
        'low': lambda x, n: P(x).rolling(_win(n, 'low'), min_periods=1).min(),
        'dd': lambda x, n: P(x) / P(x).rolling(_win(n, 'dd'), min_periods=1).max() - 1,
        'rsi': rsi,
        'month': lambda: pd.Series(F.index.month, index=F.index),
        'weekday': lambda: pd.Series(F.index.weekday, index=F.index),
        'min': lambda a, b: np.minimum(a, b),
        'max': lambda a, b: np.maximum(a, b),
        'abs': lambda a: np.abs(a),
        'lag': lambda s, n=1: s.shift(_win(n, 'lag')),
        'latch': lambda on, off: _latch(on, off, F.index),
        'corr': corr, 'zscore': zscore, 'ewvol': ewvol, 'since': since, 'hold_min': hold_min,
        'invvol': invvol, 'rp': rp, 'level': level,
    }
    return fn


FUNCS = ('price', 'sma', 'ema', 'ret', 'vol', 'high', 'low', 'dd', 'rsi', 'month', 'weekday', 'min', 'max', 'abs',
         'lag', 'latch', 'corr', 'zscore', 'ewvol', 'since', 'hold_min', 'invvol', 'rp', 'level')


def _hold_min(b, n):
    """On from a day cond turns on, for at least n days (the turn-on day counts as day 1), then as long as cond holds.
    Causal: day t reads cond at t and the state at t-1."""
    out = np.zeros(len(b), bool)
    on, start = False, 0
    for t, x in enumerate(b.tolist()):
        if x:
            if not on:
                on, start = True, t
        elif on and t - start >= n:
            on = False
        out[t] = on
    return out


def _lev_vol(P, a, n):
    """Rolling n-day vol of a sleeve = leverage x its underlying's daily log-return std (same on real and path data)."""
    r = np.log(P(a)).diff()
    return (_lev(a) * r).rolling(n, min_periods=n).std().values * np.sqrt(252)


def _iv_weights(V, mask):
    iv = np.where(mask & (V > 0), 1.0 / np.where(V > 0, V, 1.0), 0.0)
    s = iv.sum(1, keepdims=True)
    return np.where(s > 0, iv / np.where(s > 0, s, 1.0), 0.0)


def _roll_cov(X, n):
    """X: T x k daily returns (NaN allowed). Rolling n-day sample covariance, T x k x k (NaN until n full rows)."""
    T, k = X.shape
    df = pd.DataFrame(X)
    C = np.full((T, k, k), np.nan)
    for i in range(k):
        for j in range(i, k):
            c = df[i].rolling(n, min_periods=n).cov(df[j]).values
            C[:, i, j] = C[:, j, i] = c
    return C


def _erc(C, mask, tol=1e-13, max_sweeps=500):
    """Equal-risk-contribution weights (sum 1) over the masked assets, row by row.
    Cyclic coordinate descent on f(y) = y'Cy / 2 - b * sum(log y_i) (b = 1 / #assets): its unique minimiser has
    y_i (Cy)_i = b for every i, i.e. equal risk contributions, and w = y / sum(y). Each step solves df/dy_i = 0 exactly,
    y_i = (-c_i + sqrt(c_i^2 + 4 C_ii b)) / (2 C_ii) with c_i = sum_{j != i} C_ij y_j, so it converges for any
    positive semi-definite C, negative correlations included (the old multiplicative fixed point froze a weight whose
    risk contribution went negative). Assets with zero or non-finite variance are left out of the row."""
    T, k = mask.shape
    C = np.where(np.isfinite(C), C, 0.0)
    d = np.einsum('tii->ti', C)
    m = mask & (d > 0)
    cnt = m.sum(1, keepdims=True)
    b = np.where(m, 1.0 / np.maximum(cnt, 1), 0.0)
    dd = np.where(m, d, 1.0)
    y = np.where(m, 1.0 / np.sqrt(dd), 0.0)                       # start: inverse-vol (exact when uncorrelated)
    for _ in range(max_sweeps):
        y0 = y.copy()
        for i in range(k):
            c = np.einsum('tj,tj->t', C[:, i, :], y) - C[:, i, i] * y[:, i]
            yi = (-c + np.sqrt(c * c + 4.0 * dd[:, i] * b[:, i])) / (2.0 * dd[:, i])
            y[:, i] = np.where(m[:, i], yi, 0.0)
        s = np.maximum(y.sum(1, keepdims=True), 1e-300)
        if np.max(np.abs(y / s - y0 / np.maximum(y0.sum(1, keepdims=True), 1e-300)), initial=0.0) < tol:
            break
    s = y.sum(1, keepdims=True)
    return np.where(s > 0, y / np.where(s > 0, s, 1.0), 0.0)


def _latch(on, off, idx):
    """State signal: True from a day `on` is true, False from a day `off` is true, else the previous state;
    starts False. NaN counts as false. If `on` and `off` are both true on the same day, `off` wins (lab choice:
    the risk-reducing side). Causal: day t only reads on/off at t and the state at t-1."""
    ev = np.where(_boolv(off, idx), 0.0, np.where(_boolv(on, idx), 1.0, np.nan))
    return pd.Series(ev, index=idx).ffill().fillna(0.0).astype(bool)


_OK = (ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare, ast.Call, ast.Name, ast.Load,
       ast.Constant, ast.And, ast.Or, ast.Not, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub,
       ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.Eq, ast.NotEq, ast.BitAnd, ast.BitOr, ast.Invert, ast.Mod,
       ast.List, ast.Tuple)


class _Bool(ast.NodeTransformer):
    """and/or/not -> & | ~ so they work element-wise on Series; chained a<b<c -> (a<b)&(b<c). Integer constants become
    floats (window arguments are still checked to be whole numbers), so constant arithmetic like 10**10**9 overflows at
    once instead of building a huge integer."""
    def visit_Constant(self, node):
        if isinstance(node.value, int) and not isinstance(node.value, bool):
            return ast.copy_location(ast.Constant(value=float(node.value)), node)
        return node

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        op = ast.BitAnd() if isinstance(node.op, ast.And) else ast.BitOr()
        out = node.values[0]
        for v in node.values[1:]:
            out = ast.BinOp(left=out, op=op, right=v)
        return out

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Not):
            return ast.UnaryOp(op=ast.Invert(), operand=node.operand)
        return node

    def visit_Compare(self, node):
        self.generic_visit(node)
        if len(node.ops) == 1:
            return node
        parts, left = [], node.left
        for op, right in zip(node.ops, node.comparators):
            parts.append(ast.Compare(left=left, ops=[op], comparators=[right])); left = right
        out = parts[0]
        for p in parts[1:]:
            out = ast.BinOp(left=out, op=ast.BitAnd(), right=p)
        return out


_STAR = re.compile(r'(?<=[(,\[])\s*\*\s*(?=[,)\]])')


def star(expr, asset):
    """Replace the '*' asset placeholder (a '*' standing alone as a call / list argument, e.g. ret(*, 126)) by asset."""
    return _STAR.sub(asset, str(expr))


def _parse(expr):
    tree = ast.parse(str(expr), mode='eval')
    for node in ast.walk(tree):
        if not isinstance(node, _OK):
            raise ValueError(f'not allowed in expression: {type(node).__name__} in {expr!r}')
        if isinstance(node, ast.Name) and node.id.startswith('__'):
            raise ValueError(f'bad name {node.id!r}')
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) > 64:
            raise ValueError(f'string constant too long in {expr!r}')
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool) \
                and abs(node.value) > 1e300:
            raise ValueError(f'constant too large in {expr!r}')
    return tree


def _eval(expr, env, assets):
    if isinstance(expr, (int, float)):
        return float(expr)
    tree = ast.fix_missing_locations(_Bool().visit(_parse(expr)))
    # bare asset names (TQQQ, _NDX given as strings) -> string constants
    scope = dict(env)
    for a in assets:
        scope.setdefault(a, a)
    unknown = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id not in scope}
    if unknown:  # bare panel keys (_IRX, KRW_X, ..) read like quoted names; anything else stays a NameError (typos)
        keys = set(data.keys())
        for u in unknown & keys:
            scope[u] = u
    return eval(compile(tree, '<spec>', 'eval'), {'__builtins__': {}}, scope)


def spec_exprs(spec):
    """Every expression string of a spec, with rotate '*' placeholders expanded per asset (plugin `inputs` included:
    an input is an expression too, a bare name = its price)."""
    out = list((spec.get('signals') or {}).values())
    out += [x for x in (spec.get('inputs') or []) if _parses(x)]
    for r in spec.get('rules') or []:
        if 'when' in r:
            out.append(r['when'])
        out += list((r.get('else') if 'else' in r else (r.get('hold') or {})).values())
        if 'rotate' in r:
            ro = r['rotate']
            for a in ro.get('assets') or []:
                out += [star(ro[k], a) for k in ('score', 'filter') if ro.get(k) is not None]
    br = spec.get('brake') or {}
    if isinstance(br, dict) and isinstance(br.get('floor_when'), dict) and 'when' in br['floor_when']:
        out.append(br['floor_when']['when'])
    return out


def _parses(x):
    try:
        ast.parse(str(x), mode='eval')
        return True
    except SyntaxError:
        return False


def level_names(spec):
    """Sleeves read through level(x) anywhere in the spec."""
    out = set()
    for e in spec_exprs(spec):
        if isinstance(e, (int, float)) or not _parses(e):
            continue
        for n in ast.walk(ast.parse(str(e), mode='eval')):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'level' and n.args:
                a = n.args[0]
                if isinstance(a, ast.Name):
                    out.add(a.id)
                elif isinstance(a, ast.Constant) and isinstance(a.value, str):
                    out.add(a.value)
    return out


def spec_names(spec):
    """Series names a spec reads: bare names in expressions (minus DSL functions and the spec's own signal names),
    every string constant (price('XLK') reads a series just like price(XLK)), rotate / invvol / rp assets and the
    plugin's `inputs` (an input that is not an expression counts as a name)."""
    own = set(spec.get('signals') or {})
    out = {str(x) for x in (spec.get('inputs') or []) if not _parses(x)}
    for e in spec_exprs(spec):
        if isinstance(e, (int, float)):
            continue
        for n in ast.walk(ast.parse(str(e), mode='eval')):
            if isinstance(n, ast.Name) and n.id not in FUNCS and n.id not in own:
                out.add(n.id)
            elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                out.add(n.value)
    return out


# ---------------- cadence ----------------
_PER = {'weekly': 'W', 'monthly': 'M', 'quarterly': 'Q'}


def _cadence(c, what):
    if c in ('daily',) or c in _PER:
        return c
    if isinstance(c, (int, np.integer)) and not isinstance(c, bool) and c >= 1:
        return int(c)
    raise ValueError(f'{what} must be daily | weekly | monthly | quarterly | an integer N >= 1, not {c!r}')


def reb_rows(idx, c):
    """Rows on which a cadence decides. weekly / monthly / quarterly = the FIRST row of each new period (row 0
    included); N = every N-th row from row 0. Only row t and t-1 are read, so a path cut at any row gives the same
    flags (v1 used the period's last row, which needs the next date and failed the truncation test)."""
    c = _cadence(c, 'cadence'); n = len(idx)
    if c == 'daily':
        return np.ones(n, bool)
    if isinstance(c, int):
        return np.arange(n) % c == 0
    p = idx.to_period(_PER[c]).asi8 if n else np.zeros(0, np.int64)
    return np.r_[True, p[1:] != p[:-1]][:n]


def _ffill_rows(V, rows, fill=0.0):
    """Rows not flagged take the last flagged row's values (before the first flagged row: fill)."""
    n = len(V)
    pos = np.maximum.accumulate(np.where(rows, np.arange(n), -1))
    out = V[np.maximum(pos, 0)].copy()
    out[pos < 0] = fill
    return out, pos


# ---------------- rotate ----------------
def _rot_cfg(ro):
    if not isinstance(ro, dict) or not ro.get('assets'):
        raise ValueError('rotate needs assets: [..]')
    A = list(ro['assets'])
    if len(set(A)) != len(A) or 'CASH' in A:
        raise ValueError('rotate assets must be distinct sleeves (no CASH)')
    top = ro.get('top', 1 if ro.get('score') is not None else len(A))
    if isinstance(top, bool) or not isinstance(top, int) or not 1 <= top <= len(A):
        raise ValueError(f'rotate top must be an integer in 1..{len(A)}, not {top!r}')
    w = ro.get('weight', 'equal')
    if w not in ('equal', 'score', 'invvol', 'rp'):
        raise ValueError(f'rotate weight must be equal | score | invvol | rp, not {w!r}')
    if w == 'score' and ro.get('score') is None:
        raise ValueError('rotate weight: score needs a score expression')
    tot = ro.get('total', 1.0)
    if isinstance(tot, bool) or not isinstance(tot, (int, float)) or not 0 < tot <= 1:
        raise ValueError(f'rotate total must be in (0, 1], not {tot!r}')
    ex = ro.get('exit', 'none')
    if ex not in ('none', 'daily'):
        raise ValueError(f"rotate exit must be 'daily' or 'none', not {ex!r}")
    if ex == 'daily' and ro.get('filter') is None:
        raise ValueError('rotate exit: daily needs a filter')
    fill = ro.get('fill', 'CASH')
    if fill in A:
        raise ValueError('rotate fill must not be one of the ranked assets')
    for k in ('score', 'filter'):
        if ro.get(k) is not None and '*' not in str(ro[k]):
            raise ValueError(f"rotate {k} must use the '*' asset placeholder, e.g. ret(*, 126)")
    return dict(A=A, top=top, w=w, total=float(tot), every=_cadence(ro.get('every', 'monthly'), 'rotate every'),
                exit=ex, fill=fill, n=_win(ro.get('n', 60), 'rotate n'), score=ro.get('score'), filter=ro.get('filter'))


def _rotate(ro, env, assets, F):
    """T x (k + 1) weights: the k ranked assets and the fill sleeve (last column). On each `every` row the assets that
    pass the filter (and have a finite score) are ranked by score (ties: list order), the top k are held with equal /
    score / invvol / rp weights, total x (picked / top); the unfilled share goes to `fill`. Between decision rows the
    picks and weights are kept; exit: daily drops a held asset (to fill) from the first day its filter fails until the
    next decision row."""
    c = _rot_cfg(ro); A = c['A']; k = len(A); idx = F.index; n = len(idx)

    def mat(key, dflt, conv):
        if c[key] is None:
            return np.full((n, k), dflt)
        return np.stack([conv(_eval(star(c[key], a), env, assets)) for a in A], 1)
    num = lambda v: (v.reindex(idx).values.astype(float) if isinstance(v, pd.Series) else np.full(n, float(v)))
    S = mat('score', 0.0, num)
    Fm = mat('filter', True, lambda v: _boolv(v, idx))
    valid = Fm & np.isfinite(S)
    P = lambda x: data.price_for_signal(F, x)
    if c['w'] in ('invvol', 'rp'):
        V = np.stack([_lev_vol(P, a, c['n']) for a in A], 1)
        valid &= np.isfinite(V) & (V > 0)
    rows = reb_rows(idx, c['every'])
    ri = np.flatnonzero(rows)
    Sx = np.where(valid[ri], S[ri], -np.inf)
    order = np.argsort(-Sx, axis=1, kind='stable')
    rank = np.empty_like(order); np.put_along_axis(rank, order, np.arange(k)[None, :].repeat(len(ri), 0), 1)
    pick = (rank < c['top']) & valid[ri]
    npk = pick.sum(1, keepdims=True).astype(float)
    if c['w'] == 'equal':
        w = pick / c['top']
    else:
        if c['w'] == 'score':
            raw = np.where(pick, np.maximum(S[ri], 0.0), 0.0)
            raw = np.where(raw.sum(1, keepdims=True) > 0, raw, pick.astype(float))
        elif c['w'] == 'invvol':
            raw = _iv_weights(V[ri], pick)
        else:
            r = np.stack([_lev(a) * np.log(P(a)).diff().values for a in A], 1)
            raw = _erc(_roll_cov(r, c['n'])[ri], pick)
        s = raw.sum(1, keepdims=True)
        w = np.where(s > 0, raw / np.where(s > 0, s, 1.0), 0.0) * npk / c['top']
    Wr = np.zeros((n, k)); Wr[ri] = w * c['total']
    Wd, pos = _ffill_rows(Wr, rows)
    if c['exit'] == 'daily':
        fail = ~Fm
        lastfail = np.maximum.accumulate(np.where(fail, np.arange(n)[:, None], -1), axis=0)
        Wd = np.where(lastfail >= pos[:, None], 0.0, Wd)        # failed on a day since the last decision row
        Wd[pos < 0] = 0.0
    fillw = np.where(pos >= 0, c['total'] - Wd.sum(1), 0.0)
    return A, c['fill'], Wd, np.maximum(fillw, 0.0)


# ---------------- brake ----------------
def _brake_levels(br):
    """brake forms:
         {dd: -0.20, scale: 0.5, recover: -0.10}                 one step with hysteresis (recover default dd / 2)
         {ladder: [[-0.15, 0.7], [-0.25, 0.4, -0.12]], recover: -0.05}   several steps (each [dd, scale(, recover)])
         {knee: [-0.45, -0.75], floor: 0.0}                      linear: 1 above -45%, floor at/below -75%
       common options: basis: own (default) | raw, cooldown: N, floor_when: {when: <expr>, scale: s}."""
    if not isinstance(br, dict):
        raise ValueError('brake must be a mapping')
    num = lambda v, w, lo=-1.0, hi=1.0: (v if (not isinstance(v, bool) and isinstance(v, (int, float))
                                              and lo <= v <= hi) else _bad(f'brake {w} must be a number in [{lo}, {hi}], not {v!r}'))
    lv, knee = [], None
    if 'knee' in br:
        k = br['knee']
        if not isinstance(k, list) or len(k) != 2:
            _bad('brake knee must be [dd_start, dd_full] e.g. [-0.45, -0.75]')
        a, b = num(k[0], 'knee', -1, 0), num(k[1], 'knee', -1, 0)
        if not b < a:
            _bad('brake knee: dd_full must be below dd_start')
        knee = (float(a), float(b), float(num(br.get('floor', 0.0), 'floor', 0, 1)))
    else:
        steps = br.get('ladder') or [[br.get('dd'), br.get('scale', 0.5)] + ([br['recover']] if 'recover' in br and 'ladder' not in br else [])]
        for s in steps:
            if not isinstance(s, (list, tuple)) or len(s) not in (2, 3):
                _bad('brake ladder steps are [dd, scale] or [dd, scale, recover]')
            d = float(num(s[0], 'dd', -1, -1e-9)); sc = float(num(s[1], 'scale', 0, 1))
            rc = s[2] if len(s) == 3 else br.get('recover', d / 2)
            rc = float(num(rc, 'recover', -1, 0))
            if not rc > d:
                _bad(f'brake recover ({rc}) must be above dd ({d})')
            lv.append((d, sc, rc))
    basis = br.get('basis', 'own')
    if basis not in ('own', 'raw'):
        _bad("brake basis must be 'own' or 'raw'")
    cd = br.get('cooldown')
    cd = None if cd is None else _win(cd, 'brake cooldown')
    fw = br.get('floor_when')
    if fw is not None and not (isinstance(fw, dict) and 'when' in fw):
        _bad('brake floor_when must be {when: <expr>, scale: s}')
    return dict(levels=lv, knee=knee, basis=basis, cooldown=cd,
                floor_when=None if fw is None else (fw['when'], float(num(fw.get('scale', 0.0), 'floor_when scale', 0, 1))))


def _bad(msg):
    raise ValueError(msg)


def brake_scale(g, cfg, floor=None):
    """Scale s[t] in [0, 1] from the paper equity. g[t] = return on day t of the UNSCALED weights decided at t-1
    (sum_j w[t-1, j] * r[t, j]). basis own: E[t] = E[t-1] * (1 + s[t-1] * g[t]) (the braked strategy's own equity);
    basis raw: E[t] = E[t-1] * (1 + g[t]). dd[t] = E[t] / max(E[..t]) - 1; s[t] is decided from dd[t] (and the state
    at t-1) only, so the weights of day t use the equity through the close of t. Steps latch on at dd <= level and off
    at dd >= recover; the scale is the smallest engaged step. cooldown N: after N days braked, every step releases
    and the peak is reset to the current equity. floor_when: on days the condition holds, s >= its scale."""
    n = len(g); s = np.ones(n)
    lv, knee, own, cd = cfg['levels'], cfg['knee'], cfg['basis'] == 'own', cfg['cooldown']
    gl = g.tolist(); fl = floor.tolist() if floor is not None else None
    E = pk = 1.0; sp = 1.0; on = [False] * len(lv); braked = 0
    for t in range(n):
        if t:
            E *= 1.0 + (sp * gl[t] if own else gl[t])
        if E > pk:
            pk = E
        d = E / pk - 1.0
        if knee is not None:
            a, b, f = knee
            x = 1.0 if d >= a else (f if d <= b else max(f, 1.0 - (a - d) / (a - b) * (1.0 - f)))
        else:
            x = 1.0
            for i, (lvl, sc, rc) in enumerate(lv):
                if on[i]:
                    if d >= rc:
                        on[i] = False
                elif d <= lvl:
                    on[i] = True
                if on[i] and sc < x:
                    x = sc
        if x < 1.0:
            braked += 1
            if cd is not None and braked > cd:
                on = [False] * len(lv); pk = E; braked = 0; x = 1.0
        else:
            braked = 0
        if fl is not None and fl[t] > x:
            x = fl[t]
        s[t] = x; sp = x
    return s


def sleeve_returns(F, cols, R=None):
    """Close-to-close returns of each risk sleeve for the brake's paper equity: R[col] when given (dev summary: the
    lab sleeve returns incl. the synthetic pre-listing part), else the sleeve's own price column in F (bar path:
    blackbox2's in-path sleeve price), else leverage x its underlying's return. NaN -> 0."""
    out = np.zeros((len(F), len(cols)))
    for j, c in enumerate(cols):
        if R is not None and c in R.columns:
            r = R[c].reindex(F.index)
        elif c in F.columns:
            r = F[c].pct_change(fill_method=None)
        else:
            r = _lev(c) * data.price_for_signal(F, c).pct_change(fill_method=None)
        out[:, j] = np.nan_to_num(r.values.astype(float), nan=0.0, posinf=0.0, neginf=0.0)
    return out


# ---------------- plugin ----------------
_PLUG = {}
_FORBID = re.compile(r'\bopen\s*\(|\.load\s*\(|fromfile|loadtxt|genfromtxt|read_\w+\s*\(|\blzma\b|\bpickle\b|\bnpz\b|'
                     r'/mnt/|\bimportlib\b|__import__|\bsubprocess\b|\bsocket\b|\burllib\b|\brequests\b|\bexec\s*\(|'
                     r'\beval\s*\(|\bglobals\s*\(|__builtins__|\bsys\b|\bos\b|\bdata\s*\.|lab\.data|import\s+data|'
                     r'\b_z\b|\bPANEL\b|\bseries\s*\(|\bgetattr\s*\(|__dict__|__class__|__subclasses__')
PLUGIN_IMPORTS = ('numpy', 'pandas', 'math', 'itertools', 'functools', 'collections', 'statistics', 'bisect', 'heapq',
                  'operator', 're')
PluginError = sandbox.PluginError


def _scan_plugin(src, f):
    """Early, readable refusals (the enforcement is the process isolation in lab/sandbox.py): a source scan for file /
    panel / system access, imports only from PLUGIN_IMPORTS, no dunder names or attributes."""
    base = os.path.basename(f)
    try:                                  # scan code only: comments dropped, string literals blanked (checked below)
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, SyntaxError) as e:
        raise PluginError(f'plugin {base}: cannot tokenize: {e}')
    lines = [list(x) for x in src.splitlines()]
    for t in toks:                        # blank comments and string bodies in place (layout kept)
        if t.type == tokenize.STRING and re.search(r'/mnt/|\.npz\b|\.xz\b', t.string):
            raise PluginError(f'plugin {base}:{t.start[0]}: string {t.string[:40]!r} names a data file / panel')
        if t.type in (tokenize.COMMENT, tokenize.STRING):
            (r0, c0), (r1, c1) = t.start, t.end
            for r in range(r0, r1 + 1):
                if r - 1 < len(lines):
                    a, b = (c0 if r == r0 else 0), (c1 if r == r1 else len(lines[r - 1]))
                    lines[r - 1][a:b] = ' ' * (b - a)
    for i, line in enumerate((''.join(x) for x in lines), 1):
        m = _FORBID.search(line)
        if m:
            raise PluginError(f'plugin {base}:{i}: {m.group(0)!r} is not allowed (no file / panel / system access; use '
                              'numpy, pandas, math on the F it is given)')
    try:
        tree = ast.parse(src, f)
    except SyntaxError as e:
        raise PluginError(f'plugin {base}: syntax error: {e}')
    for n in ast.walk(tree):
        mods = [a.name for a in n.names] if isinstance(n, ast.Import) else \
               [n.module or ''] if isinstance(n, ast.ImportFrom) else []
        for mname in mods:
            if (isinstance(n, ast.ImportFrom) and n.level) or mname.split('.')[0] not in PLUGIN_IMPORTS:
                raise PluginError(f'plugin {base}:{n.lineno}: import {mname or "."!r} is not allowed '
                                  f'(only {", ".join(PLUGIN_IMPORTS)})')
        nm = n.id if isinstance(n, ast.Name) else n.attr if isinstance(n, ast.Attribute) else None
        if nm is not None and nm.startswith('__'):
            raise PluginError(f'plugin {base}:{n.lineno}: dunder name {nm!r} is not allowed')


def load_plugin(ref):
    """Read and scan a plugin file -> (source, func name, file). The code itself never runs in this process: every
    call goes to a fresh forked child of the plugin runner (lab/sandbox.py)."""
    f, fn = _plugin_ref(ref)
    sha = _file_sha(f)
    key = (os.path.abspath(f), fn, sha)
    if key in _PLUG:
        return _PLUG[key]
    with open(f, encoding='utf-8') as fh:
        src = fh.read()
    _scan_plugin(src, f)
    _PLUG[key] = (src, fn, f)
    return _PLUG[key]


_SESSIONS = []          # stack of open session registries (see plugin_calls)


class plugin_calls:
    """Inside `with plugin_calls():` plugin calls on frames that EXTEND each other share one child process (state the
    plugin keeps then only holds rows it has already been given); a frame that does not extend the previous one gets
    a fresh child. Outside, every call is its own fresh child. The truncation tests send the cuts in increasing order
    and the full frame last inside one of these blocks."""

    def __enter__(self):
        _SESSIONS.append({})
        return self

    def __exit__(self, *e):
        for ses in _SESSIONS.pop().values():
            ses.close()


def _plugin_weights(spec, F, sleeves, cols, R=None):
    """F for the plugin = one column per declared input: a bare name reads like price(x) (a sleeve name = its
    underlying index), any other input is a DSL expression (e.g. 'level(TQQQ)', 'vol(QQQ, 20)'); same rows as the DSL
    frame (dev: real <= 2014; bar: the synthetic path). The plugin runs out of process (lab/sandbox.py)."""
    src, fn, f = load_plugin(spec['plugin'])
    env = None
    Fp = {}
    for x in (spec.get('inputs') or []):
        x = str(x)
        if x.isidentifier() or not _parses(x):
            Fp[x] = data.price_for_signal(F, x).astype(float)
        else:
            if env is None:
                env = dict(_mk(F, R))
            v = _eval(x, env, set(F.columns) | set(data.SLEEVES) | set(cols))
            Fp[x] = (v.reindex(F.index).astype(float) if isinstance(v, pd.Series)
                     else pd.Series(float(v), index=F.index))
    Fp = pd.DataFrame(Fp, index=F.index)
    key = (f, fn, json.dumps(spec.get('params') or {}, sort_keys=True, default=str), tuple(sleeves), tuple(cols))
    reg = _SESSIONS[-1] if _SESSIONS else None
    ses = reg.get(key) if reg is not None else None
    if ses is None:
        ses = sandbox.Session(src, fn, f, list(sleeves), json.loads(json.dumps(spec.get('params') or {}, default=str)),
                              list(cols))
        if reg is not None:
            reg[key] = ses
    try:
        ocols, V = ses.call(Fp)
    finally:
        if reg is None:
            ses.close()
    Wv = np.zeros((len(F), len(cols)))
    for j, c in enumerate(cols):
        if c != 'CASH' and c in ocols:
            x = np.clip(V[:, ocols.index(c)], 0, 1)
            Wv[:, j] = np.where(np.isnan(x), 0.0, x)
    return Wv


# ---------------- compile ----------------
def compile_weights(spec, F, sleeves, R=None):
    """spec + price frame F (+ sleeve returns R for the brake, dev summary only) -> daily target weights (incl. CASH).
    Order: rules or plugin -> risk sum <= 1 -> rebalance sampling -> brake -> band."""
    idx = F.index
    n = len(idx)
    cols = sorted(set(held_sleeves(spec)) | {'CASH'})
    ci = {c: i for i, c in enumerate(cols)}
    if spec.get('plugin'):
        Wv = _plugin_weights(spec, F, spec.get('sleeves') or sleeves, cols, R)
    else:
        fn = _mk(F, R)
        assets = set(F.columns) | set(sleeves) | set(data.SLEEVES) | set(cols)
        env = dict(fn)
        for name, expr in (spec.get('signals') or {}).items():
            v = _eval(expr, env, assets)
            env[name] = v
        # rule assembly on numpy arrays (same values as the pandas .loc version, ~3x faster per path)
        Wv = np.zeros((n, len(cols)))
        taken = np.zeros(n, bool)
        for r in spec['rules']:
            if 'else' in r:
                cond, hold = np.ones(n, bool), r['else']
            else:
                cond = _boolv(_eval(r['when'], env, assets), idx) if 'when' in r else np.ones(n, bool)
                hold = r.get('hold') or {}
            m = cond & ~taken
            if 'rotate' in r:
                A, fill, Wd, fw = _rotate(r['rotate'], env, assets, F)
                for j, a in enumerate(A):
                    Wv[m, ci[a]] = Wd[m, j]
                if fill != 'CASH':
                    Wv[m, ci[fill]] = fw[m]
            for a, w in hold.items():
                wv = _eval(w, env, assets)
                wv = (wv.reindex(idx).values.astype(float) if isinstance(wv, pd.Series)
                      else np.full(n, float(wv)))
                x = np.clip(wv[m], 0, 1)
                Wv[m, ci[a]] = np.where(np.isnan(x), 0.0, x)
            taken |= m
    risk = np.array([c != 'CASH' for c in cols])
    tot = Wv[:, risk].sum(1)
    over = tot > 1
    if over.any():
        Wv[np.ix_(over, risk)] = Wv[np.ix_(over, risk)] / tot[over, None]
    Wv[:, ci['CASH']] = 1 - Wv[:, risk].sum(1)
    reb = spec.get('rebalance', 'daily')
    if reb != 'daily':
        Wv, pos = _ffill_rows(Wv, reb_rows(idx, reb))
    if spec.get('brake') is not None:
        cfg = _brake_levels(spec['brake'])
        rc = [c for c in cols if c != 'CASH']
        rr = sleeve_returns(F, rc, R)
        g = np.r_[0.0, (Wv[:-1][:, risk] * rr[1:]).sum(1)] if n else np.zeros(0)
        floor = None
        if cfg['floor_when'] is not None:
            env_b = env if not spec.get('plugin') else dict(_mk(F, R))
            fwc = _boolv(_eval(cfg['floor_when'][0], env_b, set(F.columns) | set(data.SLEEVES) | set(cols)), idx)
            floor = np.where(fwc, cfg['floor_when'][1], 0.0)
        s = brake_scale(g, cfg, floor)
        Wv[:, risk] *= s[:, None]
        Wv[:, ci['CASH']] = 1 - Wv[:, risk].sum(1)
    W = pd.DataFrame(Wv, index=idx, columns=cols)
    band = float(spec.get('band', 0))
    if band > 0:  # only move when some weight changes by >= band
        W = pd.DataFrame(_band(W.values, band), index=idx, columns=W.columns)
    return W


def boundary_cuts(idx, rng, per=4, lo=2):
    """Cuts at `per` sampled week / month / quarter boundaries each, two per boundary: ending on the period's last row
    and on its second-to-last row. Look-ahead tied to the calendar (e.g. 'act on the last trading day of the month',
    which needs the next row's date) shows up on cuts like these whenever the decision there changes; random cuts
    cover the rest."""
    out = set()
    n = len(idx)
    if n < 3:
        return []
    for f in ('W', 'M', 'Q'):
        p = idx.to_period(f).asi8
        b = np.flatnonzero(p[1:] != p[:-1]) + 1
        b = b[(b >= lo) & (b < n)]
        if len(b):
            for x in rng.choice(b, size=min(per, len(b)), replace=False):
                out |= {int(x), int(x) - 1}
    return sorted(c for c in out if lo <= c < n)


N_CUTS_DEV = 12           # random cuts of the dev truncation test (+ calendar-boundary cuts)
N_CUTS_PLUGIN = 300       # plugin specs: the code is opaque, so many more cuts (cheap inside one plugin session)


def truncation_check(spec, F, sleeves, R=None, n_cuts=None, seed=None):
    """Dev-side causality: weights built on F (and R) cut at a row must equal the full-frame weights up to that row.
    Cuts: n_cuts random rows (default N_CUTS_DEV, N_CUTS_PLUGIN for a plugin spec) from a fresh OS seed (recorded)
    + 4 week / month / quarter boundaries each. Builds run in increasing length with the full frame LAST, inside one
    plugin session (a plugin cannot replay a stored full-length answer on a cut). Returns dict(ok, cuts, violations,
    seed)."""
    if seed is None:
        seed = int.from_bytes(os.urandom(8), 'little')
    if n_cuts is None:
        n_cuts = N_CUTS_PLUGIN if spec.get('plugin') else N_CUTS_DEV
    rng = np.random.default_rng(seed)
    n = len(F)
    lo = max(2, min(260, n - 1))
    cuts = sorted({int(x) for x in rng.integers(lo, n, size=n_cuts)} | set(boundary_cuts(F.index, rng, 4, lo))) \
        if n > lo else []
    bad = []
    with plugin_calls():
        prev = None                                   # (cut, weights) of the previous, shorter build
        for c in cuts + [n]:
            Wc = compile_weights(spec, F.iloc[:c], sleeves, None if R is None else R.iloc[:c]).values if c < n \
                else compile_weights(spec, F, sleeves, R).values
            if prev is not None:                      # each build vs the next longer one: all agree <=> each agrees
                d = float(np.nanmax(np.abs(prev[1] - Wc[:prev[0]])))       # with the full frame
                if not d <= 1e-9:
                    bad.append((str(F.index[prev[0] - 1].date()), d))
            prev = (c, Wc)
    return dict(ok=not bad, cuts=len(cuts), violations=bad, seed=seed)


def _band(Wv, band):
    """Same result as the row loop `if max|W[i] - held[i-1]| < band: W[i] = held[i-1]`, but only rows whose raw
    weights differ from the previous raw row are visited: on a row equal to the previous raw row the held row cannot
    change (either the previous row was taken, then the move is 0, or it was refused, then the move is the same as
    before), so it is carried forward."""
    Wv = np.asarray(Wv, float)
    n = len(Wv)
    if n < 2:
        return Wv.copy()
    ch = np.flatnonzero(np.any(Wv[1:] != Wv[:-1], axis=1)) + 1
    src = np.zeros(n, np.int64)  # row index whose weights are held on each day
    held = 0
    rows = Wv.tolist()
    for i in ch:
        r, h = rows[i], rows[held]
        if max(abs(a - c) for a, c in zip(r, h)) >= band:
            held = i
        src[i] = held
    # forward-fill: days between visited rows keep the last decision
    mark = np.zeros(n, bool); mark[0] = True; mark[ch] = True
    pos = np.maximum.accumulate(np.where(mark, np.arange(n), 0))
    return Wv[src[pos]]
