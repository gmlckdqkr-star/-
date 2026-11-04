import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1/work')
import harness as h, cands as c, exec_engine as ee
cand = {114: dict(m0=0.10, A=1.25, ns=42, sv=120, B=0.5, nl=252), 113: dict(m0=0.08, A=1.25, ns=42, sv=120, B=0.5, nl=252),
        119: dict(m0=0.08, A=1.5, ns=42, sv=120, B=0.75, nl=252), 112: dict(m0=0.08, A=1.25, ns=42, sv=60, B=0.5, nl=252),
        117: dict(m0=0.10, A=1.0, ns=42, sv=120, B=0.5, nl=252), 116: dict(m0=0.08, A=1.5, ns=42, sv=120, B=0.5, nl=252),
        82: dict(m0=0.08, A=1.0, ns=42, sv=60, B=0.5, nl=504)}
r, rf = h.data(12, False); P = r.shape[0]
print('seed12 OFF best const', max(ee.summary(ee.run(r, rf, np.full((P, h.T), L)))['cagr_med'] for L in (0.5, 1.0)))
for n, p in cand.items():
    p = dict(p, kf=0.5)
    o = h.evaluate(c.F_kelly, p, f'confirm_of_N{n}', seed=12)
    print(o['N'], n, p, {kk: round(vv, 4) for kk, vv in o.items() if kk != 'N'}, flush=True)
