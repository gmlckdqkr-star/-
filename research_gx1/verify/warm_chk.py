import sys, json; sys.path.insert(0,'/mnt/project-files/research/gx1/code')
import gx1lib as G, numpy as np, pandas as pd
from gx1lib import std, ov
o=json.load(open('/mnt/project-files/research/gx1/results/foreign_le2014.json')); H=o['hosts']
for h in ('CH','JP','KR','MX'):
    X,i0=G.host(h); y3,y10=G.rates(h,X.index); ok=(y3.notna()&y10.notna()).values; f=int(np.argmax(ok))
    F=ov.flags_hist(X); X2=X.copy(); X2.iloc[:f, X2.columns.get_loc('y3m')]=np.nan; X2.iloc[:f, X2.columns.get_loc('y10')]=np.nan; F2=ov.flags_hist(X2)
    rows=np.arange(i0,len(X)); diff={k:int((F[k].values[rows]!=F2[k].values[rows]).sum()) for k in F.columns}
    D=G.world_signals(X.index,h); g=D['G11'].values.astype(bool)
    def run(FF,gg=None,md=None): c=ov.Ctx(X,FF,rows[None,:]); return G.acct(c,Ghist=gg,mode=md)[0][0]
    v=run(F); v2=run(F2); a=run(F,g,'CAP1'); a2=run(F2,g,'CAP1')
    print(h,'flag diffs on account rows',{k:x for k,x in diff.items() if x},'first diff row offset from i0', (np.argmax(F['shock6m'].values[rows]!=F2['shock6m'].values[rows]) if diff['shock6m'] else None),
          '| v1 %.5f vs fixed %.5f | rule24 d %.5f vs fixed %.5f (json %.5f)'%(v,v2,a-v,a2-v2,H[h]['d'][24]))
