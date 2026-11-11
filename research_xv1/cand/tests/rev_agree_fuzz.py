"""Reviewer's branch test of the agree package: the package against the naive rule (rev_agree_xcheck.py) on MADE-UP inputs.
The <= 2014 calendar rows are kept; the index return, the yields and every extra input are replaced by seeded random series
with changing volatility and drift, late-starting funds and a few missing values, so that branches the real history does
not reach are compared too (missing inputs in the middle, two-class vehicle jumps, re-entries, runs that restart).
Random data only: decisions are compared, nothing is scored, no performance figure of anything."""
import sys
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand'); sys.path.insert(0, '/home/user/-/research_xv1/cand/tests')
import numpy as np, xv1
import t_world; t_world.old()
import rev_agree_xcheck as nx
from xv1 import mkt


def regimes(g, n, values, mean_len):
    out = np.empty(n); t = 0
    while t < n:
        k = int(g.integers(mean_len // 3, mean_len * 2)); out[t:t + k] = g.choice(values); t += k
    return out


def ar1(g, n, mean, phi, sd):
    out = np.empty(n); x = 0.0
    for t in range(n): x = phi * x + g.normal(0, sd); out[t] = mean + x
    return out


def world(seed):
    g = np.random.default_rng(seed); X = xv1.frame(xv1.OLD_END); n = len(X); Xn = X.copy()
    r = np.clip(regimes(g, n, [-0.0025, -0.0008, 0.0004, 0.0012, 0.002], 180) + regimes(g, n, [0.006, 0.011, 0.018, 0.03], 140) * g.standard_normal(n), -0.3, 0.3)
    Xn['r'] = r; y10 = np.clip(ar1(g, n, 6.0, 0.995, 0.07), 1.0, 14.0)
    Xn['y10'] = y10; Xn['y3m'] = y10 - ar1(g, n, 1.0, 0.99, 0.12)
    Xn['rb'] = mkt.bond10(Xn); Xn['p'] = (1 + Xn['r']).cumprod()
    E = {}; i0 = nx.I0
    semis = np.clip(0.8 * r + regimes(g, n, [-0.002, -0.0005, 0.0005, 0.002], 200) + regimes(g, n, [0.007, 0.015, 0.022, 0.03, 0.045], 110) * g.standard_normal(n), -0.4, 0.4)
    miss = i0 + g.integers(400, nx.T - 200, 3); semis[miss] = np.nan                      # three missing closes of the semiconductor series
    E['semis'] = semis
    for a, b in nx.PAIRS:
        base = 0.9 * r + regimes(g, n, [-0.0015, 0.0, 0.0015], 160) + 0.008 * g.standard_normal(n)
        E['kf:' + b] = base.copy(); e = base + 0.002 * g.standard_normal(n); e[:i0 + int(g.integers(900, 3500))] = np.nan; E['ret:' + a] = e
    E['kf:' + nx.PAIRS[0][1]][i0 + int(g.integers(50, 250))] = np.nan                       # one missing industry return early on
    for k in ('SOXL', 'USD', 'QQQ', 'QLD', 'PSQ'):
        e = 0.02 * g.standard_normal(n); e[:i0 + int(g.integers(600, 6000))] = np.nan; E['ret:' + k] = e
    e = semis.copy(); e[:i0 + int(g.integers(600, 6000))] = np.nan; E['ret:SOXX'] = e      # as xdata: 'semis' is SOXX itself once SOXX exists
    return Xn, {k: E[k] for k in nx.NAMES}


if __name__ == '__main__':
    seeds = [int(a) for a in sys.argv[1:]] or [1, 2, 3, 4, 5, 6]; tot = 0
    for sd in seeds:
        Xn, E = world(sd); v = xv1.View(Xn, E); n = nx.compare(v, verbose=False); tot += n
        # how much of the rule the made-up world exercises (counts only)
        B1 = nx.naive_agree4(0.3)[2]; B4 = nx.naive_agree4(0.3, k_on=3)[2]; C4 = nx.naive_qqq(2.0, 0.3)[2]; E1 = nx.naive_ladder('full')[2]
        inval = sum(1 for t in range(nx.xv1.WARM, nx.T) if not (nx.ok_row(t, 'X') and nx.ok_row(t, 'Q')))
        print('seed', sd, 'differences', n, '| invalid account rows', inval, '| B1', B1, '| B4', B4, '| C4', C4, '| E1', E1, flush=True)
    print('TOTAL differences over', len(seeds), 'made-up worlds:', tot)
