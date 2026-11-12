"""VXR1 main + stresses -> results/main_le2014.json (development numbers, <=2014)."""
import sys, os, json, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vxrun as R, uprun as U
OUT = '/mnt/project-files/research/vxr1/results/main_le2014.json'
C6 = [(g, s) for g in ('G0', 'G1', 'G2') for s in (0.10, 0.20)]
BASES = ['real_ndx_86_14', 'dev250_path', 'dev250_glued', 'real_spx_55_85', 'real_spx_70_85']
STRESS = {'base': {}, 'a_cost2': dict(cmul=2.0, fee_add=0.01), 'b_cut50': dict(cut=0.50), 'c_gdelay3': dict(gdelay=3), 'd_rf0': dict(rf_on=False)}
res = json.load(open(OUT)) if os.path.exists(OUT) else {}
def save(): json.dump(res, open(OUT, 'w'), indent=1)
res['calib'] = R.calib()
which = sys.argv[1] if len(sys.argv) > 1 else 'main'
for bn in (BASES if which == 'main' else ['real_ndx_86_14', 'dev250_path']):
    for sn, kw in (STRESS.items() if which == 'stress' else [('base', {})]):
        if which == 'stress' and sn == 'base': continue
        key = '%s|%s' % (bn, sn); t = time.time()
        kref = {k: v for k, v in kw.items() if k == 'cmul'}
        ref = R.run(bn, None, 0.0, **kref); rows = {'v1': U.row(ref)}
        if bn == 'real_ndx_86_14': rows['v1']['act_cagr'], rows['v1']['act_mdd'] = R.actual_window(ref)
        for g, s in C6:
            x = R.run(bn, g, s, **kw); rw = U.row(x, ref)
            if bn == 'real_ndx_86_14':
                rw['act_cagr'], rw['act_mdd'] = R.actual_window(x); rw['act_d'] = rw['act_cagr'] - rows['v1']['act_cagr']
            rows['%s_s%02d' % (g, int(s * 100))] = rw
        res[key] = rows; save()
        print(key, '%.0fs' % (time.time() - t), flush=True)
        for nm, rw in rows.items():
            print('  %-8s cagr %6.2f p10 %6.2f mdd %6.1f dd80 %5.1f d %s %s' % (nm, 100 * rw['cagr'], 100 * rw['p10'], 100 * rw['mdd'], 100 * rw['dd80'],
                  ('%+6.2f (%3.0f%%)' % (100 * rw['d_ref'], 100 * rw['pw_ref'])) if 'd_ref' in rw else '',
                  ('ACT %6.2f d %+6.2f mdd %5.1f' % (100 * rw['act_cagr'], 100 * rw.get('act_d', 0), 100 * rw['act_mdd'])) if 'act_cagr' in rw else ''), flush=True)
