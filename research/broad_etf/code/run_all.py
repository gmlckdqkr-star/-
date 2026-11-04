"""BE1 main run: 20 configs (F1-F4) x 5 MS1 bases + s0.85 reference. <=2014 only. Writes results/main_le2014.json + path cagr npz."""
import sys, json, time, gc, numpy as np
import be1eng as G, bstrat as S
OUT = '/mnt/project-files/research/broad_etf/results/'
CFG = [('F1_k%d_L%d' % (k, L), ('F1', k, L)) for k in (1, 3, 5) for L in (1, 2, 3)]
CFG += [('F2_%s_k%d' % (s, k), ('F2', s, k)) for s in ('def', 'all') for k in (1, 3)]
CFG += [('F3_w%02d_s%02d' % (int(w * 100), int(sg * 100)), ('F3', w, sg)) for w in (0.70, 0.85) for sg in (0.12, 0.25)]
CFG += [('F4_s%02d' % int(sg * 100), ('F4', sg)) for sg in (0.12, 0.25, 0.40)]

def spec(b, bn, c, delay=2):
    if c[0] == 'F1': return S.F1(b, c[1], c[2], delay)
    if c[0] == 'F2': return S.F2(b, bn, c[1], c[2], delay)
    if c[0] == 'F3': return S.F3(b, bn, c[1], c[2], delay)
    if c[0] == 'F4': return S.F4(b, c[1], delay)

if __name__ == '__main__':
    bases = sys.argv[1].split(',') if len(sys.argv) > 1 else G.BASES
    res = {}
    try: res = json.load(open(OUT + 'main_le2014.json'))
    except Exception: pass
    for bn in bases:
        t0 = time.time(); b = G.basis(bn)
        ref = S.runspec(b, S.S085(b, bn)); res.setdefault(bn, {})['s085'] = G.row(ref)
        paths = {'s085': ref['cagr']}
        if bn == 'real_ndx_86_14': res[bn]['s085']['sharpe'] = G.sharpe_from_curve(ref, b['rf'])
        for name, c in CFG:
            x = S.runspec(b, spec(b, bn, c)); rw = G.row(x, ref)
            if bn == 'real_ndx_86_14': rw['sharpe'] = G.sharpe_from_curve(x, b['rf'])
            res[bn][name] = rw; paths[name] = x['cagr']
            print(bn, name, 'cagr %.4f d %.4f pw %.2f dd80 %.3f' % (rw['cagr'], rw['d_ref'], rw['pw_ref'], rw['dd80']), '%.0fs' % (time.time() - t0), flush=True)
            del x; gc.collect()
        np.savez(OUT + 'paths_%s.npz' % bn, **paths)
        json.dump(res, open(OUT + 'main_le2014.json', 'w'), indent=1)
        G._D.pop((bn, False), None); gc.collect()
