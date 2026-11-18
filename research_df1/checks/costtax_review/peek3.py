import json
D='/mnt/project-files/research/df1/checks/costtax/'
for v in ['base','W0_30M','W0_100M','W0_300M','bond7y','bondER25','harvest0','cost020','cost045','combo_mid','combo_adv']:
    R=json.load(open(D+'resel_%s.json'%v)); t=R['tiers']['T40']; cp=R['compact']
    g=t.get('gate')
    print(v, 'union',t['union_best'], cp[t['union_best']][:2], 'df1',t['df1_best'], cp[t['df1_best']][:2], '| src->',t['adopted_src'], cp[t['adopted_src']][0], '| path->',t['adopted_path'], cp[t['adopted_path']][0])
    if g: print('    gate df2',g['df2'],'\n    gate df1',g['df1'])
r=json.load(open(D+'result.json')); print(r['base_reproduction'])
