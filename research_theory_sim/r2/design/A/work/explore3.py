"""event study: forward excess log returns after cascade signals and after meter-peak signals (seed 1)."""
from harness import *
from rulelib import *
P = 1000
Hs = [5, 10, 21, 63, 126, 252]
for mech in (True, False):
    w = world(1, P, mech); r, rf = w['r'], w['rf']
    F = feats(close_of(r), hl_fast=10, hl_slow=60)
    ex = np.log1p(r) - np.log1p(rf)
    cs = np.concatenate([np.zeros((P, 1)), np.cumsum(ex, axis=1)], axis=1)
    T_ = r.shape[1]
    vf, vs, dd, lp, ma = F['vf'], F['vs'], F['dd'], F['lp'], F['ma']
    ratio = np.sqrt(vf / vs)
    vfs = np.sqrt(vf)
    pk = np.maximum.accumulate  # not used
    # rolling 21-day max of fast vol (causal)
    from numpy.lib.stride_tricks import sliding_window_view
    vmax = np.full_like(vfs, np.nan); vmax[:, 20:] = sliding_window_view(vfs, 21, axis=1).max(axis=2)
    sigs = {
        'cascade: ratio>1.4 & lp<ma': (ratio > 1.4) & (lp < ma),
        'cascade: ratio>1.2 & dd<-0.1': (ratio > 1.2) & (dd < -0.1),
        'peakpast: vf<0.75*max21 & dd<-0.2 & ratio>1': (vfs < 0.75 * vmax) & (dd < -0.2) & (ratio > 1.0),
        'peakpast: vf<0.75*max21 & dd<-0.2': (vfs < 0.75 * vmax) & (dd < -0.2),
        'calm: ratio<0.8 & dd>-0.05': (ratio < 0.8) & (dd > -0.05),
        'calm & stretched: ratio<0.85 & lp>ma+0.1': (ratio < 0.85) & (lp > ma + 0.1),
    }
    print('==== mech', mech)
    tt = np.arange(300, T_ - 254)
    base = {H: ((cs[:, tt + 2 + H] - cs[:, tt + 2]) * 252 / H).mean() for H in Hs}
    print('  %-46s frac  ' % 'unconditional', ' '.join('%7s' % ('H%d' % H) for H in Hs))
    print('  %-46s %.3f ' % ('', 1.0), ' '.join('%+7.3f' % base[H] for H in Hs))
    for name, S in sigs.items():
        m = S[:, tt]
        vals = []
        for H in Hs:
            f = (cs[:, tt + 2 + H] - cs[:, tt + 2]) * 252 / H
            vals.append(f[m].mean())
        print('  %-46s %.3f ' % (name, m.mean()), ' '.join('%+7.3f' % v for v in vals))
