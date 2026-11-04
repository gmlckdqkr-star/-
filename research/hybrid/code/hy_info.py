"""PRECOMMIT_HY1 section 3 (C): information test of 29 pre-registered switching rules (G1-S), two real eras.
Output results/info_le2014.json (verdicts filled by hy_verdict.py using the ladder)."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/hybrid/code')
import hy_common as C, hyeng as H, ii, el, sl

PARTNERS = ['VALPROF4_L1', 'BOND10_L3', 'SPXH_L1']
RULES = ['MOM12', 'MOM6', 'MOM3', 'TSM12', 'DD30', 'VOL80', 'CHOP', 'RATEUP', 'CAPEHI']
N_C = 29
WARM = H.WARM
OUT = '/mnt/project-files/research/hybrid/results/info_le2014.json'


def exp_pct(x, q):
    """expanding percentile of x (1-D) using values up to and including t (NaN before 63 obs)"""
    out = np.full(x.shape, np.nan); v = []
    import bisect
    for t in range(len(x)):
        if np.isfinite(x[t]): bisect.insort(v, x[t])
        if len(v) >= 63: out[t] = v[min(int(q * (len(v) - 1)), len(v) - 1)]
    return out


def era_data(bn):
    c = el.ctx(bn)
    R = C.sleeve_returns(bn, PARTNERS)[0]                       # (T, 4) scored axis
    T = R.shape[0]
    rfull = np.asarray(c['r'])[0]                                # index daily return incl. warm (T + WARM)
    I = sl.inputs(np.asarray(c['ii']), c['off'])
    y10 = I['y10'][0]; cape_ok = I['CAPE_OK'][0]
    lr = np.log1p(rfull)
    vol21 = np.full(lr.shape, np.nan); er126 = np.full(lr.shape, np.nan)
    cs = np.r_[0, np.cumsum(lr)]; cs2 = np.r_[0, np.cumsum(lr * lr)]; ca = np.r_[0, np.cumsum(np.abs(lr))]
    for t in range(21, len(lr)):
        m = (cs[t + 1] - cs[t - 20]) / 21; vol21[t] = np.sqrt(max((cs2[t + 1] - cs2[t - 20]) / 21 - m * m, 0) * 252)
    for t in range(126, len(lr)):
        er126[t] = abs(cs[t + 1] - cs[t - 125]) / max(ca[t + 1] - ca[t - 125], 1e-12)
    v80 = exp_pct(vol21, 0.8); e30 = exp_pct(er126, 0.3)
    # map full-axis (incl. warm) to scored axis k: full index = k + WARM
    sh = lambda a: a[WARM:WARM + T]
    st = dict(vol_hi=sh(vol21 > v80), chop=sh(er126 < e30),
              rate_up=sh(np.r_[np.full(252, False), (y10[252:] - y10[:-252]) > 0.005]),
              cape_hi=sh(cape_ok < 0.5))
    return R, st


def trailing(lrc, k, n):
    a = max(k - n + 1, 0)
    return lrc[k + 1] - lrc[a]


res = {}
for bn in ['real_ndx_86_14', 'real_spx_55_85']:
    R, st = era_data(bn); T, M = R.shape
    lrc = np.concatenate([np.zeros((1, M)), np.cumsum(np.log1p(R), axis=0)], axis=0)
    lvl = np.exp(lrc[1:, 0])                                     # s0.85 sleeve level
    f, _ = C.block_logsum(R[None]); ks = C.block_starts(T, 252)
    G = np.stack([f(k)[0] for k in ks])                          # (nb, M) block log sums
    def evaluate(pick, cand):
        """pick (nb,) in cand indices (global columns); truth among cand"""
        sub = G[:, cand]; tru = np.array(cand)[np.argmax(sub, axis=1)]
        hit = float(np.mean(pick == tru)); n = len(pick); se = (hit * (1 - hit) / n) ** .5
        gain = G[np.arange(n), pick] - G[:, 0]
        sw = pick != 0
        return dict(hit=hit, n=n, se=se, hit_defl=hit - 2 * se * (1 + np.log(N_C)) ** .5, base_s085=float(np.mean(tru == 0)),
                    best_const=float(max(np.mean(tru == j) for j in cand)), frac_switch=float(np.mean(sw)),
                    gain_mean=float(np.mean(gain)), gain_t=float(np.mean(gain) / (np.std(gain, ddof=1) / n ** .5)) if np.std(gain) > 0 else 0.0,
                    gain_when_switched=float(np.mean(gain[sw])) if sw.any() else 0.0)
    for j, X in enumerate(PARTNERS, start=1):
        cand = [0, j]
        for rule in RULES:
            pick = np.zeros(len(ks), int)
            for i, k in enumerate(ks):
                if rule.startswith('MOM'):
                    n = {'MOM12': 252, 'MOM6': 126, 'MOM3': 63}[rule]
                    pick[i] = j if trailing(lrc[:, j], k, n) > trailing(lrc[:, 0], k, n) else 0
                elif rule == 'TSM12':
                    pick[i] = 0 if trailing(lrc[:, 0], k, 252) > 0 else j
                elif rule == 'DD30':
                    a = max(k - 251, 0); pick[i] = j if lvl[k] / lvl[a:k + 1].max() - 1 < -0.30 else 0
                elif rule == 'VOL80':
                    pick[i] = j if st['vol_hi'][k] else 0
                elif rule == 'CHOP':
                    pick[i] = j if st['chop'][k] else 0
                elif rule == 'RATEUP':
                    pick[i] = j if st['rate_up'][k] else 0
                elif rule == 'CAPEHI':
                    pick[i] = j if st['cape_hi'][k] else 0
            res['%s|%s|%s' % (bn, X, rule)] = evaluate(pick, cand)
    for rule, n in (('BK4_MOM12', 252), ('BK4_MOM6', 126)):
        pick = np.array([int(np.argmax([trailing(lrc[:, m], k, n) for m in range(M)])) for k in ks])
        res['%s|BK4|%s' % (bn, rule)] = evaluate(pick, list(range(M)))
    for key in [k for k in res if k.startswith(bn)]:
        v = res[key]; print(key, 'hit %.3f defl %.3f base %.3f best %.3f sw %.2f gain %.4f t %.2f' % (
            v['hit'], v['hit_defl'], v['base_s085'], v['best_const'], v['frac_switch'], v['gain_mean'], v['gain_t']), flush=True)
json.dump(res, open(OUT, 'w'), indent=1)
print('done')
