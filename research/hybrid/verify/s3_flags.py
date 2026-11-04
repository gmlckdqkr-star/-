"""Verifier step 3 (check B): state flags recomputed independently (pandas rolling / expanding quantile), compared with a verbatim copy
of the author's era_data flag code, look-ahead perturbation test of the flags, and all 29 rules recomputed vs the stored JSON."""
import json, bisect, numpy as np, pandas as pd

D = '/tmp/claude-0/-home-user--/0e26f5bd-b937-55ae-81a7-0c4a9abb6560/scratchpad/verify/'
STORED = json.load(open('/mnt/project-files/research/hybrid/results/info_le2014.json'))
PARTNERS = ['VALPROF4_L1', 'BOND10_L3', 'SPXH_L1']
RULES = ['MOM12', 'MOM6', 'MOM3', 'TSM12', 'DD30', 'VOL80', 'CHOP', 'RATEUP', 'CAPEHI']
NC = 29


# ---- verbatim copy of the author's flag code (hy_info.exp_pct / era_data), array inputs
def exp_pct(x, q):
    out = np.full(x.shape, np.nan); v = []
    for t in range(len(x)):
        if np.isfinite(x[t]): bisect.insort(v, x[t])
        if len(v) >= 63: out[t] = v[min(int(q * (len(v) - 1)), len(v) - 1)]
    return out


def author_flags(rfull, y10, cape_ok, WARM, T):
    lr = np.log1p(rfull)
    vol21 = np.full(lr.shape, np.nan); er126 = np.full(lr.shape, np.nan)
    cs = np.r_[0, np.cumsum(lr)]; cs2 = np.r_[0, np.cumsum(lr * lr)]; ca = np.r_[0, np.cumsum(np.abs(lr))]
    for t in range(21, len(lr)):
        m = (cs[t + 1] - cs[t - 20]) / 21; vol21[t] = np.sqrt(max((cs2[t + 1] - cs2[t - 20]) / 21 - m * m, 0) * 252)
    for t in range(126, len(lr)):
        er126[t] = abs(cs[t + 1] - cs[t - 125]) / max(ca[t + 1] - ca[t - 125], 1e-12)
    v80 = exp_pct(vol21, 0.8); e30 = exp_pct(er126, 0.3)
    sh = lambda a: a[WARM:WARM + T]
    return dict(vol_hi=sh(vol21 > v80), chop=sh(er126 < e30),
                rate_up=sh(np.r_[np.full(252, False), (y10[252:] - y10[:-252]) > 0.005]), cape_hi=sh(cape_ok < 0.5))


# ---- my own flags (pandas)
def my_flags(rfull, y10, cape_ok, WARM, T):
    lr = pd.Series(np.log1p(rfull))
    vol = lr.rolling(21).std(ddof=0) * np.sqrt(252)
    vol[:21] = np.nan                                   # author starts at t = 21 (first 21-day window ending at t=21)
    v80 = vol.expanding(min_periods=63).quantile(0.8, interpolation='lower')
    net = lr.rolling(126).sum().abs(); path = lr.abs().rolling(126).sum()
    er = net / path.clip(lower=1e-12); er[:126] = np.nan
    e30 = er.expanding(min_periods=63).quantile(0.3, interpolation='lower')
    y = pd.Series(y10); dy = y - y.shift(252)
    full = dict(vol_hi=(vol > v80).values, chop=(er < e30).values, rate_up=(dy > 0.005).values, cape_hi=(pd.Series(cape_ok) < 0.5).values)
    return {k: v[WARM:WARM + T] for k, v in full.items()}


def sleeve_formula(TQ, DEP, CU):
    Lp = np.r_[CU[0], CU[:-1]] / 3.0
    r = Lp * TQ + (1 - Lp) * DEP; r[0] = 0.0; return r


