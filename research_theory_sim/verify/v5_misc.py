"""TS1 verifier, check 5/6 extras (<=2014 only):
(a) G1: harness.g1 concatenates SPX 1928-85 and NDX 1984-2014 targets and keeps the LAST duplicate, so SPX-era blocks dated
    1984-01-03..1985-12-31 get the NDX-path target. Recompute G1 with each era fed its own market's target.
(b) scale invariance on real data: close x100 and x1e-3 -> engine CAGR (real_ndx_86_14, dev250_path).
(c) real_spx_29_85: KF calendar has Saturday sessions before 1952; MS1 annualises with 252 days/yr. Count real years."""
import sys, json, importlib.util, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std  # noqa
import jp, ov  # noqa
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code'); import gate  # noqa
sys.path.insert(0, '/mnt/project-files/research/theory_sim/verify'); from v2b_engine import my_engine, my_hold, load  # noqa
TS = '/mnt/project-files/research/theory_sim/'
WARM = 300


def main():
    out = {}
    Xn = jp.mkX(*jp.calendar('1984-01-03', '2014-12-31'), 'NDX'); Xs = jp.mkX(*jp.calendar('1928-01-03', '1985-12-31'), 'SPX')
    cn = ov.Ctx(Xn, ov.flags_hist(Xn), np.arange(len(Xn))[None, :]); cs = ov.Ctx(Xs, ov.flags_hist(Xs), np.arange(len(Xs))[None, :])
    lab = gate.labels()
    sl = lab['spx_55_85']; nover = int((sl.index >= Xn.index[0]).sum())
    print('SPX-era G1 blocks dated >= %s (fed the NDX target by harness.g1): %d of %d' % (Xn.index[0].date(), nover, len(sl)))
    C = std.contexts()
    for L in ('L1', 'L2', 'L3'):
        rule = load(L); rep = json.load(open(TS + 'test/out/real_%s.json' % L)); o = {}
        Bn = pd.Series(np.asarray(rule.target_levels(np.array(cn.lvl), np.array(cn.rf)))[0], index=Xn.index).fillna(0.0)
        Bs = pd.Series(np.asarray(rule.target_levels(np.array(cs.lvl), np.array(cs.rf)))[0], index=Xs.index).fillna(0.0)
        mix = pd.concat([Bs, Bn]); mix = mix[~mix.index.duplicated(keep='last')]
        for nm, f in (('ge1.5', lambda s: s >= 1.5), ('gt0', lambda s: s > 0)):
            gh = gate.test(f(mix), trials=3, verbose=False)                 # harness construction (reproduce)
            gn = gate.test(f(Bn), trials=3, verbose=False); gs = gate.test(f(Bs), trials=3, verbose=False)
            fixed = dict(ndx=gn['ndx_86_14']['hit'], spx=gs['spx_55_85']['hit'],
                         low_defl=min(gn['ndx_86_14']['hit_deflated'], gs['spx_55_85']['hit_deflated']))
            o['g1_' + nm] = dict(reported=(rep['g1'][nm]['ndx_86_14']['hit'], rep['g1'][nm]['spx_55_85']['hit'], rep['g1'][nm]['verdict']),
                                 reproduced=(gh['ndx_86_14']['hit'], gh['spx_55_85']['hit'], gh['verdict']),
                                 own_market_target=(fixed['ndx'], fixed['spx'], fixed['low_defl']),
                                 spx_blocks_1984_85_where_targets_differ=int(((f(Bs).reindex(sl.index[sl.index >= Xn.index[0]]) !=
                                                                              f(Bn).reindex(sl.index[sl.index >= Xn.index[0]]))).sum()))
        # (b) scale invariance
        for bn in ('real_ndx_86_14', 'dev250_path'):
            c = C[bn]; base = None
            for k in (1.0, 100.0, 1e-3):
                B = np.asarray(rule.target_levels(np.array(c.lvl) * k, np.array(c.rf)), dtype=np.float64)
                fin, _ = my_engine(c.r, c.rf, B); m = float(np.median(fin))
                if base is None: base = (m, B, fin)
                else:
                    o['scale_%s_x%g' % (bn, k)] = dict(cagr=m, d_cagr=m - base[0], max_abs_B=float(np.nanmax(np.abs(B - base[1]))),
                                                      paths_cagr_differ=int(np.sum(fin != base[2])))
        out[L] = o
        print(L, json.dumps(o, default=float), flush=True)
    # (c) calendar years of real_spx_29_85
    d = Xs.index[WARM:]; yrs_cal = (d[-1] - d[0]).days / 365.25 + 1 / 252; yrs_252 = len(d) / 252
    per = pd.Series(1, index=Xs.index).groupby(Xs.index.year).sum()
    print('real_spx_29_85: measured days %d, %s..%s; years by 252-day rule %.2f vs calendar %.2f; trading days/yr 1929-51 mean %.0f, 1953-85 mean %.0f' % (
        len(d), d[0].date(), d[-1].date(), yrs_252, yrs_cal, per.loc[1929:1951].mean(), per.loc[1953:1985].mean()))
    sats = int((Xs.index.dayofweek == 5).sum())
    adj = {}
    for L in ('L1', 'L2', 'L3'):
        rep = json.load(open(TS + 'test/out/real_%s.json' % L))['base']['real_spx_29_85']
        adj[L] = {k: ((1 + rep[k]) ** (yrs_252 / yrs_cal) - 1) for k in ('cagr', 'ref_s085', 'hold1x', 'hold2x', 'hold3x')}
        print('  %s real_spx_29_85 reported cagr %.4f s085 %.4f hold1x %.4f -> per calendar year %.4f / %.4f / %.4f (Saturday sessions in calendar: %d)' % (
            L, rep['cagr'], rep['ref_s085'], rep['hold1x'], adj[L]['cagr'], adj[L]['ref_s085'], adj[L]['hold1x'], sats))
    out['spx29_calendar'] = dict(yrs_252=yrs_252, yrs_cal=yrs_cal, saturdays=sats, adjusted=adj)
    json.dump(out, open(TS + 'verify/v5_misc.json', 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
