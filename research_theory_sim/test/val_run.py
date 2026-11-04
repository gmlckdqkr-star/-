import sys, json, numpy as np; sys.path.insert(0, '/mnt/project-files/research/theory_sim/test'); import harness as H
ref = json.load(open('/mnt/project-files/research/measure_std/ref_s085.json'))
r = H.load_rule('/mnt/project-files/research/theory_sim/test/val/const3.py')
o = H.measure(r, 'const3', verbose=False)
for bn in H.STD_BASES:
    print(bn, 'ref_s085 %.5f vs locked %.5f' % (o[bn]['ref_s085'], ref[bn]['cagr']), '| const3 %.5f vs hold3x %.5f' % (o[bn]['cagr'], o[bn]['hold3x']), '| hold1x %.5f vs locked %.5f' % (o[bn]['hold1x'], ref[bn]['hold1x']))
print('spx29', o['real_spx_29_85'])
r2 = H.load_rule('/mnt/project-files/research/theory_sim/test/val/sma_y10.py')
print('causality sma_y10', H.causality(r2, n_cut=30))
o2 = H.measure(r2, 'sma_y10', bases=('dev250_path', 'real_ndx_86_14'), verbose=True)
