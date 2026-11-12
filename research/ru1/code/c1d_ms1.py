"""C1d: does the 3-month definition move the MS1 path median, or only single histories? (robustness, not selection)
dev250_path and real NDX with y3m (+ model rf) shifted to the CMT level (+0.087 %p, median CMT-IRX gap 1990-2014) and IRX->bond-equivalent."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/acct3/code'); sys.path.insert(0, '/mnt/project-files/research/ru1/code')
import ac3, ru, std, bk, rx
from std import jp, ov, iv
PP = ac3.PP
def ctxs(mod):
    out = {}
    a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX'); X = mod(X); F = ov.flags_hist(X)
    ii = ov.boot_idx(len(X), P=P, years=30, block=blk, seed=seed, lo=1); c = ov.Ctx(X, F, ii); c.F = std.path_flags(X, ii); c._c = {}
    out['dev250_path'] = c
    R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX'); X = mod(X); F = ov.flags_hist(X)
    i0 = X.index.searchsorted(pd.Timestamp('1986-01-02')) - ov.WARM; out['real_ndx_86_14'] = ov.Ctx(X, F, np.arange(i0, len(X))[None, :])
    return out
def shift(X, d=0.087):
    X = X.copy(); X['y3m'] = X['y3m'] + d; X['rf'] = X['rf'] + d / 100 / 252; return X
def bey(X):
    X = X.copy(); dsc = X['y3m'] / 100; b = 100 * 365 * dsc / (360 - 91 * dsc); X['rf'] = X['rf'] + (b - X['y3m']) / 100 / 252; X['y3m'] = b; return X
base = ac3.prep(); res = {}
for nm, mod in (('research', lambda X: X), ('y3m_plus_0.087', shift), ('y3m_bey', bey)):
    C = ctxs(mod); res[nm] = {}
    for bn, c in C.items():
        Bs = np.ascontiguousarray(bk.C3sig(c), dtype=np.float64); feat = np.ascontiguousarray(bk.features(c))
        L, _ = ac3.levels(np.ascontiguousarray(c.r), np.ascontiguousarray(c.rf), Bs, feat, int(PP['delay']), PP['cost'], PP['tax'], 0.25,
                          int(PP['harvest']), PP['hthr'], PP['cspr'], PP['er3'], PP['step'], rx.av23s, rx.P_av23s(.85), 0.1)
        b0 = base[bn]; P, T = b0['R'].shape; n = T - ru.WARM
        o, EU, _ = ru.acctP(b0['R'], b0['RF'], np.ascontiguousarray(L), np.ones((P, T)), np.zeros((P, n)), 0, 0, 0.0, .003, .22, .25, .0245, 1.0)
        if nm == 'research': res.setdefault('_ref', {})[bn] = ru.cagr(o[:, 0], n / 252)
        s, cg = ru.stats(o[:, 0], EU, n / 252, res['_ref'][bn]); s['level_diff_share'] = float(np.mean(np.abs(L - b0['L']) > 1e-9))
        res[nm][bn] = s; print(nm, bn, {k: round(v, 4) for k, v in s.items()}, flush=True)
res.pop('_ref'); json.dump(res, open('/mnt/project-files/research/ru1/results/c1d_ms1.json', 'w'), indent=1)
