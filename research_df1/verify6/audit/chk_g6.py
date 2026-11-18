import sys, numpy as np, pandas as pd
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import df6
d = df6._daily_sleeves()
for k in ('TECH','DEF3','RF','STAP'):
    s=d[k]; print(k, s.index.min().date(), s.index.max().date(), len(s), 'sat', int((s.index.weekday==5).sum()), 'sun', int((s.index.weekday==6).sum()), 'nan', int(s.isna().sum()))
G = df6.g6_data(); cal=G['cal']
print('cal', cal[0].date(), cal[-1].date(), len(cal), 'weekday set', sorted(set(cal.weekday)))
# known Saturdays
for sat in ['1929-10-26','1931-09-19','1933-03-04','1950-06-24','1951-12-29','1945-08-18','1937-07-03']:
    t=pd.Timestamp(sat); inT = t in d['TECH'].index
    pos=cal.searchsorted(t); tgt=cal[pos]
    # recompute expected: compounding of TECH on all source dates mapping to tgt
    prev=cal[pos-1]
    src=d['TECH'][(d['TECH'].index>prev)&(d['TECH'].index<=tgt)]
    exp=float((1+src).prod()-1)
    print(sat, t.day_name(), 'in TECH src', inT, '-> maps to', tgt.date(), tgt.day_name(), 'src dates', [x.date().isoformat() for x in src.index], 'g6 %.6f exp %.6f'%(G['TECH'][pos], exp))
# product preservation over 1928-01-04..1985-12-31
for k in ('TECH','DEF3','RF'):
    s=d[k]; s=s[(s.index>cal[0])]
    a=np.prod(1+G[k][1:]); b=float((1+s).prod())
    print(k,'prod check', a, b, a/b-1)
# first day lump
for k in ('TECH','DEF3','RF'):
    s=d[k]; print(k, 'first day value %.4f'%G[k][0], 'pre-1928 compounded %.4f'%float((1+s[s.index<=cal[0]]).prod()-1))
# any NaN in DEF3 source pre-1986? any weekday source date not in cal?
for k in ('DEF3','RF'):
    s=d[k]; s=s[s.index>=cal[0]]; wk=s.index[s.index.weekday<5]
    print(k,'weekday src dates not in cal:', int((~wk.isin(cal)).sum()), [x.date().isoformat() for x in wk[~wk.isin(cal)][:10]])
print('TECH cal dates without DEF3 source', int((~cal.isin(d['DEF3'].index)).sum()), 'without RF', int((~cal.isin(d['RF'].index)).sum()))
# R2885 eval start
print('R2885 eval start', cal[300].date(), 'T', len(cal), 'yrs', (len(cal)-300)/252)
# annual stats of the weekday series vs source (sanity)
for k in ('TECH','DEF3'):
    s=d[k]; s=s[(s.index>cal[0])]
    print(k, 'ann geo src %.4f'%(float((1+s).prod())**(252/ (len(cal)-1))-1), 'calendar-year geo %.4f'%(float((1+s).prod())**(1/ ( (cal[-1]-cal[0]).days/365.25))-1))
