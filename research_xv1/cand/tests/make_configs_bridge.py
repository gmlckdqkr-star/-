import json
F = '/home/user/-/research_xv1/cand/bridge.py'
SOXN = ['ret:SOXL', 'semis']; LOS = ['semis', 'ret:SOXL', 'ret:FAS', 'ret:TNA', 'ret:TECL', 'ret:ERX', 'ret:DRN', 'ret:XLF', 'ret:IWM', 'ret:XLK', 'ret:XLE', 'ret:IYR', 'kf:Money', 'kf:Lo 10', 'kf:BusEq', 'kf:Enrgy']
out = []
nm = {'TQQQ': ['ret:TQQQ'], 'SOXL': SOXN, 'LOSER': LOS, 'USD': ['ret:USD', 'semis']}
for X in ('TQQQ', 'SOXL', 'LOSER'):
    for d in (0.20, 0.25):
        out.append(dict(family='fast-crash bridge', name='FCB_%s_%d' % (X, d * 100), file=F, func='fast_crash', params=dict(X=X, d=d, w=0.20), names=nm[X], t0=None))
for s in 'AB':
    for b in (0.10, 0.20, 0.30):
        out.append(dict(family='SOXL staged crash bridge', name='SSB_%s_%d' % (s, b * 100), file=F, func='staged_bridge', params=dict(X='SOXL', depth_set=s, budget=b), names=SOXN, t0=None))
for X in ('TQQQ', 'SOXL'):
    for th in (1.15, 1.25):
        out.append(dict(family='panic-peak bridge', name='PPB_%s_%d' % (X, round(th * 100)), file=F, func='panic_peak', params=dict(X=X, theta=th), names=['lvl:_VIX3M@ext'] + nm[X], t0='2006-07-17'))
for X in ('SOXL', 'USD'):
    out.append(dict(family='hold-to-cycle-top', name='HCT_%s' % X, file=F, func='hold_to_top', params=dict(X=X), names=nm[X], t0=None))
json.dump(out, open('/home/user/-/research_xv1/cand/bridge.configs.json', 'w'), indent=1)
print(len(out))
