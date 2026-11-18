"""shared helpers for KRW measurements (recon runs + FX alignment). <=2014 only."""
import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/checks/costtax')
import ctlib as CT, dfctx as DC, dfe, run_grid as RG, run_df2 as R2
W = CT.W

def run_rec(cfg, m, **kw):
    L = DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax']) if cfg['fam'] != 'static' else np.full(m['r'].shape, cfg['w'])
    if cfg['fam'] == 'static':
        k = dict(roff=2, reb_every=252); k.update(kw); return dfe.run(m, L, recon=True, **k)
    k = dict(RG.KNEES[cfg['knee']])
    if cfg['fam'] == 'df2':
        k.update(step_lo=R2.BANDS[cfg['band']][0], step_hi=R2.BANDS[cfg['band']][1], vmode=0 if cfg['M'] == 'M0' else 2)
    k.update(kw)
    return dfe.run(m, L, recon=True, roff=RG.ROFF[cfg['roff']], **k)

def kstats(EE, fin, rel, prepend):
    if prepend:
        EE = np.c_[np.ones(EE.shape[0]), EE]; rel = np.c_[np.ones(rel.shape[0]), rel]
    yrs = (EE.shape[1] - (1 if prepend else 0)) / 252
    Ek = EE * rel
    mdk = (Ek / np.maximum.accumulate(Ek, axis=1) - 1).min(axis=1); mdu = (EE / np.maximum.accumulate(EE, axis=1) - 1).min(axis=1)
    cgk = np.maximum(fin * rel[:, -1], 1e-9) ** (1 / yrs) - 1; cgu = np.maximum(fin, 1e-9) ** (1 / yrs) - 1
    return cgu, mdu, cgk, mdk

def fx_rel():
    mn = DC.market('real_ndx_86_14'); Xn = CT.getX('real_ndx_86_14'); dn = Xn.index[mn['ctx'].ii[0][W:]]
    fxn, _ = CT.fx_on(dn); rel_n = (fxn / fxn[0])[None, :]
    mp = DC.market('dev250_path'); Xp = CT.getX('dev250_path'); fxp, _ = CT.fx_on(Xp.index)
    fr = np.r_[0.0, fxp[1:] / fxp[:-1] - 1]; frp = fr[mp['ctx'].ii]; frp[:, 0] = 0.0
    lv = np.cumprod(1 + frp, axis=1); rel_p = lv[:, W:] / lv[:, W:W + 1]
    return rel_n, rel_p
