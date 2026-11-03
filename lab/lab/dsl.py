"""Strategy spec -> daily target weights.

A spec is a short YAML (or JSON) file. Example:

    name: trend_tqqq_200
    family: price_trend        # family tag: multiple-testing count N is kept per family
    known: 3                   # how known the idea is, 0 (new) .. 3 (textbook)
    idea: NDX above 200-day average -> TQQQ, else cash
    rebalance: daily           # daily | weekly | monthly
    signals:                   # evaluated in order; later lines may use earlier names
      up: price(TQQQ) > sma(TQQQ, 200)
    rules:                     # first rule whose `when` is true wins
      - when: up
        hold: {TQQQ: 1.0}
      - else: {CASH: 1.0}

Weights may be expressions, e.g. {TQQQ: "min(1, 0.3 / vol(TQQQ, 20))"}; the rest goes to CASH.
State signal: latch(on, off) is True from a day `on` holds, False from a day `off` holds, else keeps the previous
state; it starts False and `off` wins on a tie. Example (price hysteresis, sonnet C2 style):
    on: price(SPY) > sma(SPY, 200) * 1.02
    off: price(SPY) < sma(SPY, 200) * 0.98
    up: latch(on, off)
Expressions are checked with an AST whitelist (no attributes, no subscripts, no imports).
Every indicator only uses data up to the decision close; the engine adds the execution delay.
"""
import ast, hashlib, json
import numpy as np, pandas as pd
from . import data

try:
    import yaml
except ImportError:  # JSON specs still work
    yaml = None


def load_spec(path):
    txt = open(path, encoding='utf-8').read()
    if path.endswith('.json') or yaml is None:
        return json.loads(txt)
    return yaml.safe_load(txt)


