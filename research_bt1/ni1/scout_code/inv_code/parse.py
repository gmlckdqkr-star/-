import re,sys,os,glob,json,datetime as dt
D=sys.argv[1]; out=[]
mon={m:i+1 for i,m in enumerate(['january','february','march','april','may','june','july','august','september','october','november','december'])}
for p in sorted(glob.glob(D+'/mtis*.txt')):
    b=os.path.basename(p); yy=int(b[4:6]); mm=int(b[6:8]); y=1900+yy if yy>50 else 2000+yy
    t=open(p,errors='replace').read()
    rel=None
    m=re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})\s*,\s*(\d{4})',t[:3000])
    if m: rel=dt.date(int(m.group(3)),mon[m.group(1).lower()],int(m.group(2))).isoformat()
    ratio=None; src=None
    m=re.search(r'TOTAL BUSINESS\s+([\d,]+\s+){6}([\d.]+)',t)
    if m: ratio=float(m.group(2)); src='tbl'
    if ratio is None:
        m=re.search(r'Total business\.+\s+([\d,]+\s+){6}([\d.]+)',t)
        if m: ratio=float(m.group(2)); src='tbl2'
    if ratio is None:
        m=re.search(r'inventories/sales\s+ratio\s+based\s+on\s+seasonally\s+adjusted\s+data\s+at\s+the\s+end\s+of\s+\w+\s+was\s+([\d.]+)',re.sub(r'\s+',' ',t),re.I)
        if m: ratio=float(m.group(1).rstrip('.')); src='prose'
    out.append(dict(y=y,m=mm,rel=rel,ratio=ratio,src=src))
json.dump(out,open(sys.argv[2],'w'))
print(sum(o['ratio'] is not None for o in out),len(out),sum(o['rel'] is not None for o in out))
for o in out:
    if o['ratio'] is None or o['ratio']<1 or o['ratio']>2: print('bad',o)
