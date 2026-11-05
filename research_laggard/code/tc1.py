"""TC1 (PRECOMMIT_TC1.md). Laggard-industry (contrarian) partner + v1 under MS1. <=2014."""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/bottleneck/code')
import tb1, ii, el, sl, dv1
OUT = '/mnt/project-files/research/laggard/results/'
ALL = list(tb1.kf49().columns)
B12 = ['Oil', 'Util', 'Chips', 'Trans', 'Mach', 'Banks', 'Drugs', 'Rtail', 'RlEst', 'Cnstr', 'Hardw', 'Aero']
RULE = {'C1': 252, 'C2': 756}
ST = [(r, u, L) for u in ('B12', 'ALL') for r in RULE for L in (1, 2, 3)]
NM = ['%s_%s_L%d' % x for x in ST]
W = (0.1, 0.2, 0.3)

def tw_for(pool, look, k=3):
    S = sl.src(); idx = pd.DatetimeIndex(S['dates']); n = len(idx); vw = tb1.kf49().reindex(idx)
    for c in pool:
        if 'K_' + c not in S: S['K_' + c] = vw[c].fillna(0.0).values
    lv = np.stack([np.cumsum(np.log1p(S['K_' + c])) for c in pool], axis=1)
    ok = np.stack([vw[c].notna().values for c in pool], axis=1)
    m = len(pool); TW = np.full((n, m), 1.0 / m)
    for t in np.where(S['ME'] > 0.5)[0]:
        if t < look: continue
        sc = lv[t - 21] - lv[t - look]; sc = np.where(ok[t - look] & ok[t], sc, 1e9)     # lowest = laggard; missing never chosen
        w = np.zeros(m); w[np.argsort(sc)[:k]] = 1.0 / k; TW[t] = w
    return TW

_A = {}
def arrays(bn, chunk=50):
    if bn in _A: return _A[bn]
    tb1.build(); ii.ext(); c = ii.ctx(bn); I0 = c['ii']; off = c['off']; P, T = I0.shape
    TWs = {(r, u): tw_for(B12 if u == 'B12' else ALL, RULE[r]) for r in RULE for u in ('B12', 'ALL')}
    S = np.zeros((P, T - ii.WARM, len(ST)), np.float32); SO = np.zeros_like(S); hi = off + int(I0.max()) + 1
    for a in range(0, P, chunk):
        sub = I0[a:a + chunk]; I = sl.inputs(sub, off, hi=hi); g = I.g; z = np.arange(I['T'])[None, :] == 0
        for j, (r, u, L) in enumerate(ST):
            pool = B12 if u == 'B12' else ALL
            A = np.stack([sl.asset(I, 'eq', np.where(z, 0.0, I['K_' + q]), L) for q in pool], axis=2)
            s, so = sl.simw(np.ascontiguousarray(A), I['dep'], np.ascontiguousarray(TWs[(r, u)][g]), I['ME'].copy(), 2, 0.003)
            S[a:a + chunk, :, j] = s[:, ii.WARM:]; SO[a:a + chunk, :, j] = so[:, ii.WARM:]
    _A.clear(); _A[bn] = (S, SO); return S, SO

def run(bn, j, w, cost=0.003):
    TQ, DEP, CU, IDL = ii.ref_in(bn); S, SO = arrays(bn)
    if w == 0:
        Sa = np.zeros((S.shape[0], S.shape[1], 1), S.dtype); SOa = Sa.copy(); wv = np.zeros(1)
    else:
        Sa = np.ascontiguousarray(S[:, :, j:j + 1]); SOa = np.ascontiguousarray(SO[:, :, j:j + 1]); wv = np.array([w])
    return el._comb(np.ascontiguousarray(TQ), np.ascontiguousarray(DEP), np.ascontiguousarray(CU), np.ascontiguousarray(IDL), Sa, SOa,
                    1 - w, wv, 0, cost, ii._PP['tax'], ii._D, int(ii._PP['harvest']), ii._PP['hthr'], 21, 0.05, 0.25)

