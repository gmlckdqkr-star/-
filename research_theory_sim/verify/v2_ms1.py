"""TS1 verifier, check 2: independent MS1 re-measure via std.measure (<=2014 only).
make(ctx) -> (rule.target_levels(ctx.lvl, ctx.rf), std.ident, np.zeros(1), 0.5). Compares with test/out/real_L*.json.
Also: INPUTS / y10 usage (AST + behavioural), input mutation, NaN / range of outputs after warm-up on every basis.
Run: NUMBA_CACHE_DIR=<scratch> /root/.cache/ts-venv/bin/python -B v2_ms1.py L1 [L2 L3]"""
import sys, os, json, ast, hashlib, importlib.util, numpy as np
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std  # noqa
import ov  # noqa
TS = '/mnt/project-files/research/theory_sim/'


def load(L):
    p = TS + 'design/%s/rule.py' % L
    spec = importlib.util.spec_from_file_location('vrule_' + L, p); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m); return m, p


def y10_usage(path):
    src = open(path).read(); tree = ast.parse(src)
    names = [n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == 'y10']
    return dict(n_name_refs_y10=len(names), lines_with_y10=[i + 1 for i, l in enumerate(src.splitlines()) if 'y10' in l])


def h(a): return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()[:16]


def main(L):
    rule, path = load(L)
    print('==', L, path, 'INPUTS', getattr(rule, 'INPUTS', None), y10_usage(path), flush=True)
    stats = {}

    def make(c):
        lv0, rf0 = h(c.lvl), h(c.rf)
        B = rule.target_levels(c.lvl, c.rf)
        assert h(c.lvl) == lv0 and h(c.rf) == rf0, 'rule mutated its input'
        B = np.asarray(B, dtype=np.float64)
        assert B.shape == c.r.shape, (B.shape, c.r.shape)
        # behavioural y10 check: passing garbage y10 must not change anything
        g = np.random.default_rng(1).normal(5, 3, c.r.shape)
        B2 = np.asarray(rule.target_levels(c.lvl.copy(), c.rf.copy(), g), dtype=np.float64)
        same = bool(np.array_equal(B, B2, equal_nan=True))
        Bt = B[:, ov.WARM:]
        stats[len(stats)] = dict(P=c.P, T=c.T, y10_garbage_identical=same, nan_after_warm=int(np.isnan(Bt).sum()),
                                 nan_in_warm=int(np.isnan(B[:, :ov.WARM]).sum()), min=float(np.nanmin(Bt)), max=float(np.nanmax(Bt)),
                                 mean=float(np.nanmean(Bt)), share_le0=float(np.mean(np.nan_to_num(Bt) <= 0)))
        return B, std.ident, np.zeros(1), 0.5

    T = std.measure('verify_' + L, make)
    names = [k for k in std.contexts().keys()]
    st = {names[i]: v for i, v in stats.items()}
    R = json.load(open(TS + 'test/out/real_%s.json' % L))['base']
    cmp = {}
    for bn in names:
        mine, rep = T[bn], R[bn]
        cmp[bn] = {k: (mine[k], rep.get(k), abs(mine[k] - rep[k]) if rep.get(k) is not None else None) for k in mine}
        worst = max(v[2] for v in cmp[bn].values() if v[2] is not None)
        print('%s %-15s mine cagr=%.6f rep=%.6f |d|=%.2e  hold1x %.4f/%.4f s085 %.4f/%.4f  max|d| over all keys %.2e  %s' % (
            L, bn, mine['cagr'], rep['cagr'], abs(mine['cagr'] - rep['cagr']), mine['hold1x'], rep['hold1x'],
            mine['ref_s085'], rep['ref_s085'], worst, st[bn]), flush=True)
    ref = json.load(open('/mnt/project-files/research/measure_std/ref_s085.json'))
    for bn in names:
        print('locked s0.85 %s: locked %.6f  this run %.6f' % (bn, ref[bn]['cagr'], T[bn]['ref_s085']))
    json.dump(dict(rule=L, measure=T, compare=cmp, stats=st), open(TS + 'verify/v2_ms1_%s.json' % L, 'w'), indent=1, default=float)


if __name__ == '__main__':
    for L in sys.argv[1:]: main(L)
