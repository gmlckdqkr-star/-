import json, numpy as np
R = json.load(open('rebuild_raw.json'))['cfg']; D = json.load(open('/mnt/project-files/research/df1/results/df3.json'))['configs']
out = {}
for key, mine in (('P0', 'dev250_path|bx0'), ('P', 'dev250_path|std'), ('N', 'real_ndx_86_14|std'), ('N', 'real_ndx_86_14|bx0'), ('S', 'real_spx_29_54|std'), ('S', 'real_spx_29_54|bx0')):
    mx = {}; 
    for st in ('cagr', 'p10', 'mdd', 'mdd_p10'):
        d = [abs(D[i][key][st] - R[i][mine][st]) for i in D if st in D[i][key]]
        if d: mx[st] = float(max(d))
    worst = max(D, key=lambda i: abs(D[i][key]['cagr'] - R[i][mine]['cagr']))
    out[key + '_vs_' + mine] = mx; print('%-3s vs %-20s maxabs %s  worst %s' % (key, mine, mx, worst))
json.dump(out, open('cmp_df3.json', 'w'), indent=1)
