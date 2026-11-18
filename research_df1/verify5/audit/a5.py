import json
D = json.load(open('/mnt/project-files/research/df1/results/df5_main.json')); Q = D['qqq']; rows = D['rows']
for i in ['A1|T200|F1.0|TBILL','A1|T200H|F1.0|TBILL','A1|M252|F1.0|TBILL','A1|N|F1.5|TBILL','A1|N|F2.0|TBILL','A1|T200|F2.0|TBILL','A1|VOTE|F1.0|TBILL','A1|D10|F1.0|TBILL','A1|TE3|F1.0|TBILL']:
    r = rows[i]; print('%-25s' % i, ' '.join('%s %.2f/%.1f' % (k, r[k]['cagr']*100, r[k]['mdd_p10']*100) for k in ['REAL','P30','X30']))
print('QQQ', ' '.join('%s %.2f/%.1f' % (k, Q[k]['cagr']*100, Q[k]['mdd_p10']*100) for k in ['REAL','P30','X30']))
