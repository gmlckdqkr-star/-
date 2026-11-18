import json, collections
R='/mnt/project-files/research/df1/results/'
F=json.load(open(R+'df6_final.json')); M=json.load(open(R+'df6_main.json'))
print(sorted(F.keys())); print('counts',F['counts']); print('select',F['select']); print('kstar_top',F.get('kstar_top_reportonly'))
H=F['H']; gp=F['gpass']; print(len(gp))
c=collections.Counter(tuple(H[i]['fails']) for i in gp); print(c)
print('tiers',collections.Counter(H[i]['tier'] for i in gp))
only=[i for i in gp if [f for f in H[i]['fails'] if f in ('H1','H2','H3','H4','H5')]==['H4']]
print('onlyH4',len(only))
G=M['gates']
for i in only: print(i, H[i]['H4'], 'score %.4f ddm %.3f'%(G[i]['score'],G[i]['ddm']), 'G6 real ddm', round(1-H[i]['G6']['real_v']['mdd']/H[i]['G6']['real_v']['core_mdd'],4))
# G6 margins for all
dd=[]
for i in gp:
    rv=H[i]['G6']['real_v']; bv=H[i]['G6']['boot_v']; bc=H[i]['G6']['boot_core']
    dd.append((1-abs(rv['mdd'])/abs(rv['core_mdd']), 1-abs(bv['mdd_p10'])/abs(bc['mdd_p10']), rv['cagr']-rv['core_cagr']))
print('G6 real ddm range %.4f..%.4f, boot ddm %.4f..%.4f, real cagr diff %.4f..%.4f'%(min(x[0] for x in dd),max(x[0] for x in dd),min(x[1] for x in dd),max(x[1] for x in dd),min(x[2] for x in dd),max(x[2] for x in dd)))
print('H6 pass',sum(H[i]['H6'] for i in gp),'H7',sum(H[i]['H7'] for i in gp),'N3ks',sum(H[i]['N3ks'] for i in gp),'H5',sum(H[i]['H5'] for i in gp))
