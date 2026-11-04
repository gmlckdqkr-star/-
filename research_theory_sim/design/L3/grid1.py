"""Stage-1 grid on design seed 1 (P=2000, ON and OFF). Every variant is logged (counts toward N)."""
import sys, json, itertools, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L3')
import design_lib as dl, rules_lib as rl
fam = sys.argv[1]
OUT = f'/mnt/project-files/research/theory_sim/design/L3/runs_stage1_{fam}.jsonl'
W = {m: dl.get(1, m, 2000) for m in (True, False)}
C = {m: dl.close_from(W[m][0]) for m in W}
grids = {
    'A': [dict(a=a, b=b, H=H, Hv=Hv) for a in (0.0, 0.01, 0.02, 0.04) for b in (0.25, 0.5, 1.0, 2.0)
          for H in (20, 40, 80, 160) for Hv in (20, 60)],
    'B': [dict(W=Wd, Lmax=L, Hv=Hv, mu0=m0) for Wd in (2, 3, 4, 6, 8) for L in (1.5, 2.0, 2.5, 3.0)
          for Hv in (20, 60) for m0 in (0.0, 0.02)],
    'C': [dict(N=N, th=th, Lhi=Lh, Llo=0.0, Hv=60) for N in (60, 120, 250) for th in (0.1, 0.2, 0.3, 0.5)
          for Lh in (1.5, 2.0, 3.0)],
    'D': [dict(tau=tau, H=H, Hv=Hv) for tau in (0.2, 0.3, 0.45, 0.6) for H in (20, 40, 80, 160) for Hv in (20, 60)],
}
grids['E1'] = [dict(N=N, th=th, Lup=Lu, Ldn=0.0, Hv=Hv) for N in (21, 42, 63) for th in (0.5, 1.0, 1.5, 2.0) for Lu in (1.5, 3.0) for Hv in (60, 250)]
grids['E2'] = [dict(N=N, th=th, Lup=Lu, Ldn=0.0, Hv=Hv) for N in (126, 252) for th in (0.5, 1.0, 1.5, 2.0) for Lu in (1.5, 3.0) for Hv in (60, 250)]
grids['G1'] = [dict(a=a, beta=b, N=N) for a in (0.0, 0.01, 0.02, 0.03) for b in (0.02, 0.04, 0.06, 0.08) for N in (42,)]
grids['G2'] = [dict(a=a, beta=b, N=N) for a in (0.0, 0.01, 0.02, 0.03) for b in (0.02, 0.04, 0.06, 0.08) for N in (63, 126)]
grids['G3'] = [dict(a=a, beta=b, N=N) for a in (0.0, 0.005) for b in (0.005, 0.01, 0.015) for N in (126, 252)]
grids['H1'] = [dict(a=0.0, beta=b, N=N, kap=kp, n0=n0, mu0=0.02) for n0 in (3.0, 10.0, 30.0) for b in (0.01, 0.02, 0.03) for N in (126,) for kp in (0.5, 1.0)]
grids['H2'] = [dict(a=0.0, beta=b, N=N, kap=kp, n0=n0, mu0=0.02) for n0 in (3.0, 10.0, 30.0) for b in (0.01, 0.02, 0.03) for N in (252,) for kp in (0.5, 1.0)]
fn = dict(G3=rl.fam_kz, H1=rl.fam_kz, H2=rl.fam_kz, G1=rl.fam_kz, G2=rl.fam_kz, A=rl.fam_kelly, B=rl.fam_cusum, C=rl.fam_dd, D=rl.fam_vt, E1=rl.fam_latch, E2=rl.fam_latch)[fam]
with open(OUT, 'w') as fo:
    for i, g in enumerate(grids[fam]):
        row = dict(fam=fam, **g)
        for m in (True, False):
            B = fn(C[m], W[m][1], **g)
            s = dl.evaluate(W[m][0], W[m][1], B)
            k = 'on' if m else 'off'
            row[k] = round(s['cagr_med'], 5); row[k + '_p10'] = round(s['cagr_p10'], 5)
            row[k + '_dd80'] = round(s['p_dd80'], 4); row[k + '_tpy'] = round(s['trades_per_year_med'], 2)
            row[k + '_lev'] = round(s['avg_level_med'], 3)
        row['J'] = round(0.5 * row['on'] + 0.5 * row['off'], 5)
        fo.write(json.dumps(row) + '\n'); fo.flush()
print(fam, 'done', len(grids[fam]))
