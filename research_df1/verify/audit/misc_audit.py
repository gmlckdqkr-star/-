"""AUDIT misc: (1) t_parity MDD diffs explained by MDD start-point convention, (2) units bond_final_diff = tax*cost basis convention,
(3) AU drawdown anatomy of the two tier -40% candidates (<=2014), (4) a skipped DF2 M0|b1 config equals its DF1 grid row."""
import sys, os, json, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, std, run_grid as RG, run_df2 as R2
W = dfe.WARM; OUT = {}
# (1) parity MDD convention
m = DC.market('dev250_path'); c = m['ctx']; B = m['st_v1'].astype(float); res = {}
for tag, BB, fs in (('v1B_step05', B, 0.5), ('halfB_fstep01', 0.5 * B, 0.1)):
    cg, E = std.engine(c, BB, std.ident, np.zeros(1), fs, cspr=10.0)
    o, _ = dfe.run(m, BB, vmode=1, step_hi=0.5, step_lo=fs, roff=0, kon=0)
    E1 = np.c_[np.ones(E.shape[0]), E]; md_start1 = (E1 / np.maximum.accumulate(E1, axis=1) - 1).min(axis=1)
    md_rec = (E / np.maximum.accumulate(E, axis=1) - 1).min(axis=1)
    res[tag] = dict(dfe_vs_start1=float(np.max(np.abs(o[:, 1] - md_start1))), dfe_vs_recorded=float(np.max(np.abs(o[:, 1] - md_rec))),
                    cagr_diff=float(np.max(np.abs(cg - dfe.stats(o, m['r'].shape[1])[0]))), n_paths_differ=int(np.sum(np.abs(o[:, 1] - md_rec) > 1e-12)))
OUT['parity_mdd_convention'] = res; print(res, flush=True)
# (2) units bond final diff
u = json.load(open('/mnt/project-files/research/df1/results/units.json'))
OUT['units_bond_final_diff'] = dict(recorded=u['bond_final_diff'], tax_x_cost=0.22 * 0.003, diff=abs(u['bond_final_diff'] - 0.22 * 0.003))
# (3) AU anatomy
mA = DC.market('AU'); X, i0 = DC.PX.build('AU'); dates = X.index[i0 + W:]
an = {}
for i, cfg in (('DF2|M2|b1|v1|s0.3|L1.5|K2|RB', dict(fam='df2', M='M2', band='b1', k='v1', sig=0.3, Lmax=1.5, knee='K2', roff='RB')),
               ('v1|s0.3|L1.0|K2|RB', dict(fam='grid', k='v1', sig=0.3, Lmax=1.0, knee='K2', roff='RB'))):
    L = DC.target(mA, cfg['k'], cfg['sig'], cfg['Lmax']); kw = dict(RG.KNEES[cfg['knee']]); kw['roff'] = 2
    if cfg['fam'] == 'df2': kw.update(vmode=2)
    o, E = dfe.run(mA, L, recon=True, **kw); e = np.r_[1.0, E[0]]; pk = np.maximum.accumulate(e); dd = e / pk - 1; j = int(np.argmin(dd)); jp_ = int(np.argmax(e[:j + 1]))
    r = mA['r'][0, W:]; d1 = int(np.argmin(dd[1:] - dd[:-1]))
    an[i] = dict(mdd=float(dd[j]), peak_date=str(dates[max(jp_ - 1, 0)].date()), trough_date=str(dates[j - 1].date()),
                 worst_1day_equity_move=float(dd[1:][d1] - dd[:-1][d1]), worst_day=str(dates[d1].date()), index_ret_that_day=float(r[d1]))
OUT['AU_anatomy'] = an; print(an, flush=True)
# (4) skipped duplicate equivalence (DF2 M0|b1 == DF1 grid row), on real_ndx_86_14 and real_spx_29_54
G1 = json.load(open('/mnt/project-files/research/df1/results/grid.json'))['configs']; eq = {}
for bn in ('real_ndx_86_14', 'real_spx_29_54'):
    mm = DC.market(bn); T = mm['r'].shape[1]
    for k, s, L, kn, ro in (('v1', 0.3, 1.0, 'K2', 'RB'), ('always', 0.1, 3.0, 'K1', 'RBT')):
        cfg = dict(fam='df2', M='M0', band='b1', k=k, sig=s, Lmax=L, knee=kn, roff=ro)
        cg, md = dfe.stats(R2.run_cfg(cfg, mm), T); gid = '%s|s%s|L%s|%s|%s' % (k, s, L, kn, ro)
        eq['%s|%s' % (bn, gid)] = dict(cagr_diff=abs(float(cg[0]) - G1[gid][bn]['cagr']), mdd_diff=abs(float(md[0]) - G1[gid][bn]['mdd']))
OUT['dup_equivalence'] = eq; print(eq, flush=True)
json.dump(OUT, open(sys.argv[1], 'w'), indent=1)
