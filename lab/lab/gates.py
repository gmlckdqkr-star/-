"""Dev summary: dev-window (<= 2014-12-31) metrics on real data + paired block bootstrap of the dev returns.

This is a SCREEN, not a bar verdict: the project bar (A17 Q + A50 G60-W + A49 G-MKT) is applied by lab/bb.py on the
blackbox2 paths. The old ad-hoc holdout look (2015+ PASS/REJECT with a per-family look budget) is removed: no number,
pass flag or look over dates after 2014-12-31 is computed here. The caller passes data cut at DEV_END.
"""
import numpy as np, pandas as pd
from . import dsl, engine

DEV_END = pd.Timestamp('2014-12-31')
DEV_VERSION = 2          # bump when the dev summary changes for an unchanged spec hash (cli recomputes stale rows)
                         # 2: periodic rebalance trades drift back on sampled rows; rp solver; invvol warm-up
SCREEN_LABEL = '개발 선별 (기준 아님)'


def paired_bootstrap(rs, rb, years=(7, 12), n_paths=2000, block=63, seed=7):
    """Circular block bootstrap on daily net returns; strategy and baseline share the same draws."""
    rs = np.asarray(rs, float); rb = np.asarray(rb, float); T = len(rs)
    H = 252 * max(years); nb = H // block + 1
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, T, size=(n_paths, nb))
    ix = ((starts[:, :, None] + np.arange(block)[None, None, :]) % T).reshape(n_paths, -1)[:, :H]
    out = {}
    for tag, r in (('s', rs), ('b', rb)):
        lw = np.cumsum(np.log1p(r[ix]), axis=1)
        for y in years:
            out[f'{tag}_med_y{y}'] = float(np.exp(np.median(lw[:, 252 * y - 1])))
        peak = np.maximum.accumulate(lw, axis=1)
        out[f'{tag}_p_dd80'] = float(np.mean((lw - peak).min(axis=1) <= np.log(0.2)))
    return out


def evaluate(W, R, spec, baseline='QQQ'):
    """W, R: weights and sleeve returns. Only rows <= DEV_END are used (refuses anything later)."""
    R = R[R.index <= DEV_END]
    W = W[W.index <= DEV_END]
    dsl.check_spec(spec)                                  # delay >= 2 (no same-bar / future fills)
    acct, A = dsl.account_of(spec)
    cost = max(A['min_cost'], float(spec.get('cost', A['min_cost']))); delay = int(spec.get('delay', dsl.MIN_DELAY))
    kw = dict(cost=cost, delay=delay, tax=A['tax'], tax_mode=A['tax_mode'])
    if acct == 'kr_etf':
        from . import data
        kw['tax_by_col'] = dict(data.KR_TAX)
    start = pd.Timestamp(spec.get('dev_start', '1986-10-01'))
    Wb = pd.DataFrame({baseline: 1.0, 'CASH': 0.0}, index=R.index)
    # start only when every held sleeve and the baseline have return data (no silent zero returns)
    held = [c for c in W.columns if c != 'CASH' and (W[c] > 0).any()] + [baseline]
    start = max([start] + [R[c].first_valid_index() for c in held])
    reb = spec.get('rebalance', 'daily')
    # a non-daily `rebalance` trades back to target on its sampled rows (else constant weights would just drift)
    rebal = None if reb == 'daily' else pd.Series(dsl.reb_rows(W.index, reb), index=W.index)
    dev = engine.run(W, R, start, DEV_END, rebal=rebal, **kw)
    devb = engine.run(Wb, R, start, DEV_END, **kw)
    assert dev['E'].index[-1] <= DEV_END
    rs = dev['E'].pct_change().dropna(); rb = devb['E'].pct_change().reindex(rs.index).fillna(0.0)
    bs = paired_bootstrap(rs.values, rb.values)
    screen = (bs['s_med_y12'] >= bs['b_med_y12']) and (bs['s_p_dd80'] < 0.01)
    return dict(
        baseline=baseline, account=acct, dev_start=str(start.date()), dev_end=str(DEV_END.date()), dev_version=DEV_VERSION,
        dev=dict(cagr_at=dev['cagr_at'], mdd=dev['mdd'], turn=dev['turn'], trades=dev['trades'],
                 yrs=dev['yrs'], base_cagr_at=devb['cagr_at'], base_mdd=devb['mdd']),
        boot=bs, screen=SCREEN_LABEL, screen_pass=bool(screen))
