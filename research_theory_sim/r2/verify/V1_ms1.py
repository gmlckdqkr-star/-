"""V1 check 2: MS1 recomputation (<=2014 only) for A, B, C, D and round-1 L1 on the 5 MS1 bases + real_spx_29_85,
with same-basis 1x/2x/3x hold and s0.85; stresses delay 3 / delay 5 / cost 0.6% on dev250_path and real_ndx_86_14
(all five rules); real_spx_29_85 also per calendar year. Compares every number with r2/test/out/real_*.json.
Own code: std.contexts / std.engine / std.hold / std.s085 / std.row called directly (no harness import)."""
import sys, time, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/verify'); import V1_common as V  # noqa
std, ov, ce = V.std, V.ov, V.ce

BASES = ('dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85', 'real_spx_29_85')
STRESS = (('delay3', dict(delay=3)), ('delay5', dict(delay=5)), ('cost2x', dict(cost=0.006)))
KEYS = ('cagr', 'mdd', 'w7', 'w12', 'p10', 'dd80', 'dd95', 'd_vs_s085', 'pw_vs_s085', 'ref_s085', 'hold1x', 'hold2x', 'hold3x',
        'avg_target', 'share_cash', 'share_ge2')
_S = {}


def ref(bn, c, kw):
    k = (bn, tuple(sorted(kw.items())))
    if k not in _S:
        fr, Er = V.s085(c, **kw); _S[k] = (fr, std.row(fr, Er)[0])
    return _S[k]


_H = {}
def holds(bn, c):
    if bn not in _H:
        h1, E1 = std.hold(c, 1); h2, E2 = std.hold(c, 2); f3, E3 = V.run(c, np.full(c.r.shape, 3.0)); m1 = ce.mdd(E1)
        _H[bn] = dict(hold1x=float(np.median(h1)), hold2x=float(np.median(h2)), hold3x=float(np.median(f3)),
                      hold1x_mdd=float(np.median(m1)), hold1x_dd80=float(np.mean(m1 <= -0.8)), hold1x_dd95=float(np.mean(m1 <= -0.95)),
                      hold2x_mdd=float(np.median(ce.mdd(E2))), hold3x_mdd=float(np.median(ce.mdd(E3))), _h1=h1)
    return _H[bn]


def one(rule, bn, c, B, kw):
    fc, EE = V.run(c, B, **kw); cand, _ = std.row(fc, EE); fr, rr = ref(bn, c, kw); H = holds(bn, c)
    d = fc - fr; Bt = B[:, V.WARM:]
    cand.update(d_vs_s085=float(np.median(d)), pw_vs_s085=float(np.mean(d > 1e-5)), ref_s085=rr['cagr'], ref_s085_mdd=rr['mdd'],
                **{k: v for k, v in H.items() if not k.startswith('_')},
                d_vs_hold1x=float(np.median(fc - H['_h1'])), pw_vs_hold1x=float(np.mean(fc - H['_h1'] > 1e-5)),
                avg_target=float(np.nanmean(Bt)), share_cash=float(np.mean(np.nan_to_num(Bt) <= 0)),
                share_ge2=float(np.mean(np.nan_to_num(Bt) >= 2)), nan_after_warm=int(np.isnan(Bt).sum()),
                min_target=float(np.nanmin(Bt)), max_target=float(np.nanmax(Bt)))
    return cand, fc


