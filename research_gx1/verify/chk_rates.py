import sys; sys.path.insert(0,'/mnt/project-files/research/gx1/code')
import gx1lib as G, pandas as pd, numpy as np
for m in G.MARKETS:
    if m not in G.OECD: print(m,'no OECD entry'); continue
    cc=G.OECD[m]; s3='IR3TCD01JPM156N' if m=='JP' else 'IR3TIB01%sM156N'%cc; sl='IRLTLT01%sM156N'%cc
    f3=G._rate_file(s3); fl=G._rate_file(sl)
    def rng(f):
        if f is None: return None
        x=pd.read_csv(f,parse_dates=['observation_date']).set_index('observation_date').iloc[:,0]; x=pd.to_numeric(x,errors='coerce').dropna()
        # gaps > 1 month
        d=x.index.to_period('M'); gaps=[(str(a),str(b)) for a,b in zip(d[:-1],d[1:]) if (b-a).n>1]
        return (str(x.index.min().date()),str(x.index.max().date()),len(x),gaps[:5])
    s=G.index(m)
    print(m, G.REGION[m], 'idx',s.index.min().date(),s.index.max().date(), '|3m',f3 and f3.split('/')[-3], rng(f3),'|LT', fl and fl.split('/')[-3], rng(fl))
