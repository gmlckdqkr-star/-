import json, numpy as np
D = json.load(open('/mnt/project-files/research/df1/results/df5_main.json'))
print(D['meta'])
Q = D['qqq']; print(json.dumps(Q, indent=0))
print('shifts', json.dumps(D['shifts'], indent=0)[:3000])
print('v1locked', D.get('v1locked'))
rows = D['rows']; print('nrows', len(rows))
# X30 zero-margin
for k in ['X30','X10','P30','P10']:
    q = Q[k]; c = []
    for i, r in rows.items():
        a = r[k]
        if a['pair'] > 0 and abs(a['mdd_p10']) <= abs(q['mdd_p10']): c.append((i, a['pair'], 1-abs(a['mdd_p10'])/abs(q['mdd_p10']), a['cagr']-q['cagr'], a['p10']-q['p10']))
    print(k, 'pair>0 & dd shallower (0 margin):', len(c)); 
    for x in sorted(c, key=lambda x: -x[2])[:8]: print('   ', x)
