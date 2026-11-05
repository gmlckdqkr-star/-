"""OV1-B step 2: EARLY pre-gate (PRECOMMIT section 5). Reads opens only up to 1999-12-31.
(i)  x_t = ln(O_t/C_{t-1}) - ln(C_t/O_t); SPY 1993-02-01..1999-03-10 + QQQ 1999-03-11..1999-12-31; mean > 0 and NW t (lag 10) >= 2.
(ii) S = sum over v1 (mode 0) decrease fills on real_ndx_86_14 with fill open e+1 in 1993-02-01..1999-12-31 of |dexp| x on_{e+1} > 0."""
import os, sys, json
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/code'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ov1lib as L, std
import eng_ov1b as G, onleg as O
OUT = '/mnt/project-files/research/ov1/lanes/OV1-B/results/'
CUT = pd.Timestamp('1999-12-31'); SW = pd.Timestamp('1999-03-11')


def nw_t(x, lag=10):
    x = np.asarray(x, float); n = len(x); m = x.mean(); e = x - m
    lrv = e @ e / n
    for l in range(1, lag + 1):
        lrv += 2 * (1 - l / (lag + 1)) * (e[l:] @ e[:-l]) / n
    return m, m / np.sqrt(lrv / n), n


cal_all = L.dates()['real_ndx_86_14']
cal = cal_all[(cal_all >= pd.Timestamp('1993-01-29')) & (cal_all <= CUT)]
spy = O.spy_panel('1999-12-31'); qqq = O.qqq_td('1999-12-31')
assert spy.index.max() <= CUT and qqq.index.max() <= CUT
on_s, st_s = O.raw_on(spy, cal); on_q, st_q = O.raw_on(qqq, cal)
id_s = np.log(spy['close'].reindex(cal) / spy['open'].reindex(cal)); id_q = np.log(qqq['close'].reindex(cal) / qqq['open'].reindex(cal))
# (i)
sel_s = (cal >= pd.Timestamp('1993-02-01')) & (cal < SW); sel_q = (cal >= SW) & (cal <= CUT)
lon = pd.concat([np.log1p(on_s[sel_s]), np.log1p(on_q[sel_q])]); lid = pd.concat([id_s[sel_s], id_q[sel_q]])
x = (lon - lid); ok = x.notna(); dropped = int((~ok).sum()); x = x[ok]
m, t, n = nw_t(x.values, 10)
pi = dict(window='SPY 1993-02-01..1999-03-10 + QQQ 1999-03-11..1999-12-31', n=int(n), dropped_days=dropped,
          stale_open_spy=int(st_s[sel_s].sum()), stale_open_qqq=int(st_q[sel_q].sum()),
          mean_log_overnight=float(lon[ok].mean()), mean_log_intraday=float(lid[ok].mean()),
          mean_x=float(m), nw_t_lag10=float(t), ann_overnight=float(lon[ok].mean() * 252), ann_intraday=float(lid[ok].mean() * 252),
          spy_part=dict(n=int(x[x.index < SW].shape[0]), mean_x=float(x[x.index < SW].mean()), nw_t=float(nw_t(x[x.index < SW].values)[1])),
          qqq_part=dict(n=int(x[x.index >= SW].shape[0]), mean_x=float(x[x.index >= SW].mean())))
pi['PASS'] = bool(m > 0 and t >= 2.0)
print('(i)', pi, flush=True)
# (ii)
c = std.contexts()['real_ndx_86_14']; B, bfn, bp, fs = std.s085(c)
o, rec, ev = G.engine_log(c, B, bfn, bp, fs, np.zeros(c.r.shape), mode=0)
d = cal_all[c.ii[0]]
on_mix = pd.concat([on_s[(cal >= pd.Timestamp('1993-02-01')) & (cal < SW)], on_q[(cal >= SW) & (cal <= CUT)]])
rows = []
for tj, dexp, kind, elig in ev:
    tj = int(tj)
    if tj >= len(d): continue
    day = d[tj]
    if not (pd.Timestamp('1993-02-01') <= day <= CUT): continue
    onv = on_mix.get(day, np.nan)
    rows.append(dict(date=str(day.date()), dexp=float(dexp), kind=int(kind), elig=int(elig), on=None if pd.isna(onv) else float(onv)))
R = pd.DataFrame(rows)
E = R[R.elig == 1].copy(); miss = int(E.on.isna().sum()); E['on'] = E.on.fillna(0.0)
S = float((E.dexp * E.on).sum())
pii = dict(window='real_ndx_86_14 v1 decrease fills, open e+1 in 1993-02-01..1999-12-31', n_events=int(len(E)),
           n_level=int((E.kind == 1).sum()), n_tax=int((E.kind == 2).sum()), n_not_eligible_k251=int((R.elig == 0).sum()),
           missing_on=miss, sum_dexp=float(E.dexp.sum()), S=S, S_level_only=float((E.dexp * E.on)[E.kind == 1].sum()),
           mean_on_event_days=float(E.on.mean()), mean_on_all_days=float(on_mix.dropna().mean()),
           frac_on_positive=float((E.on > 0).mean()), v1_real_cagr_check=float(np.maximum(o[0], 1e-9) ** (252 / rec.shape[0]) - 1))
pii['PASS'] = bool(S > 0)
print('(ii)', pii, flush=True)
R.to_csv(OUT + 'pregate_ii_events.csv', index=False)
res = dict(pregate_i=pi, pregate_ii=pii, PREGATE_PASS=bool(pi['PASS'] and pii['PASS']))
json.dump(res, open(OUT + 'pregate.json', 'w'), indent=1)
print('PREGATE_PASS', res['PREGATE_PASS'])
