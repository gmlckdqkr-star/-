"""Verifier step 5 (check D): hy_struct.invvol_targets and the D2 spot check on real_ndx_86_14.
  (a) rerun D2 and the paired S085 through the module, compare stored cagr / d_pair;
  (b) own inverse-vol weights (np.std per window) and own in-force schedule vs the module's WW / A / Wd;
  (c) look-ahead perturbation of invvol_targets (monkeypatched sleeve returns scrambled after day j);
  (d) double-trade check: band check at k % 21 == 0 two days before the new target is traded at k + 2."""
import os, sys, json, time
os.environ['NUMBA_CACHE_DIR'] = '/tmp/claude-0/-home-user--/0e26f5bd-b937-55ae-81a7-0c4a9abb6560/scratchpad/verify/nbcache'
sys.path.insert(0, '/mnt/project-files/research/hybrid/code')
import numpy as np
import hy_struct as HS, hy_common as C, hyeng as H, ii

ST = json.load(open('/mnt/project-files/research/hybrid/results/struct_le2014.json'))
bn = sys.argv[1] if len(sys.argv) > 1 else 'real_ndx_86_14'
t0 = time.time()
# (a)
fref, Eref, _ = HS.run_kind(bn, 'S085')
fin, E, ex = HS.run_kind(bn, 'D2')
r = HS.row(bn, fin, E, fref)
st = ST['%s|D2' % bn]
print(bn, 'D2 rerun: cagr %.6f (stored %.6f)  d_pair %.6f (stored %.6f)  mdd %.4f (stored %.4f)  share_mean %.4f (stored %.4f)' % (
    r['cagr'], st['cagr'], r['d_pair'], st['d_pair'], r['mdd'], st['mdd'], ex['share_mean'], st['share_mean']))
print('   S085 paired ref cagr %.6f (stored %.6f)' % (float(np.median(H.cagr(fref, E.shape[1]))), ST['%s|S085' % bn]['cagr']))

# (b) own weights
R = C.sleeve_returns(bn, HS.D2N); P, T, M = R.shape
A0, Wd0, WW0 = HS.invvol_targets(bn)
fl = 0.05 / np.sqrt(252)
ks = list(range(0, T, 21)); WW = np.zeros((P, len(ks), M))
for i, k in enumerate(ks):
    if k < 21: WW[:, i] = 1.0 / M; continue
    win = R[:, max(k - 62, 1):k + 1, :]                       # returns of days k-62..k (day 0 carries no return)
    sd = np.std(win, axis=1, ddof=1); iv = 1 / np.maximum(sd, fl); WW[:, i] = iv / iv.sum(1, keepdims=True)
# in-force: weights decided at close k are traded at close k+2; the target array at day t holds the latest decision with k + 2 <= t
dec_day = np.array(ks) + 2; dec_day[0] = 0
idx_t = np.searchsorted(dec_day, np.arange(T), side='right') - 1
A1 = WW[:, idx_t, 0]; Wd1 = WW[:, idx_t, 1:]
print('   own weights vs module WW: max abs diff %.2e ; own in-force A vs module A %.2e ; Wd %.2e' % (
    np.max(np.abs(WW - WW0)), np.max(np.abs(A1 - A0)), np.max(np.abs(Wd1 - Wd0))))
print('   mean weights s085 / VPF4 / B10L3 = %.3f / %.3f / %.3f' % tuple(WW.mean((0, 1))))
# how much of the s0.85 weight comes from days where the sleeve sat in cash (vol floor)?
TQ, DEP, CU, _ = H.ref(bn)
cu_k = CU[:, ks]; hi = WW[:, :, 0] > 0.5
print('   blocks with s0.85 weight > 0.5: %.3f ; mean s0.85 weight when CU_k == 0: %.3f, when CU_k == 3: %.3f' % (
    hi.mean(), WW[:, :, 0][cu_k == 0].mean() if (cu_k == 0).any() else np.nan, WW[:, :, 0][cu_k == 3].mean() if (cu_k == 3).any() else np.nan))

# (c) perturbation of the module function (monkeypatch the data source)
orig = C.sleeve_returns
for j in [500, 2999, 5001]:
    rng = np.random.default_rng(j); R2 = R.copy(); R2[:, j + 1:, :] = rng.normal(0, 0.03, R2[:, j + 1:, :].shape)
    HS.C.sleeve_returns = lambda b, n, _R=R2: _R
    A2, Wd2, _ = HS.invvol_targets(bn)
    HS.C.sleeve_returns = orig
    print('   perturb after day %d: A[:j+3] unchanged %s, Wd[:j+3] unchanged %s, later A changed %s' % (
        j, np.array_equal(A0[:, :j + 3], A2[:, :j + 3]), np.array_equal(Wd0[:, :j + 3], Wd2[:, :j + 3]), not np.array_equal(A0, A2)))
print('   %.1f s' % (time.time() - t0))
