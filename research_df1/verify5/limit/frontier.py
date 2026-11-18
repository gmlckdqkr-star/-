import json, numpy as np
D = json.load(open('/mnt/project-files/research/df1/results/df5_main.json'))
Q = D['qqq']; rows = D['rows']
print('QQQ', {k: {kk: round(vv, 4) for kk, vv in v.items()} for k, v in Q.items()})
q = Q['X30']
rs = []
for i, r in rows.items():
    if 'X30' not in r: continue
    a = r['X30']; ddm = 1 - abs(a['mdd_p10']) / abs(q['mdd_p10'])
    rs.append((i, a['pair'], ddm, a['cagr'], a['p10'], a['mdd_p10'], r['fam']))
print('n', len(rs))
sh = [x for x in rs if x[2] > 0]
print('--- highest pair among p10MDD shallower than QQQ (X30)')
for x in sorted(sh, key=lambda x: -x[1])[:15]: print('%-45s pair %+.4f ddm %+.3f med %.4f p10 %.4f mddp10 %.4f %s' % x)
pp = [x for x in rs if x[1] > 0]
print('--- shallowest p10 MDD among pair>0 (X30)')
for x in sorted(pp, key=lambda x: -x[2])[:15]: print('%-45s pair %+.4f ddm %+.3f med %.4f p10 %.4f mddp10 %.4f %s' % x)
print('--- A1 vol-target best by pair+ddm')
a1 = [x for x in rs if x[0].startswith('A1|') and '|V' in x[0]]
for x in sorted(a1, key=lambda x: -(x[1]*10 + x[2]))[:10]: print('%-45s pair %+.4f ddm %+.3f med %.4f p10 %.4f mddp10 %.4f %s' % x)
print('--- A3 static best')
a3 = [x for x in rs if x[0].startswith('A3|') and x[0].endswith('|none')]
for x in sorted(a3, key=lambda x: -(x[1]*10 + x[2]))[:12]: print('%-45s pair %+.4f ddm %+.3f med %.4f p10 %.4f mddp10 %.4f %s' % x)
# Pareto front in (pair, ddm)
pts = sorted(rs, key=lambda x: (-x[1], -x[2]))
front = []; best = -9
for x in pts:
    if x[2] > best: front.append(x); best = x[2]
print('--- Pareto front (pair desc)')
for x in front: print('%-45s pair %+.4f ddm %+.3f med %.4f p10 %.4f mddp10 %.4f %s' % x)
