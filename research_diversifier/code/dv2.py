"""DV2 (PRECOMMIT_DV2.md sha 6b76bc16). <=2014. s0.85 + fixed-weight 2x/3x sector/small/SPX partner under MS1 (el._comb)."""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/c3_create/lanes/I_INTEGRATE/code')
sys.path.insert(0, '/mnt/project-files/research/diversifier/code')
import ii, el, sl, kf_parse
import dv1
OUT = '/mnt/project-files/research/diversifier/results/'
ST = [(s, 2) for s in ['HLTH', 'UTIL', 'FIN', 'ENER', 'SHOP', 'MANU', 'STAP', 'TELE', 'SMALL', 'SPX', 'TECH']] + \
     [(s, 3) for s in ['HLTH', 'UTIL', 'FIN', 'SHOP', 'MANU', 'SMALL', 'SPX', 'TECH']]
NM = ['%s_L%d' % x for x in ST]

def add_small():
    S = sl.src()
    if 'SMALL' in S: return
    import pandas as pd
    S6 = kf_parse.sections('/mnt/project-files/research/data/ken_french/raw/cur/6_Portfolios_2x3_daily_CSV.zip')
    vw = [v for k, v in S6.items() if k.startswith('The')][0]; vw = vw[vw.index <= pd.Timestamp('2014-12-31')]
    sm = vw[['SMALL LoBM', 'ME1 BM2', 'SMALL HiBM']].mean(axis=1) / 100.0
    S['SMALL'] = sm.reindex(pd.DatetimeIndex(S['dates'])).fillna(0.0).values

_A = {}
def arrays(bn, chunk=100):
    if bn in _A: return _A[bn]
    add_small(); ii.ext(); c = ii.ctx(bn); I0 = c['ii']; off = c['off']; P, T = I0.shape
    S = np.zeros((P, T - ii.WARM, len(ST)), np.float32); SO = np.zeros_like(S); hi = off + int(I0.max()) + 1
    for a in range(0, P, chunk):
        sub = I0[a:a + chunk]; I = sl.inputs(sub, off, hi=hi); p, t = I['P'], I['T']
        for j, (nm, L) in enumerate(ST):
            r = I[nm]
            if nm == 'SMALL': r = r.copy(); r[:, 0] = 0.0
            A = sl.asset(I, 'eq', r, L)[:, :, None]; TW = np.ones((p, t, 1)); dc = np.zeros((p, t)); dc[:, 0] = 1.0
            s, so = sl.simw(np.ascontiguousarray(A), I['dep'], np.ascontiguousarray(TW), dc, 0, 0.003)
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

W = (0.1, 0.2, 0.3, 0.4)
def early():
    res = {}
    for bn in ('real_spx_55_85', 'real_spx_70_85'):
        f0, E0 = run(bn, 0, 0); g0 = ii.stats(bn, f0, E0)['cagr']; res['_s085|' + bn] = g0
        for j, n in enumerate(NM):
            for w in W:
                f, E = run(bn, j, w); res.setdefault('%s|%.1f' % (n, w), {})[bn] = (ii.stats(bn, f, E)['cagr'] - g0) * 100
    for k, v in res.items():
        if not k.startswith('_'): v['score'] = min(v['real_spx_55_85'], v['real_spx_70_85'])
    rk = sorted([k for k in res if not k.startswith('_')], key=lambda k: (-round(res[k]['score'], 6), float(k.split('|')[1])))
    json.dump(dict(res=res, rank=rk), open(OUT + 'dv2_early.json', 'w'), indent=1)
    for k in rk[:12]: print(k, {a: round(b, 2) for a, b in res[k].items()})
    return rk[:5]

def confirm(top):
    out = {}; D = dv1.dates('real_ndx_86_14')
    f0, E0 = run('dev250_path', 0, 0); s0 = ii.stats('dev250_path', f0, E0); T = E0.shape[1]
    fc0, _ = run('dev250_path', 0, 0, cost=0.006)
    fn, En = run('real_ndx_86_14', 0, 0); gn = ii.stats('real_ndx_86_14', fn, En)['cagr']; b00 = dv1.seg(En[0], D, '2000-01-01', '2014-12-31')
    out['_s085'] = dict(path=float(s0['cagr']), dd80=float(s0['dd80']), mdd=float(s0['mdd']), ndx=float(gn), nd00=float(b00))
    for k in top:
        n, w = k.split('|'); j = NM.index(n); w = float(w); r = {}
        f, E = run('dev250_path', j, w); st = ii.stats('dev250_path', f, E); dd = np.log(f / f0) / (T / 252) * 100
        r['path'] = dict(cagr=float(st['cagr']) * 100, mdd=float(st['mdd']), dd80=float(st['dd80']), p10=float(st.get('p10', np.nan)), dmed=float(np.median(dd)), win=float(np.mean(dd > 0)))
        fc, _ = run('dev250_path', j, w, cost=0.006); r['cost2x_dmed'] = float(np.median(np.log(fc / fc0) / (T / 252) * 100))
        f, E = run('real_ndx_86_14', j, w); r['ndx'] = float(ii.stats('real_ndx_86_14', f, E)['cagr']) * 100
        r['d_ndx'] = r['ndx'] - gn * 100; r['d00_14'] = float((dv1.seg(E[0], D, '2000-01-01', '2014-12-31') - b00) * 100)
        for bn in ('real_spx_55_85', 'real_spx_70_85', 'dev250_glued'):
            f, E = run(bn, j, w); r[bn] = float(ii.stats(bn, f, E)['cagr']) * 100
        p = r['path']
        r['verdict'] = dict(a=bool(p['dmed'] >= 0 and p['win'] >= 0.55), b=bool(r['d_ndx'] >= -1.0), c=bool(r['d00_14'] >= 0),
                            d=bool(p['mdd'] >= -0.90 and p['dd80'] <= s0['dd80']), e=bool(r['cost2x_dmed'] >= -0.3))
        out[k] = r; print(k, json.dumps(r), flush=True)
    json.dump(out, open(OUT + 'dv2_confirm.json', 'w'), indent=1)

if __name__ == '__main__':
    t = time.time(); top = early(); print('early sec', round(time.time() - t), flush=True); confirm(top); print('sec', round(time.time() - t))
