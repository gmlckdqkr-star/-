"""DV1 (PRECOMMIT_DV1.md sha fc9cb1c5). <=2014 only. s0.85 + partner fixed-weight combos on the I_INTEGRATE / MS1 engine.
usage: python3 dv1.py early | confirm"""
import os, sys, json, time, itertools, numpy as np
sys.path.insert(0, '/mnt/project-files/research/c3_create/lanes/I_INTEGRATE/code')
import ii, el, sl
OUT = '/mnt/project-files/research/diversifier/results/'
KF = ('VALUE', 'LOWVOL', 'INDMOM', 'EW9', 'VALPROF', 'VALPROF4')
PAIRSET = ['VALPROF4_L1', 'VALUE_L2', 'BOND10_L3', 'CAPE_L3', 'GOLDHV_L2', 'LOWVOL_L2', 'EW9_L2']

def cands():
    C = []
    for s in ii.SID:
        for w in (0.1, 0.2, 0.3, 0.4, 0.5): C.append({s: w})
    for a, b in itertools.combinations(PAIRSET, 2):
        for w in (0.2, 0.3, 0.4): C.append({a: w / 2, b: w / 2})
    return C

def key(c): return '+'.join('%s:%.2f' % (s, w) for s, w in sorted(c.items()))

def run(bn, w, drag=0.6, cost=0.003, kfdrag=True):
    TQ, DEP, CU, IDL = ii.ref_in(bn); S, SO = ii.arrays(bn)
    wv = np.array([w.get(s, 0.0) for s in ii.SID]); act = np.where(wv > 1e-9)[0]
    Sa = np.array(S[:, :, act], dtype=np.float64); SOa = np.ascontiguousarray(SO[:, :, act])
    for j, i in enumerate(act):
        if kfdrag and ii.SID[i].rsplit('_L', 1)[0] in KF: Sa[:, :, j] -= drag / 100 / 252
    Sa = np.ascontiguousarray(Sa.astype(S.dtype))
    return el._comb(np.ascontiguousarray(TQ), np.ascontiguousarray(DEP), np.ascontiguousarray(CU), np.ascontiguousarray(IDL), Sa, SOa,
                    float(1 - wv.sum()), np.ascontiguousarray(wv[act]), 0, cost, ii._PP['tax'], ii._D, int(ii._PP['harvest']), ii._PP['hthr'], 21, 0.05, 0.25)

def dates(bn):
    c = el.ctx(bn); S = sl.src()
    return np.asarray(S['dates'])[c['off'] + np.asarray(c['ii'])[0]][ii.WARM:]

def seg(E, d, a, b):
    m = (d >= np.datetime64(a)) & (d <= np.datetime64(b)); ix = np.where(m)[0]
    i0 = max(ix[0] - 1, 0); i1 = ix[-1]; return (E[i1] / E[i0]) ** (252.0 / (i1 - i0)) - 1

ERA = {'55-69': ('real_spx_55_85', '1955-01-01', '1969-12-31'), '70-85': ('real_spx_70_85', '1970-01-01', '1985-12-31'),
       '86-99': ('real_ndx_86_14', '1986-01-01', '1999-12-31'), '00-14': ('real_ndx_86_14', '2000-01-01', '2014-12-31')}

def early():
    res = {}; D = {bn: dates(bn) for bn in ('real_spx_55_85', 'real_spx_70_85', 'real_ndx_86_14')}
    base = {}
    for nm, (bn, a, b) in ERA.items():
        if nm == '00-14': continue
        fin, E = ii.run(bn, 1.0, {}); base[nm] = seg(E[0], D[bn], a, b)
    res['_base'] = base
    for c in cands():
        r = {}
        for nm, (bn, a, b) in ERA.items():
            if nm == '00-14': continue
            fin, E = run(bn, c); r[nm] = (seg(E[0], D[bn], a, b) - base[nm]) * 100
        r['score'] = min(r.values()); res[key(c)] = r
    json.dump(res, open(OUT + 'early.json', 'w'), indent=1)
    rk = sorted([k for k in res if not k.startswith('_')], key=lambda k: -res[k]['score'])
    for k in rk[:15]: print(k, {x: round(v, 2) for x, v in res[k].items()})
    json.dump(rk[:5], open(OUT + 'top5.json', 'w'))

def parse(k): return {p.split(':')[0]: float(p.split(':')[1]) for p in k.split('+')}

def confirm():
    top = json.load(open(OUT + 'top5.json')); res = {}
    D = dates('real_ndx_86_14'); fin, E = ii.run('real_ndx_86_14', 1.0, {}); b00 = seg(E[0], D, *ERA['00-14'][1:])
    f0, E0 = ii.run('dev250_path', 1.0, {}); r0 = ii.stats('dev250_path', f0, E0); T = E0.shape[1]
    res['_s085'] = dict(path=float(r0['cagr']), dd80=float(r0['dd80']), nd00_14=float(b00))
    f0c, _ = run('dev250_path', {}, cost=0.006) if False else ii.run('dev250_path', 1.0, {}) , None
    # cost 2x reference: s0.85 alone with cost 2x through the same _comb call
    TQ, DEP, CU, IDL = ii.ref_in('dev250_path'); S, SO = ii.arrays('dev250_path')
    z = np.zeros((S.shape[0], S.shape[1], 1), S.dtype)
    fc0, _ = el._comb(np.ascontiguousarray(TQ), np.ascontiguousarray(DEP), np.ascontiguousarray(CU), np.ascontiguousarray(IDL), z, z.copy(),
                      1.0, np.zeros(1), 0, 0.006, ii._PP['tax'], ii._D, int(ii._PP['harvest']), ii._PP['hthr'], 21, 0.05, 0.25)
    for k in top:
        c = parse(k); r = {}
        fin, E = run('real_ndx_86_14', c); r['d00_14'] = float((seg(E[0], D, *ERA['00-14'][1:]) - b00) * 100)
        for dg in (0.0, 0.6, 1.5, 2.5):
            fin, E = run('dev250_path', c, drag=dg); st = ii.stats('dev250_path', fin, E)
            dd = np.log(fin / f0) / (T / 252) * 100
            r['path_drag%.1f' % dg] = dict(cagr=float(st['cagr']) * 100, dd80=float(st['dd80']), dmed=float(np.median(dd)), win=float(np.mean(dd > 0)))
        fin, E = run('dev250_path', c, cost=0.006); dd = np.log(fin / fc0) / (T / 252) * 100
        r['cost2x_dmed'] = float(np.median(dd))
        for bn in ('real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85', 'dev250_glued'):
            fin, E = run(bn, c); r[bn] = float(ii.stats(bn, fin, E)['cagr']) * 100
        p = r['path_drag0.6']
        r['verdict'] = {k_: bool(v_) for k_, v_ in dict(a=r['d00_14'] >= 0, b=(p['dmed'] >= 0 and p['win'] >= 0.5), c=p['dd80'] <= r0['dd80'] / 2, d=r['cost2x_dmed'] >= -0.3).items()}
        res[k] = r; print(k, json.dumps(r), flush=True)
    json.dump(res, open(OUT + 'confirm.json', 'w'), indent=1)

if __name__ == '__main__':
    t = time.time(); {'early': early, 'confirm': confirm}[sys.argv[1]](); print('sec', round(time.time() - t))
