import json, re
D = json.load(open('/mnt/project-files/research/df1/results/df5_main.json'))
Q = D['qqq']; rows = D['rows']; q = Q['X30']; qp = Q['P30']
def show(pat):
    for i, r in rows.items():
        if re.match(pat, i) and 'X30' in r:
            a = r['X30']; b = r['P30']
            print('%-42s X30 pair %+.4f ddm %+.3f med %.4f | P30 pair %+.4f ddm %+.3f' % (i, a['pair'], 1 - abs(a['mdd_p10'])/abs(q['mdd_p10']), a['cagr'], b['pair'], 1-abs(b['mdd_p10'])/abs(qp['mdd_p10'])))
show(r'A3\|e1.00\|.*\|none'); print()
show(r'A1\|N\|V0.20'); print()
show(r'A1\|(T200|VOTE|TE3)\|V0.20w20L1.5\|DEF3'); print()
show(r'A6\|'); print()
show(r'A2\|N\|'); print()