def main(names):
    C = V.bases(); out = {}
    locked = json.load(open('/mnt/project-files/research/measure_std/ref_s085.json'))
    for L in names:
        rule = V.load_rule(L); res = {'base': {}}; t0 = time.time()
        for bn in BASES:
            c = C[bn]
            lv0, rf0 = c.lvl.copy(), c.rf.copy()
            B = V.targets(rule, c.lvl, c.rf)
            assert np.array_equal(lv0, c.lvl) and np.array_equal(rf0, c.rf), 'input mutated'
            if bn in ('real_ndx_86_14', 'real_spx_55_85'):   # behavioural y10 check: garbage y10 must change nothing
                g = np.random.default_rng(3).normal(5, 3, c.r.shape)
                B2 = np.asarray(rule.target_levels(c.lvl.copy(), c.rf.copy(), g), dtype=np.float64)
                res.setdefault('y10_garbage_identical', {})[bn] = bool(np.array_equal(B, B2, equal_nan=True))
            assert B.shape == c.r.shape
            row, fc = one(rule, bn, c, B, {})
            if bn == 'real_spx_29_85':
                d = C['_spx_dates'][V.WARM:]
                yrs_cal = (d[-1] - d[0]).days / 365.25; yrs_252 = (c.T - V.WARM) / 252
                fin = (1 + row['cagr']) ** yrs_252            # single path: final after-tax multiple
                f85 = (1 + row['ref_s085']) ** yrs_252
                row['cal'] = dict(yrs_252=yrs_252, yrs_cal=yrs_cal, yrs_cal_plus1d=yrs_cal + 1 / 252,
                                  saturdays=int((C['_spx_dates'].dayofweek == 5).sum()),
                                  saturdays_measured=int((d.dayofweek == 5).sum()),
                                  cagr_cal=fin ** (1 / yrs_cal) - 1, ref_s085_cal=f85 ** (1 / yrs_cal) - 1,
                                  **{k + '_cal': (1 + row[k]) ** (yrs_252 / yrs_cal) - 1 for k in ('hold1x', 'hold2x', 'hold3x')})
            res['base'][bn] = row
            print('%-3s %-15s %s' % (L, bn, ' '.join('%s=%.4f' % (k, row[k]) for k in KEYS if k in row)), flush=True)
        for lab, kw in STRESS:
            res[lab] = {}
            for bn in ('dev250_path', 'real_ndx_86_14'):
                c = C[bn]; B = V.targets(rule, c.lvl, c.rf); row, _ = one(rule, bn, c, B, kw); res[lab][bn] = row
                print('%-3s %-6s %-15s %s' % (L, lab, bn, ' '.join('%s=%.4f' % (k, row[k]) for k in KEYS if k in row)), flush=True)
        res['secs'] = round(time.time() - t0, 1)
        # compare with the orchestrator's json
        rp = V.R2 + 'test/out/real_%s.json' % L
        try:
            R = json.load(open(rp)); cmp = {}
            for sec in ('base',) + tuple(s for s, _ in STRESS):
                for bn, row in res[sec].items():
                    rr = R[sec][bn]
                    for k in KEYS:
                        if k in row and k in rr:
                            cmp['%s|%s|%s' % (sec, bn, k)] = (row[k], rr[k], abs(row[k] - rr[k]))
            if 'spx29_calendar' in R:
                rc = R['spx29_calendar']; mc = res['base']['real_spx_29_85']['cal']
                for k in ('cagr', 'ref_s085', 'hold1x', 'hold2x', 'hold3x'):
                    cmp['spx29cal|%s' % k] = (mc[k + '_cal'], rc[k + '_cal'], abs(mc[k + '_cal'] - rc[k + '_cal']))
            res['compare_max_abs'] = max(v[2] for v in cmp.values())
            res['compare_over_1e-3'] = {k: v for k, v in cmp.items() if v[2] > 1e-3}
            res['compare_over_1e-9'] = sorted(k for k, v in cmp.items() if v[2] > 1e-9)[:40]
            res['compare_n'] = len(cmp)
            print(L, 'compare n=%d max|d|=%.3g over0.1pp=%s' % (len(cmp), res['compare_max_abs'], list(res['compare_over_1e-3'])[:10]), flush=True)
        except FileNotFoundError:
            res['compare'] = 'no json (%s)' % rp
            if L == 'L1':
                R = json.load(open(V.TS + 'test/out/real_L1.json'))
                res['compare_round1_json'] = {bn: (res['base'][bn]['cagr'], R['base'][bn]['cagr']) for bn in BASES if bn in R['base']}
                print('L1 vs round-1 real_L1.json', res['compare_round1_json'], flush=True)
        out[L] = res
    out['locked_s085_check'] = {bn: (locked[bn]['cagr'], _S[(bn, ())][1]['cagr']) for bn in BASES[:5] if (bn, ()) in _S}
    print('locked s0.85 vs this run', out['locked_s085_check'])
    return out


if __name__ == '__main__':
    names = sys.argv[1:] or ['D', 'A', 'B', 'C', 'L1']
    o = main(names); p = V.dump(o, 'V1_ms1_%s.json' % '_'.join(names)); print('wrote', p)
