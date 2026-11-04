# Information requirement: rho of a monthly signal with the forward 21d (t+3..t+23) 3x-vs-cash excess return
# -> MS1 after-tax CAGR (dev250_path headline, real NDX 86-14, real SPX 55-85). <=2014 only (std contexts).
import os, sys, json, numpy as np
os.environ['NUMBA_CACHE_DIR'] = os.path.abspath('nbc')
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
C = std.contexts()
def fwd_excess(c):
    r = c.r; rf = c.rf; P, T = r.shape
    x3 = np.log1p(3*r - 2*rf - 0.0245/252) - np.log1p((rf - 0.02/252)*(1-0.154))
    cs = np.concatenate([np.zeros((P,1)), np.cumsum(x3, axis=1)], axis=1)
    f = np.full((P, T), np.nan)
    t = np.arange(T); a = t + 3; b = t + 24  # sum of days t+3..t+23
    ok = b <= T
    f[:, ok] = cs[:, b[ok]] - cs[:, a[ok]]
    return f
def make_oracle(rho, seed):
    def make(c):
        f = fwd_excess(c); P, T = f.shape
        rng = np.random.default_rng(seed + 7919*int(rho*1000))
        mu = np.nanmean(f); sd = np.nanstd(f)
        B = np.zeros((P, T))
        for s0 in range(0, T, 21):
            z = (f[:, s0] - mu) / sd
            z = np.where(np.isnan(z), 0.0, z)
            s = rho*z + np.sqrt(1-rho**2)*rng.standard_normal(P)
            thr = -mu/(max(rho,1e-6)*sd) if rho > 0 else -np.inf  # rho=0 -> always in (mu>0)
            on = s > thr
            B[:, s0:s0+21] = np.where(on, 3.0, 0.0)[:, None]
        return B, std.ident, np.zeros(1), 0.5
    return make
def hitrate(c, B):
    f = fwd_excess(c); P, T = f.shape
    idx = np.arange(0, T-24, 21)
    lab = f[:, idx] > 0; on = B[:, idx] > 0
    return float(np.mean(lab == on)), float(np.mean(on))
out = {}
bases = ['dev250_path', 'real_ndx_86_14', 'real_spx_55_85']
for rho in [0.0, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6]:
    for seed in [1, 2, 3]:
        mk = make_oracle(rho, seed)
        for bn in bases:
            c = C[bn]; B, bf, bp, fs = mk(c)
            fin, E = std.engine(c, B, bf, bp, fs)
            r, _ = std.row(fin, E)
            h, inf = hitrate(c, B)
            out.setdefault('%.2f' % rho, {}).setdefault(bn, []).append(dict(cagr=r['cagr'], dd80=r.get('dd80'), hit=h, infrac=inf))
    row = out['%.2f' % rho]
    print('rho %.2f R2 %.3f | ' % (rho, rho**2) + ' | '.join('%s cagr %.3f hit %.3f in %.2f' % (bn, np.mean([x['cagr'] for x in row[bn]]), np.mean([x['hit'] for x in row[bn]]), np.mean([x['infrac'] for x in row[bn]])) for bn in bases), flush=True)
json.dump(out, open('rho_need.json', 'w'), indent=1)
