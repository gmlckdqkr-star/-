import json, numpy as np, ac3
ref = json.load(open('/mnt/project-files/research/measure_std/ref_s085.json'))
for bn in ac3.prep():
    r, cg = ac3.run(bn, 1.0, 0.0, 0.0)
    print('%-15s mine=%.4f  MS1=%.4f  dd80=%s  d_vs_ref=%.2e' % (bn, r['cagr'], ref[bn]['cagr'], r.get('dd80'), r['d_vs_s085']))