def spec_hash(spec):
    core = {k: spec.get(k) for k in ('signals', 'rules', 'rebalance', 'cost', 'delay')}
    if spec.get('band'):  # band changes the weights; added only when set so older hashes stay the same
        core['band'] = spec.get('band')
    return hashlib.sha256(json.dumps(core, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


MIN_DELAY = 2          # engine delay 2 = decide at close t, trade at close t+1 (delay < 2 would fill at or before the decision close)
MIN_COST = 0.003       # 0.25% fee + 0.05% spread; a spec may only raise it


def check_spec(spec):
    """Refuse spec settings that would let a back-test see or trade on information it could not have had.
    delay must be an integer >= MIN_DELAY; cost must be a finite number (it is clamped up to MIN_COST where used)."""
    d = spec.get('delay', MIN_DELAY)
    if isinstance(d, bool) or not isinstance(d, (int, float)) or not np.isfinite(d) or float(d) != int(d) \
            or int(d) < MIN_DELAY:
        raise ValueError(f'delay must be an integer >= {MIN_DELAY} (same-bar or earlier fills are look-ahead), not {d!r}')
    c = spec.get('cost', MIN_COST)
    if isinstance(c, bool) or not isinstance(c, (int, float)) or not np.isfinite(c):
        raise ValueError(f'cost must be a finite number, not {c!r}')
    return spec


def _win(n, f):
    """Window / lag argument: a plain integer >= 1. Zero or negative values (lag(x, -1), ret(x, -5)) read rows after
    the decision row, i.e. the future, and are refused."""
    if isinstance(n, (bool, np.bool_)) or not isinstance(n, (int, float, np.integer, np.floating)) \
            or not np.isfinite(n) or float(n) != int(n) or int(n) < 1:
        raise ValueError(f'{f}(): window / lag must be an integer >= 1, not {n!r} (n <= 0 would read future rows)')
    return int(n)


# ---- indicator library (all causal: every window / lag is checked to be an integer >= 1) ----
def _mk(F):
    P = lambda x: data.price_for_signal(F, x)
    lr = lambda x: np.log(P(x)).diff()
    def rsi(x, n=14):
        n = _win(n, 'rsi')
        d = P(x).diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
        dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
        return 100 - 100 / (1 + up / dn)
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
    }
    return fn


def _latch(on, off, idx):
    """State signal: True from a day `on` is true, False from a day `off` is true, else the previous state;
    starts False. NaN counts as false. If `on` and `off` are both true on the same day, `off` wins (lab choice:
    the risk-reducing side). Causal: day t only reads on/off at t and the state at t-1."""
    def b(x):
        if isinstance(x, pd.Series):
            return x.reindex(idx).fillna(False).astype(bool).values
        return np.full(len(idx), bool(x))
    ev = np.where(b(off), 0.0, np.where(b(on), 1.0, np.nan))
    return pd.Series(ev, index=idx).ffill().fillna(0.0).astype(bool)


_OK = (ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare, ast.Call, ast.Name, ast.Load,
       ast.Constant, ast.And, ast.Or, ast.Not, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub,
       ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.Eq, ast.NotEq, ast.BitAnd, ast.BitOr, ast.Invert, ast.Mod)


class _Bool(ast.NodeTransformer):
    """and/or/not -> & | ~ so they work element-wise on Series; chained a<b<c -> (a<b)&(b<c)."""
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


def _eval(expr, env, assets):
    if isinstance(expr, (int, float)):
        return float(expr)
    tree = ast.parse(str(expr), mode='eval')
    for node in ast.walk(tree):
        if not isinstance(node, _OK):
            raise ValueError(f'not allowed in expression: {type(node).__name__} in {expr!r}')
        if isinstance(node, ast.Name) and node.id.startswith('__'):
            raise ValueError(f'bad name {node.id!r}')
    tree = ast.fix_missing_locations(_Bool().visit(tree))
    # bare asset names (TQQQ, _NDX given as strings) -> string constants
    scope = dict(env)
    for a in assets:
        scope.setdefault(a, a)
    return eval(compile(tree, '<spec>', 'eval'), {'__builtins__': {}}, scope)


def compile_weights(spec, F, sleeves):
    fn = _mk(F)
    assets = set(F.columns) | set(sleeves) | set(data.SLEEVES)
    env = dict(fn)
    for name, expr in (spec.get('signals') or {}).items():
        v = _eval(expr, env, assets)
        env[name] = v
    idx = F.index
    cols = sorted({a for r in spec['rules'] for a in (r.get('hold') or r.get('else') or {})} | {'CASH'})
    # rule assembly on numpy arrays (same values as the pandas .loc version, ~3x faster per path)
    n = len(idx); ci = {c: i for i, c in enumerate(cols)}
    Wv = np.zeros((n, len(cols)))
    taken = np.zeros(n, bool)
    for r in spec['rules']:
        if 'else' in r:
            cond, hold = np.ones(n, bool), r['else']
        else:
            c = _eval(r['when'], env, assets)
            if isinstance(c, pd.Series):
                cond = c.reindex(idx).fillna(False).astype(bool).values
            else:
                cond = np.full(n, bool(c))
            hold = r['hold']
        m = cond & ~taken
        for a, w in hold.items():
            wv = _eval(w, env, assets)
            wv = (wv.reindex(idx).values.astype(float) if isinstance(wv, pd.Series)
                  else np.full(n, float(wv)))
            x = np.clip(wv[m], 0, 1)
            Wv[m, ci[a]] = np.where(np.isnan(x), 0.0, x)
        taken |= m
    W = pd.DataFrame(Wv, index=idx, columns=cols)
    risk = [c for c in cols if c != 'CASH']
    tot = W[risk].sum(1)
    over = tot > 1
    W.loc[over, risk] = W.loc[over, risk].div(tot[over], axis=0)
    W['CASH'] = 1 - W[risk].sum(1)
    reb = spec.get('rebalance', 'daily')
    if reb in ('weekly', 'monthly'):
        per = idx.to_period('W' if reb == 'weekly' else 'M')
        last = pd.Series(idx, index=idx).groupby(per).transform('max') == pd.Series(idx, index=idx)
        W = W.loc[last.values].reindex(idx).ffill()
        W['CASH'] = W['CASH'].fillna(1.0); W = W.fillna(0.0)
    band = float(spec.get('band', 0))
    if band > 0:  # only move when some weight changes by >= band
        W = pd.DataFrame(_band(W.values, band), index=idx, columns=W.columns)
    return W


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
