import sys, pandas as pd, numpy as np
sys.path.insert(0,'/mnt/project-files/research/breakthrough/code'); import gate
S=sys.argv[1]
d=pd.read_csv(S+'/igrea_verify/igrea.csv')
d.columns=['date','v']+list(d.columns[2:]); d['date']=pd.to_datetime(d['date']); d=d.set_index('date')['v'].astype(float)
d.index=d.index.to_period('M'); d=d[d.index<=pd.Period('2014-12','M')]
x=d.diff(3)                      # 3-month change of month value
use=x.shift(2)                   # month m uses value of month m-2 (published mid m-1)
med=use.expanding(24).median()
sig_m=(use>med)
idx=pd.bdate_range('1955-01-01','2014-12-31')
s=pd.Series(sig_m.reindex(idx.to_period('M')).values,index=idx)
s=s.dropna().astype(bool)
gate.test(s,trials=2,name='IGREA3m_m2_gt_expmedian')
gate.test(~s,trials=2,name='inverse')
