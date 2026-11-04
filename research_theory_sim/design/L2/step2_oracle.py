# diagnostic only: Kelly with the TRUE hidden state (not a candidate rule; counted in N as a diagnostic)
import numpy as np, sim, harness as H, sys
sys.path.insert(0,'/mnt/project-files/research/theory_sim/common'); import exec_engine as ee
for seed in (1,2):
    d=sim.simulate(1000,7860,seed,True,return_state=True); p=d['params']
    A=d['A']; x=d['x']; sf=d['sf']; rf=d['rf']*252; s=d['y10']/100-rf; sb=d['sbar']
    a_r=np.log(2)/p['HLr']; F=(1-np.exp(-10*a_r))/(10*a_r)
    k=p['k'][:,None]
    mu=p['m_p'][:,None]+k*A*(p['c_ts'][:,None]*(s-sb)-p['kappa'][:,None]*x)+A*(p['b_r'][:,None]+k*p['D_b'][:,None]*F[:,None])*a_r[:,None]*(rf-p['m_r'][:,None])
    var=(A*sf)**2
    for c in (0.5,0.75,1.0):
        B=np.clip(c*mu/var,0,3)
        res=ee.run(d['r'],d['rf'],B); sm=ee.summary(res)
        H.log_variant(dict(name='oracle_diag',prm={'c':c},seeds=[seed],on=sm['cagr_med']))
        print(seed,'oracle c=%.2f cagr_med %.4f p10 %.4f dd80 %.3f tpy %.1f lev %.2f'%(c,sm['cagr_med'],sm['cagr_p10'],sm['p_dd80'],sm['trades_per_year_med'],sm['avg_level_med']))
    # vol-only oracle: m_p / var (no ledger info)
    for c in (0.5,1.0):
        B=np.clip(c*p['m_p'][:,None]/var,0,3); sm=ee.summary(ee.run(d['r'],d['rf'],B))
        H.log_variant(dict(name='oracle_volonly_diag',prm={'c':c},seeds=[seed],on=sm['cagr_med']))
        print(seed,'vol-only oracle c=%.2f cagr_med %.4f'%(c,sm['cagr_med']))
