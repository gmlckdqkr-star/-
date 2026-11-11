"""<= 2014 only (no post-2014 row is touched): evaluator v2 against the locked standard.
 1 the account of v1 through xeng is bit-identical to std.engine (ce.runPE / beng.run1), zero idle interest, on the <= 2014 calendar;
 2 the liquidation value on the last day equals the engine's final after-tax wealth, and on sampled days equals the final wealth of a
   run cut at that day (so V is exactly what MS1 reports, day by day);
 3 the recorded figures 30.53% (zero interest) and 31.08% (standard cash) are reproduced;
 4 the prefix test passes for v1 and FAILS for a planted look-ahead, a planted full-sample statistic and a centred window;
   brake parameters that carry a full-sample number are void by the output rules;
 5 the raw-level test of the extra inputs passes, and fails for a planted backward fill;
 6 a look-ahead planted in the v1 shadow level is caught through a candidate that reads it."""
import sys, numpy as np
sys.path.insert(0, '/home/user/-/research_xv1/code')
import xv1, std, xeng
from std import bk, beng, ce

X = xv1.frame(xv1.OLD_END); v = xv1.View(X); m = xv1._call(xv1.ref, v); cal = xv1.Cal(xv1.acc_dates(X))
print('days', cal.n, cal.dates[0].date(), cal.dates[-1].date())
c = std.contexts()['real_ndx_86_14']
fin, EE = std.engine(c, *std.s085(c), cspr=10.0)
rec = xv1._run(v, m)
print('1 equity path xeng vs std.engine: differing cells', int(np.sum(rec[:, 0] != EE[0])), '| max abs rel diff %.1e' % np.max(np.abs(rec[:, 0] / EE[0] - 1)))
k = dict(beng.F1); k['fstep'] = m['fstep']; k['cspr'] = 10.0; pp, D = beng._args(k)
def final(n):
    o = np.zeros(beng.NOUT); r4 = np.zeros((1, 4)); T = n + xv1.WARM + 1
    beng.run1(np.ascontiguousarray(c.r[0][:T]), np.ascontiguousarray(c.rf[0][:T]), np.ascontiguousarray(m['B'][:T]), np.ascontiguousarray(v.feat[:T]),
              int(pp['delay']), pp['cost'], pp['tax'], D, int(pp['harvest']), pp['hthr'], pp['cspr'], pp['er3'], pp['step'], m['bfn'], m['bp'], o, r4, 0, float(pp['fstep']))
    return o[0]
days = list(range(5, cal.n, 97)) + [cal.n - 1]
dv = max(abs(rec[n, 4] / final(n) - 1) for n in days)
print('2 liquidation value vs final wealth of a run cut at the day: %d days, max abs rel diff %.1e' % (len(days), dv))
yrs = cal.n / 252
print('3 zero-interest CAGR after liquidation tax: %.4f%% from V (record 30.53) | std.engine %.4f%%' % (100 * (rec[-1, 4] ** (1 / yrs) - 1), 100 * fin[0]))
print('  standard cash: %.4f%% (record 31.08)' % (100 * std.engine(c, *std.s085(c))[0][0]))
def pt(mk):
    try: return xv1.prefix_test(mk, end=xv1.OLD_END, n_rand=25)
    except xv1.Void as e: return 'VOID: %s' % e
print('4 prefix test, v1:', pt(xv1.ref))

def cheat_future(w):
    o = xv1.ref(w); B = np.array(o['B'], dtype=float).reshape(-1); r = w.c.r[0]
    B[:-3][r[3:] < -0.03] = 0.0; o['B'] = B; return o
def cheat_fullsample(w):
    o = xv1.ref(w); B = np.array(o['B'], dtype=float).reshape(-1); vol = w.c.vol(20)[0]
    B[vol > np.nanquantile(vol, 0.9)] = 0.0; o['B'] = B; return o
print('  planted look-ahead (3 rows):', pt(cheat_future))
print('  planted full-sample quantile:', pt(cheat_fullsample))
def cheat_centred(w):
    o = xv1.ref(w); B = np.array(o['B'], dtype=float).reshape(-1); r = w.c.r[0]
    m = np.convolve(r, np.ones(5) / 5, 'same'); B[m < -0.02] = np.minimum(B[m < -0.02], 1.0); o['B'] = B; return o
def cheat_bp(w):
    o = xv1.ref(w); bp = np.array(o['bp'], dtype=float); bp[-1] += 1e-9 * float(np.nansum(w.c.r[0])); o['bp'] = bp; return o
print('  planted centred 5-row window:', pt(cheat_centred))
print('  planted full-sample number in the brake parameters:', pt(cheat_bp))
import xdata, pandas as pd
NM = ('chips', 'semis', 'ret:SOXX', 'ret:TLT', 'ret:SOXL', 'kf:BusEq', 'kf:Money', 'lvl:_VIX3M@ext', 'cal:month', 'cal:ymod4')
print('5 raw-level test of extra inputs %s:' % (NM,), xv1.raw_extras_test(NM, end=xv1.OLD_END))
_ret = xdata.ret
xdata.ret = lambda key, idx, f='panel_f32.npz.xz': pd.Series(_ret(key, idx, f)).bfill(limit=3).values
print('  planted 3-row backward fill:', xv1.raw_extras_test(('ret:SOXX',), end=xv1.OLD_END)); xdata.ret = _ret
real_shadow = xv1._Eng.shadow
def ahead(e):
    tg, hd = real_shadow(e); return (np.r_[tg[3:], np.repeat(tg[-1], 3)], hd)
def uses_shadow(w):
    o = xv1.ref(w); B = np.array(o['B'], dtype=float).reshape(-1); k = w.ref_target < 1.5; B[k] = np.minimum(B[k], 1.0); o['B'] = B; return o
xv1._Eng.shadow = ahead; print('6 shadow level taken 3 rows early, candidate that reads it:', pt(uses_shadow))
xv1._Eng.shadow = real_shadow; print('  the same candidate with the true shadow level:', pt(uses_shadow))
