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
    return hashlib.sha256(json.dumps(core, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


# ---- indicator library (all causal) ----
def _mk(F):
    P = lambda x: data.price_for_signal(F, x)
    lr = lambda x: np.log(P(x)).diff()
    def rsi(x, n=14):
        d = P(x).diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
        dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
        return 100 - 100 / (1 + up / dn)
    fn = {
        'price': lambda x: P(x),
        'sma': lambda x, n: P(x).rolling(int(n), min_periods=int(n)).mean(),
        'ema': lambda x, n: P(x).ewm(span=int(n), adjust=False, min_periods=int(n)).mean(),
        'ret': lambda x, n: P(x) / P(x).shift(int(n)) - 1,
        'vol': lambda x, n: lr(x).rolling(int(n), min_periods=int(n)).std() * np.sqrt(252),
        'high': lambda x, n: P(x).rolling(int(n), min_periods=1).max(),
        'low': lambda x, n: P(x).rolling(int(n), min_periods=1).min(),
        'dd': lambda x, n: P(x) / P(x).rolling(int(n), min_periods=1).max() - 1,
        'rsi': rsi,
        'month': lambda: pd.Series(F.index.month, index=F.index),
        'weekday': lambda: pd.Series(F.index.weekday, index=F.index),
        'min': lambda a, b: np.minimum(a, b),
        'max': lambda a, b: np.maximum(a, b),
        'abs': lambda a: np.abs(a),
        'lag': lambda s, n=1: s.shift(int(n)),
    }
    return fn


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
    W = pd.DataFrame(0.0, index=idx, columns=cols)
    taken = pd.Series(False, index=idx)
    for r in spec['rules']:
        if 'else' in r:
            cond, hold = pd.Series(True, index=idx), r['else']
        else:
            c = _eval(r['when'], env, assets)
            cond = (c if isinstance(c, pd.Series) else pd.Series(bool(c), index=idx)).reindex(idx)
            cond = cond.fillna(False).astype(bool); hold = r['hold']
        m = cond & ~taken
        for a, w in hold.items():
            wv = _eval(w, env, assets)
            wv = wv.reindex(idx) if isinstance(wv, pd.Series) else pd.Series(wv, index=idx)
            W.loc[m, a] = wv[m].clip(0, 1).fillna(0.0)
        taken |= m
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
        Wv = W.values.copy()
        for i in range(1, len(Wv)):
            if np.abs(Wv[i] - Wv[i - 1]).max() < band:
                Wv[i] = Wv[i - 1]
        W = pd.DataFrame(Wv, index=idx, columns=W.columns)
    return W
