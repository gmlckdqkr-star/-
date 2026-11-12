import sys; sys.path.insert(0,'/mnt/project-files/research/gx1/code')
import gx1lib as G, numpy as np, pandas as pd
from gx1lib import std, ov
for h in ('CH','JP','KR','MX'):
    X,i0=G.host(h); y3,y10=G.rates(h,X.index); ok=(y3.notna()&y10.notna()).values; f=int(np.argmax(ok))
    F=ov.flags_hist(X); X2=X.copy(); X2.iloc[:f, X2.columns.get_loc('y3m')]=np.nan; X2.iloc[:f, X2.columns.get_loc('y10')]=np.nan; F2=ov.flags_hist(X2)
    rows=np.arange(i0,len(X)); D=G.world_signals(X.index,h)
    def run(FF,gg=None,md=None): c=ov.Ctx(X,FF,rows[None,:]); return G.acct(c,Ghist=gg,mode=md)[0][0]
    v=run(F); v2=run(F2); mx=0
    for rid,(k,th,md) in enumerate(G.RULES):
        g=D['G%02d'%G.SIGNALS.index((k,th))].values.astype(bool); mx=max(mx,abs((run(F,g,md)-v)-(run(F2,g,md)-v2)))
    print(h,'v1 diff %.2e'%(v-v2),'max |delta d| over 26 rules %.2e'%mx, flush=True)
