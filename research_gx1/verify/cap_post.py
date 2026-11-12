"""CAP1 as implemented (cap B before the brake fn) vs cap applied to the brake's output tg (post-bfn)."""
import sys; sys.path.insert(0,'/mnt/project-files/research/gx1/code')
import gx1lib as G, numpy as np, pandas as pd
from gx1lib import std, ov
import bk, beng, ce, rx
from numba import njit
NF = bk.NF
@njit(cache=False)
def capfn(k, E, pk, b, held, x, st, p):
    L = rx.av23s(k, E, pk, b, held, x, st, p)
    if x[x.shape[0]-1] > 0.5 and L > 1.0: L = 1.0
    return L
def eng_post(c, g):
    B, bfn, bp, fs = std.s085(c); B = np.array(B, dtype=np.float64)
    f = bk.features(c); FE = np.concatenate([f, g[:, :, None].astype(np.float32)], axis=2)
    k = dict(beng.F1); k['fstep'] = fs; k['cspr'] = 10.0; pp, D = beng._args(k)
    o, EE = ce.runPE(np.ascontiguousarray(c.r), np.ascontiguousarray(c.rf), np.ascontiguousarray(B), np.ascontiguousarray(FE), int(pp['delay']), pp['cost'], pp['tax'], D,
                     int(pp['harvest']), pp['hthr'], pp['cspr'], pp['er3'], pp['step'], capfn, np.asarray(bp, dtype=np.float64), float(pp['fstep']))
    yrs = EE.shape[1] / 252
    return np.maximum(o[:, 0], 1e-9) ** (1 / yrs) - 1, EE
col = 'G11'
fr = G.us_frames()
for bn in ('real_ndx_86_14', 'dev250_path', 'dev250_glued'):
    X, F, ii, kind = fr[bn]
    if kind == 'path': g = G.path_world(X.index, ii, 'US')[col]
    else: g = G.world_signals(X.index, 'US')[col].values.astype(bool)[ii]
    v, Ev = G.acct(G.us_ctx(X, F, ii, kind)); a, Ea = G.acct(G.us_ctx(X, F, ii, kind), Gpath=g, mode='CAP1')
    b, Eb = eng_post(G.us_ctx(X, F, ii, kind), g)
    rv = std.row(v, Ev)[0]['cagr']; ra = std.row(a, Ea)[0]['cagr']; rb = std.row(b, Eb)[0]['cagr']
    print(bn, 'v1 %.4f  CAP1(pre-brake, as run) %.4f  CAP1(post-brake) %.4f  med d pre %.4f post %.4f' % (rv, ra, rb, np.median(a - v), np.median(b - v)), flush=True)
# foreign hosts: rule 24 d under both variants
out = {}
for h in G.HOSTS:
    X, i0 = G.host(h); F = ov.flags_hist(X); rows = np.arange(i0, len(X)); D = G.world_signals(X.index, h); g = D[col].values.astype(bool)
    c = lambda: ov.Ctx(X, F, rows[None, :])
    v = G.acct(c())[0][0]; a = G.acct(c(), Ghist=g, mode='CAP1')[0][0]; b = eng_post(c(), g[rows][None, :])[0][0]
    out[h] = (round(a - v, 5), round(b - v, 5))
print('foreign rule24 d (pre, post):', out)
