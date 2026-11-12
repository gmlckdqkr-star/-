"""ADDENDUM 1: P6 tail injection (10y, 5y), P7 PTP 10% sale withholding -> results/add1_le2014.json"""
import sys, os, json, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vxrun as R, uprun as U
OUT = '/mnt/project-files/research/vxr1/results/add1_le2014.json'
C6 = [(g, s) for g in ('G0', 'G1', 'G2') for s in (0.10, 0.20)]
res = {}
SEED = 20261112
for bn in ['dev250_path', 'real_ndx_86_14']:
    ref = R.run(bn, None, 0.0)
    if bn == 'real_ndx_86_14': refa = R.actual_window(ref)[0]
    for g, s in C6:
        nm = '%s_s%02d' % (g, int(s * 100)); t = time.time()
        row = {}
        for tag, kw in (('inj10', dict(inject=(10, SEED))), ('inj5', dict(inject=(5, SEED))), ('ptp10', dict(ptp=0.10))):
            if bn == 'dev250_path':
                x = R.run(bn, g, s, **kw); rw = U.row(x, ref); row[tag] = dict(d=rw['d_ref'], pw=rw['pw_ref'], cagr=rw['cagr'], dd80=rw['dd80'])
            else:
                seeds = range(SEED, SEED + 200) if tag.startswith('inj') else [SEED]
                ds = []; da = []
                for sd in seeds:
                    kk = dict(kw); 
                    if 'inject' in kk: kk['inject'] = (kw['inject'][0], sd)
                    x = R.run(bn, g, s, **kk); ds.append(x['cagr'][0] - ref['cagr'][0]); da.append(R.actual_window(x)[0] - refa)
                ds = np.array(ds); da = np.array(da)
                row[tag] = dict(d_med=float(np.median(ds)), d_pw=float(np.mean(ds > 0)), act_d_med=float(np.median(da)), act_pw=float(np.mean(da > 0)))
        res.setdefault(bn, {})[nm] = row
        json.dump(res, open(OUT, 'w'), indent=1)
        print(bn, nm, '%.0fs' % (time.time() - t), json.dumps({k: {a: round(100 * b, 2) for a, b in v.items()} for k, v in row.items()}), flush=True)
