"""Stage 1 information check (PRECOMMIT_ML.md sec 5.1). usage: python3 info.py [real|null N]"""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/mega_lattice/code')
import ml
from scipy.stats import rankdata
OUT = '/mnt/project-files/research/mega_lattice/results/'


def pic(mu, y, trend):
    a = rankdata(mu); b = rankdata(y); X = np.c_[np.ones(len(a)), trend]
    ra = a - X @ np.linalg.lstsq(X, a, rcond=None)[0]; rb = b - X @ np.linalg.lstsq(X, b, rcond=None)[0]
    return float(np.corrcoef(ra, rb)[0, 1]), float(np.corrcoef(a, b)[0, 1])


def blocks(df, a, b):
    d = df[(df.index >= a) & (df.index <= b)].dropna(subset=['mu', 'y'])
    return d.iloc[::21]


def evaluate(lat, rows, tag):
    R = {r['name']: r for r in lat.R}
    res = {}
    pr = {}
    for key, mk, mode, a, b in [('ndx_F', 'NDX', 'F', '1986-01-01', '2014-12-31'),
                                ('ndx_E', 'NDX', 'E', '1986-01-01', '2014-12-31'),
                                ('spx_E', 'SPX', 'E', '1955-01-01', '1985-12-31')]:
        r = R[mk]; df = lat.predict(r, mode)
        p = r['price']; trend = (p > p.rolling(200).mean()).astype(float)
        df['trend'] = trend.reindex(df.index).values
        bl = blocks(df, a, b)
        pc, ic = pic(bl['mu'].values, bl['y'].values, bl['trend'].values)
        res[key] = dict(ic=ic, pic=pc, n=len(bl), mu_sd=float(bl['mu'].std()), S_sd=float(bl['S'].std()))
        pr[key] = df
    # cross-market diagnostic: foreign + DJ 1990-2014 with F tables, pooled blocks
    xs = []
    for mk in ['DJ', 'FTSE', 'DAX', 'CAC', 'SMI', 'EURSTOXX', 'NIKKEI', 'HSI', 'SSEC', 'CSI']:
        df = lat.predict(R[mk], 'F'); xs.append(blocks(df, '1986-01-01', '2014-12-31'))
    X = pd.concat(xs)
    res['world_F'] = dict(ic=float(np.corrcoef(rankdata(X['mu']), rankdata(X['y']))[0, 1]), n=len(X))
    # cross-sectional IC (diagnostic, added before nulls): same calendar dates, markets ranked against each other
    W = {}
    for mk in ['DJ', 'FTSE', 'DAX', 'CAC', 'SMI', 'EURSTOXX', 'NIKKEI', 'HSI', 'SSEC', 'CSI', 'NDX', 'SPX']:
        df = pr.get('ndx_F') if mk == 'NDX' else lat.predict(R[mk], 'F')
        W[mk] = df[['mu', 'y']]
    MU = pd.DataFrame({k: v['mu'] for k, v in W.items()}).ffill(limit=3)
    YY = pd.DataFrame({k: v['y'] for k, v in W.items()}).ffill(limit=3)
    MU = MU[(MU.index >= '1991-01-01') & (MU.index <= '2014-11-01')].iloc[::21]; YY = YY.reindex(MU.index)
    ics = []
    for d in MU.index:
        m = MU.loc[d].notna() & YY.loc[d].notna()
        if m.sum() >= 6:
            ics.append(np.corrcoef(rankdata(MU.loc[d][m]), rankdata(YY.loc[d][m]))[0, 1])
    ics = np.array(ics)
    res['xs_F'] = dict(ic=float(ics.mean()), t=float(ics.mean() / ics.std() * len(ics) ** .5), n=len(ics))
    res['tag'] = tag
    return res, pr


if __name__ == '__main__':
    t0 = time.time()
    rows, edges, subs, off, ncell = ml.build()
    print('build', round(time.time() - t0), 's, cells', ncell, flush=True)
    if sys.argv[1] == 'real':
        lat = ml.Lattice(rows, edges, subs, off, ncell)
        print('lattice', round(time.time() - t0), 's', flush=True)
        res, pr = evaluate(lat, rows, 'real')
        print(json.dumps(res, indent=1), flush=True)
        json.dump(res, open(OUT + 'info_real.json', 'w'), indent=1)
        for k, df in pr.items():
            df.to_csv(OUT + 'pred_%s.csv.gz' % k)
        cal = {int(k): v for k, v in lat._cal.items()}
        json.dump(cal, open(OUT + 'calib_real.json', 'w'), indent=1)
        # G1
        sys.path.insert(0, '/mnt/project-files/research/breakthrough/code'); import gate
        g = {}
        for k in ('ndx_F', 'ndx_E'):
            df = pr[k].dropna(subset=['mu'])
            sig = pd.concat([(pr['spx_E'].dropna(subset=['mu']).eval('mu > mu_med')), (df.mu > df.mu_med)])
            sig = sig[~sig.index.duplicated(keep='last')].sort_index()
            g[k] = gate.test(sig, trials=3, name='ML_' + k, verbose=False)
        json.dump(g, open(OUT + 'g1_real.json', 'w'), indent=1, default=str)
        print(json.dumps(g, indent=1, default=str))
        print('done', round(time.time() - t0), 's')
    else:
        k = int(sys.argv[2]); shifts = np.linspace(1500, 5000, 20).astype(int)
        lat = ml.Lattice(rows, edges, subs, off, ncell, shift=int(shifts[k]))
        res, _ = evaluate(lat, rows, 'null_shift_%d' % shifts[k])
        json.dump(res, open(OUT + 'null_%02d.json' % k, 'w'), indent=1)
        print(k, shifts[k], json.dumps({kk: v for kk, v in res.items() if kk != 'tag'}), round(time.time() - t0), 's', flush=True)
