"""conditional forward excess returns by state (selection seeds only), ON vs OFF."""
from harness import *

def ewm_var(lr, hl):
    a = 1 - np.exp(np.log(0.5) / hl)
    out = np.empty_like(lr); v = np.nanmean(lr[:, 1:60] ** 2, axis=1)
    for t in range(lr.shape[1]):
        v = (1 - a) * v + a * lr[:, t] ** 2; out[:, t] = v
    return out

def ema(x, hl):
    a = 1 - np.exp(np.log(0.5) / hl)
    out = np.empty_like(x); v = x[:, 0].copy()
    for t in range(x.shape[1]):
        v = (1 - a) * v + a * x[:, t]; out[:, t] = v
    return out

for mech in (True, False):
    w = world(1, 1000, mech)
    r, rf = w['r'], w['rf']
    lr = np.log1p(r); ex = lr - np.log1p(rf)
    lp = np.cumsum(lr, axis=1)
    vf = np.sqrt(ewm_var(lr, 10) * 252); vs = np.sqrt(ewm_var(lr, 120) * 252)
    ma = ema(lp, 100)
    hi = np.maximum.accumulate(lp, axis=1)  # all-time high (for drawdown)
    H = 63
    cs = np.concatenate([np.zeros((lr.shape[0], 1)), np.cumsum(ex, axis=1)], axis=1)
    t_idx = np.arange(300, lr.shape[1] - H - 2)
    fwd = (cs[:, t_idx + 2 + H] - cs[:, t_idx + 2]) * 252 / H   # annualised fwd excess (after 2-day delay)
    fvar = None
    ratio = (vf / vs)[:, t_idx]; trend = (lp - ma)[:, t_idx]; dd = (lp - hi)[:, t_idx]
    vlev = vf[:, t_idx] / np.sqrt(np.cumsum(lr ** 2, axis=1) / np.arange(1, lr.shape[1] + 1) * 252)[:, t_idx]
    print('==== mech', mech, ' unconditional fwd63 ann mean %.3f' % fwd.mean())
    def tab(name, f, edges):
        for lo, hi_ in zip(edges[:-1], edges[1:]):
            m = (f >= lo) & (f < hi_)
            if m.sum() < 1000: continue
            print('  %-10s [%6.2f,%6.2f) frac %.3f  fwd mean %+.3f  (realised vol in window ~ %.3f)' % (name, lo, hi_, m.mean(), fwd[m].mean(), np.sqrt(np.mean((vf[:, t_idx][m])**2))))
    tab('volratio', ratio, [0, 0.7, 0.85, 1.0, 1.2, 1.5, 2.0, 99])
    tab('trend', trend, [-9, -0.2, -0.1, -0.05, 0, 0.05, 0.1, 0.2, 9])
    tab('dd', dd, [-9, -0.5, -0.3, -0.2, -0.1, -0.05, -0.0001, 1])
    tab('vlev', vlev, [0, 0.6, 0.8, 1.0, 1.3, 1.7, 99])
    # joint: dd deep & vol ratio falling
    for a_ in [(dd < -0.2) & (ratio < 1), (dd < -0.2) & (ratio >= 1), (dd >= -0.05) & (ratio < 0.9), (trend < 0) & (ratio > 1.3)]:
        print('  joint frac %.3f fwd %+.3f' % (a_.mean(), fwd[a_].mean()))
