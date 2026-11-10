"""Independent verifier, lane STACK rows S0-S5 (+S8 report-only) of PRECOMMIT_FINAL1 section 1.
Written from the PRECOMMIT text only; does not import research/final1/code/*. Data <= 2014-12-31."""
import os, sys, json, time
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/code')
import ov1lib as L
OUT = '/mnt/project-files/research/final1/verify_main/results/'
END = pd.Timestamp('2014-12-31')
# calendar check: no basis may hold a row after 2014-12-31
cal = {bn: (str(ix.min().date()), str(ix.max().date()), int(len(ix))) for bn, ix in L.dates().items()}
for bn, ix in L.dates().items():
    assert ix.max() <= END, bn
print('calendars', cal, flush=True)
TERMS = {
    'S0_base': {},                                   # cspr .02, cost .003 (engine defaults)
    'S1_CASH0': {'cspr': 10.0},                      # idle USD earns 0
    'S2_CASHRP': {'cspr': 0.005},                    # rf - 0.5pp, taxed 15.4%
    'S3_FEE': {'cost': 0.0012},                      # 0.12% per side
    'S4_CASHRP_FEE': {'cspr': 0.005, 'cost': 0.0012},
    'S5_CASH0_FEE': {'cspr': 10.0, 'cost': 0.0012},
    'S8_delay1_CASHRP_FEE': {'cspr': 0.005, 'cost': 0.0012, 'delay': 1},
}
def maker(kw):
    def make2(c, basis):
        B = L.v1_B(c); bfn, bp, fstep = L.v1_parts(c)
        return (B, bfn, bp, fstep, dict(kw))
    return make2
res = {'calendars': cal}; t0 = time.time()
for nm, kw in TERMS.items():
    t1 = time.time()
    T = L.measure2(nm, maker(kw), verbose=False)
    res[nm] = T
    print('%-22s path %.6f d %+.6f pw %.3f dd80 %.3f | real %.6f d %+.6f | glued %.6f | spx55 %.6f spx70 %.6f  (%.0fs)' % (
        nm, T['dev250_path']['cagr'], T['dev250_path']['d_vs_s085'], T['dev250_path']['pw_vs_s085'], T['dev250_path']['dd80'],
        T['real_ndx_86_14']['cagr'], T['real_ndx_86_14']['d_vs_s085'], T['dev250_glued']['cagr'],
        T['real_spx_55_85']['cagr'], T['real_spx_70_85']['cagr'], time.time() - t1), flush=True)
json.dump(res, open(OUT + 'v_stack.json', 'w'), indent=1, default=float)
print('done %.0fs' % (time.time() - t0))
