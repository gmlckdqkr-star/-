"""V1 check 5: causality of D (and A, B, C, L1 more lightly) by FUTURE PERTURBATION on real NDX <= 2014, plus truncation,
multi-path / cross-path on dev250_path, determinism, input mutation and y10 independence. Exact (bitwise, NaN-aware).
For a cut t, columns t+1.. of close / rf (and y10) are replaced by: other real data (S&P 1955-85 returns and T-bill),
the NDX path reversed, garbage (NaN / 0 / negative / inf / huge closes, NaN / negative / huge rf), a flat close with rf 0,
close-only and rf-only changes. B[:, :t+1] must be unchanged. <=2014 data only."""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/verify'); import V1_common as V  # noqa


def same(a, b): return bool(np.array_equal(a, b, equal_nan=True))


def cont(kind, lv, rf, t, g, spx):
    lv2, rf2 = lv.copy(), rf.copy(); P, T = lv.shape; n = T - t - 1
    if n <= 0: return lv2, rf2
    rs, rfs = spx
    if kind == 'spx':          # other real data: S&P 1955-85 daily returns and T-bill, spliced at the cut
        j = g.integers(0, len(rs) - n) if len(rs) > n else 0
        rr = np.resize(rs[j:j + n], n); ff = np.resize(rfs[j:j + n], n)
        lv2[:, t + 1:] = lv[:, t:t + 1] * np.cumprod(1 + rr)[None, :]; rf2[:, t + 1:] = ff[None, :]
    elif kind == 'reverse':    # the same market, time reversed after the cut
        r = lv[:, 1:] / lv[:, :-1] - 1; rr = r[:, ::-1][:, :n]
        lv2[:, t + 1:] = lv[:, t:t + 1] * np.cumprod(1 + rr, axis=1); rf2[:, t + 1:] = rf[:, ::-1][:, :n]
    elif kind == 'garbage':
        x = lv[:, t:t + 1] * np.cumprod(1 + g.normal(0, 0.1, (P, n)), axis=1); m = g.random((P, n))
        x[m < 0.05] = np.nan; x[(m >= 0.05) & (m < 0.08)] = 0.0; x[(m >= 0.08) & (m < 0.10)] = -3.0
        x[(m >= 0.10) & (m < 0.11)] = np.inf; x[(m >= 0.11) & (m < 0.12)] = 1e300
        lv2[:, t + 1:] = x
        f = g.uniform(-0.01, 0.05, (P, n)); m2 = g.random((P, n)); f[m2 < 0.1] = np.nan; f[(m2 >= 0.1) & (m2 < 0.12)] = 1e9
        rf2[:, t + 1:] = f
    elif kind == 'flat':
        lv2[:, t + 1:] = lv[:, t:t + 1]; rf2[:, t + 1:] = 0.0
    elif kind == 'close_only':
        lv2[:, t + 1:] = lv[:, t:t + 1] * np.cumprod(1 + g.normal(-0.002, 0.05, (P, n)), axis=1)
    elif kind == 'rf_only':
        rf2[:, t + 1:] = g.uniform(0.0, 0.002, (P, n))
    return lv2, rf2


KINDS = ('spx', 'reverse', 'garbage', 'flat', 'close_only', 'rf_only')


def check_rule(L, n_cut, g, spx, C, light=False):
    rule = V.load_rule(L); c = C['real_ndx_86_14']
    lv, rf = np.array(c.lvl, dtype=np.float64), np.array(c.rf, dtype=np.float64); T = lv.shape[1]
    lv0, rf0 = lv.copy(), rf.copy()
    full = V.targets(rule, lv, rf); det = same(full, V.targets(rule, lv, rf))
    mut = not (np.array_equal(lv0, lv) and np.array_equal(rf0, rf))
    yg = np.asarray(rule.target_levels(lv.copy(), rf.copy(), np.random.default_rng(9).normal(4, 4, lv.shape)), dtype=np.float64)
    special = [0, 1, 2, 19, 20, 21, 59, 60, 61, 249, 250, 251, 298, 299, 300, 301, 302, 303, 304, 551, 552, T - 3, T - 2]
    cuts = sorted(set(g.integers(0, T - 1, n_cut).tolist() + special))
    kinds = KINDS if not light else ('spx', 'garbage', 'flat')
    bad, n, chg = [], 0, 0
    for t in cuts:
        for kd in kinds:
            lv2, rf2 = cont(kd, lv, rf, t, g, spx); B = V.targets(rule, lv2, rf2); n += 1
            if not same(B[:, :t + 1], full[:, :t + 1]): bad.append((int(t), kd))
            if not same(B[:, t + 1:], full[:, t + 1:]): chg += 1
    # truncation: rule on columns 0..t only
    tbad = []
    for t in cuts[:: (1 if not light else 3)]:
        Bp = V.targets(rule, lv[:, :t + 1], rf[:, :t + 1])
        if not same(Bp, full[:, :t + 1]): tbad.append(int(t))
    o = dict(deterministic=det, input_mutated=mut, y10_garbage_identical=same(full, yg), cuts=len(cuts), perturbations=n,
             violations=len(bad), first_bad=bad[:10], future_changed_share=chg / max(n, 1), truncation_cuts=len(cuts[:: (1 if not light else 3)]),
             truncation_violations=len(tbad), first_trunc_bad=tbad[:10])
    if not light:   # multi-path and cross-path on dev250_path
        d = C['dev250_path']; dl, dr = np.array(d.lvl, dtype=np.float64), np.array(d.rf, dtype=np.float64); Td = dl.shape[1]
        fd = V.targets(rule, dl, dr); mp_bad, leak = [], []
        dcuts = sorted(set(g.integers(0, Td - 1, 8).tolist() + [298, 299, 300, 301]))
        for t in dcuts:
            dl2, dr2 = cont('garbage', dl, dr, t, g, spx); B = V.targets(rule, dl2, dr2)
            if not same(B[:, :t + 1], fd[:, :t + 1]): mp_bad.append(int(t))
            dl3, dr3 = dl.copy(), dr.copy(); dl3[7] = dl2[7]; dr3[7] = dr2[7]
            B3 = V.targets(rule, dl3, dr3); oth = np.r_[0:7, 8:dl.shape[0]]
            if not same(B3[oth], fd[oth]) or not same(B3[7, :t + 1], fd[7, :t + 1]): leak.append(int(t))
        # path order: permuting the paths must permute the output
        perm = np.random.default_rng(4).permutation(dl.shape[0]); Bp = V.targets(rule, dl[perm], dr[perm])
        o.update(multipath_cuts=len(dcuts), multipath_bad=mp_bad, crosspath_leak=leak, path_permutation_equivariant=same(Bp, fd[perm]))
    return o


def main(names):
    C = V.bases(); g = np.random.default_rng(20261105)
    cs = C['real_spx_55_85']; spx = (cs.r[0, 1:].copy(), cs.rf[0, 1:].copy())   # S&P 1954-85 (<=1985) returns / T-bill
    out = {}
    for L in names:
        t0 = time.time(); o = check_rule(L, 200 if L == 'D' else 60, g, spx, C, light=(L != 'D')); o['secs'] = round(time.time() - t0, 1)
        out[L] = o; print(L, json.dumps(o), flush=True)
    return out


if __name__ == '__main__':
    names = sys.argv[1:] or ['D', 'A', 'B', 'C', 'L1']
    p = V.dump(main(names), 'V1_causal.json'); print('wrote', p)
