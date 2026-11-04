exec(open('val1.py').read().split("C = {")[0])
C = {}
for name, kw in C.items():
    res = {}; d = {True: [], False: []}
    for (sd, mech), (s, F, bl) in W.items():
        c = score(fam.level(F, **kw), s)['cagr_med']; res['%d_%s' % (sd, mech)] = round(c, 5); d[mech].append(c - bl['best_const'])
    n = log_variant('val2_' + name, kw, seeds, P, res)
    print('%3d %s %-50s dON=%+.4f dOFF=%+.4f  min=%+.4f' % (n, name, json.dumps(kw), np.mean(d[True]), np.mean(d[False]), min(np.mean(d[True]), np.mean(d[False]))), flush=True)
# robustness of C1 (not new variants: same rule, different execution)
kw = dict(k=0.6, hfwd=20, bh=0.1, hy=1)
for lab, ex in (('delay3', dict(delay=3)), ('delay5', dict(delay=5)), ('cost6', dict(cost=0.006))):
    d = {True: [], False: []}
    for (sd, mech), (s, F, bl) in W.items():
        c = score(fam.level(F, **kw), s, **ex)['cagr_med']; d[mech].append(c - bl['best_const'])
    print('C1 robustness %s dON=%+.4f dOFF=%+.4f' % (lab, np.mean(d[True]), np.mean(d[False])), flush=True)
