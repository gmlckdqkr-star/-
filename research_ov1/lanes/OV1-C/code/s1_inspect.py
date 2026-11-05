"""Step 1: data-quality inspection only (no labels, no returns, no v1 states, no signal on-dates)."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/lanes/OV1-C/code'); sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std, sig_c, jp  # noqa (std sets paths)
LANE = '/mnt/project-files/research/ov1/lanes/OV1-C/'
S = sig_c.raw_sources(); X = sig_c.change_index(); out = {}
for k, s in S.items():
    d = s.diff().dropna(); nz = d[d.abs() > 1e-9]
    out['src_' + k] = dict(first=str(s.index[0].date()), last=str(s.index[-1].date()), n=int(len(s)), nan=int(s.isna().sum()),
        n_nonzero_changes=int(len(nz)), abs_change_q=[float(x) for x in nz.abs().quantile([.1, .5, .9]).values] if len(nz) else [],
        n_changes_lt_0p25=int((nz.abs() < .25 - 1e-6).sum()), min=float(s.min()), max=float(s.max()))
    if k in ('jp_disc', 'jp_call', 'de', 'uk'):
        m = pd.date_range(s.index[0], s.index[-1], freq='MS'); out['src_' + k]['month_gaps'] = int(len(m.difference(s.index)))
# splice values
S0 = S
out['splice_JP'] = dict(disc_1985_06=float(S0['jp_disc'].iloc[-1]), call_1985_07=float(S0['jp_call'].iloc[0]))
out['splice_DE_EZ'] = dict(de_1998_12=float(S0['de'].iloc[-1]), ez_1999_01_01=float(S0['ez'].iloc[0]))
for k, x in X.items():
    dx = x.diff().dropna(); out['X_' + k] = dict(first_avail=str(x.index[0].date()), last_avail=str(x.index[-1].date()), n=int(len(x)),
        nan=int(x.isna().sum()), n_nonzero_changes=int((dx.abs() > 1e-9).sum()))
# check X diffs == source diffs except joins (JP), and availability mapping
xj = X['JP']; j = xj[(xj.index >= '1985-06-01') & (xj.index <= '1985-10-01')]
out['X_JP_around_join'] = {str(a.date()): float(b) for a, b in j.items()}
xd = X['DE_EZ']; j = xd[(xd.index >= '1998-11-01') & (xd.index <= '1999-01-10')]
out['X_DE_EZ_around_join'] = {str(a.date()): float(b) for a, b in j.items()}
# ECB filled: source mix and check filled==MRO where present
e = pd.read_csv(sig_c.D + 'derived_ecb_mro_filled.csv'); out['ecb_fill_sources'] = e['source'].value_counts().to_dict()
mro = sig_c._rd('cut_ECBMRRFR.csv'); dfr = sig_c._rd('cut_ECBDFR.csv'); ef = sig_c._rd('derived_ecb_mro_filled.csv')
both = mro.dropna().index; out['ecb_filled_eq_mro_where_present'] = bool(np.allclose(ef.reindex(both).values, mro.reindex(both).values))
cor = (mro - dfr).dropna(); out['ecb_mro_minus_dfr_values'] = {str(round(k, 2)): int(v) for k, v in cor.round(2).value_counts().items()}
efc = ef.diff(); out['ecb_filled_changes'] = {str(a.date()): round(float(b), 3) for a, b in efc[efc.abs() > 1e-9].items()}
# UK cross-check with BOERUKM 2013-04..2014-12
bo = sig_c._rd('cut_BOERUKM.csv'); out['boe_2013_04_2014_12_unique'] = sorted(set(bo[(bo.index >= '2013-04-01')].round(4).tolist()))
uk = S['uk']; ov_ = bo.reindex(uk.index); out['uk_eq_boerukm_overlap'] = bool(np.allclose(uk.values, ov_.values))
# coverage on calendars: first trading day where all three 126-day differences exist
for nm, (a, b, st) in dict(SPX=('1928-01-03', '1985-12-31', 'SPX'), NDX=('1984-01-03', '2014-12-31', 'NDX')).items():
    R, M = jp.calendar(a, b); cal = jp.mkX(R, M, st).index
    V = {}
    for k, x in X.items():
        V[k] = x.reindex(cal.union(x.index)).ffill().reindex(cal).values[None, :].astype(float)
    on, cnt, ok = sig_c.on_matrix(V)
    out['first_valid_' + nm] = str(cal[np.argmax(ok[0])].date()); out['n_invalid_after_first_' + nm] = int((~ok[0][np.argmax(ok[0]):]).sum())
print(json.dumps(out, indent=1, default=str))
json.dump(out, open(LANE + 'results/s1_inspect.json', 'w'), indent=1, default=str)
