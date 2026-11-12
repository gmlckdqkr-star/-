"""VXR1 runner (PRECOMMIT_VXR1.md). user_port_up MS1 multi-sleeve engine + SVX product (short 30d CM VIX futures, -1x ETF form).
Cash earns 0 on both sides. <=2014 ONLY."""
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/user_port_up/code'); sys.path.insert(0, '/mnt/project-files/research/volprem/code')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uprun as U, upeng as E, updata as UD, vpdata as VP, vxdata as VX, vxeng as XE
WARM = E.WARM
PRODS = E.PRODS + ['SVX']; J = {n: i for i, n in enumerate(PRODS)}; NJ = len(PRODS)
NOTAX = np.array([n == 'CASH' for n in PRODS])
FEE = 0.0095 + 0.005
_C = {}

def vfull(D):
    """V by date: VIX close, else VP1 proxy m*max(rv21, rv63)*100 (SPX realized)"""
    m = VP.vix_rv_ratio(); prox = m * np.maximum(D['rvs21'], D['rvs63']) * 100
    return D['vix'].where(D['vix'].notna(), prox).ffill().fillna(20.0)

def calib():
    """beta, a, b on the ACTUAL window (real NDX table dates with CM1 and VIX)"""
    if 'cal' in _C: return _C['cal']
    D = VP.frame('real_ndx_86_14'); V = vfull(D); cm = VX.load()['r']
    z = np.log(V / V.rolling(252, min_periods=126).mean())
    dl = np.log(V).diff()
    F = pd.DataFrame({'r': cm, 'dl': dl, 'z1': z.shift(1)}).dropna()
    beta = F['r'].std() / F['dl'].std()
    y = F['r'] - beta * F['dl']; Xm = np.c_[np.ones(len(F)), F['z1']]
    a, b = np.linalg.lstsq(Xm, y.values, rcond=None)[0]
    rhat = beta * F['dl'] + a + b * F['z1']
    mo = pd.DataFrame({'r': F['r'], 'h': rhat}).resample('ME').apply(lambda x: (1 + x).prod() - 1)
    _C['cal'] = dict(beta=float(beta), a=float(a), b=float(b), mean_r=float(F['r'].mean()), n=len(F), first=str(F.index[0].date()),
                     corr_d=float(np.corrcoef(F['r'], rhat)[0, 1]), corr_m=float(mo.corr().iloc[0, 1]),
                     mean_hat=float(rhat.mean()), max_r=float(F['r'].max()), max_hat=float(rhat.max()), sd_r=float(F['r'].std()), sd_hat=float(rhat.std()))
    return _C['cal']

def svx_bydate(bn, cut=0.25, fee_add=0.0, rf_on=True):
    """by-date SVX simple return on the X table of basis bn; ACTUAL where CM1 exists, SYNTH before. Also returns V by date."""
    D = VP.frame(bn); V = vfull(D); cal = calib(); cm = VX.load()['r'].reindex(D.index)
    z = np.log(V / V.rolling(252, min_periods=126).mean()).shift(1).fillna(0.0)
    dl = np.log(V).diff().fillna(0.0)
    rhat = cal['beta'] * dl + (cal['a'] + cut * abs(cal['mean_r'])) + cal['b'] * z
    act = cm.notna() & (D.index >= pd.Timestamp(cal['first']))
    rc = np.where(act, cm.fillna(0.0), rhat.values)
    rc = np.maximum(rc, -0.95)
    rs = -rc + (D['rf'].values if rf_on else 0.0) - (FEE + fee_add) / 252
    rs = np.maximum(rs, -1.0)
    return rs, V.values, D['spx'].values, act.values, D.index

def products(bn, cut=0.25, fee_add=0.0, rf_on=True):
    key = ('p', bn, cut, fee_add, rf_on)
    if key in _C: return _C[key]
    b = U.basis(bn); c = b['c']; r0, dg0, do0 = U.prod(bn)
    P, T, _ = r0.shape
    r = np.zeros((P, T, NJ)); dg = np.zeros_like(r); do = np.zeros_like(r)
    r[:, :, :len(E.PRODS)] = r0; dg[:, :, :len(E.PRODS)] = dg0; do[:, :, :len(E.PRODS)] = do0
    r[:, :, J['CASH']] = 0.0                                      # idle cash earns 0 (user rule 11-11)
    rs, V, spx, act, idx = svx_bydate(bn, cut, fee_add, rf_on)
    r[:, :, J['SVX']] = rs[c.ii]
    r[:, 0, :] = 0; dg[:, 0, :] = 0; do[:, 0, :] = 0
    _C[key] = (r, dg, do, V[c.ii], np.nan_to_num(spx[c.ii]), act[c.ii]); return _C[key]

