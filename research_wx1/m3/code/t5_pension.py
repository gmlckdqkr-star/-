"""M3 (c) desk: pension account (연금저축 / IRP) 1x NDX hold or 1x/cash timing vs s0.85 in the taxable account (종합), after-tax terminal
wealth per 10M KRW contributed once at t=0, MS1 paths (dev250_path 30y, real NDX 1986-2014). USD basis like MS1 (FX ignored).
Inside the pension: no yearly tax; domestic-listed 1x NDX ETF (fee 0.07 %/yr assumed, plus MS1 1x hold fee 0.2 % -> we keep 0.2 % conservative),
trade cost 0.1 %/side (domestic ETF), cash = max(rf - 2 %, 0) untaxed (deferred). Withdrawal: pension 5.5 % (55-69, fixed-term) or
early 16.5 % (기타소득) on the whole balance (all principal assumed tax-credited). Tax credit refund (13.2 % / 16.5 % / 0 %) paid at t=0 and kept
in the MS1 after-tax deposit. IRP: risky assets <= 70 % -> exposure x 0.7, rest cash. 1x/cash timing = exposure min(L, 1), L = s0.85 in-force level."""
import sys, json, numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m3/code')
import m3env
G = m3env.G; WARM = G.WARM


def grow(r, rf, e, fee=0.002, cost=0.001):
    """pre-tax growth of a 1x/cash book with exposure e (P,K) in force; r, rf (P,K)"""
    cash = np.maximum(rf - 0.02 / 252, 0.0)
    x = e * (r - fee / 252) + (1 - e) * cash
    tc = cost * np.abs(np.diff(np.concatenate([np.zeros((e.shape[0], 1)), e], axis=1), axis=1))
    lg = np.log1p(x) + np.log1p(-tc)
    return np.exp(lg.sum(axis=1))


def run(bn):
    b = G.Basis(bn); L = G.s085_levels(bn); c = b.c
    r = np.asarray(c.r, float)[:, WARM:]; rf = np.asarray(c.rf, float)[:, WARM:]; r[:, 0] = 0; rf[:, 0] = 0
    yrs = r.shape[1] / 252
    ref = G.run(b, ['TQQQ', 'CASH'], [G.sl_s085(L)], [1.0]); W_s085 = (1 + ref['cagr']) ** yrs        # after-tax incl. liquidation
    hold = G.run(b, ['QQQ', 'CASH'], G.bind(b, [G.sl_static({'QQQ': 1.0})]), [1.0]); W_hold = (1 + hold['cagr']) ** yrs
    dep = np.exp(np.log1p(np.maximum(rf - 0.02 / 252, 0) * 0.846).sum(axis=1))                           # after-tax deposit growth
    e_hold = np.ones_like(r); e_tim = np.minimum(L, 1.0)
    books = {'P_hold_연금저축': grow(r, rf, e_hold), 'P_timing_연금저축': grow(r, rf, e_tim),
             'P_hold_IRP70': grow(r, rf, 0.7 * e_hold), 'P_timing_IRP70': grow(r, rf, 0.7 * e_tim)}
    out = {'_meta': dict(basis=bn, years=yrs, P=b.P),
           '종합_s085': dict(med=float(np.median(W_s085)), p10=float(np.percentile(W_s085, 10)), cagr=float(np.median(ref['cagr']))),
           '종합_1x_hold': dict(med=float(np.median(W_hold)), p10=float(np.percentile(W_hold, 10)), cagr=float(np.median(hold['cagr'])))}
    for k, Gp in books.items():
        for cr in (0.165, 0.132, 0.0):
            for wt, tw in (('연금수령5.5', 0.055), ('중도16.5', 0.165)):
                W = Gp * (1 - tw) + cr * dep
                eq = W ** (1 / yrs) - 1
                d = W - W_s085
                out['%s|공제%.1f|%s' % (k, cr * 100, wt)] = dict(med=float(np.median(W)), p10=float(np.percentile(W, 10)),
                    cagr_equiv=float(np.median(eq)), d_vs_s085_med=float(np.median(d)), win_vs_s085=float(np.mean(d > 0)),
                    pre_tax_cagr=float(np.median(Gp ** (1 / yrs) - 1)))
    return out


if __name__ == '__main__':
    res = {bn: run(bn) for bn in ('dev250_path', 'real_ndx_86_14')}
    json.dump(res, open(m3env.SCR + 'results/t5_pension.json', 'w'), indent=1, ensure_ascii=False)
    for bn, o in res.items():
        print('==', bn, o['_meta'])
        for k, v in o.items():
            if k == '_meta': continue
            print('%-40s 1천만 -> 중앙 %7.0f만 (p10 %6.0f만) 환산연복리 %s' % (k, v['med'] * 1000, v['p10'] * 1000,
                  '%.2f%%' % (100 * v.get('cagr_equiv', v.get('cagr'))) ) + (' 세전 %.2f%% d %+.0f만 승률 %.2f' % (100 * v['pre_tax_cagr'], v['d_vs_s085_med'] * 1000, v['win_vs_s085']) if 'pre_tax_cagr' in v else ''))
