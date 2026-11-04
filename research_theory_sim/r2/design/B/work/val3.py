exec(open('val1.py').read().split("C = {")[0])
C = {'C1k7': dict(k=0.7, hfwd=20, bh=0.1, hy=1), 'C1h15': dict(k=0.6, hfwd=15, bh=0.1, hy=1), 'C1h25': dict(k=0.6, hfwd=25, bh=0.1, hy=1),
     'C1b15': dict(k=0.6, hfwd=20, bh=0.15, hy=1)}
for name, kw in C.items():
    res = {}; d = {True: [], False: []}
    for (sd, mech), (s, F, bl) in W.items():
        c = score(fam.level(F, **kw), s)['cagr_med']; res['%d_%s' % (sd, mech)] = round(c, 5); d[mech].append(c - bl['best_const'])
    n = log_variant('val3_' + name, kw, seeds, P, res)
    print('%3d %s %-50s dON=%+.4f dOFF=%+.4f  min=%+.4f' % (n, name, json.dumps(kw), np.mean(d[True]), np.mean(d[False]), min(np.mean(d[True]), np.mean(d[False]))), flush=True)
