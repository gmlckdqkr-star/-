import sys, copy, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG
import px1lib as PX, ov
W = dfe.WARM
R = json.load(open('/mnt/project-files/research/df1/checks/null/result.json'))
MK = ('dev250_path', 'real_ndx_86_14', 'real_spx_29_54', 'real_spx_55_85')
t0 = time.time()
M = {bn: DC.market(bn) for bn in MK}
print('load %.0fs' % (time.time() - t0), flush=True)
def Lpre(m, st, sig, Lmax):
    Lon = np.minimum(float(Lmax), sig / np.maximum(m['vol20'], 1e-9))
    L = np.where(st >= 3, Lon, np.where(st >= 1, np.minimum(Lon, Lmax / 3.0), 0.0)); return np.where(np.isnan(L), 0.0, L)
def run(m, L, knee, vmode=0, roff=2, **kw):
    k = dict(RG.KNEES[knee]); k.update(vmode=vmode, roff=roff, step_lo=0.1, step_hi=0.25); k.update(kw)
    o, _ = dfe.run(m, L, **k); cg, md = dfe.stats(o, m['r'].shape[1])
    if o.shape[0] > 1: return float(np.median(cg)), float(np.percentile(md, 10))
    return float(cg[0]), float(md[0])
# 1) rolled flags: check macro_cond on rolled ctx == roll of original macro_cond, and that no other F key drives the alarm
for bn in MK:
    c = M[bn]['ctx']
    print(bn, 'F keys', sorted(c.F.keys()), 'shape', c.F['inv'].shape, c.F['inv'].dtype)
    for s in (504, 504 + 63 * 20):
        c2 = copy.copy(c); c2.F = dict(c.F)
        for k in ('inv', 'shock6m'): c2.F[k] = np.roll(c.F[k], s, axis=1)
        a0 = ov.macro_cond(c, ('inv', 'shock6m')); a1 = ov.macro_cond(c2, ('inv', 'shock6m'))
        print('  shift', s, 'macro_cond rolled == roll(orig):', np.array_equal(a1, np.roll(a0, s, axis=1)), 'frac changed', float(np.mean(a0 != a1)))
        st_ref = PX.signal(c, DC.V1S); assert np.array_equal(st_ref, M[bn]['st_v1'])
        st2 = PX.signal(c2, DC.V1S); print('  st frac differ', float(np.mean(st2 != st_ref)))
# 2) twins and placebo spot checks
P = {'T25': (0.1, 1.0, 'K1', 0), 'T40fix': (0.3, 1.0, 'K2', 0), 'T30': (0.2, 1.0, 'K1', 0), 'T40': (0.3, 1.5, 'K2', 2)}
for pk, (sig, Lm, kn, vm) in P.items():
    rows = {}
    for bn in MK:
        m = M[bn]
        pick = run(m, Lpre(m, m['st_v1'], sig, Lm), kn, vm)
        on = run(m, Lpre(m, np.full(m['r'].shape, 3.0), sig, Lm), kn, vm)
        rows[bn] = (pick, on)
        plc = []
        for j in (0, 20, 39):
            s = 504 + 63 * j; c2 = copy.copy(m['ctx']); c2.F = dict(m['ctx'].F)
            for k in ('inv', 'shock6m'): c2.F[k] = np.roll(m['ctx'].F[k], s, axis=1)
            st = PX.signal(c2, DC.V1S); x = run(m, Lpre(m, st, sig, Lm), kn, vm)
            ref = R['placebo'][pk]['per_shift'][bn]
            plc.append((j, round(x[0], 5), round(ref['cagr'][j], 5), round(x[1], 5), round(ref['dd'][j], 5)))
        print(pk, bn, 'pick %.4f/%.4f on %.4f/%.4f' % (pick + on), 'ladder pick %.4f on %.4f' % (R['ladder'][pk]['pick'][bn]['cagr'], R['ladder'][pk]['always_on'][bn]['cagr']), 'plc', plc, flush=True)
    print(pk, 'WD pick %.4f on %.4f' % (min(rows[b][0][1] for b in MK[:3]), min(rows[b][1][1] for b in MK[:3])))
print('done %.0fs' % (time.time() - t0))
