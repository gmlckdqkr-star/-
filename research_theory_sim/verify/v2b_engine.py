"""TS1 verifier, check 2b/5: my own pure-numpy re-implementation of the MS1 engine (beng.run1, identity brake) and of the
same-basis holds, cross-checked against std.engine / std.hold and against test/out/real_L*.json, incl. the stresses
(delay 3/5, cost 0.6%) and real_spx_29_85 built from the protocol text (S&P 1928-01-03.., measured from day 300). <=2014 only.
Also: warm-up sensitivity of real_ndx_86_14 (NDX has no data before 1985-10: the path's first ~237 days are r=0)."""
import sys, json, importlib.util, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std  # noqa
import jp, ov  # noqa
TS = '/mnt/project-files/research/theory_sim/'
WARM = 300


def load(L):
    p = TS + 'design/%s/rule.py' % L
    spec = importlib.util.spec_from_file_location('erule_' + L, p); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m); return m


def my_engine(r, rf, B, delay=2, cost=0.003, tax=0.22, D=0.25, cspr=0.02, er3=0.0245, step=0.5, fstep=0.5, hthr=1.0):
    """vectorised over paths; identity brake; harvest = 3 (both directions) as in beng.F1"""
    P, T = r.shape
    v0 = np.zeros(P); v3 = np.zeros(P); b0 = np.zeros(P); real = np.zeros(P)
    held = np.zeros(P); cur = np.full(P, -99.0); q = np.zeros((P, delay + 1)); E = np.ones(P)
    EE = np.zeros((P, T - WARM))
    for t in range(T):
        if t >= WARM:
            k = t - WARM
            if k > 0 and k % 252 == 0:
                due = tax * np.maximum(real - D, 0.0); real = np.zeros(P)
                m = due > 0; tot = v0 + v3
                f = np.where(m, np.minimum(due / np.maximum(tot, 1e-300), 1.0), 0.0)
                real = real + np.where(m, f * (v0 - b0), 0.0)
                v0 = v0 * (1 - f); v3 = v3 * (1 - f); b0 = b0 * (1 - f)
            want = q[:, 0].copy()
            for j in range(delay - 1): q[:, j] = q[:, j + 1]
            if k > 0:
                v0 = v0 * (1 + 3 * r[:, t] - 2 * rf[:, t] - er3 / 252)
                v3 = v3 * (1 + np.maximum(rf[:, t] - cspr / 252, 0.0) * (1 - 0.154))
            ch = want != cur
            if ch.any():
                tot = v0 + v3
                if k == 0: tot = np.ones(P); v3 = np.where(ch, 1.0, v3)
                w0 = want / 3; t0 = w0 * tot; t3 = (1 - w0) * tot; d0 = t0 - v0; tc = cost * np.abs(d0)
                sell = ch & (d0 < 0) & (v0 > 0)
                fr = np.where(sell, np.minimum(-d0 / np.where(v0 > 0, v0, 1.0), 1.0), 0.0)
                real = real + fr * (v0 - b0); b0 = b0 * (1 - fr)
                b0 = np.where(ch & (d0 > 0), b0 + d0, b0)
                sc = (tot - tc) / np.maximum(tot, 1e-300)
                v0 = np.where(ch, t0 * sc, v0); v3 = np.where(ch, t3 * sc, v3); cur = np.where(ch, want, cur)
            if k % 252 == 251:
                ok = v0 > 1e-12; target = D - real; U = v0 - b0
                f = np.zeros(P)
                f = np.where(ok & (target < 0) & (U < 0), np.minimum(1.0, target / np.where(U != 0, U, 1.0)), f)
                f = np.where(ok & (target > 0) & (U > 0), np.minimum(1.0, target / np.where(U != 0, U, 1.0)), f)
                rz = f * U; sv = f * v0
                do = ok & (sv > 0) & (tax * np.abs(rz) > hthr * 2 * cost * sv)
                tc = 2 * cost * sv
                real = np.where(do, real + rz, real); b0 = np.where(do, b0 - (sv - rz) + (sv - tc), b0); v0 = np.where(do, v0 - tc, v0)
            E = v0 + v3; EE[:, k] = E
        b = np.nan_to_num(B[:, t], nan=0.0); tg = np.clip(b, 0.0, 3.0)
        stp = np.where((tg >= 1.0) | (held >= 1.0), step, fstep)
        upd = (np.abs(tg - held) >= stp) | ((tg == 0) & (held > 0))
        held = np.where(upd, np.round(tg / stp) * stp, held)
        if t == WARM - 1: q[:, :delay] = held[:, None]
        elif t >= WARM: q[:, delay - 1] = held
    fin = E - tax * np.maximum(real + (v0 - b0) - D, 0.0)
    yrs = (T - WARM) / 252
    return np.maximum(fin, 1e-9) ** (1 / yrs) - 1, EE


def my_hold(r, rf, lev, tax=0.22):
    r = r[:, WARM:]; rf = rf[:, WARM:]
    x = r - 0.002 / 252 if lev == 1 else lev * r - (lev - 1) * rf - 0.0245 / 252
    E = np.cumprod(1 + x, axis=1); yrs = E.shape[1] / 252; e = E[:, -1] * 0.997
    return np.maximum(e - tax * np.maximum(e - 1, 0), 1e-9) ** (1 / yrs) - 1


