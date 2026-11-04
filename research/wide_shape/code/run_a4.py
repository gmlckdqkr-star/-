"""WS1 A4: industry selection oracle (KF12 / KF49 VW daily, 1971-2014), top-1 industry per block at 1x or 3x.
3x = 3r - 2rf - 2.45%/252 - 1%/252 (KF returns include dividends -> extra 1%/yr haircut); 1x = r - 0.4%/252.
Cost 0.3%/side on switches; 22% yearly tax (all P&L treated as realized), deduction 0.25; final year taxed.
O2: with prob p the best industry of the block, else a random other industry. O1: rho on normal scores of ranks."""
import sys, json, time, zipfile, numpy as np, pandas as pd
from scipy.special import ndtri
RAW = '/mnt/project-files/research/broad_etf/data/raw/kf/'
END = pd.Timestamp('2014-12-31')


def kf(fn, section=0):
    z = zipfile.ZipFile(RAW + fn); txt = z.read(z.namelist()[0]).decode('latin1').splitlines()
    blocks, cur = [], None
    for ln in txt:
        p = [x.strip() for x in ln.split(',')]
        if len(p) > 1 and p[0] == '' and cur is None:
            cur = {'cols': p[1:], 'rows': []}; continue
        if cur is not None:
            if len(p) > 1 and p[0].isdigit() and len(p[0]) == 8:
                cur['rows'].append(p)
            else:
                blocks.append(cur); cur = None
    if cur:
        blocks.append(cur)
    b = blocks[section]
    df = pd.DataFrame([r[1:] for r in b['rows']], index=pd.to_datetime([r[0] for r in b['rows']]), columns=b['cols']).astype(float)
    df = df[(df.index <= END)]
    return df.where(df > -99.0) / 100.0


ff = kf('F-F_Research_Data_Factors_daily_CSV.zip')
rf_all = ff['RF']
out = {}
t0 = time.time()
for nm, fn in (('KF12', '12_Industry_Portfolios_daily_CSV.zip'), ('KF49', '49_Industry_Portfolios_daily_CSV.zip')):
    R = kf(fn)
    R = R[R.index >= pd.Timestamp('1970-07-01')]
    R = R.dropna(axis=1, how='any')                       # industries with full history in window
    rf = rf_all.reindex(R.index).fillna(0).values
    r = R.values; T, N = r.shape
    for L in (1, 3):
        prod = (3 * r - 2 * rf[:, None] - (0.0245 + 0.01) / 252) if L == 3 else (r - 0.004 / 252)
        for h in (1, 5, 21):
            t0i = int(np.searchsorted(R.index.values, np.datetime64('1971-01-01')))
            starts = np.arange(t0i, T - h, h)
            nb = len(starts)
            G = np.array([np.prod(1 + prod[s + 1:s + 1 + h], axis=0) - 1 for s in starts])   # [nb, N] block product return
            years = R.index[np.minimum(starts + h, T - 1)].year.values
            rk = np.argsort(np.argsort(G, axis=1), axis=1); z = ndtri((rk + 0.5) / N)
            best = np.argmax(G, axis=1)

            def perf(pick):
                E = 1.0; pnl = 0.0; cy = years[0]; prev = -1
                for b in range(nb):
                    if years[b] != cy:
                        E -= 0.22 * max(0.0, pnl - 0.25); pnl = 0.0; cy = years[b]
                    c = 0.0 if pick[b] == prev else (0.006 if prev >= 0 else 0.003)
                    d = E * ((1 - c) * (1 + G[b, pick[b]]) - 1); E += d; pnl += d; prev = pick[b]
                    if E < 1e-9:
                        E = 1e-9; break
                E -= 0.003 * E; E -= 0.22 * max(0.0, pnl - 0.25)
                return max(E, 1e-9) ** (252.0 / (nb * h)) - 1
            cellp = {}
            for p in (1.0 / N, .2, .3, .4, .5, .6, .7, .8, .9, 1.0):
                v = []
                for sd in range(10):
                    rng = np.random.default_rng(50 + sd)
                    other = (best + rng.integers(1, N, nb)) % N
                    pick = np.where(rng.random(nb) < p, best, other)
                    v.append(perf(pick))
                cellp['%.3f' % p] = float(np.median(v))
            cellr = {}
            for rho in (0, .05, .1, .15, .2, .3, .4, .6, 1.0):
                v = []
                for sd in range(10):
                    rng = np.random.default_rng(80 + sd)
                    s = rho * z + np.sqrt(max(0, 1 - rho * rho)) * rng.standard_normal(z.shape)
                    v.append(perf(np.argmax(s, axis=1)))
                cellr['%g' % rho] = float(np.median(v))
            key = '%s_L%d_h%d' % (nm, L, h)
            out[key] = {'N': N, 'O2_hit_best': cellp, 'O1_rho': cellr}
            print(key, 'N', N, 'O2', ' '.join('%s:%.2f' % kv for kv in cellp.items()), '| O1', ' '.join('%s:%.2f' % kv for kv in cellr.items()),
                  '%.0fs' % (time.time() - t0), flush=True)
json.dump(out, open('/mnt/project-files/research/wide_shape/results/a4_sector.json', 'w'), indent=1)
