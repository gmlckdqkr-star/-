"""M3 (d): measured stack step 'fee cut on top of ISA75/종합25 with real product costs' using the acct3 engine (research/acct3/code/ac3.py),
same setup as acct3 t6_both_real.py (TQQQ drag 1.9 %, KODEX 409820 H drag 0.9 %, ISA cost 0.15 %, ISA delay 2). Only ccost (종합 one-way cost)
changes: 0.003 (MS1) -> 0.0015 (fee 0.10 % + spread 0.05 %). Results stay in the M3 scratchpad (nothing written to research/acct3)."""
import os, sys, json, numpy as np
SCR = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m3/'
os.environ['NUMBA_CACHE_DIR'] = SCR + 'nb'
sys.path.insert(0, '/mnt/project-files/research/acct3/code'); sys.path.insert(0, '/mnt/project-files/research/measure_std')
import ac3, std, bk
B = ac3.prep(); PP = ac3.PP; out = {}
for bn, c in std.contexts().items():
    Bs = np.ascontiguousarray(bk.C3sig(c), dtype=np.float64); feat = np.ascontiguousarray(bk.features(c))
    L2, _ = ac3.levels2(B[bn]['R'], B[bn]['RF'], Bs, feat, 2, .0015, 0.099, 0.0, 0, PP['hthr'], PP['cspr'], .009, PP['step'], ac3.av23sL, ac3.bp23, 0.1)
    B[bn]['LIown'] = np.ascontiguousarray(L2 * 1.5)
PP['er3'] = 0.019
for cc in (0.003, 0.0015):
    for z in (1.0, 0.25):
        key = 'cc%.4f|Z%.2f/I%.2f' % (cc, z, 1 - z); out[key] = {}
        for bn in ('dev250_path', 'real_ndx_86_14', 'real_spx_55_85'):
            r, _ = ac3.run(bn, z, 1 - z, 0, W=1e7, rule=1, isa_own=1, icost=.0015, ier=.009, ccost=cc); out[key][bn] = r
        p = out[key]['dev250_path']
        print('%-22s path %.4f dd80 %.3f | NDX %.4f SPX55 %.4f' % (key, p['cagr'], p['dd80'], out[key]['real_ndx_86_14']['cagr'], out[key]['real_spx_55_85']['cagr']), flush=True)
json.dump(out, open(SCR + 'results/t6_stack.json', 'w'), indent=1)
