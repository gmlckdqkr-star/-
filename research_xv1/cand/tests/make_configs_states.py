import json
F = '/home/user/-/research_xv1/cand/states.py'
S = ['ret:SOXL', 'semis']; Q = ['ret:QLD']
out = []
def add(fam, name, func, params, names, t0=None):
    out.append(dict(family=fam, name=name, file=F, func=func, params=params, names=names, t0=t0))
for i, p in enumerate([dict(A=30), dict(A=21), dict(A=30, D=0.35), dict(A=30, upgrade=True)], 1):
    add('FCR fast-crash floor', 'FCR_P%d' % i, 'fast_crash_floor', p, [])
for i, p in enumerate([dict(g=0.30, c=1.0, K=21), dict(g=0.30, c=2.0, K=21), dict(g=0.30, c=1.0, K=42), dict(g=0.25, c=1.0, K=21), dict(g=0.50, c=1.0, K=21, n=126)], 1):
    add('PGC post-gain cut', 'PGC_P%d' % i, 'post_gain_cut', p, [])
add('IVV equity-IV veto', 'IVV_P1', 'iv_veto', dict(mode='D1', k=1.0), [], '1990-07-31')
add('IVV equity-IV veto', 'IVV_P2', 'iv_veto', dict(mode='D1', k=0.90), [], '1990-07-31')
add('IVV equity-IV veto', 'IVV_P3', 'iv_veto', dict(mode='D2'), [], '1990-12-28')
for i, (D, W, c) in enumerate([(0.30, 0.15, 0), (0.30, 0.30, 0), (0.40, 0.30, 0), (0.30, 0.15, 1)], 1):
    add('PRX-SOXL panic sleeve', 'PRXS_P%d' % i, 'panic_soxl', dict(D=D, W=W, carry=c), S, '1991-12-27')
for i, (a, W) in enumerate([(1.75, 0.33), (1.75, 0.50), (2.00, 0.33), (2.00, 0.50)], 1):
    add('PRX-QLD panic re-entry', 'PRXQ_P%d' % i, 'panic_qld', dict(a=a, W=W), Q, '1991-12-27')
json.dump(out, open('/home/user/-/research_xv1/cand/states.configs.json', 'w'), indent=1); print(len(out))
