"""AUDIT (lane D, TS2 r2): anchors (per-path premium / vol centres), rates regimes, mechanism-off sanity, NaN/inf."""
import sys, io, contextlib, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D')
import exec_engine as ee, sim

T = 7860; W = ee.WARM; DT = 1 / 252
q = lambda a: '%.4f / %.4f / %.4f' % tuple(np.percentile(a, [10, 50, 90]))
D = {}
for mech in (True, False):
    d = sim.simulate(2000, T, 1, mechanism=mech)
    D[mech] = d
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sim.describe(d, 'mechanism %s' % ('ON' if mech else 'OFF'))
    print(buf.getvalue(), end='')
    for k in ('r', 'rf', 'y10'):
        print('  finite %s:' % k, bool(np.isfinite(d[k]).all()), 'r[:,0]==0:' if k == 'r' else '', bool((d['r'][:, 0] == 0).all()) if k == 'r' else '')
p = D[True]['params']; po = D[False]['params']
print('same per-path params ON/OFF (mu_bar, sigma_bar, df):', all(np.array_equal(p[k], po[k]) for k in ('mu_bar', 'sigma_bar', 'df')))
print('same rates ON/OFF:', np.array_equal(D[True]['rf'], D[False]['rf']), np.array_equal(D[True]['y10'], D[False]['y10']))
# anchors: per-path draws
mb, sb, tr = p['mu_bar'], p['sigma_bar'], p['I_TR'] > 0.5
print('\n== per-path prior draws (P=2000, seed 1): p10 / median / p90')
print(' mu_bar all          ', q(mb), ' mean %.4f sd %.4f' % (mb.mean(), mb.std()))
print(' mu_bar price-index  ', q(mb[~tr]), ' n=%d mean %.4f' % ((~tr).sum(), mb[~tr].mean()))
print(' mu_bar total-return ', q(mb[tr]), ' n=%d mean %.4f' % (tr.sum(), mb[tr].mean()))
print(' sigma_bar           ', q(sb), ' geo-mean %.4f sd(log) %.3f' % (np.exp(np.log(sb).mean()), np.log(sb).std()))
print(' df                  ', q(p['df']))
for mech in (True, False):
    d = D[mech]
    r, rf = d['r'][:, W:], d['rf'][:, W:]
    prem = (r - rf).mean(1) * 252; var = r.var(1) * 252
    print(' %s realised premium all/PI/TR medians: %.4f %.4f %.4f ; realised vol median %.4f ; mean(var)/mean(sigma_bar^2) %.3f' % (
        'ON ' if mech else 'OFF', np.median(prem), np.median(prem[~tr]), np.median(prem[tr]), np.median(np.sqrt(var)),
        var.mean() / (sb ** 2).mean()))
pon = (D[True]['r'][:, W:] - D[True]['rf'][:, W:]).mean(1) * 252
poff = (D[False]['r'][:, W:] - D[False]['rf'][:, W:]).mean(1) * 252
print(' premium ON-OFF per path: mean %+.4f median %+.4f ; vs mu_bar: ON mean %+.4f, OFF mean %+.4f' % (
    (pon - poff).mean(), np.median(pon - poff), (pon - mb).mean(), (poff - mb).mean()))
von = D[True]['r'][:, W:].std(1) * np.sqrt(252) / sb; voff = D[False]['r'][:, W:].std(1) * np.sqrt(252) / sb
print(' realised vol / sigma_bar: ON median %.3f mean-of-var %.3f ; OFF median %.3f mean-of-var %.3f' % (
    np.median(von), np.mean(von ** 2), np.median(voff), np.mean(voff ** 2)))
# rates regimes (brief 2d)
R = D[True]['rf'] * 252
L = 2520
dR = R[:, L:] - R[:, :-L]
up = dR.max(1); dn = -dR.min(1)
print('\n== rates: P(10-y rise >= 3pp) %.2f  P(10-y fall >= 3pp) %.2f  P(either) %.2f  P(10-y rise >= 5pp) %.2f  P(fall >= 5pp) %.2f' % (
    np.mean(up >= 0.03), np.mean(dn >= 0.03), np.mean((up >= 0.03) | (dn >= 0.03)), np.mean(up >= 0.05), np.mean(dn >= 0.05)))
