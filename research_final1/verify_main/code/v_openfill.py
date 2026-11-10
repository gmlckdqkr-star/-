"""Independent verifier, STACK rows S6/S6x/S7/S7x and the OPENFILL adoption rule (PRECOMMIT_FINAL1 section 1).
Uses the OV1-B lane engine (eng_ov1b, onleg) directly with an explicit term list (no mutation of beng.F1) and re-derives the
'summed overnight return on v1 decrease days' statistic from the std engine's own daily record. Does not import final1/code/*."""
import os, sys, json, time
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/code'); sys.path.insert(0, '/mnt/project-files/research/ov1/lanes/OV1-B/code')
import ov1lib as L, std, beng, bk, rx
import eng_ov1b as G, onleg as O
OUT = '/mnt/project-files/research/final1/verify_main/results/'
END = pd.Timestamp('2014-12-31'); WARM = beng.WARM
res = {}
# ---- post-2014 row check of the open-price files (dates only; nothing after the cut is printed)
for fn in ('qqq_1day_cut_le20141231.csv', 'qqq_panel_xcheck_le20141231.csv'):
    dts = pd.to_datetime(pd.read_csv(O.D + fn, usecols=['date'])['date'])
    res['file|' + fn] = dict(rows=int(len(dts)), rows_after_2014=int((dts > END).sum()), first=str(dts.min().date()), last_le_cut=str(dts[dts <= END].max().date()))
print({k: v for k, v in res.items()}, flush=True)
cal = L.dates()['real_ndx_86_14']
on, info = O.on_series(cal, xcheck=True)
assert on.index.max() <= END
res['on_info'] = info

def run_mode(c, ON, mode, xcost, **kw):
    B, bfn, bp, fs = std.s085(c)
    k = dict(beng.F1); k['fstep'] = fs; k.update(kw); pp, D = beng._args(k)
    o, EE = G.runPS(np.ascontiguousarray(c.r), np.ascontiguousarray(c.rf), np.ascontiguousarray(ON, dtype=np.float64),
                    np.ascontiguousarray(B, dtype=np.float64), np.ascontiguousarray(bk.features(c)), int(pp['delay']), pp['cost'], pp['tax'], D,
                    int(pp['harvest']), pp['hthr'], pp['cspr'], pp['er3'], pp['step'], bfn, np.asarray(bp, dtype=np.float64), float(pp['fstep']),
                    int(mode), float(xcost))
    yrs = EE.shape[1] / 252
    return np.maximum(o[:, 0], 1e-9) ** (1 / yrs) - 1, EE

ROWS = (('S6_OPENFILL', 0.0, {}), ('S6x_OPENFILL_xcost0.1', 0.001, {}),
        ('S7_OPENFILL_CASHRP_FEE', 0.0, dict(cspr=0.005, cost=0.0012)), ('S7x_OPENFILL_CASHRP_FEE_xcost0.1', 0.001, dict(cspr=0.005, cost=0.0012)))
t0 = time.time(); par = {}
for bn, c in std.contexts().items():
    ON = O.on_ctx(on, L.dates()[bn], c.ii)
    rB, rbf, rbp, rfs = std.s085(c); f_ref, E_ref = std.engine(c, rB, rbf, rbp, rfs)          # v1 at BASE terms
    f0, E0 = run_mode(c, ON, 0, 0.0)                                                          # parity: mode 0 must equal std.engine
    par[bn] = float(np.max(np.abs(f0 - f_ref)))
    for nm, xc, kw in ROWS:
        f, E = run_mode(c, ON, 1, xc, **kw); row, _ = std.row(f, E); d = f - f_ref
        row.update(d_vs_s085=float(np.median(d)), pw_vs_s085=float(np.mean(d > 1e-5)), ref_s085=float(np.median(f_ref)))
        res.setdefault(nm, {})[bn] = row
    print(bn, 'done %.0fs' % (time.time() - t0), flush=True)
res['parity_mode0_vs_std'] = par
for nm, _, _ in ROWS:
    T = res[nm]
    print('%-34s path %.6f (d %+.6f pw %.3f) real %.6f (d %+.6f) spx55 %.6f spx70 %.6f' % (nm, T['dev250_path']['cagr'], T['dev250_path']['d_vs_s085'],
          T['dev250_path']['pw_vs_s085'], T['real_ndx_86_14']['cagr'], T['real_ndx_86_14']['d_vs_s085'], T['real_spx_55_85']['cagr'], T['real_spx_70_85']['cagr']))
print('parity', par)

