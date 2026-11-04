"""V1 check 3: fresh confirmation E re-implemented (<=2014-12-31 only). 8 country funds, adjusted close (panel col 4)
cut at 2014-12-31 before use, US calendar, US rf / y10 / macro flags, path from the fund's first day (300-day warm-up).
Per fund: rule (A, B, C, D), round-1 L1, s0.85, 1x/2x/3x hold. Summary: median paired difference and wins (>1e-5)
out of 8 vs L1, s0.85, 1x hold. Base and stresses delay 3 / cost 0.6% (holds unstressed, as MS1/protocol).
Also: the harness return construction ('ret') vs price-reindex ('price'), and the s0.85 base-vs-delay-3 diagnosis."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/verify'); import V1_common as V  # noqa
std, ov, ce = V.std, V.ov, V.ce
SETS = (('base', {}), ('delay3', dict(delay=3)), ('cost2x', dict(cost=0.006)))


def summ(rows, rk):
    def cmp(f):
        d = np.array([x[rk]['cagr'] - f(x) for x in rows])
        return dict(median=float(np.median(d)), wins=int((d > 1e-5).sum()), wins_gt0=int((d > 0).sum()), n=len(d), d=[float(v) for v in d])
    return dict(vs_L1=cmp(lambda x: x['L1']['cagr']), vs_s085=cmp(lambda x: x['s085']['cagr']), vs_hold1x=cmp(lambda x: x['hold1x']['cagr']),
                vs_hold2x=cmp(lambda x: x['hold2x']['cagr']), vs_hold3x=cmp(lambda x: x['hold3x']['cagr']),
                median=float(np.median([x[rk]['cagr'] for x in rows])))


def main(names, method):
    rules = {L: V.load_rule(L) for L in names + ['L1']}
    res = dict(method=method, funds={}, info={}); per = {lab: [] for lab, _ in SETS}
    for k in V.FUNDS:
        c, y, dates, info = V.fund_ctx(k, method); res['info'][k] = info
        assert dates[-1] <= V.END
        Bs = {L: V.targets(rules[L], c.lvl, c.rf) for L in rules}
        h1, E1 = std.hold(c, 1); h2, E2 = std.hold(c, 2); f3 = V.single(c, np.full(c.r.shape, 3.0))
        hold = dict(hold1x=dict(cagr=float(h1[0]), mdd=float(ce.mdd(E1)[0])), hold2x=dict(cagr=float(h2[0]), mdd=float(ce.mdd(E2)[0])),
                    hold3x=dict(cagr=f3[0], mdd=f3[1]))
        for lab, kw in SETS:
            row = dict(fund=k, **hold)
            for L, B in Bs.items():
                cg, md = V.single(c, B, **kw); Bt = np.nan_to_num(B[:, V.WARM:])
                row[L] = dict(cagr=cg, mdd=md, avg_target=float(Bt.mean()), share_cash=float((Bt <= 0).mean()))
            rB, rbf, rbp, rfs = std.s085(c); cg, md = V.single(c, rB, rbf, rbp, rfs, **kw)
            # s0.85 diagnostics: executed level path statistics
            fin, EE = V.run(c, rB, rbf, rbp, rfs, **kw)
            row['s085'] = dict(cagr=cg, mdd=md, avg_signal=float(np.nanmean(rB[:, V.WARM:])), share_sig3=float(np.mean(np.nan_to_num(rB[:, V.WARM:]) >= 3)))
            per[lab].append(row)
            print('%-6s %-4s %s' % (lab, k, ' '.join('%s=%.4f' % (L, row[L]['cagr']) for L in list(rules) + ['s085', 'hold1x', 'hold2x', 'hold3x'])), flush=True)
        res['funds'][k] = {lab: per[lab][-1] for lab, _ in SETS}
    res['summary'] = {lab: {L: summ(per[lab], L) for L in names} for lab, _ in SETS}
    for lab, _ in SETS:
        for L in names:
            s = res['summary'][lab][L]
            print('%-6s %s: median %.4f | vs L1 med %+.4f wins %d | vs s085 med %+.4f wins %d | vs 1x med %+.4f wins %d' % (
                lab, L, s['median'], s['vs_L1']['median'], s['vs_L1']['wins'], s['vs_s085']['median'], s['vs_s085']['wins'],
                s['vs_hold1x']['median'], s['vs_hold1x']['wins']), flush=True)
    return res


if __name__ == '__main__':
    a = sys.argv[1:]; method = 'ret' if '--ret' in a else 'price'; names = [x for x in a if not x.startswith('--')] or ['D', 'A', 'B', 'C']
    res = main(names, method)
    # compare with orchestrator json
    cmpd = {}
    for L in names:
        try: R = json.load(open(V.R2 + 'test/out/real_%s.json' % L))
        except FileNotFoundError: continue
        for lab, key in (('base', 'conf'), ('delay3', 'conf_delay3'), ('cost2x', 'conf_cost2x')):
            for x in R[key]['rows']:
                m = res['funds'][x['fund']][lab]
                for a1, b1 in (('rule', L), ('r1_L1', 'L1'), ('s085', 's085')):
                    cmpd['%s|%s|%s|%s' % (L, lab, x['fund'], a1)] = (m[b1]['cagr'], x[a1]['cagr'], abs(m[b1]['cagr'] - x[a1]['cagr']))
                for hk in ('hold1x', 'hold2x', 'hold3x'):
                    cmpd['%s|%s|%s|%s' % (L, lab, x['fund'], hk)] = (m[hk]['cagr'], x[hk], abs(m[hk]['cagr'] - x[hk]))
                cmpd['%s|%s|%s|start' % (L, lab, x['fund'])] = (res['info'][x['fund']]['measured_from'], x['start'], 0.0 if res['info'][x['fund']]['measured_from'] == x['start'] else 1.0)
            s = R[key]['summary']; ms = res['summary'][lab][L]
            for a1, b1 in (('vs_r1_L1', 'vs_L1'), ('vs_s085', 'vs_s085'), ('vs_hold1x', 'vs_hold1x')):
                cmpd['%s|%s|sum|%s|median' % (L, lab, a1)] = (ms[b1]['median'], s[a1]['median'], abs(ms[b1]['median'] - s[a1]['median']))
                cmpd['%s|%s|sum|%s|wins' % (L, lab, a1)] = (ms[b1]['wins'], s[a1]['wins'], abs(ms[b1]['wins'] - s[a1]['wins']))
    res['compare_max_abs'] = max([v[2] for v in cmpd.values()] or [0])
    res['compare_over_1e-3'] = {k: v for k, v in cmpd.items() if v[2] > 1e-3}
    res['compare_n'] = len(cmpd)
    print('compare n=%d max|d|=%.3g; >0.1pp: %s' % (len(cmpd), res['compare_max_abs'], json.dumps(res['compare_over_1e-3'])[:3000]))
    p = V.dump(res, 'V1_conf_%s.json' % method); print('wrote', p)
