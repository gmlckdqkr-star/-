import os, sys, json, time, numpy as np
os.environ['NUMBA_CACHE_DIR']='/tmp/df6v/gates/nb'; sys.dont_write_bytecode=True
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import df6, df5run as R, df5stress as ST
RES='/mnt/project-files/research/df1/results/'
D=json.load(open(RES+'df6_main.json')); idx={c['id']:c for c in D['configs']}
top='L|TQQQ|DEF3|R252|e0.60|c0.80'
# (a) G6 reproduction for top config
GR=df6.g6_world('R2885'); GO=df6.g6_world('OLD6')
cg,md,qcg,qmd=df6.g6_run(idx[top],GR); cg2,md2,qcg2,qmd2=df6.g6_run(idx[top],GO)
print('G6 R2885 mix cagr %.5f mdd %.5f core cagr %.5f mdd %.5f ddm %.4f'%(cg[0],md[0],qcg[0],qmd[0],1-abs(md[0])/abs(qmd[0])))
print('G6 OLD6 mix',R.summ(cg2,md2,qcg2)); print('G6 OLD6 core',R.summ(qcg2,qmd2))
print('G6 OLD6 p10 ddm %.4f'%(1-abs(np.percentile(md2,10))/abs(np.percentile(qmd2,10))))
print('gate_conds real',ST.gate_conds(cg,md,qcg,qmd,True),'boot',ST.gate_conds(cg2,md2,qcg2,qmd2))
print('G6 T (days) R2885',GR['T'],'OLD6',GO['T'],'P',GO['P'])
del GR,GO; df6._G6.clear()
# (b) N1 shift per world for DEF3 (no config evaluations)
for w in ('REAL','P','X'):
    pan=df6.panel6(w,'N1',None,['DEF3']); pan2=df6.panel6(w,'N2',None,['DEF3'])
    print(w,'N1 DEF3 shift (ann, subtracted from raw mean)',round(pan['meta']['shift6']['DEF3'],5))
    del pan,pan2; df6.drop(w)
