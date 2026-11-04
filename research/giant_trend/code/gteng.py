"""GT monthly engine (MS1 conditions mapped to monthly). See PRECOMMIT_GT.md section 2.
Decision at end of month t (index t) uses info <= t and is applied to the return of month t+1.
A strategy is a list `dec` of length T: None (no trade, let drift) or (mode, payload):
  ('w', {asset: weight})          set target weights (sum 1, 'CASH' allowed)
  ('swap', (keep_list, new_list)) keep incumbents' current weights, split the rest equally over new_list
Leverage overlay `lev` (int array length T, 0 = all cash, 1/2/3) is applied to non-cash assets.
A notional 1x portfolio `nw` drifts with 1x returns; holdings are re-mapped to it when a decision occurs
or the leverage changes. Between those, holdings drift (no trades).
"""
import numpy as np
COST = 0.003; FEE = 0.002; TAX = 0.22; DED = 0.25; WH = 0.15
DRAG = {1: 0.0, 2: 0.017, 3: 0.0245}
EXTRA = {1: 0.0, 2: 0.0, 3: 0.0}   # daily-reset calibration (annual), set by caller
IS_DEC = None

def set_calendar(idx):
    global IS_DEC
    IS_DEC = np.array([p.month == 12 for p in idx])

def product_returns(R, rf, dy, gs10):
    """R: dict asset -> monthly simple returns (np.array len T, NaN = not available). Returns P[L][asset]."""
    cash = np.maximum(rf - 0.02 / 12, 0.0) * (1 - 0.154)
    P = {}
    for L in (1, 2, 3):
        P[L] = {}
        for a, r in R.items():
            r = np.nan_to_num(r, nan=0.0)
            yld = gs10 / 100.0 if a == 'BOND10' else dy
            wh = WH * np.nan_to_num(yld) / 12
            x = L * r - (L - 1) * rf - (DRAG[L] + EXTRA[L] + FEE) / 12 - L * wh
            P[L][a] = np.maximum(x, -0.99)
        P[L]['CASH'] = cash
    return P

def _first_target(dec, t):
    for s in range(t, -1, -1):
        d = dec[s]
        if d is None: continue
        if d[0] == 'w': return dict(d[1])
        keep, new = d[1]; al = list(keep) + list(new)
        return {a: 1.0 / len(al) for a in al} if al else {'CASH': 1.0}
    return {'CASH': 1.0}

def run(dec, lev, P, months):
    """months: list of original month indices; returns of months[1:] are earned. Wealth starts at 1."""
    hold = {('CASH', 1): [1.0, 1.0]}
    st = {'real': 0.0}
    def total(): return sum(v[0] for v in hold.values())
    def sell(key, amt):
        v, b = hold[key]; frac = min(amt / v, 1.0) if v > 0 else 0.0
        if key[0] != 'CASH': st['real'] += amt - b * frac
        nv, nb = v - amt, b * (1 - frac)
        if nv <= 1e-13: del hold[key]
        else: hold[key] = [nv, nb]
    def buy(key, amt):
        v, b = hold.get(key, [0.0, 0.0]); hold[key] = [v + amt, b + amt]
    nw = None; prevL = None; wpath = [1.0]; pre = []
    for k in range(len(months) - 1):
        t = months[k]; tn = months[k + 1]; d = dec[t]; L = int(lev[t])
        if nw is None: nw = _first_target(dec, t)
        if d is not None:
            if d[0] == 'w': nw = dict(d[1])
            else:
                keep, new = d[1]
                tg = {a: nw.get(a, 0.0) for a in keep}
                free = max(1.0 - sum(tg.values()), 0.0)
                if new:
                    for a in new: tg[a] = tg.get(a, 0.0) + free / len(new)
                elif free > 0: tg['CASH'] = tg.get('CASH', 0.0) + free
                nw = tg
        if d is not None or k == 0 or L != prevL:
            Wt = total(); want = {}
            for a, w in nw.items():
                if w <= 1e-12: continue
                key = ('CASH', 1) if (a == 'CASH' or L == 0) else (a, L)
                want[key] = want.get(key, 0.0) + w * Wt
            traded = 0.0
            for key in list(hold.keys()):
                tv = want.get(key, 0.0); v = hold[key][0]
                if v > tv + 1e-12:
                    sell(key, v - tv); traded += (v - tv) if key[0] != 'CASH' else 0.0
            for key, tv in want.items():
                v = hold.get(key, [0.0, 0.0])[0]
                if tv > v + 1e-12:
                    buy(key, tv - v); traded += (tv - v) if key[0] != 'CASH' else 0.0
            c = traded * COST
            if c > 0:
                f = 1 - c / total()
                for key in hold: hold[key][0] *= f      # cost lowers value, basis unchanged (cost is a loss)
        prevL = L
        Wb = total()
        for key in hold: hold[key][0] *= (1 + P[key[1]][key[0]][tn])
        Wa = total(); pre.append(Wa / Wb - 1.0)
        # notional drift with 1x returns
        z = {a: w * (1 + P[1][a][tn]) for a, w in nw.items()}; s = sum(z.values())
        nw = {a: v / s for a, v in z.items()} if s > 0 else {'CASH': 1.0}
        last = (k == len(months) - 2)
        if IS_DEC[tn] or last:
            if last:
                for key in list(hold.keys()):
                    if key[0] != 'CASH':
                        v = hold[key][0]; sell(key, v); buy(('CASH', 1), v)
            tax = (st['real'] - DED) * TAX if st['real'] > DED else 0.0
            if tax > 0:
                f = max(1 - tax / total(), 1e-9)
                for key in hold: hold[key][0] *= f; hold[key][1] *= f
            st['real'] = 0.0
        wpath.append(total())
    return np.array(wpath), np.array(pre)

def stats(wpath, pre, rf_seq):
    years = (len(wpath) - 1) / 12.0
    cagr = wpath[-1] ** (1 / years) - 1 if wpath[-1] > 0 else -1.0
    peak = np.maximum.accumulate(wpath); mdd = float((wpath / peak - 1).min())
    ex = pre - rf_seq; sd = ex.std()
    sr = float(ex.mean() / sd * np.sqrt(12)) if sd > 0 else 0.0
    return dict(cagr=float(cagr), mdd=mdd, sharpe=sr, years=years)
