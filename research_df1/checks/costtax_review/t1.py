import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/checks/costtax')
import ctlib as CT, dfctx as DC, dfe, run_grid as RG, run_df2 as R2, mkt
W = dfe.WARM
# 1) with_bond(n=20) must reproduce the market's own rb / bondup
for b in CT.SELM:
    m = DC.market(b); m2 = CT.with_bond(m, b, 20)
    print(b, 'rb maxdiff', float(np.abs(m2['rb'] - m['rb']).max()), 'bondup mismatches', int((m2['bondup'] != m['bondup']).sum()), 'shape', m['rb'].shape)
    m7 = CT.with_bond(m, b, 14)
    # 7y vs 10y: annualised vol of rb on day >= W, and mean
    for nm, mm in (('10y', m), ('7y', m7)):
        x = mm['rb'][:, W:]
        print('   %s rb mean/yr %.4f vol/yr %.4f' % (nm, x.mean() * 252, x.std() * np.sqrt(252)))
# 2) independent KRW check on real NDX for T25 / T30 / T40 / QQQ
C = CT.all_configs()
mn = DC.market('real_ndx_86_14'); X = CT.getX('real_ndx_86_14'); dates = X.index[mn['ctx'].ii[0][W:]]
d = pd.read_csv(CT.FXRAW); d['observation_date'] = pd.to_datetime(d['observation_date']); d = d[d['observation_date'] <= '2014-12-31']
s = pd.to_numeric(d['DEXKOUS'], errors='coerce'); s.index = d['observation_date']; s = s.dropna()
fx = s.reindex(s.index.union(dates)).ffill().reindex(dates).values
print('dates', dates[0].date(), dates[-1].date(), len(dates), 'fx', fx[0], fx[-1], 'nan', np.isnan(fx).sum())
for nm, cid in (('T25', 'v1|s0.1|L1.0|K1|RB'), ('T30', 'v1|s0.2|L1.0|K1|RB'), ('T40', 'DF2|M2|b1|v1|s0.3|L1.5|K2|RB'), ('T40g', 'v1|s0.3|L1.0|K2|RB'), ('QQQ', None)):
    if cid is None:
        o, EE = dfe.run(mn, np.full(mn['r'].shape, 1.0), recon=True)
    else:
        cfg = C[cid]; L = DC.target(mn, cfg['k'], cfg['sig'], cfg['Lmax']); kw = dict(RG.KNEES[cfg['knee']])
        if cfg.get('fam') == 'df2': kw.update(step_lo=R2.BANDS[cfg['band']][0], step_hi=R2.BANDS[cfg['band']][1], vmode=0 if cfg['M'] == 'M0' else 2)
        o, EE = dfe.run(mn, L, recon=True, roff=RG.ROFF[cfg['roff']], **kw)
        assert np.allclose(o, R2.run_cfg(cfg, mn))
    E = EE[0]; Ek = E * fx / fx[0]
    dd = Ek / np.maximum.accumulate(Ek) - 1; j = int(np.argmin(dd)); p = int(np.argmax(Ek[:j + 1]))
    ddu = E / np.maximum.accumulate(E) - 1
    yrs = len(E) / 252  # = (T-W)/252
    T = mn['r'].shape[1]
    cu = o[0, 0] ** (252 / (T - W)) - 1; ck = (o[0, 0] * fx[-1] / fx[0]) ** (252 / (T - W)) - 1
    print('%-5s USD cagr %.4f mdd %.4f (engine %.4f) | KRW cagr %.4f mdd %.4f peak %s trough %s | fx peak %.1f trough %.1f' % (
        nm, cu, ddu.min(), o[0, 1], ck, dd.min(), dates[p].date(), dates[j].date(), fx[p], fx[j]))
    # KRW drawdown using the min of (start=1 prepended) too
    Ek2 = np.r_[1.0, Ek]; print('      with start 1 prepended: %.4f' % (Ek2 / np.maximum.accumulate(Ek2) - 1).min())
