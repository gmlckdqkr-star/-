"""V1 check 2 (part): how fragile the single-path real_spx_29_85 row is. Same basis (Saturdays kept, as the protocol),
start of the path moved by 0..120 sessions (measured window starts 300 sessions later), per calendar year. Also the
Saturday-removed basis with both bases started on the same measured day. <=1985 data only."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/verify'); import V1_common as V  # noqa
std, ov, ce, jp = V.std, V.ov, V.ce, V.jp


def rows(X, i0, rules):
    F = ov.flags_hist(X); c = ov.Ctx(X, F, np.arange(i0, len(X))[None, :]); d = X.index[i0 + V.WARM:]
    yc = (d[-1] - d[0]).days / 365.25; y2 = len(d) / 252; k = y2 / yc
    o = dict(measured_from=str(d[0].date()))
    for L, R in rules.items(): o[L] = (1 + V.single(c, V.targets(R, c.lvl, c.rf))[0]) ** k - 1
    rB, rbf, rbp, rfs = std.s085(c); o['s085'] = (1 + V.single(c, rB, rbf, rbp, rfs)[0]) ** k - 1
    o['hold1x'] = (1 + float(std.hold(c, 1)[0][0])) ** k - 1
    return o


def main():
    Xs = jp.mkX(*jp.calendar('1928-01-03', '1985-12-31'), 'SPX'); sat = np.asarray(Xs.index.day_of_week == 5)
    Xn = Xs[~sat].copy(); Xn['p'] = (1 + Xn['r']).cumprod()
    rules = {L: V.load_rule(L) for L in ('D', 'A', 'L1')}
    out = dict(shift=[], same_start=[])
    for s in range(0, 121, 10):
        o = rows(Xs, s, rules); o['shift'] = s; out['shift'].append(o)
        print('shift %3d from %s  D %.4f A %.4f L1 %.4f s085 %.4f hold1x %.4f' % (s, o['measured_from'], o['D'], o['A'], o['L1'], o['s085'], o['hold1x']), flush=True)
    for day in ('1929-06-03', '1930-01-02'):
        for nm, X in (('with_sat', Xs), ('no_sat', Xn)):
            i0 = int(X.index.searchsorted(pd.Timestamp(day))) - V.WARM; o = rows(X, i0, rules); o['basis'] = nm; out['same_start'].append(o)
            print('%-8s from %s  D %.4f A %.4f L1 %.4f s085 %.4f hold1x %.4f' % (nm, o['measured_from'], o['D'], o['A'], o['L1'], o['s085'], o['hold1x']), flush=True)
    Ds = [o['D'] for o in out['shift']]; Hs = [o['hold1x'] for o in out['shift']]
    out['D_range'] = (min(Ds), max(Ds)); out['D_minus_hold_range'] = (min(np.subtract(Ds, Hs)), max(np.subtract(Ds, Hs)))
    print('D range', out['D_range'], 'D - hold1x range', out['D_minus_hold_range'])
    return out


if __name__ == '__main__':
    p = V.dump(main(), 'V1_spx29_start.json'); print('wrote', p)
