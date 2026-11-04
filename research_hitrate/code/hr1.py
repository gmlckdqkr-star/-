"""HR1: average pairwise correlation / cross-sectional dispersion of S&P 500 PIT members -> NDX timing, G1 gate.
Pre-registration: research/hitrate/PRECOMMIT_HR1.md (24 trials). <=2014 only. Uses daily returns of members only.
Usage: python3 hr1.py <panel.npz (dates, adj, member) or the .npz.xz>"""
import sys, json, lzma, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code'); import gate

def load(p):
    z = np.load(lzma.open(p) if p.endswith('.xz') else p, allow_pickle=True)
    d = z['dates']; adj = z['adj'].astype(np.float64); T = len(d)
    mem = np.unpackbits(z['member'], axis=0)[:T].astype(bool)
    s = str(int(d[0]))
    idx = pd.to_datetime(d.astype(str), format='%Y%m%d') if len(s) == 8 else pd.to_datetime(d, unit='D')
    return idx, adj, mem

def features(idx, adj, mem, step=5):
    T, N = adj.shape
    r = np.full_like(adj, np.nan); r[1:] = adj[1:] / adj[:-1] - 1
    r[~np.isfinite(r)] = np.nan
    out = {k: np.full(T, np.nan) for k in ('C63', 'C21', 'D21')}
    for t in range(300, T, step):
        m = mem[t]
        for w, key in ((63, 'C63'), (21, 'C21')):
            R = r[t - w + 1:t + 1][:, m]
            ok = np.isfinite(R).all(0); R = R[:, ok]; n = R.shape[1]
            if n < 50: continue
            sd = R.std(0); keep = sd > 0; R = R[:, keep]; n = R.shape[1]
            Z = (R - R.mean(0)) / R.std(0)
            v = Z.mean(1).var()
            out[key][t] = (n * v - 1) / (n - 1)
        R = r[t - 20:t + 1][:, m]; ok = np.isfinite(R).all(0)
        if ok.sum() >= 50:
            cr = np.prod(1 + R[:, ok], 0) - 1; out['D21'][t] = np.std(cr)
    F = pd.DataFrame(out, index=idx).ffill()
    F['DC'] = F['C21'] - F['C21'].rolling(252, min_periods=200).mean()
    return F

def exp_pct(x, warm=504):
    """causal expanding percentile of x_t among x_0..x_t (computed on weekly-sampled values)."""
    v = x.values; o = np.full(len(v), np.nan); hist = []
    import bisect
    for i, a in enumerate(v):
        if np.isnan(a): continue
        bisect.insort(hist, a)
        if len(hist) >= warm // 5: o[i] = bisect.bisect_left(hist, a) / len(hist)
    return pd.Series(o, index=x.index).ffill()

if __name__ == '__main__':
    idx, adj, mem = load(sys.argv[1])
    F = features(idx, adj, mem)
    Fw = F.iloc[::5]  # weekly sample for percentile history (values already causal)
    res = []
    for var in ('C63', 'C21', 'D21', 'DC'):
        P = exp_pct(Fw[var]).reindex(F.index, method='ffill')
        for q in (.10, .20, .30):
            for dr in ('+', '-'):
                cash = (P >= 1 - q) if dr == '+' else (P <= q)
                sig = (~cash).where(P.notna())
                sig = sig.dropna().astype(bool)
                g = gate.test(sig, trials=24, name=f'{var}{dr}q{int(q*100)}', verbose=False)
                row = dict(sig=f'{var}{dr}q{int(q*100)}', verdict=g['verdict'])
                for era in ('ndx_86_14', 'spx_55_85'):
                    e = g[era]
                    if e: row.update({f'{era}_hit': round(e['hit'], 4), f'{era}_defl': round(e['hit_deflated'], 4),
                                      f'{era}_alwaysup': round(e['always_up'], 4), f'{era}_n': e['n'],
                                      f'{era}_cashfrac': round(float(1 - sig.reindex(gate.labels()[era].index, method='ffill').dropna().mean()), 3)})
                res.append(row)
    df = pd.DataFrame(res); pd.set_option('display.width', 250); print(df.to_string(index=False))
    json.dump(res, open('/mnt/project-files/research/hitrate/results_hr1.json', 'w'), indent=1)
    F.loc[:'2014-12-31'].describe().to_csv('/tmp/hr1_feat_desc.csv')
    print('first valid', {k: str(F[k].first_valid_index())[:10] for k in F})
