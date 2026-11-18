import json
D = json.load(open('/mnt/project-files/research/df1/results/df5_main.json')); Q = D['qqq']; rows = D['rows']
def show(pref, keys=('X30','X10','P30','REAL')):
    for i, r in rows.items():
        if i.startswith(pref):
            s = []
            for k in keys:
                a = r[k]; q = Q[k]; ddm = 1-abs(a['mdd_p10' if k!='REAL' else 'mdd_med'])/abs(q['mdd_p10' if k!='REAL' else 'mdd_med'])
                s.append('%s pair %+.2f med %+.2f p10 %+.2f ddm %+.1f' % (k, a['pair']*100, (a['cagr']-q['cagr'])*100, (a['p10']-q['p10'])*100, ddm*100))
            print('%-38s' % i, ' | '.join(s))
show('A3|e1.00'); show('A6|'); show('A5|DEF3|U0'); show('A4|GEM')
