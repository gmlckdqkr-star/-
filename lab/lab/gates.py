"""Evaluation: dev-window metrics, paired block bootstrap, sealed holdout verdict.

MVP gates. They are placeholders for the locked project bars (G0-G3 lock + A17/A41/A49 addenda), which the
next phase ports from the existing judge code. Labels in every output say "MVP 관문".

Holdout rule: rows after DEV_END are never printed. The holdout only returns PASS / REJECT / BUDGET
(BUDGET = this family already used its holdout looks), and each look is written to the ledger.
"""
import numpy as np, pandas as pd
from . import engine

DEV_END = pd.Timestamp('2014-12-31')
HOLDOUT_START = pd.Timestamp('2015-01-01')


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
    cost = float(spec.get('cost', 0.003)); delay = int(spec.get('delay', 2))
    start = pd.Timestamp(spec.get('dev_start', '1986-10-01'))
    Wb = pd.DataFrame({baseline: 1.0, 'CASH': 0.0}, index=R.index)
    # start only when every held sleeve and the baseline have return data (no silent zero returns)
    held = [c for c in W.columns if c != 'CASH' and (W[c] > 0).any()] + [baseline]
    start = max([start] + [R[c].first_valid_index() for c in held])
    dev = engine.run(W, R, start, DEV_END, cost=cost, delay=delay)
    devb = engine.run(Wb, R, start, DEV_END, cost=cost, delay=delay)
    rs = dev['E'].pct_change().dropna(); rb = devb['E'].pct_change().reindex(rs.index).fillna(0.0)
    bs = paired_bootstrap(rs.values, rb.values)
    # sealed holdout
    end = R.index[-1]
    ho = engine.run(W, R, HOLDOUT_START, end, cost=cost, delay=delay)
    hob = engine.run(Wb, R, HOLDOUT_START, end, cost=cost, delay=delay)
    ho_pass = (ho['cagr_at'] >= hob['cagr_at']) and (ho['mdd'] >= hob['mdd'] - 0.10)
    dev_pass = (bs['s_med_y12'] >= bs['b_med_y12']) and (bs['s_p_dd80'] < 0.01)
    return dict(
        baseline=baseline, dev_start=str(start.date()),
        dev=dict(cagr_at=dev['cagr_at'], mdd=dev['mdd'], turn=dev['turn'], trades=dev['trades'],
                 yrs=dev['yrs'], base_cagr_at=devb['cagr_at'], base_mdd=devb['mdd']),
        boot=bs, dev_pass=bool(dev_pass), holdout_pass=bool(ho_pass))