def gates(bn, g, delay=2):
    """(P, K) 0/1 SVX in force, recomputed on the path (not glued). g in G0, G1, G2."""
    r, dg, do, Vp, sp, _ = products(bn); P, T = Vp.shape
    if g == 'G0': on = np.ones((P, T))
    elif g == 'G1':
        rv = pd.DataFrame(sp.T).rolling(10).std().values.T * np.sqrt(252) * 100
        on = (Vp > rv).astype(float); on[~np.isfinite(rv)] = 0
    elif g == 'G2':
        mv = pd.DataFrame(Vp.T).rolling(252, min_periods=126).mean().values.T
        on = (Vp < mv).astype(float); on[~np.isfinite(mv)] = 0
    lag = np.zeros_like(on); lag[:, delay:] = on[:, :-delay]       # close t -> in force t+delay
    return lag[:, WARM:]

def run(bn, g=None, s=0.0, cut=0.25, fee_add=0.0, rf_on=True, gdelay=2, cmul=1.0, reb=63, inject=None, ptp=0.0, xeng=False):
    """inject=(years_per_event, seed): CM1 +100% on held days (ADDENDUM 1 P6); ptp: extra sell cost on SVX (P7); xeng: use vxeng copy"""
    r, dg, do, Vp, sp, act = products(bn, cut, fee_add, rf_on); P, T, _ = r.shape; K = T - WARM
    L = U.s085_levels(bn, 2)
    G = gates(bn, g, gdelay) if g else None
    rb = np.zeros(K, bool); rb[reb::reb] = True
    out = np.zeros((P, 7)); C = np.zeros((P, K))
    xs = np.zeros(NJ); xs[J['SVX']] = ptp
    rng = np.random.default_rng(inject[1]) if inject else None
    for p in range(P):
        rp = np.ascontiguousarray(r[p, WARM:])
        if inject and s > 0:
            hit = (rng.random(K) < 1.0 / (inject[0] * 252)) & (G[p] > 0)
            if hit.any(): rp = rp.copy(); rp[hit, J['SVX']] = -1.0
        lv = L[p]; W1 = np.zeros((K, NJ)); W1[:, J['TQQQ']] = lv / 3; W1[:, J['CASH']] = 1 - lv / 3
        f1 = np.r_[True, np.diff(lv) != 0]
        if s > 0:
            W2 = np.zeros((K, NJ)); W2[:, J['SVX']] = G[p]; W2[:, J['CASH']] = 1 - G[p]
            f2 = np.r_[True, np.diff(G[p]) != 0]
            Ws = np.stack([W1, W2]); Fl = np.stack([f1, f2]); ws = np.array([1 - s, s])
        else:
            Ws = W1[None]; Fl = f1[None]; ws = np.array([1.0])
        args = (rp, np.ascontiguousarray(dg[p, WARM:]), np.ascontiguousarray(do[p, WARM:]),
                Ws, Fl, ws, rb if s > 0 else np.zeros(K, bool), 0.0, NOTAX, 0.003 * cmul, 0.22, 0.25, 0.154, out[p], C[p])
        if xeng or ptp > 0: XE.run_port_x(*args, xs)
        else: E.run_port(*args)
    yrs = K / 252; cg = np.maximum(out[:, 0], 1e-9) ** (1 / yrs) - 1
    return dict(cagr=cg, mdd=out[:, 1], E7=out[:, 2], E12=out[:, 3], ntr=out[:, 4] / yrs, cost=out[:, 5], curve=C)

def actual_window(res, bn='real_ndx_86_14'):
    """CAGR of the curve over the ACTUAL CM1 window (first CM1 day .. 2014-12-31) on the real NDX path"""
    c = U.basis(bn)['c']; dates, X = UD.basis_dates()[bn]
    d = dates[c.ii[0, WARM:]]; first = pd.Timestamp(calib()['first'])
    C = res['curve'][0]; i0 = int(np.searchsorted(d, first)) - 1
    yrs = (len(C) - 1 - i0) / 252
    return float((C[-1] / C[i0]) ** (1 / yrs) - 1), float((C[i0:] / np.maximum.accumulate(C[i0:]) - 1).min())
