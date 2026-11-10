"""FINAL1 lane STACK (PRECOMMIT_FINAL1 section 1). Same v1 rules, only engine account/execution terms change. <=2014 only.
Rows S0-S5, S8 through ov1lib.measure2 (engine_kw); S6/S7 through the unchanged OV1-B engine (mode 1 = decreases fill at next open)."""
import os, sys, json, time
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/code'); sys.path.insert(0, '/mnt/project-files/research/ov1/lanes/OV1-B/code')
import ov1lib as L, std, beng
import eng_ov1b as G, onleg as O
OUT = '/mnt/project-files/research/final1/results/'
t0 = time.time()
ROWS = [('S0_base', {}), ('S1_CASH0', dict(cspr=10.0)), ('S2_CASHRP', dict(cspr=0.005)), ('S3_FEE', dict(cost=0.0012)),
        ('S4_CASHRP_FEE', dict(cspr=0.005, cost=0.0012)), ('S5_CASH0_FEE', dict(cspr=10.0, cost=0.0012)),
        ('S8_delay1_CASHRP_FEE', dict(cspr=0.005, cost=0.0012, delay=1))]
res = {}
for nm, kw in ROWS:
    T = L.measure2(nm, lambda c, bn, kw=kw: (L.v1_B(c),) + L.v1_parts(c) + (kw,), verbose=False)
    res[nm] = T
    print('%-22s path %.4f (d %+.4f pw %.2f dd80 %.2f) real %.4f glued %.4f spx55 %.4f spx70 %.4f' % (
        nm, T['dev250_path']['cagr'], T['dev250_path']['d_vs_s085'], T['dev250_path']['pw_vs_s085'], T['dev250_path']['dd80'],
        T['real_ndx_86_14']['cagr'], T['dev250_glued']['cagr'], T['real_spx_55_85']['cagr'], T['real_spx_70_85']['cagr']), flush=True)

# OPENFILL rows (OV1-B engine, unchanged code; terms changed only through beng.F1 values, restored afterwards)
cal = L.dates()['real_ndx_86_14']
on, info = O.on_series(cal, xcheck=True)
assert on.index.max() <= pd.Timestamp('2014-12-31')
def openfill(xcost=0.0, terms=None):
    keep = dict(beng.F1)
    if terms: beng.F1.update(terms)
    try:
        out = {}
        for bn, c in std.contexts().items():
            ON = O.on_ctx(on, L.dates()[bn], c.ii)
            B, bfn, bp, fs = std.s085(c)
            f, E, o = G.engine_s(c, B, bfn, bp, fs, ON, mode=1, xcost=xcost)
            cand, fc = std.row(f, E)
        # reference = v1 at BASE terms (same as measure2)
            beng.F1.clear(); beng.F1.update(keep)
            rB, rbf, rbp, rfs = std.s085(c); ref, fr = std.row(*std.engine(c, rB, rbf, rbp, rfs))
            if terms: beng.F1.update(terms)
            d = fc - fr
            cand.update(d_vs_s085=float(np.median(d)), pw_vs_s085=float(np.mean(d > 1e-5)), ref_s085=ref['cagr'])
            out[bn] = cand
        return out
    finally:
        beng.F1.clear(); beng.F1.update(keep)
for nm, xc, terms in (('S6_OPENFILL', 0.0, None), ('S6x_OPENFILL_xcost0.1', 0.001, None),
                      ('S7_OPENFILL_CASHRP_FEE', 0.0, dict(cspr=0.005, cost=0.0012)), ('S7x_OPENFILL_CASHRP_FEE_xcost0.1', 0.001, dict(cspr=0.005, cost=0.0012))):
    T = openfill(xc, terms); res[nm] = T
    print('%-34s path %.4f (d %+.4f pw %.2f) real %.4f (d %+.4f)' % (nm, T['dev250_path']['cagr'], T['dev250_path']['d_vs_s085'],
          T['dev250_path']['pw_vs_s085'], T['real_ndx_86_14']['cagr'], T['real_ndx_86_14']['d_vs_s085']), flush=True)

# adoption-rule diagnostic: summed overnight return on v1 decrease days, halves of the ACTUAL open-price window (real path)
c = std.contexts()['real_ndx_86_14']; B, bfn, bp, fs = std.s085(c); d = cal[c.ii[0]]
ON = O.on_ctx(on, cal, c.ii)
o0, rec0, ev0 = G.engine_log(c, B, bfn, bp, fs, ON, mode=0)
ev = pd.DataFrame(ev0, columns=['t', 'dexp', 'kind', 'elig']); ev = ev[(ev.elig == 1) & (ev.t < len(d)) & (ev.t > 0)]
ev['date'] = d[ev.t.astype(int).values]; ev['on'] = on.reindex(ev.date).values
halves = {}
for nm, a, b in (('1999_2007', '1999-03-11', '2007-12-31'), ('2008_2014', '2008-01-02', '2014-12-31')):
    w = ev[(ev.date >= pd.Timestamp(a)) & (ev.date <= pd.Timestamp(b))]
    halves[nm] = dict(n_events=int(len(w)), S=float((w.dexp * w.on).sum()), mean_on=float(w.on.mean()) if len(w) else None)
print('halves', halves, flush=True)
b6, x6 = res['S6_OPENFILL'], res['S6x_OPENFILL_xcost0.1']
adopt = bool(b6['dev250_path']['d_vs_s085'] >= 0.003 and b6['real_ndx_86_14']['d_vs_s085'] > 0 and x6['dev250_path']['d_vs_s085'] > 0
             and x6['real_ndx_86_14']['d_vs_s085'] > 0 and halves['1999_2007']['S'] > 0 and halves['2008_2014']['S'] > 0)
res['OPENFILL_rule'] = dict(halves=halves, adopt=adopt, on_info=info)
print('OPENFILL adopt', adopt)
json.dump(res, open(OUT + 'stack.json', 'w'), indent=1, default=float)
print('done %.0fs' % (time.time() - t0))
