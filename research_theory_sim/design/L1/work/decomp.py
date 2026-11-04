import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1/work')
import sim
from feat import feats, fwd_sum
np.seterr(all='ignore')
P, T = 1000, 7860
cases = {'full': None, 'no_sentiment': dict(sigma_u=0.0), 'no_spec': dict(Phi=1e-6), 'no_extrap': dict(b_X=0.0),
         'spec_only': dict(sigma_u=0.0, b_X=0.0), 'no_ratchet(tauL~0)': dict(tau_L=0.004)}
H = 63
for name, ov in cases.items():
    s = sim.simulate(P, T, seed=1, override=ov, return_state=True)
    r, rf = s['r'], s['rf']
    F = feats(r, rf)
    ex = F['lr'] - rf
    f_ex = fwd_sum(ex, H)[:, 2:]
    sl = slice(300, T - H - 2)
    lr = F['lr'][:, 300:]
    vol = np.median(lr.std(axis=1) * np.sqrt(252))
    z = (lr - lr.mean(1, keepdims=True)) / lr.std(1, keepdims=True)
    kurt = np.median((z ** 4).mean(1) - 3); skew = np.median((z ** 3).mean(1))
    # within-path slope: regress fwd 63d excess on tr (demeaned per path)
    res = []
    for key in ('tr', 'gap', 'dd'):
        x = F[key][:, :T-2][:, sl]; y = f_ex[:, sl]
        x = x - np.nanmean(x, 1, keepdims=True); y = y - np.nanmean(y, 1, keepdims=True)
        b = np.nansum(x * y, 1) / np.nansum(x * x, 1)
        res.append(f'{key} slope(med) {np.median(b):+.3f}')
    cp = np.cumsum(lr, 1); mdd = np.expm1((cp - np.maximum.accumulate(cp, 1)).min(1))
    lev = s['state']['lev'][:, 300:].mean(1)
    print(f'{name:22s} vol {vol:.3f} skew {skew:+.2f} kurt {kurt:.2f} mddmed {np.median(mdd):+.2f} specLev {np.median(lev):.2f} | ' + ' | '.join(res))
