"""JS1 driver. usage: js1_run.py DATA.npz OUTDIR cmd [args]   cmd: speed | full | rand_real N SEED | rand_placebo N SEED P0 P1 | confirm"""
import sys, os, time, json, numpy as np
sys.path.insert(0, '/home/user/repo/research_js1/code')
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/claude-0/nbc')
import js1_kern as K
NTH = 4
DES_FY = (1870, 1984)                                   # feature years of the design window (return years 1871..1985)

def placebo_tables(P, sh):
    """x outcomes rolled by sh feature years inside the design window (same shift for all countries = cross-country alignment kept), then packed
    exactly like js1_build.pack (per-country demeaning, weights)."""
    X = P['X'].copy(); yrs = P['years']; i0 = int(np.where(yrs == DES_FY[0])[0][0]); i1 = int(np.where(yrs == DES_FY[1])[0][0]) + 1
    X[:, :, i0:i1] = np.roll(X[:, :, i0:i1], sh, axis=2)
    sl = P['des_slot']; unit_rng = P['des_unit_rng']; units = P['des_units']; nb = P['des_valid'].shape[0]
    xs = np.zeros((3, nb))
    for (c, t, p) in sl: xs[:, p] = X[:, c, t]
    xd = np.zeros_like(xs); wu = np.zeros((3, len(units)))
    for ui, (a, b) in enumerate(unit_rng):
        s = slice(a * 64, b * 64); v = P['des_valid'][s]
        for m in range(3):
            xv = xs[m, s]; ok = v & ~np.isnan(xv); mu = xv[ok].mean() if ok.any() else 0.0
            d = np.where(ok, xv - mu, 0.0); xd[m, s] = d; n = int(v.sum()); wu[m, ui] = n / (n - 1) * float((d ** 2).sum())
    Q = dict(P); Q['des_xd'] = xd; Q['des_wu'] = wu; return Q

def merge(outs):
    topz = np.concatenate([o[0] for o in outs], axis=1); topc = np.concatenate([o[1] for o in outs], axis=1)
    cnt = sum(o[2] for o in outs); mx = np.max([o[3] for o in outs], axis=0)
    return topz, topc, cnt, mx

def new_state():
    return (np.full((3, K.KTOP), -1e300), np.zeros((3, K.KTOP), np.uint64), np.zeros((3, 5), np.int64), np.full(3, -1e300))

def run_full(P, pre='des'):
    b64, T, nf64, ur, wu, nu, ntot = K.prep(P, pre); nA = b64.shape[0]; outs = []; nd = [np.zeros(1, np.int64) for _ in range(NTH)]
    def f(i):
        st = new_state(); K.enum_worker(b64, T, nf64, ur, wu, nu, ntot, nA, i, NTH, 1, *st, nd[i]); return st
    return merge(K.run_threads(f, NTH)), sum(int(x[0]) for x in nd)

def run_rand(P, N, seed, pre='des'):
    b64, T, nf64, ur, wu, nu, ntot = K.prep(P, pre); nA = b64.shape[0]; nd = [np.zeros(1, np.int64) for _ in range(NTH)]
    def f(i):
        st = new_state(); K.rand_worker(b64, T, nf64, ur, wu, nu, ntot, nA, N // NTH, seed * 1000 + i, *st, nd[i]); return st
    return merge(K.run_threads(f, NTH)), sum(int(x[0]) for x in nd)

if __name__ == '__main__':
    data, out, cmd = sys.argv[1:4]; P = dict(np.load(data, allow_pickle=True)); os.makedirs(out, exist_ok=True)
    if cmd == 'speed':
        Q = placebo_tables(P, 50); t = time.time(); r, nd = run_rand(Q, 400000, 1); print('speed placebo-table rand 4e5 rules: %.1fs' % (time.time() - t), nd)
        t = time.time(); r, nd = run_rand(Q, 4000000, 2); dt = time.time() - t; print('4e6 rules: %.1fs -> %.2e rules/s' % (dt, nd / dt))
    elif cmd == 'full':
        t = time.time(); (topz, topc, cnt, mx), nd = run_full(P); print('full enum evaluated slots', nd, 'secs %.0f' % (time.time() - t))
        np.savez(out + '/full_real.npz', topz=topz, topc=topc, cnt=cnt, mx=mx, nd=nd)
    elif cmd == 'rand_real':
        N, seed = int(sys.argv[4]), int(sys.argv[5]); t = time.time(); (topz, topc, cnt, mx), nd = run_rand(P, N, seed)
        np.savez(out + '/rand_real_%d.npz' % seed, topz=topz, topc=topc, cnt=cnt, mx=mx, nd=nd); print('rand_real done', nd, '%.0fs' % (time.time() - t))
    elif cmd == 'rand_placebo':
        N, seed, p0, p1 = [int(x) for x in sys.argv[4:8]]; res = {}
        for p in range(p0, p1):
            rng = np.random.default_rng(1000 + p); sh = int(rng.integers(5, 111)); Q = placebo_tables(P, sh)
            (topz, topc, cnt, mx), nd = run_rand(Q, N, seed)
            res[p] = dict(shift=sh, cnt=cnt.tolist(), mx=mx.tolist(), top1=[float(topz[m].max()) for m in range(3)], nd=nd)
            json.dump(res, open(out + '/placebo_%d_%d.json' % (p0, p1), 'w')); print('placebo', p, sh, cnt[:, 0].tolist(), mx.round(2).tolist(), flush=True)
