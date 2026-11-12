"""Independent pandas re-check of the ACTUAL window (no engine, no tax) + SVX standalone diagnostics -> results/check_le2014.json"""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vxrun as R, uprun as U, updata as UD, vxdata as VX
bn = 'real_ndx_86_14'; out = {}
c = U.basis(bn)['c']; dates, X = UD.basis_dates()[bn]; d = dates[c.ii[0, R.WARM:]]
L = pd.Series(U.s085_levels(bn, 2)[0], index=d)
rs, V, spx, act, idx = R.svx_bydate(bn)
S = pd.Series(rs, index=idx).reindex(d); rN = X['r'].reindex(d); rf = X['rf'].reindex(d)
tq = 3 * rN - 2 * rf - 0.0245 / 252
# gates by date (real path = by date), delay 2
Vs = pd.Series(V, index=idx).reindex(d); sp = pd.Series(spx, index=idx).reindex(d)
G = {'G0': pd.Series(1.0, index=d), 'G1': (Vs > sp.rolling(10).std() * np.sqrt(252) * 100).astype(float),
     'G2': (Vs < Vs.rolling(252, min_periods=126).mean()).astype(float)}
G = {k: v.shift(2).fillna(0) for k, v in G.items()}
first = pd.Timestamp(R.calib()['first'])
w = (d >= first)
def acct(s, g):
    """two sleeves, quarterly rebalance (every 63 rows from window start), 0.3% per side on traded value, no tax"""
    dd = d[w]; lv = L[w].values; gg = G[g][w].values if g else np.zeros(w.sum()); a1 = 1 - s; a2 = s
    e = 1.0; x1 = (1 - s); x2 = s; lv0 = None; g0 = None; curve = []
    for k in range(len(dd)):
        if k > 0:
            x1 = x1 * (1 + (lv[k - 1] / 3) * tq[dd[k]]) if True else x1
            x2 = x2 * (1 + (g0 or 0) * S[dd[k]])
        # v1 internal level change cost
        if lv0 is not None and lv[k] != lv0: x1 -= 0.003 * abs(lv[k] - lv0) / 3 * x1
        if g is not None and g0 is not None and gg[k] != g0: x2 -= 0.003 * x2
        lv0 = lv[k]; g0 = gg[k] if g else 0.0
        if s > 0 and k > 0 and k % 63 == 0:
            E = x1 + x2; tr = abs(x2 - s * E); E -= 0.003 * 2 * tr; x1 = (1 - s) * E; x2 = s * E
        curve.append(x1 + x2)
    C = np.array(curve); yrs = (len(C) - 1) / 252
    return float(C[-1] ** (1 / yrs) - 1), float((C / np.maximum.accumulate(C) - 1).min())
v1 = acct(0.0, None); out['pandas_v1_act_pretax'] = v1
for g in ('G0', 'G1', 'G2'):
    for s in (0.1, 0.2):
        a = acct(s, g); out['pandas_%s_s%02d' % (g, int(s * 100))] = dict(cagr=a[0], mdd=a[1], d=a[0] - v1[0])
# SVX standalone (by date, ACTUAL window): G0 and G1 gated (cash 0), yearly returns and MDD
for g in ('G0', 'G1', 'G2'):
    r = (S[w] * G[g][w]).fillna(0); ix = (1 + r).cumprod()
    yr = ix.resample('YE').last(); yr = pd.concat([pd.Series([1.0], index=[ix.index[0] - pd.Timedelta(days=1)]), yr]).pct_change().dropna()
    out['svx_' + g] = dict(cagr=float(ix.iloc[-1] ** (252 / len(ix)) - 1), mdd=float((ix / ix.cummax() - 1).min()),
                           years={str(k.year): round(float(v), 3) for k, v in yr.items()}, on_share=float(G[g][w].mean()))
# synthetic diagnostics (1986-2003): worst SVX days and 1987-10
Sx = pd.Series(rs, index=idx); syn = Sx[(~pd.Series(act, index=idx)) & (Sx.index >= '1986-01-01')]
out['synth_worst5'] = {str(k.date()): round(float(v), 3) for k, v in syn.nsmallest(5).items()}
out['actual_worst5'] = {str(k.date()): round(float(v), 3) for k, v in Sx[pd.Series(act, index=idx)].nsmallest(5).items()}
out['synth_mean_ann'] = float(syn.mean() * 252); out['actual_mean_ann'] = float(Sx[pd.Series(act, index=idx)].mean() * 252)
json.dump(out, open('/mnt/project-files/research/vxr1/results/check_le2014.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
