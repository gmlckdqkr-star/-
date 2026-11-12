import json, numpy as np
from px1lib import *
F = json.load(open('/mnt/project-files/research/px1/results/foreign_le2014.json'))
SEL = tuple(F['div']['top'][0]['spec']); print('selected', SEL)
out = {'selected': list(SEL)}
for bn, c in std.contexts().items():
    prep(c); row = {}
    for dl in (2, 3):
        a, Ea = run(c, SEL, delay=dl); b, Eb = run(c, V1, delay=dl); d = a - b
        ma = std.row(a, Ea)[0]; mb = std.row(b, Eb)[0]
        row['delay%d' % dl] = dict(cand=ma['cagr'], v1=mb['cagr'], d_med=float(np.median(d)), win=float(np.mean(d > 1e-5)), dd80_cand=ma.get('dd80'), dd80_v1=mb.get('dd80'))
    out[bn] = row; print(bn, json.dumps(row), flush=True)
p, r = out['dev250_path'], out['real_ndx_86_14']
out['PASS'] = bool(p['delay2']['d_med'] > 0 and r['delay2']['d_med'] > 0 and p['delay3']['d_med'] >= 0 and r['delay3']['d_med'] >= 0 and p['delay2']['dd80_cand'] <= p['delay2']['dd80_v1'] + 0.05)
print('PASS', out['PASS'])
json.dump(out, open('/mnt/project-files/research/px1/results/us_oneshot_le2014.json', 'w'), indent=1)
