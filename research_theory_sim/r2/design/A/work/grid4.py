from grid import *
from clock import clock_rule
b = dict(p0=0.02, th_c=1.25, hl_m=40, L_r=0.0)
def with_rf(close, **kw):
    return clock_rule(close, **kw)
# online premium estimation needs rf: wrap
def run_rf(name, kw):
    res = {}
    bb = base()
    for mech in (True, False):
        cs = []
        for sd in SEEDS:
            w = get(sd, mech); B = clock_rule(close_of(w['r']), rf=w['rf'], **kw); s = evaluate(B, w)
            cs.append((s['cagr_med'], s['avg_level_med'], s['trades_per_year_med']))
        res['ON' if mech else 'OFF'] = tuple(np.mean(cs, axis=0))
    n = bump(1, name); on, off = res['ON'], res['OFF']
    print('%-58s ON %+.4f (vs h1 %+.4f, vs bc %+.4f; L %.2f tr %.1f) OFF %+.4f (vs bc %+.4f; L %.2f tr %.1f) N=%d' % (
        name, on[0], on[0] - bb['ON']['hold1'], on[0] - max(bb['ON']['const'].values()), on[1], on[2], off[0], off[0] - max(bb['OFF']['const'].values()), off[1], off[2], n), flush=True)
run_rf('base + online premium kp=10y', dict(b, kp_years=10))
run_rf('base + online premium kp=30y', dict(b, kp_years=30))
run_variant('base + dd_need=0.05', dict(b, dd_need=0.05))
run_variant('base + dd_need=0.03', dict(b, dd_need=0.03))
