from grid import *
kw = dict(p0=0.02, th_c=1.25, hl_m=40, L_r=0.0)
b = base()
for mech in (True, False):
    for (dl, cs) in ((3, 0.003), (5, 0.003), (2, 0.006)):
        v = []
        for sd in SEEDS:
            w = get(sd, mech); B = clock_rule(close_of(w['r']), **kw)
            v.append(evaluate(B, w, delay=dl, cost=cs)['cagr_med'])
        tag = 'ON' if mech else 'OFF'
        print(tag, 'delay', dl, 'cost', cs, 'cagr_med %.4f  vs hold1 %+.4f  vs bc %+.4f' % (np.mean(v), np.mean(v) - b[tag]['hold1'], np.mean(v) - max(b[tag]['const'].values())), flush=True)
bump(3, 'robustness rows of candidate (not selection)')
