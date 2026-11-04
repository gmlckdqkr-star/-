"""ETX1 stage 1 screen: S1 / S2 / S3 x candidates on one MS1 basis (argv[1]). <=2014 only.
Writes results/screen_<basis>.json (rows + coverage) and results/paths_<basis>.npz (per-path CAGR) for path bases."""
import sys, os, json, time, gc, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import etxeng as G, etxcands as X
OUT = '/mnt/project-files/research/etf_ext/results/'

if __name__ == '__main__':
    bn = sys.argv[1]; only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
    t0 = time.time(); b = G.Basis(bn); L = G.s085_levels(bn)
    fn = OUT + 'screen_%s.json' % bn
    res = json.load(open(fn)) if os.path.exists(fn) else {}
    ref = G.run(b, ['TQQQ', 'CASH'], [G.sl_s085(L)], [1.0]); res['s085'] = G.row(ref)
    paths = {'s085': ref['cagr']}
    for name, cfg in X.configs():
        if only and name not in only: continue
        cov = min(G.coverage(b, p) for p in X.products_of(cfg))
        prods, sl, ws = X.build(b, L, cfg)
        r = G.run(b, prods, sl, ws); rw = G.row(r, ref); rw['cover'] = cov
        res[name] = rw; paths[name] = r['cagr']
        print(bn, name, 'cagr %.4f d %+.4f pw %.2f dd80 %.3f cov %.2f' % (rw['cagr'], rw['d_ref'], rw['pw_ref'], rw['dd80'], cov),
              '%.0fs' % (time.time() - t0), flush=True)
        del r; gc.collect()
    json.dump(res, open(fn, 'w'), indent=1)
    if b.P > 1: np.savez_compressed(OUT + 'paths_%s.npz' % bn, **paths)
    print('done', bn, '%.0fs' % (time.time() - t0), flush=True)