# steadiness: within the best 10-y rise window, share of 1-year steps in the same direction
yr = R[:, ::252]
st_up = []; st_dn = []
for i in range(R.shape[0]):
    a = np.diff(yr[i]); best_u = 0; best_d = 0
    for s in range(len(a) - 9):
        w = a[s:s + 10]
        best_u = max(best_u, np.mean(w > 0) if w.sum() >= 0.03 else 0); best_d = max(best_d, np.mean(w < 0) if w.sum() <= -0.03 else 0)
    st_up.append(best_u); st_dn.append(best_d)
st_up = np.array(st_up); st_dn = np.array(st_dn)
print(' P(10-y window rising >= 3pp with >= 8 of 10 yearly steps up) %.2f ; falling likewise %.2f' % (np.mean(st_up >= 0.8), np.mean(st_dn >= 0.8)))
rng5 = np.array([min(np.ptp(R[i, s:s + 1260]) for s in range(0, T - 1260, 63)) for i in range(R.shape[0])])
print(' P(a 5-y window with rate range <= 1pp, stable) %.2f' % np.mean(rng5 <= 0.01))
print(' fraction of days with a rate change %.4f ; change sizes (pp):' % np.mean(np.diff(R, axis=1) != 0),
      np.unique(np.round(np.abs(np.diff(R, axis=1))[np.diff(R, axis=1) != 0] * 100, 4))[:6])
# mechanism-off is i.i.d.: autocorrelation of |r| and link to rates
def acf_abs(r, lag):
    a = np.abs(r[:, W:] - r[:, W:].mean(1, keepdims=True)); a = a - a.mean(1, keepdims=True)
    return np.median((a[:, lag:] * a[:, :-lag]).mean(1) / a.var(1))
for mech in (True, False):
    d = D[mech]; r = d['r']; S = d['y10'] / 100 - d['rf'] * 252
    dY = np.zeros_like(r); dY[:, 1:] = np.diff(d['y10'], axis=1)
    ex = r - d['rf']
    c_sp = np.median([np.corrcoef(ex[i, W + 1:], S[i, W:-1])[0, 1] for i in range(0, 2000, 4)])
    c_dy = np.median([np.corrcoef(ex[i, W:], dY[i, W:])[0, 1] if dY[i, W:].std() > 0 else 0 for i in range(0, 2000, 4)])
    print(' %s: median acf(|r|) lag1 %.3f lag20 %.3f lag250 %.3f ; corr(r_t, spread_{t-1}) %.4f ; corr(r_t, dy10_t) %.4f' % (
        'ON ' if mech else 'OFF', acf_abs(r, 1), acf_abs(r, 20), acf_abs(r, 250), c_sp, c_dy))
# same shocks ON / OFF
ds = sim.simulate(250, T, 1, mechanism=True, states=True)
print('\nstates=True leaves paths unchanged:', np.array_equal(ds['r'], D[True]['r'][:250]))
zoff = (D[False]['r'][:250] - D[False]['rf'][:250] - po['mu_bar'][:250, None] * DT) / (po['sigma_bar'][:250, None] * np.sqrt(DT))
zon = (ds['r'] - ds['rf'] - ds['params']['_mu'] * DT) / (ds['params']['_sig'] * np.sqrt(DT))
cc = np.array([np.corrcoef(zon[i, 1:], zoff[i, 1:])[0, 1] for i in range(250)])
print('corr(standardised ON shock, OFF shock) per path: p10 %.3f median %.3f' % tuple(np.percentile(cc, [10, 50])))
# robustness variants: no NaN / inf
for kw in (dict(prior_scale=0.5), dict(prior_scale=1.5), dict(block=True)):
    for mech in (True, False):
        d = sim.simulate(250, T, 3, mechanism=mech, **kw)
        print(' finite', kw, mech, all(bool(np.isfinite(d[k]).all()) for k in ('r', 'rf', 'y10')), 'min r %.3f' % d['r'].min())