def early():
    res = {}
    for bn in ('real_spx_55_85', 'real_spx_70_85'):
        f0, E0 = run(bn, 0, 0); g0 = ii.stats(bn, f0, E0)['cagr']
        for j, n in enumerate(NM):
            res.setdefault('_alone|' + n, {})[bn] = float(ii.stats(bn, *run(bn, j, 1.0))['cagr']) * 100
            for w in W:
                f, E = run(bn, j, w); res.setdefault('%s|%.1f' % (n, w), {})[bn] = float(ii.stats(bn, f, E)['cagr'] - g0) * 100
    for k, v in res.items():
        if not k.startswith('_'): v['score'] = min(v['real_spx_55_85'], v['real_spx_70_85'])
    rk = sorted([k for k in res if not k.startswith('_') and '_B12_' in k], key=lambda k: (-round(res[k]['score'], 6), float(k.split('|')[1])))
    ra = sorted([k for k in res if not k.startswith('_') and '_ALL_' in k], key=lambda k: -res[k]['score'])
    json.dump(dict(res=res, rank=rk, rank_all=ra), open(OUT + 'early.json', 'w'), indent=1)
    print({k: {a: round(b, 2) for a, b in v.items()} for k, v in res.items() if k.startswith('_')}, flush=True)
    for k in rk: print('B12', k, {a: round(b, 2) for a, b in res[k].items()}, flush=True)
    for k in ra[:6]: print('ALL(ref)', k, {a: round(b, 2) for a, b in res[k].items()}, flush=True)
    return rk[0], ra[0]

def confirm(keys):
    out = {}; D = dv1.dates('real_ndx_86_14')
    f0, E0 = run('dev250_path', 0, 0); s0 = ii.stats('dev250_path', f0, E0); T = E0.shape[1]; fc0, _ = run('dev250_path', 0, 0, cost=0.006)
    fn, En = run('real_ndx_86_14', 0, 0); gn = ii.stats('real_ndx_86_14', fn, En)['cagr']; b00 = dv1.seg(En[0], D, '2000-01-01', '2014-12-31')
    for k in keys:
        n, w = k.split('|'); j = NM.index(n); w = float(w); r = {}
        f, E = run('dev250_path', j, w); st = ii.stats('dev250_path', f, E); dd = np.log(f / f0) / (T / 252) * 100
        r['path'] = dict(cagr=float(st['cagr']) * 100, mdd=float(st['mdd']), dd80=float(st['dd80']), dmed=float(np.median(dd)), win=float(np.mean(dd > 0)))
        fc, _ = run('dev250_path', j, w, cost=0.006); r['cost2x_dmed'] = float(np.median(np.log(fc / fc0) / (T / 252) * 100))
        f, E = run('real_ndx_86_14', j, w); r['ndx'] = float(ii.stats('real_ndx_86_14', f, E)['cagr']) * 100
        r['d_ndx'] = r['ndx'] - gn * 100; r['d00_14'] = float((dv1.seg(E[0], D, '2000-01-01', '2014-12-31') - b00) * 100)
        p = r['path']
        r['verdict'] = dict(a=bool(p['dmed'] >= 0 and p['win'] >= 0.55), b=bool(r['d_ndx'] >= -1.0), c=bool(r['d00_14'] >= 0),
                            d=bool(p['mdd'] >= -0.90 and p['dd80'] <= s0['dd80']), e=bool(r['cost2x_dmed'] >= -0.3), big=bool(p['dmed'] >= 1.0))
        out[k] = r; print('CONFIRM', k, json.dumps(r), flush=True)
    json.dump(out, open(OUT + 'confirm.json', 'w'), indent=1)

if __name__ == '__main__':
    t = time.time(); top, topall = early(); print('early sec', round(time.time() - t), flush=True); confirm([top, topall]); print('sec', round(time.time() - t))