def main():
    C = std.contexts()
    Xs = jp.mkX(*jp.calendar('1928-01-03', '1985-12-31'), 'SPX'); ii = np.arange(len(Xs))[None, :]
    cs = ov.Ctx(Xs, ov.flags_hist(Xs), ii)
    print('real_spx_29_85 own build: path start %s, measured from %s to %s, T=%d' % (Xs.index[0].date(), Xs.index[WARM].date(), Xs.index[-1].date(), len(Xs)))
    Xn = jp.mkX(*jp.calendar('1984-01-03', '2014-12-31'), 'NDX'); cn = C['real_ndx_86_14']; dn = Xn.index[cn.ii[0]]
    z = np.where(cn.r[0] != 0)[0]
    print('real_ndx_86_14: path %s..%s, measured from %s; first nonzero return at path day %d (%s); zero-return days before WARM: %d' % (
        dn[0].date(), dn[-1].date(), dn[WARM].date(), z[0], dn[z[0]].date(), int((cn.r[0, :WARM] == 0).sum())))
    res = {}
    for L in ('L1', 'L2', 'L3'):
        rule = load(L); R = json.load(open(TS + 'test/out/real_%s.json' % L)); res[L] = {}
        for bn, c in (('real_ndx_86_14', cn), ('dev250_path', C['dev250_path']), ('real_spx_55_85', C['real_spx_55_85']),
                      ('real_spx_70_85', C['real_spx_70_85']), ('real_spx_29_85', cs)):
            B = np.asarray(rule.target_levels(np.array(c.lvl), np.array(c.rf)), dtype=np.float64)
            for lab, kw in (('base', {}), ('delay3', dict(delay=3)), ('delay5', dict(delay=5)), ('cost2x', dict(cost=0.006))):
                if lab != 'base' and bn not in ('real_ndx_86_14', 'dev250_path'): continue
                if lab != 'base' and L != 'L1' and bn == 'dev250_path': continue   # speed: stresses on dev250_path for L1 only
                fin, EE = my_engine(c.r, c.rf, B, **kw); mine = float(np.median(fin))
                fs, Es = std.engine(c, B, std.ident, np.zeros(1), 0.5, **kw); stdv = float(np.median(fs))
                rep = R[lab][bn]['cagr']
                row = dict(mine=mine, std_engine=stdv, reported=rep, max_path_diff_vs_std=float(np.max(np.abs(fin - fs))),
                           maxEE_diff=float(np.max(np.abs(EE - Es))))
                if lab == 'base':
                    row.update(hold1x_mine=float(np.median(my_hold(c.r, c.rf, 1))), hold1x_rep=R[lab][bn]['hold1x'],
                               hold2x_mine=float(np.median(my_hold(c.r, c.rf, 2))), hold2x_rep=R[lab][bn]['hold2x'])
                    f3, _ = my_engine(c.r, c.rf, np.full(c.r.shape, 3.0)); row.update(hold3x_mine=float(np.median(f3)), hold3x_rep=R[lab][bn]['hold3x'])
                    if bn == 'real_spx_29_85':
                        rB, rbf, rbp, rfs = std.s085(c); fr, _ = std.engine(c, rB, rbf, rbp, rfs)
                        row.update(s085_mine_ctx=float(np.median(fr)), s085_rep=R[lab][bn]['ref_s085'],
                                   d_mine=float(np.median(fin - fr)), d_rep=R[lab][bn]['d_vs_s085'])
                res[L][bn + '|' + lab] = row
                print(L, bn, lab, ' '.join('%s=%.6g' % kv for kv in row.items()), flush=True)
        # warm-up sensitivity: real_ndx_86_14 with the r=0 pre-1985-10 days given to the rule as NaN closes (no data)
        lv = np.array(cn.lvl); lv[0, :z[0]] = np.nan
        B0 = np.asarray(rule.target_levels(np.array(cn.lvl), np.array(cn.rf)), dtype=np.float64)
        B1 = np.asarray(rule.target_levels(lv, np.array(cn.rf)), dtype=np.float64)
        f0, _ = my_engine(cn.r, cn.rf, B0); f1, _ = my_engine(cn.r, cn.rf, B1)
        diffdays = np.where(~np.isclose(np.nan_to_num(B0[0, WARM:]), np.nan_to_num(B1[0, WARM:]), atol=1e-9))[0]
        res[L]['warmup_sens'] = dict(cagr_r0_warmup=float(f0[0]), cagr_nan_warmup=float(f1[0]),
                                     B_at_1986_01_02=(float(B0[0, WARM]), float(B1[0, WARM])),
                                     n_days_B_differs_after_warm=int(len(diffdays)), last_differing_day=str(dn[WARM + diffdays[-1]].date()) if len(diffdays) else None)
        print(L, 'warm-up sensitivity', res[L]['warmup_sens'], flush=True)
    json.dump(res, open(TS + 'verify/v2b_engine.json', 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
