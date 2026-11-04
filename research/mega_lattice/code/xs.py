"""Follow-up of the only signal above all 20 nulls: cross-market ranking (xs_F). Diagnostic + standalone Sharpe vs G1 bar 1.1.
Local-currency index returns (FX not modelled -> upper bound for a USD country-ETF version). <=2014 only."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/mega_lattice/code')
import ml
from scipy.stats import rankdata
MK = ['DJ', 'FTSE', 'DAX', 'CAC', 'SMI', 'EURSTOXX', 'NIKKEI', 'HSI', 'SSEC', 'CSI', 'NDX', 'SPX']
rows, edges, subs, off, ncell = ml.build()
lat = ml.Lattice(rows, edges, subs, off, ncell)
R = {r['name']: r for r in lat.R}
mu, y, mom, px = {}, {}, {}, {}
for k in MK:
    df = lat.predict(R[k], 'F', ymin=1986)
    mu[k] = df['mu']; y[k] = df['y']; mom[k] = R[k]['D']['z252'].set_axis(R[k]['dates']); px[k] = R[k]['price']
MU = pd.DataFrame(mu).ffill(limit=3); Y = pd.DataFrame(y).ffill(limit=3); MO = pd.DataFrame(mom).ffill(limit=3)
P = pd.DataFrame(px).ffill(limit=3)
d = MU.index[(MU.index >= '1991-01-01') & (MU.index <= '2014-11-01')][::21]
ic, pic, icm = [], [], []
for t in d:
    m = MU.loc[t].notna() & Y.loc[t].notna() & MO.loc[t].notna()
    if m.sum() < 6:
        continue
    a, b, c = rankdata(MU.loc[t][m]), rankdata(Y.loc[t][m]), rankdata(MO.loc[t][m])
    ic.append(np.corrcoef(a, b)[0, 1]); icm.append(np.corrcoef(c, b)[0, 1])
    X = np.c_[np.ones(len(c)), c]
    ra = a - X @ np.linalg.lstsq(X, a, rcond=None)[0]; rb = b - X @ np.linalg.lstsq(X, b, rcond=None)[0]
    pic.append(np.corrcoef(ra, rb)[0, 1] if ra.std() > 0 else 0)
st = lambda v: dict(mean=float(np.mean(v)), t=float(np.mean(v) / np.std(v) * len(v) ** .5), n=len(v))
out = dict(xs_ic=st(ic), xs_ic_mom12=st(icm), xs_pic_given_mom=st(pic))
# rotation: decide at close t, hold t+3..t+23 (same as label), top-k, 0.3%/side on changed weight
rf = ml.rf_daily()
def rot(score, k):
    rets, w_prev = [], pd.Series(0.0, index=MK)
    for t in d:
        s = score.loc[t]; yy = Y.loc[t]; m = s.notna() & yy.notna()
        if m.sum() < 6:
            continue
        top = s[m].sort_values(ascending=False).index[:k]
        w = pd.Series(0.0, index=MK); w[top] = 1.0 / len(top)
        cost = 0.003 * (w - w_prev).abs().sum(); w_prev = w
        rets.append(float(np.log((w[m] * np.exp(yy[m])).sum()) - cost))   # excess log return per 21d block
    r = np.array(rets)
    return dict(sharpe=float(r.mean() / r.std() * (12) ** .5), excess_ann=float(r.mean() * 12), n=len(r))
ew = MU.copy() * 0 + 1
for k in (1, 3, 6):
    out['lattice_top%d' % k] = rot(MU, k); out['mom12_top%d' % k] = rot(MO, k)
out['equal_weight_all'] = rot(ew.where(MU.notna()), 12)
json.dump(out, open('/mnt/project-files/research/mega_lattice/results/xs_follow.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
