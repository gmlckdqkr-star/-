"""TB1 step 2-3: early selection (1955-85 SPX eras, 27 trials) then confirm top-1 (verdict) + top-2..3 (reference). PRECOMMIT sha 0e057f32."""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/bottleneck/code')
import tb1, ii, dv1
from tb1 import run, NM, W, OUT

def early():
    res = {}
    for bn in ('real_spx_55_85', 'real_spx_70_85'):
        f0, E0 = run(bn, 0, 0); g0 = ii.stats(bn, f0, E0)['cagr']; res['_v1|' + bn] = g0 * 100
        for j, n in enumerate(NM):
            if n.startswith('K0'): continue
            res.setdefault('_alone|' + n, {})[bn] = float(ii.stats(bn, *run(bn, j, 1.0))['cagr']) * 100
            for w in W:
                f, E = run(bn, j, w); res.setdefault('%s|%.1f' % (n, w), {})[bn] = (ii.stats(bn, f, E)['cagr'] - g0) * 100
    for k, v in res.items():
        if not k.startswith('_'): v['score'] = min(v['real_spx_55_85'], v['real_spx_70_85'])
    rk = sorted([k for k in res if not k.startswith('_')], key=lambda k: (-round(res[k]['score'], 6), float(k.split('|')[1])))
    json.dump(dict(res=res, rank=rk), open(OUT + 'early.json', 'w'), indent=1)
    print({k: v for k, v in res.items() if k.startswith('_')}, flush=True)
    for k in rk: print(k, {a: round(b, 2) for a, b in res[k].items()}, flush=True)
    return rk[:3]

def confirm(top):
    out = {}; D = dv1.dates('real_ndx_86_14')
    f0, E0 = run('dev250_path', 0, 0); s0 = ii.stats('dev250_path', f0, E0); T = E0.shape[1]
    fc0, _ = run('dev250_path', 0, 0, cost=0.006)
    fn, En = run('real_ndx_86_14', 0, 0); gn = ii.stats('real_ndx_86_14', fn, En)['cagr']; b00 = dv1.seg(En[0], D, '2000-01-01', '2014-12-31')
    out['_v1'] = dict(path=float(s0['cagr']) * 100, dd80=float(s0['dd80']), mdd=float(s0['mdd']), ndx=float(gn) * 100, nd00=float(b00) * 100)
    for k in top:
        n, w = k.split('|'); j = NM.index(n); w = float(w); r = {}
        f, E = run('dev250_path', j, w); st = ii.stats('dev250_path', f, E); dd = np.log(f / f0) / (T / 252) * 100
        r['path'] = dict(cagr=float(st['cagr']) * 100, mdd=float(st['mdd']), dd80=float(st['dd80']), dmed=float(np.median(dd)), win=float(np.mean(dd > 0)))
        fc, _ = run('dev250_path', j, w, cost=0.006); r['cost2x_dmed'] = float(np.median(np.log(fc / fc0) / (T / 252) * 100))
        f, E = run('real_ndx_86_14', j, w); r['ndx'] = float(ii.stats('real_ndx_86_14', f, E)['cagr']) * 100
        r['d_ndx'] = r['ndx'] - gn * 100; r['d00_14'] = float((dv1.seg(E[0], D, '2000-01-01', '2014-12-31') - b00) * 100)
        r['d86_99'] = float((dv1.seg(E[0], D, '1986-01-01', '1999-12-31') - dv1.seg(En[0], D, '1986-01-01', '1999-12-31')) * 100)
        p = r['path']
        r['verdict'] = dict(a=bool(p['dmed'] >= 0 and p['win'] >= 0.55), b=bool(r['d_ndx'] >= -1.0), c=bool(r['d00_14'] >= 0),
                            d=bool(p['mdd'] >= -0.90 and p['dd80'] <= s0['dd80']), e=bool(r['cost2x_dmed'] >= -0.3), big=bool(p['dmed'] >= 1.0))
        out[k] = r; print(k, json.dumps(r), flush=True)
    json.dump(out, open(OUT + 'confirm.json', 'w'), indent=1)

if __name__ == '__main__':
    t = time.time(); top = early(); print('early sec', round(time.time() - t), flush=True); confirm(top); print('sec', round(time.time() - t))
