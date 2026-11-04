"""Verifier step 4 (check A): CPPI engine _cppi1.
  (1) stored D1a/D1b numbers on the real bases;
  (2) replay: feed the CPPI's own in-force share path AA into the general engine _dyn (A = AA, Wd = 1 - AA) -> must reproduce fin/EE
      exactly if the accounting (tax, harvest, cost, realized gains, band checks) is the same as _dyn1 under SWITCHING weights;
  (3) decision check: recompute every decision from the equity curve EE alone (HWM = running max incl. 1.0, E at close k, k % 21 == 0),
      build the in-force schedule (traded at close k+2) myself and compare with AA;
  (4) look-ahead perturbation: scramble every input strictly after day j -> AA[:j+3] and EE[:j+1] must be unchanged."""
import os, sys, json, time
os.environ['NUMBA_CACHE_DIR'] = '/tmp/claude-0/-home-user--/0e26f5bd-b937-55ae-81a7-0c4a9abb6560/scratchpad/verify/nbcache'
sys.path.insert(0, '/mnt/project-files/research/hybrid/code')
import numpy as np
import hyeng as H, ii

ST = json.load(open('/mnt/project-files/research/hybrid/results/struct_le2014.json'))
bases = sys.argv[1].split(',') if len(sys.argv) > 1 else ['real_ndx_86_14', 'real_spx_55_85']
pts = {'D1a': (3.0, 0.6), 'D1b': (2.0, 0.7)}


def cppi_raw(TQ, DEP, CU, Sa, SOa, m, f, delay=2, cost=0.003):
    return H._cppi(np.ascontiguousarray(TQ), np.ascontiguousarray(DEP), np.ascontiguousarray(CU), np.ascontiguousarray(Sa),
                   np.ascontiguousarray(SOa), float(m), float(f), float(cost), H.PP['tax'], H.DED, int(H.PP['harvest']), H.PP['hthr'],
                   21, 0.05, 0.25, int(delay))


def schedule_from_equity(EE, m, f, delay=2, rbn=21):
    """my own decision rule: decision at close k (k % rbn == 0) from E_k and HWM_k = max(1, max E_0..k); in force (traded) at close k+delay"""
    P, T = EE.shape
    hwm = np.maximum(np.maximum.accumulate(EE, axis=1), 1.0)
    a0 = min(max(m * (1 - f), 0.0), 1.0)
    S = np.full((P, T), a0)
    for k in range(0, T, rbn):
        a = np.clip(m * (EE[:, k] - f * hwm[:, k]) / EE[:, k], 0, 1)
        s = k + delay
        if s < T: S[:, s:] = a[:, None]
    return S


for bn in bases:
    t0 = time.time()
    TQ, DEP, CU, _ = H.ref(bn); S, SO = ii.arrays(bn); j = H.sid('BOND10_L1')
    Sa = S[:, :, j:j + 1].astype(np.float64); SOa = SO[:, :, j:j + 1].astype(np.float64)
    T = TQ.shape[1]
    for nm, (m, f) in pts.items():
        fin, EE, AA = H.run_cppi(bn, 'BOND10_L1', m, f)
        c = float(np.median(H.cagr(fin, T)))
        st = ST.get('%s|%s' % (bn, nm), {})
        print(bn, nm, 'cagr %.4f (stored %.4f)  share_mean %.4f (stored %.4f)' % (c, st.get('cagr', np.nan), AA.mean(), st.get('share_mean', np.nan)))
        # (2) replay through _dyn
        f2, E2, NT = H.run(bn, AA, (1.0 - AA)[:, :, None], ['BOND10_L1'])
        print('   replay via _dyn: max|log fin diff| %.2e   max|log EE diff| %.2e' % (
            np.max(np.abs(np.log(fin) - np.log(f2))), np.max(np.abs(np.log(EE) - np.log(E2)))))
        # (3) decisions from the equity curve alone
        sch = schedule_from_equity(EE, m, f)
        print('   decision schedule from EE (own code) vs AA: max abs diff %.2e ; share of days a=0 %.3f' % (np.max(np.abs(sch - AA)), np.mean(AA < 1e-9)))
        # (4) perturbation (first 50 paths only on path bases to save time)
        Pn = min(TQ.shape[0], 50)
        for jj in [400, 3001, 5000]:
            rng = np.random.default_rng(jj)
            TQ2, DEP2, Sa2 = TQ[:Pn].copy(), DEP[:Pn].copy(), Sa[:Pn].copy(); CU2 = CU[:Pn].copy()
            TQ2[:, jj + 1:] = rng.normal(0, 0.05, TQ2[:, jj + 1:].shape); Sa2[:, jj + 1:, 0] = rng.normal(0, 0.02, Sa2[:, jj + 1:, 0].shape)
            DEP2[:, jj + 1:] = rng.uniform(0, 0.001, DEP2[:, jj + 1:].shape)
            CU2[:, jj + 1:] = rng.choice([0.0, 1.0, 3.0], CU2[:, jj + 1:].shape)
            fa, Ea, Aa = cppi_raw(TQ[:Pn], DEP[:Pn], CU[:Pn], Sa[:Pn], SOa[:Pn], m, f)
            fb, Eb, Ab = cppi_raw(TQ2, DEP2, CU2, Sa2, SOa[:Pn], m, f)
            okA = np.array_equal(Aa[:, :jj + 3], Ab[:, :jj + 3]); okE = np.array_equal(Ea[:, :jj + 1], Eb[:, :jj + 1])
            chg_after = np.mean(np.any(Aa[:, jj + 3:] != Ab[:, jj + 3:], axis=1))
            print('   perturb after day %d: AA[:j+3] unchanged %s, EE[:j+1] unchanged %s (paths whose later AA changed: %.2f)' % (jj, okA, okE, chg_after))
    print(bn, 'done %.1f s' % (time.time() - t0), flush=True)
