"""Parity: lab engine + DSL must equal research/beat_qld/code (engine.run on strats.A) exactly."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/beat_qld/code')
import engine as old_engine, strats as old_strats  # noqa: E402
sys.path.insert(0, __file__.rsplit('/tests/', 1)[0])
from lab import data, dsl, engine  # noqa: E402

def test_parity():
    spec = dsl.load_spec(__file__.rsplit('/tests/', 1)[0] + '/specs/trend_tqqq_200.yaml')
    F, R, rf, SRC = data.build(['TQQQ'])
    W = dsl.compile_weights(spec, F, ['TQQQ'])
    W0 = old_strats.A()
    for (a, b) in [('1990-01-01', '2014-12-31'), ('2015-01-01', '2026-10-07')]:
        n = engine.run(W, R, pd.Timestamp(a), pd.Timestamp(b))
        o = old_engine.run(W0, old_strats.R, pd.Timestamp(a), pd.Timestamp(b))
        d = float(np.abs(n['E'].values - o['E'].values).max())
        assert d < 1e-9, d
        assert abs(n['cagr_at'] - o['cagr_at']) < 1e-12
    print('parity ok: max |E_new - E_old| =', d)

if __name__ == '__main__':
    test_parity()
