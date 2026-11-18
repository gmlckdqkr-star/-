import json, numpy as np
D = json.load(open('/mnt/project-files/research/df1/results/df5_main.json'))
Q = D['qqq']; rows = D['rows']
for k in ['X30','X10']:
    q = Q[k]
    L = []
    for i, r in rows.items():
        a = r[k]; ddm = 1-abs(a['mdd_p10'])/abs(q['mdd_p10'])
        L.append((i, a['pair']*100, ddm*100, (a['cagr']-q['cagr'])*100, (a['p10']-q['p10'])*100))
    # pareto frontier in (pair, ddm)
    L.sort(key=lambda x: -x[1])
    front = []; best = -1e9
    for x in L:
        if x[2] > best: front.append(x); best = x[2]
    print(k, 'pareto frontier (pair pp, ddm %, med diff pp, p10 diff pp):')
    for x in front[:30]: print('   %-45s pair %+.2f ddm %+.1f med %+.2f p10 %+.2f' % x)
for i in ['A3|e1.00|c0.20|GOLD+LTT+DEF3|none','A3|e1.00|c0.50|DEF3|none','A5|DEF3|U0|D2|T200|d0.3']:
    print(i, {k: {kk: round(v*100,2) for kk, v in rows[i][k].items()} for k in ['REAL','P30','P10','X30','X10']})
