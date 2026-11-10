"""Extra real-night window checks requested by the phase-3 review (information only, outside the pre-registration).
Same engines and conventions as hist_windows.py (delay 2, yearly tax + final liquidation tax, real QQQ night split, single path).
  - T5 and v1 on the reported windows and on NON-overlapping sub-periods, at fee per side 0.83 / 1.66 / 0.30 / 0.60 bp,
    with the t-statistic of the daily paired log-return difference (plain and Newey-West 10 lags)
  - the uploaded presets (US-only; tuned by the upload on 1999-2026, so in-sample everywhere) at 0.83 / 0.30 / 0.60 bp
  python -B code/hist_extra.py dev                              -> results/hist_extra_dev.json   (<=2014)
  ONF1_ALLOW_HOLDOUT=1 python -B code/hist_extra.py holdout     -> holdout/hist_extra_holdout.json (post-2014, information only)"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
import numpy as np, pandas as pd
from dataclasses import replace
import ms1f, ntilt, eng, jp, ov
which = sys.argv[1] if len(sys.argv) > 1 else ''
def add_basis(name, start, end, src_end='2014-12-31', real_file=None):
    B = ms1f.bases()
    R, M = jp.calendar('1984-01-03', src_end); X = jp.mkX(R, M, 'NDX'); F = ov.flags_hist(X)
    i0 = X.index.searchsorted(pd.Timestamp(start)) - ov.WARM; i1 = X.index.searchsorted(pd.Timestamp(end), side='right')
    c = ov.Ctx(X, F, np.arange(i0, i1)[None, :])
    B[name] = dict(dates=X.index, src_r=X['r'].values, ii=c.ii, r=c.r, rf=c.rf, alarm=(c.F['inv'] | c.F['shock6m']), ctx=c, real_file=real_file)
    return X.index[i0 + ov.WARM], X.index[i1 - 1]
if which == 'dev':
    W = {'dev_1999_2014': ('1999-03-10', '2014-12-31'), 'dev_2001_2014': ('2001-01-02', '2014-12-31'), 'dev_2005_2014': ('2005-01-03', '2014-12-31'),
         'sub_1999_2000': ('1999-03-10', '2000-12-29'), 'sub_2001_2004': ('2001-01-02', '2004-12-31'), 'sub_2005_2007': ('2005-01-03', '2007-12-31'),
         'sub_2008_2014': ('2008-01-02', '2014-12-31')}
    kw = dict(); out = paths.RES + 'hist_extra_dev.json'
elif which == 'holdout' and os.environ.get('ONF1_ALLOW_HOLDOUT') == '1':
    W = {'hold_2015_2026': ('2015-01-02', '2026-08-31'), 'all_1999_2026': ('1999-03-10', '2026-08-31'), 'all_2001_2026': ('2001-01-02', '2026-08-31'),
         'sub_2015_2020': ('2015-01-02', '2020-12-31'), 'sub_2021_2026': ('2021-01-04', '2026-08-31')}
    kw = dict(src_end='2026-08-31', real_file=paths.DATA + 'us.csv'); out = paths.HOLD + 'hist_extra_holdout.json'
else:
    sys.exit('usage: hist_extra.py dev   |   ONF1_ALLOW_HOLDOUT=1 hist_extra.py holdout  (post-2014 numbers: holdout folder only)')
T5 = dict(impl=0, tau=1.0, gate=2, phi=0.15)
US = dict(use_kr=False, cash_spread=None)
P = {'P1 v9-US': replace(eng.V9, **US), 'P2 v10-US': replace(eng.V10, **US), 'P3 A-US': replace(eng.PRESET_A, **US)}
FEES = (('0.83bp', 0.000083), ('1.66bp', 0.000166), ('0.30bp', 0.00003), ('0.60bp', 0.00006))
def mdd_of(E): return float((E / np.maximum.accumulate(E) - 1).min())
res = {}
for nm, (a, b) in W.items():
    d0, d1 = add_basis(nm, a, b, **kw); fr, E0, o0 = ntilt.ref(nm)
    r = {'window': [str(d0.date()), str(d1.date())], 'v1': dict(cagr=float(fr[0]), mdd=mdd_of(E0[0]))}
    for lab, fee in FEES:
        f, E1, o = ntilt.run(nm, 'C', fee=fee, **T5); x = np.diff(np.log(E1[0])) - np.diff(np.log(E0[0])); n = len(x)
        t = float(x.mean() / x.std(ddof=1) * np.sqrt(n)); xc = x - x.mean(); v = (xc @ xc) / n
        for L in range(1, 11): v += 2 * (1 - L / 11) * (xc[L:] @ xc[:-L]) / n
        r['T5 ' + lab] = dict(cagr=float(f[0]), mdd=mdd_of(E1[0]), d=float(f[0] - fr[0]), t=t, t_nw=float(x.mean() / np.sqrt(v / n)),
                              tilt_on=float(o[0, 10]), avg_tilt=float(o[0, 14]))
    for cn, cfg in P.items():
        for lab, fee in FEES:
            f, mdd, _, _ = ms1f.measure_one(replace(cfg, c_us=fee), nm, 'C', 2, 0.004, 0, 0.25, 0)
            r['%s %s' % (cn, lab)] = dict(cagr=float(f[0]), mdd=float(mdd[0]), d=float(f[0] - fr[0]))
        f, mdd, _, _ = ms1f.measure_one(replace(cfg, c_us=0.00003), nm, 'C', 2, 0.004, 0, 0.25, 2)
        r['%s 0.30bp bd2' % cn] = dict(cagr=float(f[0]), mdd=float(mdd[0]), d=float(f[0] - fr[0]))
    res[nm] = r
    print('%-14s %s..%s v1 %.1f%%/%.0f%% | T5 d: %s | t %.2f/%.2f | P1 d: %s | P2 d: %s | P3 d: %s' % (
        nm, d0.date(), d1.date(), fr[0] * 100, r['v1']['mdd'] * 100, ' '.join('%s %+.2f' % (l, r['T5 ' + l]['d'] * 100) for l, _ in FEES), r['T5 0.83bp']['t'], r['T5 0.83bp']['t_nw'],
        ' '.join('%+.1f' % (r['P1 v9-US ' + l]['d'] * 100) for l, _ in FEES), ' '.join('%+.1f' % (r['P2 v10-US ' + l]['d'] * 100) for l, _ in FEES),
        ' '.join('%+.1f' % (r['P3 A-US ' + l]['d'] * 100) for l, _ in FEES)), flush=True)
json.dump(res, open(out, 'w'), indent=1)
