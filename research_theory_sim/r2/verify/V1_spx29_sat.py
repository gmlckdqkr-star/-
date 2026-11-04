"""V1 check 2 (part): real_spx_29_85 and the pre-1952 Saturday sessions. <=1985 data only.
Finding: on every Saturday session of the calendar the S&P return is exactly 0 (the S&P series has no Saturday value; the
calendar does), but rf, the 3x product fee and the hold fee still accrue per session and the engine's tax year is 252 sessions.
Protocol handling = annualise per calendar year. Residual check here: the same basis with the Saturday rows removed
(returns unchanged, since Saturday r = 0), measured per 252 sessions and per calendar year, for A-D, L1, s0.85, holds."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/verify'); import V1_common as V  # noqa
std, ov, ce, jp = V.std, V.ov, V.ce, V.jp


def main():
    Xs = jp.mkX(*jp.calendar('1928-01-03', '1985-12-31'), 'SPX'); sat = np.asarray(Xs.index.day_of_week == 5)
    out = dict(saturday_rows=int(sat.sum()), saturday_abs_r_max=float(np.abs(Xs['r'].values[sat]).max()))
    Xn = Xs[~sat].copy(); Xn['p'] = (1 + Xn['r']).cumprod()
    for nm, X in (('with_saturdays', Xs), ('saturdays_removed', Xn)):
        c = ov.Ctx(X, ov.flags_hist(X), np.arange(len(X))[None, :]); d = X.index[V.WARM:]
        yc = (d[-1] - d[0]).days / 365.25; y2 = (len(d)) / 252; o = dict(measured_from=str(d[0].date()), sessions=len(d), yrs_252=y2, yrs_cal=yc)
        def put(k, cg):
            f = (1 + cg) ** y2; o[k] = dict(per252=cg, per_cal=f ** (1 / yc) - 1)
        for L in ('A', 'B', 'C', 'D', 'L1'):
            put(L, V.single(c, V.targets(V.load_rule(L), c.lvl, c.rf))[0])
        rB, rbf, rbp, rfs = std.s085(c); put('s085', V.single(c, rB, rbf, rbp, rfs)[0])
        put('hold1x', float(std.hold(c, 1)[0][0])); put('hold2x', float(std.hold(c, 2)[0][0])); put('hold3x', V.single(c, np.full(c.r.shape, 3.0))[0])
        out[nm] = o
        print(nm, o['measured_from'], o['sessions'], 'yrs252 %.2f cal %.2f' % (y2, yc), ' '.join('%s %.4f/%.4f' % (k, v['per252'], v['per_cal']) for k, v in o.items() if isinstance(v, dict)), flush=True)
    return out


if __name__ == '__main__':
    p = V.dump(main(), 'V1_spx29_sat.json'); print('wrote', p)
