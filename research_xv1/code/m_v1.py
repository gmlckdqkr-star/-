"""XV1 first measurement (PREREG section 3): data check, parity, then v1 / 1x / 3x on DESIGN and WEAK blocks only.
Run only after the structure is registered. Nothing from a sealed block is computed into any printed or stored number."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/-/research_xv1/code')
import xv1, std, xeng
from std import bk, ov
sys.path.insert(0, '/mnt/project-files/research/crash_overlay/code')
import mkt
OUT = xv1.OUT + 'results/'


def data_check(dates):
    """counts and dates only: where each raw input ends and how many account days after 2014 have no fresh value."""
    idx = dates[dates > pd.Timestamp(xv1.OLD_END)]
    src = {'NDX': mkt.pser('_NDX', 4), 'IRX(rf,y3m)': mkt.pser('_IRX', 3), 'TNX(y10)': mkt.pser('_TNX', 3, 'panel_ext_f32.npz.xz'),
           'DBAA': mkt.fred('macro_n/raw/DBAA.csv', 'DBAA'), 'DAAA': mkt.fred('macro_n/raw/DAAA.csv', 'DAAA'),
           'TQQQ': mkt.pser('TQQQ', 4)}
    out = {}
    for k, s in src.items():
        miss = int((~idx.isin(s.index)).sum()); gaps = (~pd.Series(idx.isin(s.index), index=idx))
        run = 0; mx = 0
        for g in gaps.values:
            run = run + 1 if g else 0; mx = max(mx, run)
        out[k] = dict(last=str(s.index[-1].date()), account_days_after_2014=int(len(idx)), missing=miss, longest_gap_days=int(mx))
    return out


def parity(c14, d14, cF, dF):
    n = len(d14); assert (dF[:n] == d14).all()
    a = xv1.account(c14, std.s085)[:, 0]; b = xv1.account(cF, std.s085)[:, 0][:n]
    fa = bk.features(c14)[0]; fb = bk.features(cF)[0][:fa.shape[0]]
    Ba = std.s085(c14)[0][0]; Bb = std.s085(cF)[0][0][:len(Ba)]
    return dict(days=n, equity_max_rel_diff=float(np.max(np.abs(a / b - 1))), feature_max_abs_diff=float(np.max(np.abs(fa - fb))),
                base_signal_max_abs_diff=float(np.nanmax(np.abs(Ba - Bb))))


def levels(rec, cal):
    out = []
    lv = rec[:, 1].copy(); lv[cal.sealed] = np.nan
    for b in cal.blocks:
        if xv1.kind_of(b) == 'S': continue
        m = cal.scored & (cal.blk == b)
        if not m.any(): continue
        l = lv[m]; ch = int(np.sum(np.abs(np.diff(l)) > 1e-9))
        out.append(dict(block=b, years=xv1.years_of(b), kind=xv1.kind_of(b), cash=float(np.mean(l <= 0)), low=float(np.mean((l > 0) & (l < 2.75))),
                        full=float(np.mean(l >= 2.75)), mean_level=float(np.mean(np.maximum(l, 0))), changes=ch))
    return out


def model_check(c, cal):
    """modelled 3x fund (3r - 2rf - er3/252) against the actual fund's adjusted-close return, design / weak blocks only."""
    p = mkt.pser('TQQQ', 4); a = p.pct_change().reindex(cal.dates)
    r = c.r[0, ov.WARM:]; rf = c.rf[0, ov.WARM:]; mod = 3 * r - 2 * rf - 0.0245 / 252
    ok = a.notna().values & a.shift(1).notna().values
    xa = np.log1p(a.values); xm = np.log1p(mod); xa[cal.sealed] = np.nan; xm[cal.sealed] = np.nan
    out = []
    for b in cal.blocks:
        if xv1.kind_of(b) == 'S': continue
        m = cal.scored & (cal.blk == b) & ok
        if m.sum() < 100: continue
        out.append(dict(block=b, years=xv1.years_of(b), kind=xv1.kind_of(b), n=int(m.sum()), actual=float(252 * np.nanmean(xa[m])),
                        model=float(252 * np.nanmean(xm[m])), gap=float(252 * np.nanmean(xa[m] - xm[m]))))
    return out


if __name__ == '__main__':
    c14, d14 = xv1.build(xv1.OLD_END); cF, dF = xv1.build(xv1.CAL_END); cal = xv1.Cal(dF)
    R = dict(calendar=dict(first=str(dF[0].date()), last=str(dF[-1].date()), days=len(dF), scored=int(cal.scored.sum())))
    R['data_check'] = data_check(dF); R['parity'] = parity(c14, d14, cF, dF)
    print(json.dumps(R, indent=1))
    if R['parity']['equity_max_rel_diff'] > 1e-9: raise SystemExit('PARITY FAIL: nothing after 2014 is scored')
    rec = xv1.account(cF, std.s085); x = xv1.xlog(rec[:, 0], cal); h1 = xv1.hold1_x(cF, cal)
    x3 = xv1.xlog(xv1.account(cF, xv1.hold3)[:, 0], cal)
    R['blocks'] = dict(v1=xv1.table(x, cal), hold1=xv1.table(h1, cal), hold3=xv1.table(x3, cal))
    R['sets'] = dict(v1=xv1.sets(x, cal), hold1=xv1.sets(h1, cal), hold3=xv1.sets(x3, cal))
    R['levels'] = levels(rec, cal); R['model_check'] = model_check(cF, cal)
    import os; os.makedirs(OUT, exist_ok=True); json.dump(R, open(OUT + 'v1_blocks.json', 'w'), indent=1)
    for a, b, d in zip(R['blocks']['v1'], R['blocks']['hold1'], R['blocks']['hold3']):
        print('b%-2d %s %s n=%3d  v1 %+7.2f  1x %+7.2f  3x %+7.2f' % (a['block'], a['years'], a['kind'], a['n'], 100 * a['ann'], 100 * b['ann'], 100 * d['ann']))
    for nm in R['sets']['v1']:
        print('%-16s n=%4d  v1 %+7.2f  1x %+7.2f  3x %+7.2f' % (nm, R['sets']['v1'][nm]['n'], 100 * R['sets']['v1'][nm]['ann'], 100 * R['sets']['hold1'][nm]['ann'], 100 * R['sets']['hold3'][nm]['ann']))
    for l in R['levels']: print('levels', l)
    for l in R['model_check']: print('model', l)
