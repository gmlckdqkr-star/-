"""Design helpers for lane L3 (synthetic data only). Caches simulator output on local scratch disk."""
import os, sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); import exec_engine as ee
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L3'); import sim
CACHE = '/tmp/claude-0/-home-user--/3909d02b-a58d-53ad-b2bb-fea9997a6f67/scratchpad/l3cache'
T = 300 + 30 * 252


def get(seed, mech, P=1000, prior='base'):
    f = os.path.join(CACHE, f's{seed}_{int(mech)}_{P}_{prior}.npz')
    if os.path.exists(f):
        z = np.load(f); return z['r'], z['rf']
    d = sim.simulate(P, T, seed, mech, prior)
    np.savez(f, r=d['r'], rf=d['rf'])
    return d['r'], d['rf']


def close_from(r):
    return np.cumprod(1 + r, axis=1) * 100.0


def ewm(x, hl):
    """causal EWMA along axis 1 (numpy loop over time)."""
    a = 1 - 0.5 ** (1 / hl)
    out = np.empty_like(x); m = x[:, 0].copy()
    for t in range(x.shape[1]):
        m = m + a * (x[:, t] - m); out[:, t] = m
    return out


def fix(res):
    """a daily index loss beyond -1/3 (possible only in the OFF world's story-switch jumps) drives the 3x product
    negative and the engine returns NaN for that path; count such a path as a wipe-out (CAGR -100%, MDD -100%)."""
    bad = ~np.isfinite(res['cagr'])
    if bad.any():
        res = dict(res); res['cagr'] = np.where(bad, -1.0, res['cagr']); res['mdd'] = np.where(bad, -1.0, res['mdd'])
        res['final'] = np.where(bad, 0.0, res['final'])
    return res


def evaluate(r, rf, B, **kw):
    with np.errstate(all='ignore'):
        return ee.summary(fix(ee.run(r, rf, B, **kw)))


def hold(r, rf, L):
    with np.errstate(all='ignore'):
        return ee.summary(fix(ee.hold(r, rf, L)))
