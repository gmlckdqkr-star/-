"""TB2 (PRECOMMIT_TB2.md). Decomposition of TB1 B2_L3 w0.2 near-pass. <=2014."""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/bottleneck/code')
import tb1, ii, el, sl, dv1
from tb1 import OUT, POOL
ALL = list(tb1.kf49().columns)
NONB = [k for k in ALL if k not in POOL]
TRAD = ['Oil', 'Util', 'Chips', 'Trans', 'Mach']
NOCH = [k for k in POOL if k != 'Chips']
SPEC = {'TB1_B2': (POOL, 3, 2), 'R2a_all49': (ALL, 3, 2), 'R2b_nonbottleneck': (NONB, 3, 2), 'R2c_tradeable': (TRAD, 2, 2),
        'R2d_delay5': (POOL, 3, 5), 'R2e_noChips': (NOCH, 3, 2)}
NM = list(SPEC)

def tw_for(pool, k):
    S = sl.src(); idx = pd.DatetimeIndex(S['dates']); n = len(idx)
    vw = tb1.kf49().reindex(idx)
    for c in pool:
        if 'K_' + c not in S: S['K_' + c] = vw[c].fillna(0.0).values
    lv = np.stack([np.cumsum(np.log1p(S['K_' + c])) for c in pool], axis=1)
    ok = np.stack([vw[c].notna().values for c in pool], axis=1)
    m = len(pool); TW = np.full((n, m), 1.0 / m)
    for t in np.where(S['ME'] > 0.5)[0]:
        if t < 252: continue
        sc = lv[t - 21] - lv[t - 252]; sc = np.where(ok[t - 252] & ok[t], sc, -1e9)   # industry must exist over the window
        w = np.zeros(m); w[np.argsort(-sc)[:k]] = 1.0 / k; TW[t] = w
    return TW

_A = {}
def arrays(bn, chunk=50):
    if bn in _A: return _A[bn]
    tb1.build(); ii.ext(); c = ii.ctx(bn); I0 = c['ii']; off = c['off']; P, T = I0.shape
    TWs = {nm: tw_for(p, k) for nm, (p, k, d) in SPEC.items()}
    S = np.zeros((P, T - ii.WARM, len(NM)), np.float32); SO = np.zeros_like(S); hi = off + int(I0.max()) + 1
    for a in range(0, P, chunk):
        sub = I0[a:a + chunk]; I = sl.inputs(sub, off, hi=hi); g = I.g
        for j, nm in enumerate(NM):
            pool, k, d = SPEC[nm]
            A = np.stack([sl.asset(I, 'eq', tb1.np.where(np.arange(I['T'])[None, :] == 0, 0.0, I['K_' + q]), 3) for q in pool], axis=2)
            s, so = sl.simw(np.ascontiguousarray(A), I['dep'], np.ascontiguousarray(TWs[nm][g]), I['ME'].copy(), d, 0.003)
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

if __name__ == '__main__':
    t0 = time.time(); out = {}; w = 0.2; D = dv1.dates('real_ndx_86_14')
    f0, E0 = run('dev250_path', 0, 0); s0 = ii.stats('dev250_path', f0, E0); T = E0.shape[1]; fc0, _ = run('dev250_path', 0, 0, cost=0.006)
    rows = {}
    for j, nm in enumerate(NM):
        f, E = run('dev250_path', j, w); st = ii.stats('dev250_path', f, E); dd = np.log(f / f0) / (T / 252) * 100
        fc, _ = run('dev250_path', j, w, cost=0.006)
        rows[nm] = dict(path=float(st['cagr']) * 100, mdd=float(st['mdd']), dd80=float(st['dd80']), dmed=float(np.median(dd)), win=float(np.mean(dd > 0)),
                        cost2x=float(np.median(np.log(fc / fc0) / (T / 252) * 100)))
    fn, En = run('real_ndx_86_14', 0, 0); gn = ii.stats('real_ndx_86_14', fn, En)['cagr']; b00 = dv1.seg(En[0], D, '2000-01-01', '2014-12-31')
    for j, nm in enumerate(NM):
        f, E = run('real_ndx_86_14', j, w); r = rows[nm]; r['ndx'] = float(ii.stats('real_ndx_86_14', f, E)['cagr']) * 100
        r['d_ndx'] = r['ndx'] - gn * 100; r['d00_14'] = float((dv1.seg(E[0], D, '2000-01-01', '2014-12-31') - b00) * 100)
        fa, Ea = run('real_ndx_86_14', j, 1.0); r['alone_ndx'] = float(ii.stats('real_ndx_86_14', fa, Ea)['cagr']) * 100
    for bn in ('real_spx_55_85', 'real_spx_70_85'):
        fb, Eb = run(bn, 0, 0); gb = ii.stats(bn, fb, Eb)['cagr']
        for j, nm in enumerate(NM):
            f, E = run(bn, j, w); rows[nm]['d_' + bn[9:]] = float(ii.stats(bn, f, E)['cagr'] - gb) * 100
    for nm, r in rows.items():
        r['verdict'] = dict(a=bool(r['dmed'] >= 0 and r['win'] >= 0.55), b=bool(r['d_ndx'] >= -1.0), c=bool(r['d00_14'] >= 0),
                            d=bool(r['mdd'] >= -0.90 and r['dd80'] <= s0['dd80']), e=bool(r['cost2x'] >= -0.3))
        print(nm, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    json.dump(rows, open(OUT + 'tb2.json', 'w'), indent=1); print('sec', round(time.time() - t0))
