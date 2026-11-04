"""PRECOMMIT_HY1 section 2 (B): oracle ladder for switching between method streams. Oracle evaluations, not candidate trials.
Output results/ladder_le2014.json"""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/hybrid/code')
import hy_common as C

SETS = {'B2V': ['VALPROF4_L1'], 'B2B': ['BOND10_L3'], 'BK4': ['VALPROF4_L1', 'BOND10_L3', 'SPXH_L1']}
PS = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.90, 1.00]
BASES = [('dev250_path', 1), ('real_ndx_86_14', 40), ('real_spx_55_85', 40)]
OUT = '/mnt/project-files/research/hybrid/results/ladder_le2014.json'

def picks_for(truth, M, p, rng):
    """truth (Q, nb) -> noisy picks: with prob p the truth, else uniform among the other M-1"""
    ok = rng.random(truth.shape) < p
    other = (truth + 1 + rng.integers(0, M - 1, size=truth.shape)) % M
    return np.where(ok, truth, other)

res = {}
for bn, seeds in BASES:
    for sname, names in SETS.items():
        R = C.sleeve_returns(bn, names); P, T, M = R.shape
        f, _ = C.block_logsum(R); ks = C.block_starts(T)
        truth = np.stack([np.argmax(f(k), axis=1) for k in ks], axis=1)          # (P, nb)
        base = float(np.mean(truth == 0))
        Q = P * seeds if P == 1 else P
        tr = np.repeat(truth, seeds, 0) if P == 1 else truth
        for p in PS:
            t0 = time.time()
            rng = np.random.default_rng(int(p * 1000) + 7 * len(names) + (0 if bn == 'dev250_path' else 99))
            pk = picks_for(tr, M, p, rng)
            A, Wd = C.inforce_from_picks(pk, T, M, ks)
            fin, EE, NT = C.run_tiled(bn, names, A, Wd)
            s = C.summary(fin, EE); s['hit_realized'] = float(np.mean(pk == tr)); s['base_s085'] = base
            s['trades_per_yr'] = float(np.median(NT) / (T / 252))
            res['%s|%s|%.2f' % (bn, sname, p)] = s
            print(bn, sname, p, {k: round(v, 4) if isinstance(v, float) else v for k, v in s.items()}, round(time.time() - t0, 1), flush=True)
        json.dump(res, open(OUT, 'w'), indent=1)
print('done')
