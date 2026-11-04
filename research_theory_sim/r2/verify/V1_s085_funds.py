"""V1 check 3 (part): why s0.85 on the 8 country funds moves so much between delay 2 (base) and delay 3. <=2014 only.
Per fund and on real NDX 1986-2014: s0.85 (and D, L1) CAGR at delay 1..6, s0.85 trades per year, daily-return
autocorrelation at lags 1-3, and a one-day attribution: for every executed level change of s0.85 at delay 2, the next
day's return is earned at the new level under delay 2 but at the old level under delay 3, so
sum(d_level/3 * (3x day return - cash day return)) approximates what delay 3 loses (negative = delay 3 gains)."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/verify'); import V1_common as V  # noqa
std, ov, ce = V.std, V.ov, V.ce
import beng, bk  # noqa


def rec_run(c, B, bfn, bp, fstep, delay):
    k = dict(beng.F1); k['fstep'] = fstep; k['delay'] = delay; pp, D = beng._args(k)
    out, rec = beng.run_rec(np.ascontiguousarray(c.r[0]), np.ascontiguousarray(c.rf[0]), np.ascontiguousarray(B[0], dtype=np.float64),
                            np.ascontiguousarray(bk.features(c)[0]), int(pp['delay']), pp['cost'], pp['tax'], D, int(pp['harvest']), pp['hthr'],
                            pp['cspr'], pp['er3'], pp['step'], bfn, np.asarray(bp, dtype=np.float64), float(pp['fstep']))
    yrs = rec.shape[0] / 252
    return dict(cagr=float(max(out[0], 1e-9) ** (1 / yrs) - 1), trades_per_yr=float(out[5] / yrs), cur=rec[:, 1].copy())


def ac(x, l): x = x - x.mean(); return float(np.sum(x[l:] * x[:-l]) / np.sum(x * x))


def one(name, c):
    rB, rbf, rbp, rfs = std.s085(c); o = dict(s085={}, D={}, L1={})
    for d in range(1, 7):
        rr = rec_run(c, rB, rbf, rbp, rfs, d); o['s085'][d] = dict(cagr=rr['cagr'], trades_per_yr=rr['trades_per_yr'])
        if d == 2: cur2 = rr['cur']
    for L in ('D', 'L1'):
        B = V.targets(V.load_rule(L), c.lvl, c.rf)
        for d in range(1, 7): o[L][d] = V.single(c, B, delay=d)[0]
    r = c.r[0, V.WARM:]; rf = c.rf[0, V.WARM:]
    o['autocorr'] = {l: ac(r[1:], l) for l in (1, 2, 3)}
    x3 = 3 * r - 2 * rf - 0.0245 / 252; xc = np.maximum(rf - 0.02 / 252, 0) * 0.846
    cur = np.where(cur2 < 0, 0, cur2); dl = np.r_[0, np.diff(cur)]; idx = np.where(dl != 0)[0]; idx = idx[idx + 1 < len(r)]
    o['one_day_attr'] = dict(n_changes=int(len(idx)), sum_dlevel_times_next_day=float(np.sum(dl[idx] / 3 * (x3[idx + 1] - xc[idx + 1]))),
                             entries_next_day_mean_r=float(np.mean(r[idx[dl[idx] > 0] + 1])) if np.any(dl[idx] > 0) else None,
                             exits_next_day_mean_r=float(np.mean(r[idx[dl[idx] < 0] + 1])) if np.any(dl[idx] < 0) else None,
                             all_days_mean_r=float(np.mean(r)))
    print('%-5s s085 by delay %s | trades/yr d2 %.1f | D %s | L1 %s | ac1-3 %s | 1-day attr %.3f (n %d; next-day r after entries %.4f, exits %.4f, all %.4f)' % (
        name, ' '.join('%d:%.3f' % (d, v['cagr']) for d, v in o['s085'].items()), o['s085'][2]['trades_per_yr'],
        ' '.join('%.3f' % o['D'][d] for d in range(1, 7)), ' '.join('%.3f' % o['L1'][d] for d in range(1, 7)),
        ' '.join('%.3f' % v for v in o['autocorr'].values()), o['one_day_attr']['sum_dlevel_times_next_day'], o['one_day_attr']['n_changes'],
        o['one_day_attr']['entries_next_day_mean_r'] or 0, o['one_day_attr']['exits_next_day_mean_r'] or 0, o['one_day_attr']['all_days_mean_r']), flush=True)
    return o


def main():
    out = {}
    out['real_ndx_86_14'] = one('NDX', V.bases()['real_ndx_86_14'])
    for k in V.FUNDS:
        c, y, dates, info = V.fund_ctx(k, 'price'); out[k] = one(k, c)
    s = {d: float(np.median([out[k]['s085'][d]['cagr'] for k in V.FUNDS])) for d in range(1, 7)}
    out['fund_median_s085_by_delay'] = s
    out['funds_s085_d3_gt_d2'] = int(sum(out[k]['s085'][3]['cagr'] > out[k]['s085'][2]['cagr'] for k in V.FUNDS))
    out['funds_s085_d1_lt_d2'] = int(sum(out[k]['s085'][1]['cagr'] < out[k]['s085'][2]['cagr'] for k in V.FUNDS))
    print('fund median s0.85 by delay', s, 'd3>d2 in', out['funds_s085_d3_gt_d2'], 'of 8; d1<d2 in', out['funds_s085_d1_lt_d2'])
    return out


if __name__ == '__main__':
    p = V.dump(main(), 'V1_s085_funds.json'); print('wrote', p)
