import sys, json, math; sys.path.insert(0,'/mnt/project-files/research/gx1/code')
import gx1lib as G, numpy as np, pandas as pd
from gx1lib import std, ov
sys.argv=[sys.argv[0]]; import gx1run as RUN
o=json.load(open('/mnt/project-files/research/gx1/results/foreign_le2014.json')); H=o['hosts']
# 1) e == d - median(d_shift) consistency, all hosts/rules
mx=0
for h in H:
    for r in range(26): mx=max(mx, abs(H[h]['e'][r]-(H[h]['d'][r]-np.median(H[h]['d_shift'][r]))))
print('max |e - (d - med d_shift)|', mx)
# 2) host i0 / first check + independent first-both-rates date
from indep_sig import mrate
for h in G.HOSTS:
    X,i0=G.host(h); cc=G.OECD[h]; s3='IR3TCD01JPM156N' if h=='JP' else 'IR3TIB01%sM156N'%cc; sl='IRLTLT01%sM156N'%cc
    a=mrate(X.index,s3); b=mrate(X.index,sl); ok=~np.isnan(a)&~np.isnan(b); f=int(np.argmax(ok))
    pre=int(f)  # index rows before first-both-rates
    nan_inside=int((~ok[f:]).sum())
    print(h,'first both',X.index[f].date(),'i0+W row',i0+G.W,'= first+378?',i0+G.W==f+378,'scored',X.index[i0+G.W].date(),'json',H[h]['scored_from'],'| index rows before rates',pre,'| invalid-rate rows after first',nan_inside)
