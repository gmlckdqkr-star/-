"""TS1 verifier, check 3: causality by FUTURE PERTURBATION (not truncation), <=2014 data only.
On the real NDX path std.contexts()['real_ndx_86_14'] (and a few cuts on dev250_path, 500 paths):
for each cut t, replace close/rf after t with a random continuation (3 kinds: plausible random walk, wild jumps,
garbage with NaN / 0 / negative closes and NaN rf) and require B_pert[:, :t+1] == B_full[:, :t+1] bit for bit.
Also: perturbing one path must not change any other path (no cross-path leakage). Same array length T always."""
import sys, json, importlib.util, numpy as np
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std  # noqa
TS = '/mnt/project-files/research/theory_sim/'


def load(L):
    p = TS + 'design/%s/rule.py' % L
    spec = importlib.util.spec_from_file_location('crule_' + L, p); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m); return m


def cont(g, lv, rf, t, kind):
    lv2, rf2 = lv.copy(), rf.copy(); P, T = lv.shape; n = T - t - 1
    if n <= 0: return lv2, rf2
    if kind == 0:
        ret = g.normal(0.0005, 0.015, (P, n)); r2 = g.uniform(0, 0.0004, (P, n))
    elif kind == 1:
        ret = g.normal(0, 0.08, (P, n)); ret[g.random((P, n)) < 0.02] = -0.5; r2 = g.uniform(-0.001, 0.01, (P, n))
    else:
        ret = g.normal(0, 0.03, (P, n)); r2 = g.uniform(0, 0.001, (P, n)); r2[g.random((P, n)) < 0.1] = np.nan
    lv2[:, t + 1:] = lv[:, t:t + 1] * np.cumprod(1 + np.maximum(ret, -0.95), axis=1)
    if kind == 2:
        m = g.random((P, n)); x = lv2[:, t + 1:]
        x[m < 0.05] = np.nan; x[(m >= 0.05) & (m < 0.08)] = 0.0; x[(m >= 0.08) & (m < 0.10)] = -1.0
    rf2[:, t + 1:] = r2
    return lv2, rf2


def same(a, b): return bool(np.array_equal(a, b, equal_nan=True))


def main():
    C = std.contexts(); c = C['real_ndx_86_14']; d = C['dev250_path']
    lv, rf = np.array(c.lvl, dtype=np.float64), np.array(c.rf, dtype=np.float64); T = lv.shape[1]
    g = np.random.default_rng(20261104)
    cuts = sorted(set(g.integers(0, T - 1, 150).tolist() + [0, 1, 2, 19, 20, 21, 41, 42, 59, 60, 61, 119, 120, 125, 126, 127,
                                                             236, 237, 238, 251, 252, 253, 299, 300, 301, 302, T - 3, T - 2]))
    out = {}
    for L in ('L1', 'L2', 'L3'):
        rule = load(L)
        full = np.asarray(rule.target_levels(lv.copy(), rf.copy()), dtype=np.float64)
        full2 = np.asarray(rule.target_levels(lv.copy(), rf.copy()), dtype=np.float64)
        bad = []; nchk = 0; changed_future = 0
        for t in cuts:
            for kind in (0, 1, 2):
                lv2, rf2 = cont(g, lv, rf, t, kind)
                B = np.asarray(rule.target_levels(lv2, rf2), dtype=np.float64); nchk += 1
                if not same(B[:, :t + 1], full[:, :t + 1]): bad.append((int(t), kind))
                if not same(B[:, t + 1:], full[:, t + 1:]): changed_future += 1
        # multi-path: dev250_path, 8 cuts, perturb the future of ALL paths; then perturb only path 7 (whole path after t)
        dl, dr = np.array(d.lvl, dtype=np.float64), np.array(d.rf, dtype=np.float64); Td = dl.shape[1]
        fd = np.asarray(rule.target_levels(dl.copy(), dr.copy()), dtype=np.float64)
        bad_mp = []; leak = []
        for t in sorted(set(g.integers(0, Td - 1, 6).tolist() + [299, 300])):
            dl2, dr2 = cont(g, dl, dr, t, 1)
            B = np.asarray(rule.target_levels(dl2, dr2), dtype=np.float64)
            if not same(B[:, :t + 1], fd[:, :t + 1]): bad_mp.append(int(t))
            dl3, dr3 = dl.copy(), dr.copy(); dl3[7, t + 1:] = dl2[7, t + 1:]; dr3[7, t + 1:] = dr2[7, t + 1:]
            B3 = np.asarray(rule.target_levels(dl3, dr3), dtype=np.float64)
            others = np.r_[0:7, 8:dl.shape[0]]
            if not same(B3[others], fd[others]) or not same(B3[7, :t + 1], fd[7, :t + 1]): leak.append(int(t))
        out[L] = dict(deterministic=same(full, full2), cuts=len(cuts), checks=nchk, violations=len(bad), first_bad=bad[:10],
                      future_changed_share=changed_future / nchk, multipath_cuts_bad=bad_mp, crosspath_leak=leak)
        print(L, out[L], flush=True)
    json.dump(out, open(TS + 'verify/v3_causal.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
