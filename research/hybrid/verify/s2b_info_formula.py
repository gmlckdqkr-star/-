"""Same as s2_info.py but with the s0.85 sleeve defined by the PRECOMMIT formula (CU_{t-1}/3) TQ_t + (1 - CU_{t-1}/3) DEP_t (daily
constant weight), to separate logic differences from the sleeve definition. Also measures the drifting-vs-formula sleeve gap."""
import json, numpy as np
import s2_info as V

def formula_sleeve(TQ, DEP, CU, cost=0.0):
    Lp = np.r_[CU[0], CU[:-1]] / 3.0
    r = Lp * TQ + (1 - Lp) * DEP; r[0] = 0.0; return r

V.s085_sleeve_drift = V.s085_sleeve
V.s085_sleeve = formula_sleeve
for bn in ['real_ndx_86_14', 'real_spx_55_85']:
    base, ks = V.run(bn)
    for (X, rule), v in base.items():
        st = V.STORED['%s|%s|%s' % (bn, X, rule)]
        print('%-15s %-12s %-6s formula sleeve: hit %.4f defl %.4f base %.4f sw %.4f gain %+.6f t %+.3f | stored: hit %.4f defl %.4f base %.4f sw %.4f gain %+.6f t %+.3f'
              % (bn, X, rule, v['hit'], v['hit_defl'], v['base'], v['sw'], v['gain'], v['t'],
                 st['hit'], st['hit_defl'], st['base_s085'], st['frac_switch'], st['gain_mean'], st['gain_t']))
    z = np.load(V.D + 'data_%s.npz' % bn)
    a = V.s085_sleeve_drift(z['TQ'], z['DEP'], z['CU']); b = formula_sleeve(z['TQ'], z['DEP'], z['CU'])
    la = np.cumsum(np.log1p(a)); lb = np.cumsum(np.log1p(b)); T = len(a)
    print('  drifting sleeve vs daily-formula sleeve: total log ret %.3f vs %.3f (CAGR %.2f%% vs %.2f%%); max |daily diff| %.4f; share of days at intermediate level %.2f'
          % (la[-1], lb[-1], 100 * (np.exp(la[-1] * 252 / T) - 1), 100 * (np.exp(lb[-1] * 252 / T) - 1), np.max(np.abs(a - b)),
             np.mean((z['CU'] > 0) & (z['CU'] < 3))))
