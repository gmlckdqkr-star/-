"""JS1 kernel vs independent numpy reference on random rules (design and confirm sets)."""
import sys, numpy as np; sys.path.insert(0, '/home/user/repo/research_js1/code')
from numba import njit
import js1_kern as K, js1_ref as R
P = dict(np.load(sys.argv[1], allow_pickle=True))
@njit
def one(b64, T, nf64, ur, wu, nu, ntot, sh, a, b, c, d):
    z = np.zeros(3); ok = K.eval_rule(b64, T, nf64, ur, wu, nu, ntot, sh, a, b, c, d, z); return ok, z
rng = np.random.default_rng(5); A = P['A']; nA = A.shape[0]; X = P['X']; mx = 0; nchk = 0
for pre in ('des', 'con'):
    b64, T, nf64, ur, wu, nu, ntot = K.prep(P, pre)
    sl = P[pre + '_slot']; oc, ot = sl[:, 0], sl[:, 1]; order = np.lexsort((ot, oc)); oc, ot = oc[order], ot[order]
    for it in range(400):
        k = rng.choice([1, 2, 3, 4]); ids = rng.choice(nA, 4, replace=False)
        sh = {1: 0, 2: rng.integers(1, 3), 3: rng.integers(3, 11), 4: rng.integers(11, 17)}[k]
        code = K.code_of(sh, ids[0], ids[1], ids[2], ids[3]); on = R.cond(A, code)[oc, ot]
        ok, z = one(b64, T, nf64, ur, wu, nu, ntot, sh, ids[0], ids[1], ids[2], ids[3])
        zr = [R.zref(on, oc, ot, X, m) for m in range(3)]
        assert (zr[0] is not None) == ok, (pre, it, ok, zr)
        if ok:
            nchk += 1
            for m in range(3): mx = max(mx, abs(z[m] - zr[m]))
print('checked', nchk, 'rules; max |z_kernel - z_numpy| = %.3e' % mx); assert mx < 1e-8
