from harness import *
from clock import clock_rule
import itertools
P = 500
def go(name, kw, seeds=(1,), P=P):
    out = []
    for mech in (True, False):
        cs = []
        for sd in seeds:
            w = world(sd, P, mech)
            B = clock_rule(close_of(w['r']), **kw)
            s = evaluate(B, w); cs.append((s['cagr_med'], s['avg_level_med'], s['trades_per_year_med']))
        out.append(tuple(np.mean(cs, axis=0)))
    n = bump(1, name)
    print('%-60s ON %+.4f (L %.2f, tr %.1f)  OFF %+.4f (L %.2f, tr %.1f)  N=%d' % ((name,) + out[0] + out[1] + (n,)), flush=True)
    return out
if __name__ == "__main__":   # (already run once: N=13..22)
    go('kelly base only (th_c=99)', dict(th_c=99))
    go('const 1 base only', dict(th_c=99, kelly=False, Lb_const=1.0))
    for th_c, d_r, L_r in itertools.product((1.3, 1.6), (0.1, 0.2), (2.0, 3.0)):
        go('clock th_c=%.1f d_r=%.2f L_r=%.1f' % (th_c, d_r, L_r), dict(th_c=th_c, d_r=d_r, L_r=L_r))