# ---- adoption-rule statistic, re-derived from the std engine's own record of v1 on the real path (base terms)
c = std.contexts()['real_ndx_86_14']; B, bfn, bp, fs = std.s085(c)
k = dict(beng.F1); k['fstep'] = fs; pp, D = beng._args(k)
feat = np.ascontiguousarray(bk.features(c)[0])
o, rec = beng.run_rec(np.ascontiguousarray(c.r[0]), np.ascontiguousarray(c.rf[0]), np.ascontiguousarray(B[0], dtype=np.float64), feat, int(pp['delay']),
                      pp['cost'], pp['tax'], D, int(pp['harvest']), pp['hthr'], pp['cspr'], pp['er3'], pp['step'], bfn, np.asarray(bp, dtype=np.float64), float(pp['fstep']))
d = cal[c.ii[0]]; T = len(d); cur = rec[:, 1]                       # level in force at the close of simulated day k (path index t = k + WARM)
onv = on.reindex(d).values
ev = []
for kk in range(1, len(cur)):
    if cur[kk] < cur[kk - 1] - 1e-12:
        t = kk + WARM
        elig = (kk % 252 != 251) and (t < T - 1)
        if t + 1 < T: ev.append(dict(kind=1, t_open=t + 1, date=d[t + 1], dexp=cur[kk - 1] - cur[kk], on=onv[t + 1], elig=int(elig)))
ev = pd.DataFrame(ev)
# tax-payment sales: taken from the OV1-B engine log (kind 2) because the sold fraction is internal to the engine
ONr = O.on_ctx(on, cal, c.ii)
o0, rec0, ev0 = G.engine_log(c, B, bfn, bp, fs, ONr, mode=0)
lg = pd.DataFrame(ev0, columns=['t', 'dexp', 'kind', 'elig'])
lg1 = lg[lg.kind == 1]; lg2 = lg[(lg.kind == 2) & (lg.t < T)].copy()
res['event_xcheck'] = dict(my_level_decreases=int(len(ev)), log_level_decreases=int(len(lg1)),
                           same_days=bool(len(ev) == len(lg1) and np.array_equal(ev.t_open.values, lg1.t.astype(int).values)),
                           max_abs_dexp_diff=float(np.max(np.abs(ev.dexp.values - lg1.dexp.values))) if len(ev) == len(lg1) else None,
                           tax_sales=int(len(lg2)))
tx = pd.DataFrame(dict(kind=2, t_open=lg2.t.astype(int).values, date=d[lg2.t.astype(int).values], dexp=lg2.dexp.values, on=onv[lg2.t.astype(int).values], elig=1))
allv = pd.concat([ev, tx], ignore_index=True)
halves = {}
for nm, a, b in (('1999_2007', '1999-03-11', '2007-12-31'), ('2008_2014', '2008-01-02', '2014-12-31')):
    w = allv[(allv.date >= pd.Timestamp(a)) & (allv.date <= pd.Timestamp(b)) & (allv.elig == 1)]
    w1 = w[w.kind == 1]
    halves[nm] = dict(n_events=int(len(w)), n_level=int(len(w1)), n_tax=int((w.kind == 2).sum()),
                      S_weighted_all=float((w.dexp * w.on).sum()),          # OV1-B definition: sum |d exposure| x overnight return, incl. tax sales
                      S_weighted_level_only=float((w1.dexp * w1.on).sum()),
                      S_plain_sum_level_only=float(w1.on.sum()),             # literal reading: summed overnight return on decrease days
                      S_plain_sum_all=float(w.on.sum()),
                      frac_pos_level=float((w1.on > 0).mean()) if len(w1) else None,
                      n_zero_on=int((w.on == 0).sum()))
res['halves'] = halves
print('event_xcheck', res['event_xcheck']); print('halves', json.dumps(halves, indent=1))
b6, x6 = res['S6_OPENFILL'], res['S6x_OPENFILL_xcost0.1']
cond = dict(c1_path_d_ge_0p3pp=bool(b6['dev250_path']['d_vs_s085'] >= 0.003), c2_real_d_gt0=bool(b6['real_ndx_86_14']['d_vs_s085'] > 0),
            c3_xcost_path_gt0=bool(x6['dev250_path']['d_vs_s085'] > 0), c3_xcost_real_gt0=bool(x6['real_ndx_86_14']['d_vs_s085'] > 0),
            c4_half1_gt0=bool(halves['1999_2007']['S_weighted_all'] > 0), c4_half2_gt0=bool(halves['2008_2014']['S_weighted_all'] > 0),
            c4_half2_gt0_plain=bool(halves['2008_2014']['S_plain_sum_level_only'] > 0), c4_half1_gt0_plain=bool(halves['1999_2007']['S_plain_sum_level_only'] > 0))
cond['adopt'] = bool(all(cond[k] for k in ('c1_path_d_ge_0p3pp', 'c2_real_d_gt0', 'c3_xcost_path_gt0', 'c3_xcost_real_gt0', 'c4_half1_gt0', 'c4_half2_gt0')))
res['adoption_rule'] = cond; print('adoption', cond)
json.dump(res, open(OUT + 'v_openfill.json', 'w'), indent=1, default=float)
print('done %.0fs' % (time.time() - t0))
