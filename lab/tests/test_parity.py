"""Parity: lab engine + DSL must equal research/beat_qld/code (engine.run on strats.A) exactly."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/beat_qld/code')
import engine as old_engine, strats as old_strats  # noqa: E402
sys.path.insert(0, __file__.rsplit('/tests/', 1)[0])
from lab import data, dsl, engine  # noqa: E402

SEAL = pd.Timestamp('2014-12-31')   # holdout seal: no equity / metric is computed on a date after this


def test_parity():
    spec = dsl.load_spec(__file__.rsplit('/tests/', 1)[0] + '/specs/trend_tqqq_200.yaml')
    F, R, rf, SRC = data.build(['TQQQ'])
    F, R = F[F.index <= SEAL], R[R.index <= SEAL]
    W = dsl.compile_weights(spec, F, ['TQQQ'])
    W0 = old_strats.A(); W0 = W0[W0.index <= SEAL]
    R0 = old_strats.R[old_strats.R.index <= SEAL]
    dmax = 0.0
    for (a, b) in [('1990-01-01', '2004-12-31'), ('2005-01-01', '2014-12-31'), ('1990-01-01', '2014-12-31')]:
        assert pd.Timestamp(b) <= SEAL
        n = engine.run(W, R, pd.Timestamp(a), pd.Timestamp(b))
        o = old_engine.run(W0, R0, pd.Timestamp(a), pd.Timestamp(b))
        assert n['E'].index[-1] <= SEAL and o['E'].index[-1] <= SEAL
        d = float(np.abs(n['E'].values - o['E'].values).max())
        assert d < 1e-9, d
        assert abs(n['cagr_at'] - o['cagr_at']) < 1e-12
        dmax = max(dmax, d)
    print('parity ok (windows <= 2014-12-31): max |E_new - E_old| =', dmax)

if __name__ == '__main__':
    test_parity()
