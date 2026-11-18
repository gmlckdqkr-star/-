import sys, json, numpy as np
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import df6
D=json.load(open('/mnt/project-files/research/df1/results/df6_main.json')); idx={c['id']:c for c in D['configs']}
F=json.load(open('/mnt/project-files/research/df1/results/df6_final.json'))
GR=df6.g6_world('R2885'); GO=df6.g6_world('OLD6')
print('OLD6 shape', GO['P'], GO['T'], 'R2885 T', GR['T'])
for i in ['L|TQQQ|DEF3|R252|e0.60|c0.80','L|QLD|DEF3|R252|e0.70|c0.60']:
    c=idx[i]; cg,md,qcg,qmd=df6.g6_run(c,GR); cg2,md2,qcg2,qmd2=df6.g6_run(c,GO)
    h=F['H'][i]['G6']
    print(i,'R2885 cagr %.4f mdd %.4f core %.4f %.4f | stored %.4f %.4f %.4f %.4f'%(cg[0],md[0],qcg[0],qmd[0],h['real_v']['cagr'],h['real_v']['mdd'],h['real_v']['core_cagr'],h['real_v']['core_mdd']))
    print('   OLD6 med %.4f p10 %.4f mddp10 %.4f pair %.4f | core med %.4f p10 %.4f mddp10 %.4f'%(np.median(cg2),np.percentile(cg2,10),np.percentile(md2,10),np.median(cg2-qcg2),np.median(qcg2),np.percentile(qcg2,10),np.percentile(qmd2,10)))
# independent gross sim (no tax/cost/delay) on R2885 path, 20% 3x + 80% DEF3, annual rebalance
d=df6.g6_data(); tech=d['TECH']; def3=d['DEF3']; rf=d['RF']; W=300
lev=3*(tech-0.02/252)-2*rf-0.0245/252
def sim(rets, w, reb):
    v=np.array(w,float); E=[]; 
    for k,t in enumerate(range(W+1,len(tech))):
        v=v*(1+np.array([r[t] for r in rets]))
        if reb and (k+1)%reb==0: v=v.sum()*np.array(w)
        E.append(v.sum())
    E=np.array(E); pk=np.maximum.accumulate(E); return E[-1]**(252/len(E))-1, (E/pk-1).min()
print('indep gross 0.2x3BusEq+0.8DEF3 annual', sim([lev,def3-0.0015/252],[0.2,0.8],252))
print('indep gross BusEq core', sim([tech-0.002/252],[1.0],0))
print('indep gross DEF3 alone', sim([def3-0.0015/252],[1.0],0))
print('indep gross 3xBusEq alone', sim([lev],[1.0],0))
