"""Dry gate of batch 1 on the <= 2014 calendar, before registration: every configuration of m_batch1.configs() must pass the
source gate, build, pass the instrument check and the tests that run_batch applies before scoring (raw-level test of its
inputs, prefix test, level-scale test), must not differ from v1 before its T0, and its T0 must respect the bound. Prints
PASS / FAIL, dates of first valid input rows and activity counts only; no account figure of any candidate is computed or printed.

  python t_batch1_old.py [first [last]]     configurations first..last-1 (default all)"""
import os
import sys, time, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import xv1, t_world, m_batch1

t_world.old()
C = m_batch1.configs(); lo = int(sys.argv[1]) if len(sys.argv) > 1 else 0; hi = int(sys.argv[2]) if len(sys.argv) > 2 else len(C)
assert len(set(c.name for c in C)) == len(C) and len(set(c.hash for c in C)) == len(C), 'names or hashes are not unique'
X = xv1.frame(xv1.OLD_END); bad = []; raw = {}
if lo == 0:
    for f in sorted(set(c.file for c in C)): print('source gate %-12s %s' % (f.split('/')[-1], xv1.gate(f) or 'clean'))
    fam = collections.defaultdict(set)
    for c in C: fam[(c.file, c.func)].add(c.family)
    print('functions under more than one family label:', [k[1] for k, v in fam.items() if len(v) > 1], '| families', len(set(c.family for c in C)))
    print('configurations', len(C), '| calendar ends', str(X.index[-1].date()), flush=True)
for c in C[lo:hi]:
    t_ = time.time()
    try:
        pre = xv1._prepare(c.fresh(), c.names, xv1.OLD_END); v, m = pre['v'], pre['m']; e = xv1._eng(v); i0 = len(X) - e.T
        rB = xv1._refm(e.c, e.T)['B']; on = (m['Wt'] != 0).any(axis=1); dB = m['B'] != rB
        fv = [int(np.argmax(~np.isnan(a))) for a in e.x.values() if (~np.isnan(a)).any()]
        first = str(X.index[i0 + max(fv)].date()) if fv else '-'
        t0ok = xv1._t0_ok(pre, c.t0); before = xv1._pre_t0_sig(pre, c.t0)
        if c.names not in raw: raw[c.names] = xv1.raw_extras_test(c.names, end=xv1.OLD_END)['result'] if c.names else 'PASS'
        p = xv1.prefix_test(None, c.names, end=xv1.OLD_END, n_rand=25, fresh=c.fresh, pre=pre); s = xv1.scale_test(c.fresh(), c.names, pre=pre)
        ok = raw[c.names] == 'PASS' and p['result'] == 'PASS' and s == 'PASS' and before == 0 and t0ok
        print('%-16s raw %s prefix %s (%4d cuts) scale %s | inputs from %s T0 %s bound %s differs_before_t0 %d | rows_B_differs %5d rows_w_nonzero %5d mode %s inc %s reads %s | %.0fs' % (
            c.name, raw[c.names], p['result'], p['cuts'], s, first, c.t0, 'ok' if t0ok else 'LATE', before, int(dB[xv1.WARM:].sum()), int(on[xv1.WARM:].sum()),
            m['mode'], m['inc'], ','.join(sorted(e.touched)) or '-', time.time() - t_), flush=True)
    except xv1.Void as err:
        ok = False; print('%-16s VOID: %s | %.0fs' % (c.name, err, time.time() - t_), flush=True)
    if not ok: bad.append(c.name)
print('checked', hi - lo, 'failed', len(bad), bad, '| ALL PASS' if not bad else '| NOT ALL PASS')
