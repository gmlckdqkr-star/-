"""beat_qld strategies H, J, E as lab plugins (shapes the DSL cannot write).
H and J use a 10-month SMA of month-start closes. The originals sample the LAST trading day of each month, which needs
the next row's date (not causal on a truncated path), so here each month decides on its FIRST trading day.
E reads the traded TQQQ level through the input 'level(TQQQ)' and matches strats.E exactly on the dev data."""
import numpy as np
import pandas as pd


def _first(idx):
    p = idx.to_period('M').asi8
    return np.r_[True, p[1:] != p[:-1]][:len(idx)]


def _msma10(p, fm):
    s = pd.Series(p[fm]).rolling(10, min_periods=10).mean().values
    out = np.full(len(p), np.nan)
    out[fm] = s
    return out


def _monthly(choice, fm, cols, idx):
    cur, out = 'CASH', []
    for i in range(len(idx)):
        if fm[i]:
            cur = choice(i)
        out.append(cur)
    o = np.array(out)
    return pd.DataFrame({c: (o == c).astype(float) for c in cols}, index=idx)


def H(F, sleeves, params):
    """Month start: NDX above its 10-month SMA -> TQQQ, else QQQ (cash until the SMA exists)."""
    p = F['TQQQ'].values
    fm = _first(F.index)
    s = _msma10(p, fm)
    return _monthly(lambda i: 'TQQQ' if p[i] > s[i] else ('QQQ' if not np.isnan(s[i]) else 'CASH'),
                    fm, ['TQQQ', 'QQQ'], F.index)


def J(F, sleeves, params):
    """Month start: NDX below its 10-month SMA -> QQQ; else SOXL if its 6-month return beats NDX's, else TQQQ."""
    n, x = F['QLD'], F['SOXL']
    mn = (n / n.shift(126) - 1).values
    mx = (x / x.shift(126) - 1).values
    nv = n.values
    fm = _first(F.index)
    s = _msma10(nv, fm)

    def f(i):
        if np.isnan(mx[i]) or np.isnan(s[i]):
            return 'CASH'
        if nv[i] <= s[i]:
            return 'QQQ'
        return 'SOXL' if mx[i] > mn[i] else 'TQQQ'
    return _monthly(f, fm, ['QQQ', 'SOXL', 'TQQQ'], F.index)


def E(F, sleeves, params):
    """TQQQ take-profit / pullback / wait on the traded TQQQ level: hold until +tp from entry, then wait in cash
    until a -pb pullback from the exit level or `wait` days, then re-enter."""
    tp, pb, wait = float(params['tp']), float(params['pb']), int(params['wait'])
    lvl = F['level(TQQQ)'].values
    st, entry, exitp, t = True, lvl[0], None, 0
    out = np.zeros(len(lvl))
    for i in range(len(lvl)):
        x = lvl[i]
        if st:
            if x >= entry * (1 + tp):
                st, exitp, t = False, x, 0
        else:
            t += 1
            if x <= exitp * (1 - pb) or t >= wait:
                st, entry = True, x
        out[i] = 1.0 if st else 0.0
    return pd.DataFrame({'TQQQ': out}, index=F.index)
