"""JS1 confirmation (PRECOMMIT s.6) + reference alarm rules (s.5). usage: js1_confirm.py DATA.npz OUTDIR   (reads full_real.npz, rand_real_*.npz)"""
import sys, os, glob, json, numpy as np, hashlib
sys.path.insert(0, '/home/user/repo/research_js1/code'); import js1_ref as R, js1_kern as K
data, out = sys.argv[1:3]; P = dict(np.load(data, allow_pickle=True)); A = P['A']; X = P['X']; yrs = P['years']; ctry = list(P['ctry'])
def obs(pre):
    sl = P[pre + '_slot']; o = np.lexsort((sl[:, 1], sl[:, 0])); return sl[o, 0], sl[o, 1]
dc, dt = obs('des'); cc, ct = obs('con')
def z_any(on, oc, ot, m, Xa=None):
    """same formula as the kernel, no class/size filters; also returns skill>0 country count."""
    x = (X if Xa is None else Xa)[m, oc, ot]; skill = 0.0; var = 0.0; flips = 0; pos = 0; nun = 0
    for c in np.unique(oc):
        i = oc == c; xi = x[i]; oi = on[i]; ti = ot[i]; nu = len(xi); mu = xi.mean(); p = oi.mean()
        s = float(((xi - mu) * oi).sum()); skill += s; var += p * (1 - p) * nu / (nu - 1) * float(((xi - mu) ** 2).sum()); flips += int(((oi[1:] != oi[:-1]) & (ti[1:] == ti[:-1] + 1)).sum())
        if 0 < p < 1: nun += 1; pos += s > 0
    z = (skill - R.COST[m] * flips) / np.sqrt(var) if var > 0 else 0.0
    return z, pos, nun, float(on.mean())
def cand_lists():
    L = {0: {}, 1: {}}
    for f in [out + '/full_real.npz'] + sorted(glob.glob(out + '/rand_real_*.npz')):
        d = np.load(f)
        for m in (0, 1):
            for z, c in zip(d['topz'][m], d['topc'][m]):
                if z > -1e200: L[m][int(c)] = float(z)
    return L
def pattern(code): return hashlib.md5(np.packbits(R.cond(A, code)[dc, dt]).tobytes()).hexdigest()
def select(L, m, k=20):
    sel = []; seen = set()
    for code, z in sorted(L[m].items(), key=lambda t: -t[1]):
        h = pattern(code)
        if h in seen: continue
        seen.add(h); sel.append((code, z))
        if len(sel) == k: break
    return sel
def name(code):
    sh = code & 31; ids = [(code >> s) & 2047 for s in (5, 16, 27, 38)]; nm = [str(P['names'][i]) for i in ids]
    f = {0: '{0}', 1: '{0} & {1}', 2: '{0} | {1}', 3: '{0} & {1} & {2}', 4: '{0} | {1} | {2}', 5: '{0} & ({1} | {2})', 6: '{1} & ({0} | {2})', 7: '{2} & ({0} | {1})',
         8: '{0} | ({1} & {2})', 9: '{1} | ({0} & {2})', 10: '{2} | ({0} & {1})', 11: '{0} & {1} & {2} & {3}', 12: '({0} & {1}) | ({2} & {3})', 13: '{0} & {1} & ({2} | {3})',
         14: '{0} & ({1} | {2} | {3})', 15: '{0} | {1} | {2} | {3}', 16: '({0} | {1}) & ({2} | {3})'}[sh]
    return f.format(*nm)
if __name__ == '__main__':
    L = cand_lists(); res = {'cands': []}
    for m in (0, 1):
        for code, zd in select(L, m):
            on_d = R.cond(A, code)[dc, dt]; on_c = R.cond(A, code)[cc, ct]
            zc, pos, nun, frac = z_any(on_c, cc, ct, m)
            res['cands'].append(dict(map=m, code=code, name=name(code), z_design=zd, z_confirm=float(zc), pos_units=int(pos), n_units=int(nun), on_frac_con=frac, on_frac_des=float(on_d.mean()),
                                     L1=bool(zc >= 3.0 and nun and pos / nun >= 0.625)))
    # reference alarm rules (not searched): ON = not alarm
    nm = {n: i for i, n in enumerate(P['names'])}
    inv1, shock1 = A[nm['NAT inv1']], A[nm['NAT shock1']]
    gl = np.zeros_like(inv1)                                   # g1_EQ < 0 is not an atom: build from outcomes of previous year
    ret = P['r']; prev = np.full_like(ret, np.nan); prev[:, 1:] = ret[:, :-1]; gl = np.where(np.isnan(prev), False, prev < 0)
    refs = {'A1 OFF=inv1': ~inv1, 'A2 OFF=shock1': ~shock1, 'A3 OFF=inv1|shock1': ~(inv1 | shock1), 'A4 OFF=(ret1<0)&(inv1|shock1)': ~(gl & (inv1 | shock1))}
    res['refs'] = {}
    for k, ONm in refs.items():
        d = {}
        for m in range(3):
            zd = z_any(ONm[dc, dt], dc, dt, m); zc = z_any(ONm[cc, ct], cc, ct, m); d['map%d' % m] = dict(design=zd, confirm=zc)
        # placebo: roll outcomes within design window
        pz = {m: [] for m in range(3)}; i0 = int(np.where(yrs == 1870)[0][0]); i1 = int(np.where(yrs == 1984)[0][0]) + 1
        for p in range(200):
            sh = int(np.random.default_rng(1000 + p).integers(5, 111)); Xr = X.copy(); Xr[:, :, i0:i1] = np.roll(X[:, :, i0:i1], sh, axis=2)
            for m in range(3):
                xs = Xr[m]; xs = np.where(np.isnan(xs), np.nanmean(xs, axis=1, keepdims=True), xs)
                Xt = X.copy(); Xt[m] = xs; pz[m].append(z_any(ONm[dc, dt], dc, dt, m, Xt)[0])
        for m in range(3): d['map%d' % m]['p_placebo'] = (1 + sum(v >= d['map%d' % m]['design'][0] for v in pz[m])) / 201
        res['refs'][k] = d
    json.dump(res, open(out + '/confirm.json', 'w'), indent=1, default=str)
    for c in res['cands'][:6] + res['cands'][20:26]: print(c['map'], '%.2f' % c['z_design'], '%.2f' % c['z_confirm'], c['pos_units'], '/', c['n_units'], c['L1'], c['name'][:110])
    print('L1 passes:', sum(c['L1'] for c in res['cands']), 'of', len(res['cands']))
    for k, d in res['refs'].items(): print(k, {m: ('des %.2f' % v['design'][0], 'con %.2f' % v['confirm'][0], 'p %.3f' % v['p_placebo']) for m, v in d.items()})
