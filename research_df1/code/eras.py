"""Era breakdown of the adopted picks on single real paths (<=2014): calendar-year returns, worst year, segment CAGR/MDD."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_df2 as R2, std
G = json.load(open('/mnt/project-files/research/df1/results/grid.json'))['configs']; G.update(json.load(open('/mnt/project-files/research/df1/results/grid_df2.json'))['configs'])
PK = {'T25': 'v1|s0.1|L1.0|K1|RB', 'T30': 'v1|s0.2|L1.0|K1|RB', 'T40': 'v1|s0.3|L1.0|K2|RB', 'T40_DF2old': 'DF2|M2|b1|v1|s0.3|L1.5|K2|RB'}  # T40 corrected by gate_fix.py (audit F1)
SEG = {'real_ndx_86_14': [('1986-01-01', '1999-12-31'), ('2000-01-01', '2002-12-31'), ('2003-01-01', '2007-12-31'), ('2008-01-01', '2009-12-31'), ('2010-01-01', '2014-12-31')],
       'real_spx_29_54': [('1929-03-01', '1932-12-31'), ('1933-01-01', '1945-12-31'), ('1946-01-01', '1954-12-31')],
       'real_spx_55_85': [('1955-01-01', '1969-12-31'), ('1970-01-01', '1975-12-31'), ('1976-01-01', '1985-12-31')]}
out = {}
for bn, segs in SEG.items():
    m = DC.market(bn); c = m['ctx']; W = dfe.WARM
    d = pd.DatetimeIndex(m['X_index'][c.ii[0]][W:])
    curves = {}
    for tag, i in PK.items():
        cfg = G[i]['cfg']
        if cfg.get('fam') == 'df2':
            L = DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax']); kw = dict(R2.RG.KNEES[cfg['knee']])
            kw.update(step_lo=R2.BANDS[cfg['band']][0], step_hi=R2.BANDS[cfg['band']][1], vmode=2)
        else:
            L = DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax']); kw = dict(R2.RG.KNEES[cfg['knee']])
        o, E = dfe.run(m, L, recon=True, roff=R2.RG.ROFF[cfg['roff']], **kw); curves[tag] = E[0]
    o, E = dfe.run(m, np.ones_like(m['r']), recon=True); curves['QQQ1x'] = E[0]
    B, bfn, bp, fs = std.s085(c); cg, E = std.engine(c, B, bfn, bp, fs, cspr=10.0); curves['v1'] = E[0]
    res = {}
    for tag, E in curves.items():
        s = pd.Series(E, index=d); yr = s.groupby(s.index.year).last(); yr0 = pd.concat([pd.Series([s.iloc[0]], index=[yr.index[0] - 1]), yr])
        yret = (yr0 / yr0.shift(1) - 1).dropna()
        r = dict(worst_year=(int(yret.idxmin()), float(yret.min())), best_year=(int(yret.idxmax()), float(yret.max())),
                 neg_years=int((yret < 0).sum()), n_years=int(len(yret)), worst_day=float((s / s.shift(1) - 1).min()))
        for a, b in segs:
            x = s[(s.index >= a) & (s.index <= b)]
            if len(x) > 20:
                yrs = len(x) / 252; r['%s_%s' % (a[:4], b[:4])] = dict(cagr=float((x.iloc[-1] / x.iloc[0]) ** (1 / yrs) - 1), mdd=float((x / x.cummax() - 1).min()))
        res[tag] = r
    out[bn] = res
    print('==', bn)
    for tag, r in res.items():
        print('  %-6s worst yr %s %.3f | neg %d/%d | worst day %.3f | ' % (tag, r['worst_year'][0], r['worst_year'][1], r['neg_years'], r['n_years'], r['worst_day'])
              + ' '.join('%s %.3f/%.3f' % (k, v['cagr'], v['mdd']) for k, v in r.items() if isinstance(v, dict)))
json.dump(out, open('/mnt/project-files/research/df1/results/eras.json', 'w'), indent=1)
