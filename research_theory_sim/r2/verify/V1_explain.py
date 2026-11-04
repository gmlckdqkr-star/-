"""V1 check 7: two explanations with <=2014 numbers only.
(a) cost of the 3x-product-plus-cash vehicle against the 1x hold at the same average exposure, on real NDX 1986-2014
    and dev250_path: my own numpy replica of the MS1 engine (validated bit-for-bit against std.engine at default
    settings) with switches, applied to D (E0 1.25), a drift-tracked constant level 1 (D's own code with E0 = 1.0) and a
    never-rebalanced constant level 1; frictions removed one at a time; and an ideal daily-rebalanced x-times index
    (x r - (x-1) rf, 1x-hold fee and tax treatment) at D's measured average effective exposure.
(b) why D's P(MDD <= -80%) on dev250_path is high: MDD of 1x hold / ideal 1.2x / D per path, and by how many
    250-day blocks of the 2000-03..2002-10 crash a path contains."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/verify'); import V1_common as V  # noqa
std, ov, ce, jp, iv = V.std, V.ov, V.ce, V.jp, None
import iv  # noqa
WARM = V.WARM


def eng(r, rf, B, delay=2, cost=0.003, tax=0.22, D=0.25, cspr=0.02, er3=0.0245, cash_tax=0.154, step=0.5, fstep=0.5,
        hthr=1.0, yearly_tax=True, harvest=True):
    """vectorised replica of beng.run1 (identity brake, harvest 3). Returns fin CAGR, EE, mean effective exposure
    3*v0/(v0+v3) over measured days, trades per year, tax paid, cost paid (both as share of start capital)."""
    P, T = r.shape
    v0 = np.zeros(P); v3 = np.zeros(P); b0 = np.zeros(P); real = np.zeros(P)
    held = np.zeros(P); cur = np.full(P, -99.0); q = np.zeros((P, delay + 1)); E = np.ones(P)
    EE = np.zeros((P, T - WARM)); X = np.zeros((P, T - WARM)); ntr = np.zeros(P); taxp = np.zeros(P); costp = np.zeros(P)
    for t in range(T):
        if t >= WARM:
            k = t - WARM
            if yearly_tax and k > 0 and k % 252 == 0:
                due = tax * np.maximum(real - D, 0.0); real = np.zeros(P)
                m = due > 0; tot = v0 + v3; taxp += np.where(m, due, 0.0)
                f = np.where(m, np.minimum(due / np.maximum(tot, 1e-300), 1.0), 0.0)
                real = real + np.where(m, f * (v0 - b0), 0.0)
                v0 = v0 * (1 - f); v3 = v3 * (1 - f); b0 = b0 * (1 - f)
            want = q[:, 0].copy()
            for j in range(delay - 1): q[:, j] = q[:, j + 1]
            if k > 0:
                v0 = v0 * (1 + 3 * r[:, t] - 2 * rf[:, t] - er3 / 252)
                v3 = v3 * (1 + np.maximum(rf[:, t] - cspr / 252, 0.0) * (1 - cash_tax))
            ch = want != cur
            if ch.any():
                tot = v0 + v3
                if k == 0: tot = np.ones(P); v3 = np.where(ch, 1.0, v3)
                w0 = want / 3; t0 = w0 * tot; t3 = (1 - w0) * tot; d0 = t0 - v0; tc = np.where(ch, cost * np.abs(d0), 0.0)
                costp += tc; ntr += ch
                sell = ch & (d0 < 0) & (v0 > 0)
                fr = np.where(sell, np.minimum(-d0 / np.where(v0 > 0, v0, 1.0), 1.0), 0.0)
                real = real + fr * (v0 - b0); b0 = b0 * (1 - fr)
                b0 = np.where(ch & (d0 > 0), b0 + d0, b0)
                sc = (tot - tc) / np.maximum(tot, 1e-300)
                v0 = np.where(ch, t0 * sc, v0); v3 = np.where(ch, t3 * sc, v3); cur = np.where(ch, want, cur)
            if harvest and yearly_tax and k % 252 == 251:
                ok = v0 > 1e-12; target = D - real; U = v0 - b0
                f = np.zeros(P)
                f = np.where(ok & (target < 0) & (U < 0), np.minimum(1.0, target / np.where(U != 0, U, 1.0)), f)
                f = np.where(ok & (target > 0) & (U > 0), np.minimum(1.0, target / np.where(U != 0, U, 1.0)), f)
                rz = f * U; sv = f * v0
                do = ok & (sv > 0) & (tax * np.abs(rz) > hthr * 2 * cost * sv)
                tc = 2 * cost * sv; costp += np.where(do, tc, 0.0)
                real = np.where(do, real + rz, real); b0 = np.where(do, b0 - (sv - rz) + (sv - tc), b0); v0 = np.where(do, v0 - tc, v0)
            E = v0 + v3; EE[:, k] = E; X[:, k] = 3 * v0 / np.maximum(E, 1e-300)
        b = np.nan_to_num(B[:, t], nan=0.0); tg = np.clip(b, 0.0, 3.0)
        stp = np.where((tg >= 1.0) | (held >= 1.0), step, fstep)
        upd = (np.abs(tg - held) >= stp) | ((tg == 0) & (held > 0))
        held = np.where(upd, np.round(tg / stp) * stp, held)
        if t == WARM - 1: q[:, :delay] = held[:, None]
        elif t >= WARM: q[:, delay - 1] = held
    if yearly_tax:
        fin = E - tax * np.maximum(real + (v0 - b0) - D, 0.0)
    else:   # all tax deferred to the end, on total gain (as the 1x hold)
        fin = E - tax * np.maximum(E - 1.0 - D, 0.0) if D else E - tax * np.maximum(E - 1.0, 0.0)
    yrs = (T - WARM) / 252
    return dict(cagr=np.maximum(fin, 1e-9) ** (1 / yrs) - 1, EE=EE, expo=X.mean(axis=1), trades=ntr / yrs, taxp=taxp, costp=costp)


def ideal(r, rf, x, fee=0.002, tax=0.22, fin_cost=0.003):
    """daily-rebalanced x-times index financed at rf (no product fee beyond the 1x hold's 0.2%), final tax only."""
    r = r[:, WARM:]; rf = rf[:, WARM:]
    g = 1 + x * r - (x - 1) * rf - fee / 252; E = np.cumprod(g, axis=1); yrs = E.shape[1] / 252
    e = E[:, -1] * (1 - fin_cost); fin = e - tax * np.maximum(e - 1, 0)
    return np.maximum(fin, 1e-9) ** (1 / yrs) - 1, E


def med(a): return float(np.median(a))


def main():
    C = V.bases(); D = V.load_rule('D'); out = {}
    for bn in ('real_ndx_86_14', 'dev250_path'):
        c = C[bn]; r, rf = c.r, c.rf; o = {}
        BD = V.targets(D, c.lvl, c.rf); B1 = V.targets(D, c.lvl, c.rf, params={'E0': 1.0, 'THETA': 0.35})
        Bc = np.full(c.r.shape, 1.0)
        # validation of the replica against std.engine (default MS1 settings)
        for nm, B in (('D', BD), ('track1', B1), ('const1', Bc)):
            fs, Es = V.run(c, B); m = eng(r, rf, B)
            o['validate_' + nm] = dict(max_abs_cagr_diff=float(np.max(np.abs(fs - m['cagr']))), max_abs_EE_diff=float(np.max(np.abs(Es - m['EE']))))
        h1, E1 = std.hold(c, 1); o['hold1x'] = dict(cagr=med(h1), mdd=med(ce.mdd(E1)), dd80=float(np.mean(ce.mdd(E1) <= -0.8)))
        for nm, B in (('D_E0_1.25', BD), ('track_level1', B1), ('const_level1_no_rebal', Bc)):
            steps = [('MS1 engine', {}), ('no trading cost', dict(cost=0.0)), ('+ tax deferred to the end', dict(cost=0.0, yearly_tax=False)),
                     ('+ product fee 0.6%/yr on the 3x part (=0.2% per unit exposure)', dict(cost=0.0, yearly_tax=False, er3=0.006)),
                     ('+ cash earns rf (no 2pp spread, no 15.4% cash tax)', dict(cost=0.0, yearly_tax=False, er3=0.006, cspr=0.0, cash_tax=0.0))]
            rows = []
            for lab, kw in steps:
                m = eng(r, rf, B, **kw); mdd = ce.mdd(m['EE'])
                rows.append(dict(step=lab, cagr=med(m['cagr']), mean_expo=med(m['expo']), trades_per_yr=med(m['trades']),
                                 tax_paid=med(m['taxp']), cost_paid=med(m['costp']), mdd=med(mdd), dd80=float(np.mean(mdd <= -0.8)),
                                 mean_target=float(np.nanmean(B[:, WARM:]))))
            # ideal x-times index at the same (per-path) mean effective exposure
            x = eng(r, rf, B)['expo'][:, None]
            fi, Ei = ideal(r, rf, x); mi = ce.mdd(Ei)
            o[nm] = dict(steps=rows, ideal_same_expo=dict(cagr=med(fi), mdd=med(mi), dd80=float(np.mean(mi <= -0.8)), x_median=med(x)))
            print(bn, nm, 'ideal same-expo %.4f' % med(fi), ' | '.join('%s: %.4f (expo %.3f, trades %.1f, tax %.3f, cost %.3f, dd80 %.3f)' % (
                s['step'][:22], s['cagr'], s['mean_expo'], s['trades_per_yr'], s['tax_paid'], s['cost_paid'], s['dd80']) for s in rows), flush=True)
        for x in (1.0, 1.1, 1.2, 1.25):
            fi, Ei = ideal(r, rf, x); mi = ce.mdd(Ei)
            o['ideal_x%.2f' % x] = dict(cagr=med(fi), mdd=med(mi), dd80=float(np.mean(mi <= -0.8)))
        print(bn, 'hold1x', o['hold1x'], {k: v for k, v in o.items() if k.startswith('ideal_x') or k.startswith('validate')}, flush=True)
        if bn == 'dev250_path':
            # (b) which paths reach -80%: blocks drawn from the 2000-03-10 .. 2002-10-09 crash
            a, b_, P, blk, seed = iv.POOLS['dev250']; Xd = jp.mkX(*jp.calendar(a, b_), 'NDX'); dates = Xd.index; ii = c.ii
            mD = ce.mdd(eng(r, rf, BD)['EE']); m1 = ce.mdd(E1)
            xD = eng(r, rf, BD)['expo'][:, None]; _, Ei = ideal(r, rf, xD); mI = ce.mdd(Ei)
            lo, hi = dates.searchsorted(pd.Timestamp('2000-03-10')), dates.searchsorted(pd.Timestamp('2002-10-09'))
            starts = ii[:, ::blk]                       # block start indices (blocks of 250 consecutive source days)
            ov_days = np.array([np.sum((ii[p, WARM:] >= lo) & (ii[p, WARM:] <= hi)) for p in range(ii.shape[0])])
            nblk = np.round(ov_days / 250).astype(int)
            tab = []
            for kk in range(0, int(nblk.max()) + 1):
                m = nblk == kk
                if m.sum() == 0: continue
                tab.append(dict(crash_blocks=kk, paths=int(m.sum()), dd80_hold1x=float(np.mean(m1[m] <= -0.8)), dd80_ideal_same_expo=float(np.mean(mI[m] <= -0.8)),
                                dd80_D=float(np.mean(mD[m] <= -0.8)), mdd_med_hold1x=med(m1[m]), mdd_med_D=med(mD[m])))
            o['dd80_by_crash_blocks'] = tab
            o['dd80'] = dict(hold1x=float(np.mean(m1 <= -0.8)), ideal_same_expo=float(np.mean(mI <= -0.8)), D=float(np.mean(mD <= -0.8)),
                             share_paths_with_any_crash_days=float(np.mean(ov_days > 0)), mean_crash_days_per_path=float(ov_days.mean()),
                             crash_days_in_source=int(hi - lo), source_days=int(len(dates)),
                             D_dd80_given_hold1x_dd80=float(np.mean(mD[m1 <= -0.8] <= -0.8)) if np.any(m1 <= -0.8) else None,
                             D_dd80_given_hold1x_not=float(np.mean(mD[m1 > -0.8] <= -0.8)))
            o['real_ndx_crash_depth'] = dict(ndx_price_peak_to_trough=float(Xd['p'].iloc[lo:hi + 1].min() / Xd['p'].iloc[lo] - 1))
            print('dd80', o['dd80'], flush=True)
            for row in tab: print('  ', row, flush=True)
            print('NDX 2000-03-10..2002-10-09', o['real_ndx_crash_depth'], flush=True)
        out[bn] = o
    return out


if __name__ == '__main__':
    p = V.dump(main(), 'V1_explain.json'); print('wrote', p)
