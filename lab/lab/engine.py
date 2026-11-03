"""Backtest engine. Logic copied from research/beat_qld/code/engine.py run() (parity test in tests/).

Weights decided at close t (info <= t) earn returns from t+2 on (delay=2 means 1-bar execution delay).
Cost per side (default 0.30% = 0.25% fee + 0.05% spread) on traded notional. Korean overseas CGT 22% on
yearly net realized gain (average cost, no deduction, no carry-forward); final liquidation taxed.
Cash earns T-bill.
"""
import numpy as np, pandas as pd


def limit_target(tgt, val, frozen, no_buy, cashi, V):
    """Clip a target book to what can be traded on the row (lab addition, single stocks). A `frozen` column (no real
    price that day: a pause inside the price series or a no-trade day) keeps its value; a `no_buy` column may only
    shrink (no price: before the first or after the last price). If the clipped holdings leave too little value, the
    free columns' targets are scaled down; CASH takes the rest (an unbuyable share goes to CASH). Works on one row
    (1-d) or on D books at once (2-d, rows = books). Returns (target, blocked) with blocked = frozen columns held off
    their target (the trade is retried once the column trades again)."""
    t = np.where(frozen, val, tgt)
    t = np.where(no_buy, np.minimum(t, val), t)
    t[..., cashi] = 0.0
    free = ~(frozen | no_buy)
    free[..., cashi] = False
    over = t.sum(-1) - V
    fs = np.where(free, t, 0.0).sum(-1)
    sc = np.where((over > 0) & (fs > 0), np.maximum(0.0, 1.0 - over / np.where(fs > 0, fs, 1.0)), 1.0)
    t = np.where(free, t * np.expand_dims(sc, -1), t)
    t[..., cashi] = V - t.sum(-1)
    blocked = frozen & (np.abs(t - tgt) > 1e-12 * np.expand_dims(V, -1))
    blocked[..., cashi] = False
    return t, blocked


def run(W, R, start, end, cost=0.003, tax=0.22, delay=2, rebal=None, tax_mode='yearly', tax_by_col=None,
        frozen=None, no_buy=None):
    """rebal (lab addition, default None = the original rule): a boolean Series on W's index; on a flagged decision row the
    book is traded back to the target even if the target row did not change (periodic rebalancing of drifted weights).
    It is shifted by `delay` exactly like the weights.
    tax_mode (lab addition): 'yearly' = the original rule; 'per_sale' = `tax` withheld on each sold lot's positive gain
    at the trade (no loss offset, no yearly netting), final liquidation taxed per position on positive gains only.
    tax_by_col (per_sale only): {column: rate} overrides `tax` for those columns (e.g. KR domestic-equity ETFs 0).
    frozen / no_buy (lab addition for single stocks, default None = the original rule): boolean DataFrames on R's index
    (execution-day facts, NOT shifted): see limit_target. A trade held off its target by `frozen` is retried on the
    first row that column trades again."""
    assert tax_mode in ('yearly', 'per_sale')
    ps = tax_mode == 'per_sale'
    idx = R.index[(R.index >= start) & (R.index <= end)]
    W = W.reindex(R.index).ffill().shift(delay).reindex(idx).fillna(0.0)
    force = np.zeros(len(idx), bool) if rebal is None else \
        rebal.astype(float).reindex(R.index).fillna(0.0).shift(delay).reindex(idx).fillna(0.0).values > 0
    if 'CASH' not in W.columns:
        W['CASH'] = 0.0
    W.loc[W.sum(1) == 0, 'CASH'] = 1.0
    cols = list(W.columns)
    Rr = R[cols].reindex(idx).fillna(0.0).values
    Wv = W[cols].values
    n, k = Wv.shape
    val = Wv[0] * 1.0
    basis = val.copy()
    cashi = cols.index('CASH')
    lim = frozen is not None or no_buy is not None
    if lim:
        msk = lambda M: np.zeros((n, k), bool) if M is None else \
            M.reindex(index=idx, columns=cols).fillna(False).values.astype(bool)
        FZ, NB = msk(frozen), msk(no_buy)
        FZ[:, cashi] = NB[:, cashi] = False
        pend = np.zeros(k, bool)
    trate = np.array([(tax_by_col or {}).get(c, tax) for c in cols], float)
    assert tax_by_col is None or ps, 'tax_by_col needs tax_mode per_sale'
    eq = np.empty(n)
    realized = 0.0; yr = idx[0].year; turnover = 0.0; taxpaid = 0.0; trades = 0
    for i in range(n):
        if idx[i].year != yr and not ps:
            t = tax * max(0.0, realized); taxpaid += t
            realized = 0.0; yr = idx[i].year
            if t > 0:
                s = val.sum(); f = t / s
                realized += f * sum(val[j] - basis[j] for j in range(k) if j != cashi)
                val *= 1 - f; basis *= 1 - f
        if i > 0:
            val *= 1.0 + Rr[i]
        V = val.sum(); tgt = Wv[i] * V
        go = i == 0 or force[i] or np.any(Wv[i] != Wv[i - 1])
        if lim:
            go = go or bool(pend.any() and np.any(pend & ~FZ[i]))
            if go:
                tgt, blk = limit_target(tgt, val, FZ[i], NB[i], cashi, V)
        if np.abs(tgt - val).sum() > 1e-9 * V and go:
            if lim:
                pend = blk
            d = tgt - val; c = cost * np.abs(np.delete(d, cashi)).sum()
            for j in np.where(d < 0)[0]:
                if j == cashi or val[j] <= 0:
                    continue
                f = min(1.0, -d[j] / val[j]); g = f * (val[j] - basis[j]); basis[j] *= (1 - f)
                if ps:
                    tps = trate[j] * max(0.0, g); c += tps; taxpaid += tps
                else:
                    realized += g
            for j in np.where(d > 0)[0]:
                if j != cashi:
                    basis[j] += d[j]
            turnover += np.abs(np.delete(d, cashi)).sum() / V; trades += 1
            val = tgt * (V - c) / V
        eq[i] = val.sum()
    if ps:
        t = sum(trate[j] * max(0.0, val[j] - basis[j]) for j in range(k) if j != cashi)
    else:
        unreal = sum(val[j] - basis[j] for j in range(k) if j != cashi)
        t = tax * max(0.0, realized + unreal)
    final_at = eq[-1] - t
    E = pd.Series(eq, index=idx); yrs = (idx[-1] - idx[0]).days / 365.25
    return dict(E=E, cagr_pre=E.iloc[-1] ** (1 / yrs) - 1, cagr_at=final_at ** (1 / yrs) - 1,
                final_at=final_at, mdd=(E / E.cummax() - 1).min(), turn=turnover / yrs,
                taxpaid=taxpaid, yrs=yrs, trades=trades)
