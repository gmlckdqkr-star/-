# independent SPA / RW implementation (verifier), stationary bootstrap with explicit index draws
import numpy as np, time, sys
def sb_indices(T, B, L, seed):
    rng = np.random.default_rng(seed); p = 1.0/L
    I = np.empty((B, T), np.int64)
    start = rng.integers(0, T, size=(B, T)); newb = rng.random((B, T)) < p
    I[:, 0] = start[:, 0]
    for t in range(1, T):
        I[:, t] = np.where(newb[:, t], start[:, t], (I[:, t-1] + 1) % T)
    return I
def spa(D, B=1000, L=3.0, seed=7, chunk=20000):
    N, T = D.shape
    I = sb_indices(T, B, L, seed)
    W = np.zeros((B, T), np.float32)
    for b in range(B): W[b] = np.bincount(I[b], minlength=T)
    dbar = D.mean(1).astype(np.float64)
    # pass 1: bootstrap var of mean
    var = np.zeros(N)
    for i in range(0, N, chunk):
        Mb = (W @ D[i:i+chunk].T).astype(np.float64)/T
        var[i:i+chunk] = Mb.var(0)
    se = np.sqrt(var); ok = se > 1e-12
    t = np.where(ok, dbar/np.where(ok, se, 1), -np.inf)
    Tobs = max(0.0, t.max())
    thr = -se*np.sqrt(2*np.log(np.log(T)))
    mu_c = np.where(dbar < thr, dbar, 0.0)     # Hansen: keep very poor models' negative mean
    mu_l = np.minimum(dbar, 0.0)
    Tc = np.full(B, -np.inf); Tl = Tc.copy(); Tu = Tc.copy()
    for i in range(0, N, chunk):
        Mb = (W @ D[i:i+chunk].T).astype(np.float64)/T
        s = se[i:i+chunk]; o = ok[i:i+chunk]
        Zc = (Mb - dbar[i:i+chunk])                  # centered
        inv = np.where(o, 1/np.where(o, s, 1), 0)
        Tu = np.maximum(Tu, (Zc*inv).max(1))
        Tc = np.maximum(Tc, ((Zc + mu_c[i:i+chunk])*inv).max(1))
        Tl = np.maximum(Tl, ((Zc + mu_l[i:i+chunk])*inv).max(1))
    Tc, Tl, Tu = [np.maximum(x, 0) for x in (Tc, Tl, Tu)]
    return dict(Tobs=float(Tobs), p_c=float((Tc >= Tobs).mean()), p_l=float((Tl >= Tobs).mean()), p_u=float((Tu >= Tobs).mean()),
                q50=float(np.median(Tu)), q95=float(np.quantile(Tu, .95)), argmax=int(np.argmax(t))), t, Tu
if __name__ == '__main__':
    W1 = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m1/cache/'
    D = np.load(W1+'D.npy', mmap_mode='r'); keep = np.load(W1+'keep.npy')
    t0 = time.time(); Dk = np.ascontiguousarray(D[keep]); print('loaded', Dk.shape, time.time()-t0, flush=True)
    res, t, Tu = spa(Dk)
    print(res, time.time()-t0, flush=True)
    np.save('t_mine.npy', t)
    # activity: nonzero months per rule
    nz = (Dk != 0).sum(1)
    np.save('nz.npy', nz)
    print('nonzero months quantiles', np.quantile(nz, [0, .01, .05, .1, .25, .5, .75, .9]), flush=True)
