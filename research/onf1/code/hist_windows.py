"""Same-basis real-history windows (MS1 conventions: delay 2, yearly tax, final liquidation tax, NDX price index, real QQQ
night split) for v1 and the 12 pre-registered candidates.
  python -B code/hist_windows.py dev       -> windows inside <=2014 (results/hist_dev.json)
  ONF1_ALLOW_HOLDOUT=1 python -B code/hist_windows.py holdout
                                           -> 2015-01-02..2026-08-31 and 1999-03-10..2026-08-31, ONE TIME, information only
                                              (holdout/hist_holdout.json; never used for selection)"""
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
    W = {'dev_1999_2014': ('1999-03-10', '2014-12-31'), 'dev_2001_2014': ('2001-01-02', '2014-12-31'), 'dev_2005_2014': ('2005-01-03', '2014-12-31')}
    kw = dict(); out = paths.RES + 'hist_dev.json'
elif which == 'holdout' and os.environ.get('ONF1_ALLOW_HOLDOUT') == '1':
    W = {'hold_2015_2026': ('2015-01-02', '2026-08-31'), 'all_1999_2026': ('1999-03-10', '2026-08-31'), 'all_2001_2026': ('2001-01-02', '2026-08-31')}
    kw = dict(src_end='2026-08-31', real_file=paths.DATA + 'us.csv'); out = paths.HOLD + 'hist_holdout.json'
    os.makedirs(paths.HOLD, exist_ok=True)
else:
    sys.exit('usage: hist_windows.py dev   |   ONF1_ALLOW_HOLDOUT=1 hist_windows.py holdout  (post-2014 numbers: holdout folder only)')
T = {'T1': dict(impl=0, tau=1.0, gate=0, phi=0.15), 'T2': dict(impl=0, tau=0.5, gate=0, phi=0.075), 'T3': dict(impl=0, tau=2.0, gate=0, phi=0.30),
     'T4': dict(impl=0, tau=1.0, gate=1, phi=0.15), 'T5': dict(impl=0, tau=1.0, gate=2, phi=0.15), 'T6': dict(impl=0, tau=1.0, gate=0, vc=0.09, phi=0.15),
     'F1': dict(impl=1, tau=1.0, gate=0), 'F2': dict(impl=1, tau=2.0, gate=0), 'F3': dict(impl=1, tau=1.0, gate=1), 'v1 via futures (MF1)': dict(impl=1, tau=0.0)}
US = dict(use_kr=False, cash_spread=None)
P = {'P1 v9-US': replace(eng.V9, **US), 'P2 v10-US': replace(eng.V10, **US), 'P3 A-US': replace(eng.PRESET_A, **US)}
res = {}
for nm, (a, b) in W.items():
    d0, d1 = add_basis(nm, a, b, **kw); res[nm] = {'window': [str(d0.date()), str(d1.date())]}
    fr, EE, o = ntilt.ref(nm); mdd = float((EE[0] / np.maximum.accumulate(EE[0]) - 1).min())
    res[nm]['v1'] = dict(cagr=float(fr[0]), mdd=mdd); print('%-15s %s..%s  v1 %.1f%% / %.0f%%' % (nm, d0.date(), d1.date(), fr[0] * 100, mdd * 100), flush=True)
    c = ms1f.bases()[nm]['ctx']; r = c.r[0, ov.WARM:]; yrs = len(r) / 252
    for lev, lab in ((1, 'hold 1x'), (3, 'hold 3x')):
        f, E = ms1f.std.hold(c, lev); res[nm][lab] = dict(cagr=float(f[0]), mdd=float((E[0] / np.maximum.accumulate(E[0]) - 1).min()))
    for cn, k in T.items():
        f, EE, o = ntilt.run(nm, 'C', **k); res[nm][cn] = dict(cagr=float(f[0]), mdd=float((EE[0] / np.maximum.accumulate(EE[0]) - 1).min()), d=float(f[0] - fr[0]))
    for cn, cfg in P.items():
        # d2 = signals delayed 2 days, brake same close (as registered) ; bd2 = brake/cool-down also delayed 2 days (same as v1) ; d0 = no delay
        # all with the yearly tax deduction 0.25 of start equity (as v1).  pkg-assump = cash earns rf-2%p, no financing spread.
        for lab, a in (('d2', dict(delay=2, ded=0.25)), ('d2 bd2', dict(delay=2, ded=0.25, bdel=2)), ('d0', dict(delay=0, ded=0.25)),
                       ('d2 pkg-assump', dict(delay=2, s=0.0, cint=1, ded=0.25)), ('d2 fee x2', dict(delay=2, ded=0.25, fee2=True))):
            a = dict(a); c2 = replace(cfg, c_us=0.000166) if a.pop('fee2', False) else cfg
            f, mdd, w7, w12 = ms1f.measure_one(c2, nm, 'C', **a); res[nm]['%s %s' % (cn, lab)] = dict(cagr=float(f[0]), mdd=float(mdd[0]), d=float(f[0] - fr[0]))
    print('   ' + ' | '.join('%s %.1f/%.0f' % (k, v['cagr'] * 100, v['mdd'] * 100) for k, v in res[nm].items() if isinstance(v, dict) and k != 'v1'), flush=True)
json.dump(res, open(out, 'w'), indent=1)
