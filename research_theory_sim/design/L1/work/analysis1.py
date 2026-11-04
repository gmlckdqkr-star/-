import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1/work')
import sim
from feat import feats, fwd_sum
np.seterr(all='ignore')
P, T = 1000, 7860
for mech in (True, False):
    s = sim.simulate(P, T, seed=1, mechanism=mech)
    r, rf = s['r'], s['rf']
    F = feats(r, rf)
    ex = F['lr'] - rf            # daily excess log return
    H = 63
    f_ex = fwd_sum(ex, H)[:, 2:]  # forward from t+2.. (delay)
    f_v = fwd_sum(F['lr'] ** 2, H)[:, 2:]
    sl = slice(300, T - H - 2)
    def table(name, x, qs=(0, 10, 25, 50, 75, 90, 100)):
        xv = x[:, :T-2][:, sl]; fe = f_ex[:, sl]; fv = f_v[:, sl]
        # normalise per path to rank within path? use pooled quantiles
        edges = np.nanpercentile(xv, qs)
        print(f'  {name}: bucket edges', np.round(edges, 3))
        for i in range(len(edges) - 1):
            m = (xv >= edges[i]) & (xv <= edges[i + 1]) & np.isfinite(fe)
            mu = np.mean(fe[m]) * 252 / H; var = np.mean(fv[m]) * 252 / H
            print(f'    q{qs[i]:>3}-{qs[i+1]:<3} ann ex {mu:+.3f}  ann vol {np.sqrt(var):.3f}  kelly {mu/var:+.2f}')
    print('=== mechanism', mech)
    table('sig (20d vol)', F['sig'])
    table('gap M/sig (hl 252)', F['gap'])
    table('drawdown', F['dd'])
    table('trend lp-ema200', F['tr'])
    # rf change over 126 days
    drf = np.full_like(rf, np.nan); drf[:, 126:] = (rf[:, 126:] - rf[:, :-126]) * 252
    table('rf change 126d', drf)