def rules_eval(R, fl, ks):
    """R (T, 4) cols s085, VPF4, B10L3, SPXH; returns dict key -> stats (own implementation)"""
    T, M = R.shape; lr = np.log1p(R)
    G = np.array([lr[k + 3:k + 24].sum(0) for k in ks])
    def trail(j, k, n): return lr[max(k - n + 1, 0):k + 1, j].sum()
    lvl = np.exp(np.cumsum(lr[:, 0]))
    out = {}
    def stats(pick, cand):
        tru = np.array(cand)[np.argmax(G[:, cand], 1)]; n = len(pick)
        hit = np.mean(pick == tru); se = np.sqrt(hit * (1 - hit) / n); gain = G[np.arange(n), pick] - G[:, 0]
        return dict(hit=hit, hit_defl=hit - 2 * se * np.sqrt(1 + np.log(NC)), base=np.mean(tru == 0), sw=np.mean(pick != 0),
                    gain=gain.mean(), t=gain.mean() / (gain.std(ddof=1) / np.sqrt(n)))
    for j, X in enumerate(PARTNERS, 1):
        for rule in RULES:
            pk = []
            for k in ks:
                if rule.startswith('MOM'):
                    n = dict(MOM12=252, MOM6=126, MOM3=63)[rule]; pk.append(j if trail(j, k, n) > trail(0, k, n) else 0)
                elif rule == 'TSM12': pk.append(0 if trail(0, k, 252) > 0 else j)
                elif rule == 'DD30': pk.append(j if lvl[k] / lvl[max(k - 251, 0):k + 1].max() - 1 < -0.30 else 0)
                else: pk.append(j if fl[dict(VOL80='vol_hi', CHOP='chop', RATEUP='rate_up', CAPEHI='cape_hi')[rule]][k] else 0)
            out['%s|%s' % (X, rule)] = stats(np.array(pk), [0, j])
    for rule, n in (('BK4_MOM12', 252), ('BK4_MOM6', 126)):
        pk = np.array([int(np.argmax([trail(m, k, n) for m in range(M)])) for k in ks])
        out['BK4|%s' % rule] = stats(pk, list(range(M)))
    return out


worst = 0.0
for bn in ['real_ndx_86_14', 'real_spx_55_85']:
    z = np.load(D + 'data_%s.npz' % bn); WARM = int(z['WARM']); T = len(z['TQ'])
    rfull, y10, cape = z['rfull'], z['y10'], z['cape_ok']
    fa = author_flags(rfull, y10, cape, WARM, T); fm = my_flags(rfull, y10, cape, WARM, T)
    ks = np.arange(252, T - 3, 21)
    for k_ in fa:
        print(bn, k_, 'author vs mine mismatches at block starts: %d / %d ; share on %.3f' % (int(np.sum(fa[k_][ks] != fm[k_][ks])), len(ks), np.mean(fa[k_][ks])))
    # perturbation: scramble index returns, y10, cape label after full index WARM + j; flags at scored k <= j must be unchanged
    rng = np.random.default_rng(1)
    for j in [ks[10], ks[120], ks[250]]:
        r2 = rfull.copy(); y2 = y10.copy(); c2 = cape.copy(); a = WARM + j + 1
        r2[a:] = rng.normal(0, 0.05, len(r2) - a); y2[a:] = rng.uniform(0, 0.2, len(y2) - a); c2[a:] = rng.integers(0, 2, len(c2) - a)
        fp = author_flags(r2, y2, c2, WARM, T)
        for k_ in fa:
            assert np.array_equal(fa[k_][:j + 1], fp[k_][:j + 1]), ('LOOK-AHEAD', bn, k_, j)
    print(bn, 'flag perturbation test passed')
    R = np.stack([sleeve_formula(z['TQ'], z['DEP'], z['CU'])] + [z['S_' + X] for X in PARTNERS], 1)
    mine = rules_eval(R, fm, ks)
    for key, v in mine.items():
        st = STORED['%s|%s' % (bn, key) if not key.startswith('BK4') else '%s|%s' % (bn, key)]
        d = max(abs(v['hit'] - st['hit']), abs(v['gain'] - st['gain_mean']), abs(v['t'] - st['gain_t']), abs(v['sw'] - st['frac_switch']))
        worst = max(worst, d)
        if d > 1e-9: print('  MISMATCH', bn, key, v, st)
    print(bn, 'all 29 rules recomputed; max abs diff vs stored (hit, gain, t, switch share) = %.2e' % max(worst, 0))
    lo = {}
print('done')
