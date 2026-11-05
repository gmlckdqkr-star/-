"""OV1-B step 3 (only after PREGATE_PASS): data-quality rules on the full QQQ series, then the measure2-equivalent ONCE
(same loop as ov1lib.measure2: candidate through eng_ov1b mode 1, reference s0.85 through std.engine), F test, FINAL test,
report-only stress (+0.1%/side on postponed fills) and descriptive unseen statistics."""
import os, sys, json, time
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/code'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ov1lib as L, std
import eng_ov1b as G, onleg as O
OUT = '/mnt/project-files/research/ov1/lanes/OV1-B/results/'
assert json.load(open(OUT + 'pregate.json'))['PREGATE_PASS'] is True
t0 = time.time()
cal = L.dates()['real_ndx_86_14']
on, info = O.on_series(cal, xcheck=True)
assert on.index.max() <= pd.Timestamp('2014-12-31')
print('on info', info, flush=True)


def run(xcost):
    out = {}
    for bn, c in std.contexts().items():
        ON = O.on_ctx(on, L.dates()[bn], c.ii)
        B, bfn, bp, fs = std.s085(c)
        f, E, o = G.engine_s(c, B, bfn, bp, fs, ON, mode=1, xcost=xcost)
        cand, fc = std.row(f, E)
        rB, rbf, rbp, rfs = std.s085(c); ref, fr = std.row(*std.engine(c, rB, rbf, rbp, rfs))
        q, _ = std.row(*std.hold(c, 1)); d = fc - fr
        cand.update(d_vs_s085=float(np.median(d)), pw_vs_s085=float(np.mean(d > 1e-5)), ref_s085=ref['cagr'], hold1x=q['cagr'],
                    covered_frac_days=float(np.mean(ON[:, G.WARM:] != 0)), postponed_fills_med=float(np.median(o[:, 11])),
                    open_tax_sales_med=float(np.median(o[:, 12])), d_mean=float(np.mean(d)), d_p10=float(np.percentile(d, 10)),
                    d_p90=float(np.percentile(d, 90)), max_abs_d=float(np.max(np.abs(d))))
        out[bn] = cand
        print('OV1B x%.3f %-15s ' % (xcost, bn) + ' '.join('%s=%.4f' % kv for kv in cand.items()), flush=True)
    out['HEADLINE_MS1'] = out['dev250_path']['cagr']; out['REAL_NDX'] = out['real_ndx_86_14']['cagr']
    out['BEATS_V1_BOTH'] = bool(out['dev250_path']['cagr'] > 0.1616 and out['real_ndx_86_14']['cagr'] > 0.3108)
    return out


M = run(0.0)
F_PASS = bool(M['dev250_path']['d_vs_s085'] > 0.005 and M['real_ndx_86_14']['d_vs_s085'] > 0)
spx_same = bool(M['real_spx_55_85']['max_abs_d'] == 0.0 and M['real_spx_70_85']['max_abs_d'] == 0.0)
FINAL = bool(F_PASS and M['HEADLINE_MS1'] > 0.1616 and M['REAL_NDX'] > 0.3108 and M['dev250_path']['pw_vs_s085'] >= 0.55 and spx_same)
print('F_PASS', F_PASS, 'FINAL', FINAL, 'spx_same', spx_same, '%.0fs' % (time.time() - t0), flush=True)
S = run(0.001)   # report-only stress

# descriptive unseen statistics (report-only)
def nw_t(x, lag=10):
    x = np.asarray(x, float); n = len(x); m = x.mean(); e = x - m; lrv = e @ e / n
    for l in range(1, lag + 1): lrv += 2 * (1 - l / (lag + 1)) * (e[l:] @ e[:-l]) / n
    return float(m), float(m / np.sqrt(lrv / n)), int(n)
qq = O.qqq_td(); u = (cal >= pd.Timestamp('2000-01-03')) & (cal <= pd.Timestamp('2014-12-31'))
lon = np.log1p(on[u]); lid = np.log(qq['close'].reindex(cal[u]) / qq['open'].reindex(cal[u]))
ok = (on[u] != 0) & lid.notna()
m, t, n = nw_t((lon - lid)[ok].values)
desc = dict(unseen_i=dict(window='QQQ 2000-01-03..2014-12-30', n=n, mean_x=m, nw_t=t, ann_overnight=float(lon[ok].mean() * 252),
                          ann_intraday=float(lid[ok].mean() * 252)))
c = std.contexts()['real_ndx_86_14']; B, bfn, bp, fs = std.s085(c); d = cal[c.ii[0]]
ON = O.on_ctx(on, cal, c.ii)
o0, rec0, ev0 = G.engine_log(c, B, bfn, bp, fs, ON, mode=0)
o1, rec1, ev1 = G.engine_log(c, B, bfn, bp, fs, ON, mode=1)
E0 = pd.Series(rec0[:, 0], index=d[G.WARM:]); E1 = pd.Series(rec1[:, 0], index=d[G.WARM:])
ev = pd.DataFrame(ev0, columns=['t', 'dexp', 'kind', 'elig']); ev = ev[(ev.elig == 1) & (ev.t < len(d))]
ev['date'] = d[ev.t.astype(int).values]; ev['on'] = on.reindex(ev.date).values
for nm, a, b in (('1999_03_1999_12', '1999-03-11', '1999-12-31'), ('2000_2014', '2000-01-03', '2014-12-31'), ('2000_2007', '2000-01-03', '2007-12-31'), ('2008_2014', '2008-01-02', '2014-12-31')):
    w = ev[(ev.date >= pd.Timestamp(a)) & (ev.date <= pd.Timestamp(b))]
    desc['real_ndx_S_' + nm] = dict(n_events=int(len(w)), S=float((w.dexp * w.on).sum()), mean_on_event=float(w.on.mean()) if len(w) else None,
                                   frac_pos=float((w.on > 0).mean()) if len(w) else None)
desc['real_ndx_ratio_E_cand_over_v1'] = {k: float(E1.loc[:k].iloc[-1] / E0.loc[:k].iloc[-1]) for k in ('1999-12-31', '2007-12-31', '2014-12-31')}
desc['real_ndx_mode1_postponed_fills'] = float(o1[11]); desc['real_ndx_mode1_open_tax_sales'] = float(o1[12])
print('desc', desc, flush=True)
res = dict(on_info=info, measure=M, F_PASS=F_PASS, FINAL_PASS=FINAL, spx_equals_v1=spx_same, stress_xcost_0p001=S, descriptive=desc, N=1)
json.dump(res, open(OUT + 'measure.json', 'w'), indent=1, default=float)
print('done %.0fs' % (time.time() - t0))
