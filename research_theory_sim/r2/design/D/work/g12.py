"""selection-seed check (seed 5, block-resampled worlds): carry-tilted rule A vs plain tracked exposure B"""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D/work')
import exec_engine as ee, sim, rule, rules
T = 7860
for mech in (True, False):
    d = sim.simulate(2000, T, 5, mechanism=mech, block=True)
    r, rf, y = d['r'], d['rf'], d['y10']; close = 1000.0 * np.cumprod(1 + r, axis=1)
    a = ee.summary(ee.run(r, rf, rule.target_levels(close, rf, y)))
    b = ee.summary(ee.run(r, rf, rule.target_levels(close, rf, None)))
    cm = max(ee.summary(ee.run(r, rf, np.full(r.shape, L)))['cagr_med'] for L in (0.5, 1.0, 1.5))
    row = dict(tag='s12_block_seed5', mech=mech, A=a['cagr_med'], B=b['cagr_med'], bestc=cm, trA=a['trades_per_year_med'], trB=b['trades_per_year_med'])
    open('/mnt/project-files/research/theory_sim/r2/design/D/work/variants.jsonl', 'a').write(json.dumps(row) + '\n')
    print(row, flush=True)
