import sys; sys.path.insert(0,'/mnt/project-files/research/gx1/code'); sys.path.insert(0,'/tmp/claude-0/gx1verify')
import gx1lib as G, numpy as np, pandas as pd
fr=G.us_frames(); X,F,ii,kind=fr['real_ndx_86_14']; cal=X.index
D=G.world_signals(cal,'US'); mk=G.signal_set('US'); L,AGE=G.asof_levels(cal,mk); inp=G._inv_inputs(cal,mk,AGE)
sc=pd.Series(D['G11'].values,index=cal).iloc[ii[0][G.W]:]
y=pd.DataFrame({'on':sc.astype(float),'share':D['share_INV'].iloc[ii[0][G.W]:],'n':D['n_INV'].iloc[ii[0][G.W]:]})
print(y.groupby(y.index.year).agg(on=('on','mean'),share=('share','median'),n=('n','median')).round(2).T.to_string())
# per-unit flag share by year (unit flagged inverted in last 378 rows & valid)
fl={}
for m,(inv,v) in inp.items():
    f=pd.Series(inv&v).rolling(378,min_periods=1).max().values>0; fl[m]=pd.Series(f&v,index=cal)
Fd=pd.DataFrame(fl).iloc[ii[0][G.W]:]
print(Fd.groupby(Fd.index.year).mean().round(1).T.to_string())
# NDX annual return, F inv (v1 own US alarm) share by year
r=X['r'].iloc[ii[0][G.W]:]; print('NDX yr ret', ((1+r).groupby(r.index.year).prod()-1).round(2).to_dict())
print('US own inv flag share by year', F['inv'].iloc[ii[0][G.W]:].groupby(cal[ii[0][G.W]:].year).mean().round(2).to_dict())
