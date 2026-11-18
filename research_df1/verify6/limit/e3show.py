import json, sys
A=json.load(open('e3A.json'))['res']; B=json.load(open('e3B.json')); C=json.load(open('e3C.json'))
for f in sys.argv[1:]:
    X=json.load(open(f))
    for cv in X:
        for k in ('B','C'):
            src = B if k=='B' else C
            for i,r in X[cv].items(): src.setdefault(cv,{}).setdefault(i,{}).update(r)
def allslack(cv,i):
    s={}
    s.update({'G1_'+k:v for k,v in A[cv][i]['REAL']['slack'].items()})
    for key,g in (('P30','G2'),('P10','G3'),('X30','G4'),('X10','G5')):
        src = B if key[0]=='X' else C
        if i in src.get(cv,{}) and key in src[cv][i]:
            s.update({g+'_'+k:v for k,v in src[cv][i][key]['slack'].items()})
    return s
THR=float(__import__('os').environ.get('THR','0.5'))
for cv in ('N3low','NA'):
    print('==',cv)
    rows=[]
    for i in C.get(cv,{}):
        s=allslack(cv,i); m=min(s.values()); worst=min(s,key=s.get)
        sc=min(s['G2_pair'],s['G4_pair'],s['G1_ret'])
        rows.append((m,i,worst,sc,s))
    rows.sort(reverse=True)
    for m,i,w,sc,s in rows:
        print('%-26s maximin %+.2f (%s) score %+.2f | '%(i,m,w,sc)+' '.join('%s %+.2f'%(k,v) for k,v in s.items() if v<THR))
