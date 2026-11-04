from grid import *
kw = dict(p0=0.02, th_c=1.25, hl_m=40, L_r=0.0)
for mech in (True, False):
    w = get(2, mech); r, rf = w['r'], w['rf']
    B, st = clock_rule(close_of(r), ret_state=True, **kw)
    ex = np.log1p(r) - np.log1p(rf)
    # state decided at close t, earns from day t+3 under delay 2
    s = st[:, 300:-3]; e = ex[:, 303:]
    for k, nm in ((0, 'normal'), (1, 'exit')):
        m = s == k
        print('mech', mech, nm, 'time frac %.3f  ann excess drift %+.3f  ann vol %.3f' % (m.mean(), e[m].mean() * 252, e[m].std() * np.sqrt(252)))
    # episodes: mean length of exit spells
    d = np.diff((st[:, 300:] == 1).astype(int), axis=1)
    starts = (d == 1).sum(); print('   exit spells per path-year %.2f, mean spell length %.1f d' % (starts / (r.shape[0] * 30), (st[:, 300:] == 1).sum() / max(starts, 1)))
