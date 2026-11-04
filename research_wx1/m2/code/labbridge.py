"""Bridge from M2 picks to the lab stock engine (lab.stocks.Targets / fast_run / run1; lab code is imported, never
edited). Same rules as a lab stock spec: decision close D, trade at D+2, 0.3% one way, H_CONS delisting rule,
dividend tax 15.4% when paid, 22% yearly net realized gain, final liquidation tax."""
import numpy as np, pandas as pd
from lab import stocks


def targets_from_picks(P, d, picks, K, rb='M', gate=None, j_anchor=None):
    """picks [nd, >=K] (panel columns, -1 none) on d.dec rows. rb 'M' monthly, 'Q' Jan/Apr/Jul/Oct, 'T' three tranches
    (approximated as monthly decisions holding each tranche's latest picks at 1/(3K): lab rebalances every name back
    to target each month, unlike three drifting sub-books). gate [nd] bool or None (exposure decided on decision rows)."""
    nd = d.nd
    g = np.ones(nd, bool) if gate is None else np.asarray(gate, bool)
    if j_anchor is None:
        j_anchor = int(np.searchsorted(d.dd, pd.Timestamp('1986-01-01')))
    pk = [np.asarray([p for p in picks[j, :K] if p >= 0], np.int64) for j in range(nd)]
    if rb == 'M':
        js = np.arange(nd)
        dec = d.dec
        P_ = [pk[j] if g[j] else np.zeros(0, np.int64) for j in js]
        W_ = [np.full(len(p), 1.0 / K) for p in P_]
    elif rb == 'Q':
        js = np.flatnonzero(np.isin(d.mo, [1, 4, 7, 10]))
        dec = d.dec[js]
        P_ = [pk[j] if g[j] else np.zeros(0, np.int64) for j in js]
        W_ = [np.full(len(p), 1.0 / K) for p in P_]
    else:
        js = np.arange(nd); dec = d.dec
        last = [None, None, None]
        P_, W_ = [], []
        for j in js:
            k = (j - j_anchor) % 3
            last[k] = pk[j] if g[j] else np.zeros(0, np.int64)
            acc = {}
            for t in last:
                if t is None:
                    continue
                for p in t:
                    acc[int(p)] = acc.get(int(p), 0.0) + 1.0 / (3 * K)
            cols = np.array(sorted(acc), np.int64)
            P_.append(cols); W_.append(np.array([acc[c] for c in cols]))
    e = np.zeros(P.T)
    pos = np.full(P.T, -1, np.int64); pos[dec] = np.arange(len(dec)); pos = np.maximum.accumulate(pos)
    e[pos >= 0] = 1.0
    elig = d.elig[js]
    return stocks.Targets(np.asarray(dec, np.int64), P_, W_, np.full(len(dec), K), elig, e, {}, None)


def aftertax_rows(P, tg, start='1986-01-02'):
    st = pd.Timestamp(start)
    cons = stocks.run1(P, tg, stocks.H_CONS, st, 0.003, 0.22, 2, ends=True)
    base = stocks.run1(P, tg, 0.0, st, 0.003, 0.22, 2)
    all30 = stocks.run1(P, tg, stocks.H_ALL, st, 0.003, 0.22, 2)
    pre = stocks.run1(P, tg, stocks.H_CONS, st, 0.003, 0.0, 2, dtax=0.0)
    ew = stocks.ew_row(P, stocks.H_CONS, st, 0.003, 0.22, 2)
    return dict(start=str(st.date()), cons=cons['cagr_at'], cons_mdd=cons['mdd'], cons_turn=cons['turn'],
                base=base['cagr_at'], all30=all30['cagr_at'], pretax=pre['cagr_at'], ew_cons=ew['cagr_at'],
                held_ends=cons['ends'], sharpe_pretax=stocks.sharpe(pre, P))


def stream(P, tg, start='1986-01-02'):
    """lab ms1_stream equivalent for these targets: conservative book after cost and dividend tax, before the 22% tax,
    basis_add = reinvested after-tax dividend / previous value, turnover = min(1, one-way yearly turnover)."""
    st = pd.Timestamp(start)
    o = stocks.fast_run(P, tg, stocks.H_CONS, st, 0.003, 0.0, 2, want_E=True, dtax=stocks.DIV_TAX)
    E = o['E'][0]
    r = E[1:] / E[:-1] - 1.0
    q = np.where(E[:-1] > 0, o['dnet'][0][1:] / np.where(E[:-1] > 0, E[:-1], 1.0), 0.0)
    return dict(dates=[x.strftime('%Y-%m-%d') for x in o['idx'][1:]], ret=r.tolist(), basis_add=q.tolist(),
                turnover=min(1.0, float(o['turn'][0]) / 2.0), start=str(o['idx'][0].date()))
