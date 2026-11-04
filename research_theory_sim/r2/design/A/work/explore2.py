from harness import *
from rulelib import *
P = 500
rows = []
def go(name, fn):
    out = []
    for mech in (True, False):
        w = world(1, P, mech)
        F = feats(close_of(w['r']))
        B = fn(F)
        s = evaluate(B, w)
        out.append((s['cagr_med'], s['avg_level_med'], s['trades_per_year_med']))
    n = bump(1, name)
    print('%-34s ON %+.4f (L %.2f, tr %.1f)  OFF %+.4f (L %.2f, tr %.1f)  N=%d' % ((name,) + out[0] + out[1] + (n,)))
for mech in (True, False):
    b = baselines(world(1, P, mech)); print('mech', mech, 'hold1 %.4f hold2 %.4f hold3 %.4f' % (b['hold1'], b['hold2'], b['hold3']), {k: round(v, 4) for k, v in b['const'].items()})
for k in (1.0, 1.5, 2.0, 3.0):
    go('voltarget k=%.1f' % k, lambda F: np.clip(k * np.sqrt(F['vlong'] / F['vs']), 0, 3))
for k in (1.0, 1.5, 2.0):
    go('volBOOST k=%.1f' % k, lambda F: np.clip(k * np.sqrt(F['vs'] / F['vlong']), 0, 3))
for lo, hi in ((0.5, 2.0), (1.0, 3.0), (0.0, 3.0)):
    go('trend100 %.1f/%.1f' % (lo, hi), lambda F: np.where(F['lp'] > F['ma'], hi, lo))
for lo, hi in ((1.0, 3.0), (1.5, 3.0)):
    go('dd<-0.2 boost %.1f/%.1f' % (lo, hi), lambda F: np.where(F['dd'] < -0.2, hi, lo))
