"""Unit checks of the non-parity products (T-bill ETF, bond ETF, QQQ) on real NDX 1986-2014 by direct formulas."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe
m = DC.market('real_ndx_86_14'); W = dfe.WARM; T = m['r'].shape[1]; res = {}
Z = np.zeros_like(m['r'])
# T-bill ETF only
o, E = dfe.run(m, Z, recon=True, roff=1)
y = m['rf'][0, W:] - 0.001 / 252; y = np.where(y > 0, y * (1 - 0.154), y); y[0] = 0
man = (1 - 0.003) * np.cumprod(1 + y); res['tbill_final_diff'] = float(abs(o[0, 0] - man[-1])); res['tbill_curve_maxdiff'] = float(np.max(np.abs(E[0] - man)))
# bond ETF only (no sales -> no yearly tax; liquidation 22% on price gain)
o, E = dfe.run(m, Z, recon=True, roff=2, harvest=0)
rb = m['rb'][0, W:]; cp = m['cpn'][0, W:]; g = 1 + rb - 0.0015 / 252 - 0.154 * cp; g[0] = 1
v = (1 - 0.003) * np.cumprod(g); bas = (1 - 0.003) + np.sum(v[:-1] * cp[1:] * (1 - 0.154))
fin = v[-1] - 0.22 * max(v[-1] - bas - 0.25, 0)
res['bond_curve_maxdiff'] = float(np.max(np.abs(E[0] - v))); res['bond_final_diff'] = float(abs(o[0, 0] - fin))
# QQQ constant 1x: only taxes from proportional sales / harvest; check curve pre-first-tax-year
o, E = dfe.run(m, np.ones_like(m['r']), recon=True, harvest=0)
q = 1 + m['r'][0, W:] - 0.002 / 252; q[0] = 1; man = (1 - 0.003) * np.cumprod(q)
res['qqq_first_year_maxdiff'] = float(np.max(np.abs(E[0, :252] - man[:252])))
# static 50/50 QQQ/bond with yearly rebalance: weights right after day-252 rebalance
o, E = dfe.run(m, np.full_like(m['r'], 0.5), recon=True, roff=2, reb_every=252)
res['static_ok_final'] = float(o[0, 0])
print(json.dumps(res, indent=1)); json.dump(res, open('/mnt/project-files/research/df1/results/units.json', 'w'), indent=1)
