import json
D = json.load(open('/mnt/project-files/research/df1/results/df5_main.json')); Q = D['qqq']; rows = D['rows']
def ddm(i, k): return 1 - abs(rows[i][k]['mdd_p10']) / abs(Q[k]['mdd_p10'])
L = []
for i in rows:
    if ddm(i, 'X30') >= 0.1 and ddm(i, 'X10') >= 0.1:
        a, b = rows[i]['X30'], rows[i]['X10']
        worst = min(a['pair'], a['cagr'] - Q['X30']['cagr'], a['p10'] - Q['X30']['p10'], b['pair'], b['cagr'] - Q['X10']['cagr'], b['p10'] - Q['X10']['p10'])
        L.append((worst * 100, i, a['pair'] * 100, b['pair'] * 100))
L.sort(reverse=True)
print('configs with >=10% DD margin in both X30 and X10:', len(L))
for x in L[:15]: print('  worst return-gap %+.2fpp  %-35s X30 pair %+.2f X10 pair %+.2f' % x)
