"""Verifier NUMBERS: independent recomputation of the three adopted DF1/DF2 picks on single real paths.
Own day-by-day loop in plain Python (no dfe import), written from PRECOMMIT_DF1 s1-2, PRECOMMIT_DF2 and beng.run1 conventions.
Input layer only: dfctx.market(name) arrays r rf rb cpn idxup st_v1 vol20 (all <=2014). Run with cwd outside /mnt/project-files/research.
"""
import sys, json, math
import numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC          # input layer only (market arrays + DC.target for the cross-check)

OUTDIR = '/mnt/project-files/research/df1/verify/numbers/'
WARM = 300; DELAY = 2; COST = 0.003; TAX = 0.22; DED = 0.25; HTHR = 1.0
ER_T = 0.0245; ER_Q = 0.002; ER_B = 0.0015; ER_TB = 0.001; WHT = 0.154
KNEES = {'K1': (-0.10, -0.20), 'K2': (-0.15, -0.30)}; KFLOOR = 0.25
ASSETS = ('T', 'Q', 'B', 'TB')       # TQQQ-type, QQQ-type, 10y bond ETF, T-bill ETF (cash kept separately)

PICKS = {
    'tier25': dict(id='v1|s0.1|L1.0|K1|RB', src='grid', k='v1', sig=0.1, Lmax=1.0, knee='K1', ro='B', mapping='M0', lo=0.1, hi=0.25),
    'tier30': dict(id='v1|s0.2|L1.0|K1|RB', src='grid', k='v1', sig=0.2, Lmax=1.0, knee='K1', ro='B', mapping='M0', lo=0.1, hi=0.25),
    'tier40': dict(id='DF2|M2|b1|v1|s0.3|L1.5|K2|RB', src='grid_df2', k='v1', sig=0.3, Lmax=1.5, knee='K2', ro='B', mapping='M2', lo=0.1, hi=0.25),
}
MARKETS = ('real_ndx_86_14', 'real_spx_29_54', 'real_spx_55_85', 'JP', 'AU')


def my_vol20(r):
    """own vol20: population std (ddof 0) of log(1+r) over the 20 rows ending at t, x sqrt(252); NaN for the first 19 rows."""
    lr = np.log1p(r); out = np.full(len(r), np.nan)
    for t in range(19, len(r)): out[t] = np.std(lr[t - 19:t + 1]) * np.sqrt(252)
    return out


def my_target(st, vol, sig, Lmax):
    """pre-brake exposure, element by element: st 3 -> L_on, st 1 -> min(L_on, Lmax/3), else 0; L_on = min(Lmax, sig/vol20)."""
    out = np.zeros(len(st))
    for t in range(len(st)):
        if sig is None:
            lon = float(Lmax)
        else:
            lon = float('nan') if not math.isfinite(vol[t]) else min(float(Lmax), sig / max(vol[t], 1e-9))
        s = st[t]
        if s >= 3: L = lon
        elif s >= 1: L = float('nan') if math.isnan(lon) else min(lon, Lmax / 3.0)
        else: L = 0.0
        out[t] = 0.0 if math.isnan(L) else L
    return out


def mix(L, mapping):
    """exposure L (x NDX) -> weights {T, Q, RO}; remainder is cash."""
    if mapping == 'M0':
        if L <= 1.0: return {'T': 0.0, 'Q': L, 'RO': 1.0 - L}
        t = (L - 1.0) / 2.0
        return {'T': t, 'Q': 1.0 - t, 'RO': 0.0}
    if mapping == 'M2':
        return {'T': L / 3.0, 'Q': 0.0, 'RO': 1.0 - L / 3.0}
    raise ValueError(mapping)


def simulate(m, Ltg, mapping, lo, hi, knee, ro='B', harvest_order=('T', 'Q', 'B'), cpn_basis_post=False):
    r = m['r'][0]; rf = m['rf'][0]; rb = m['rb'][0]; cpn = m['cpn'][0]; iu = m['idxup'][0]
    T = len(r); d0, d1 = KNEES[knee]
    v = dict.fromkeys(ASSETS, 0.0); bs = dict.fromkeys(ASSETS, 0.0); cash = 0.0
    real = 0.0; held = 0.0; cur = None; cur_ro = None
    held_at = np.full(T, np.nan)
    E = 1.0; peak = 1.0; mdd = 0.0
    n = T - WARM
    rec = dict(E=np.zeros(n), want=np.zeros(n), tax=np.zeros(n), cost=np.zeros(n),
               pnl={a: np.zeros(n) for a in ASSETS}, w={a: np.zeros(n) for a in ASSETS}, wc=np.zeros(n), ntr=0,
               raw=np.zeros(n), mult=np.zeros(n), held=np.zeros(n))
    for t in range(T):
        if t >= WARM:
            k = t - WARM
            # (1) yearly tax on last year's net realised gains above the deduction, paid by proportional sale of everything
            if k > 0 and k % 252 == 0:
                due = TAX * max(real - DED, 0.0); real = 0.0
                if due > 0:
                    tot = sum(v.values()) + cash; f = min(due / tot, 1.0)
                    for a in ASSETS:
                        real += f * (v[a] - bs[a]); v[a] *= (1 - f); bs[a] *= (1 - f)
                    cash *= (1 - f); rec['tax'][k] += due
            # (2) execution queue: decision of close t-2 (first two days: the warm-up decision)
            want = held_at[max(t - DELAY, WARM - 1)]
            # (3) daily product returns
            if k > 0:
                g = v['T'] * (3 * r[t] - 2 * rf[t] - ER_T / 252); rec['pnl']['T'][k] = g; v['T'] += g
                g = v['Q'] * (r[t] - ER_Q / 252); rec['pnl']['Q'][k] = g; v['Q'] += g
                g = v['B'] * (rb[t] - ER_B / 252 - WHT * cpn[t])
                bs['B'] += (v['B'] + (g if cpn_basis_post else 0.0)) * cpn[t] * (1 - WHT)
                rec['pnl']['B'][k] = g; v['B'] += g
                y = rf[t] - ER_TB / 252
                if y > 0: y *= (1 - WHT)
                bs['TB'] += v['TB'] * y; rec['pnl']['TB'][k] = v['TB'] * y; v['TB'] *= (1 + y)
            # (4) rebalance when the executed level or the (relevant) risk-off asset changes
            w = mix(want, mapping)
            ro_now = ro if w['RO'] > 0 else None
            if cur is None or want != cur or ro_now != cur_ro:
                if k == 0: cash = 1.0
                tot = sum(v.values()) + cash
                tgt = dict.fromkeys(ASSETS, 0.0); tgt['T'] = w['T'] * tot; tgt['Q'] = w['Q'] * tot
                if ro_now is not None: tgt[ro_now] += w['RO'] * tot
                tc = 0.0
                for a in ASSETS:
                    d = tgt[a] - v[a]; tc += COST * abs(d)
                    if d < 0 and v[a] > 0:
                        fr = min(-d / v[a], 1.0); real += fr * (v[a] - bs[a]); bs[a] *= (1 - fr)
                    if d > 0: bs[a] += d
                sc = (tot - tc) / tot
                ctg = tot - sum(tgt.values())
                for a in ASSETS: v[a] = tgt[a] * sc
                cash = ctg * sc
                cur = want; cur_ro = ro_now; rec['ntr'] += 1; rec['cost'][k] += tc
            # (5) year-end harvest (beng rule, per product)
            if k % 252 == 251:
                for a in harvest_order:
                    if v[a] > 1e-12:
                        target = DED - real; U = v[a] - bs[a]; f = 0.0
                        if target < 0 and U < 0: f = min(1.0, target / U)
                        if target > 0 and U > 0: f = min(1.0, target / U)
                        rz = f * U; sv = f * v[a]
                        if sv > 0 and TAX * abs(rz) > HTHR * 2 * COST * sv:
                            tc = 2 * COST * sv; real += rz; bs[a] = bs[a] - (sv - rz) + (sv - tc); v[a] -= tc
                            rec['cost'][k] += tc
            E = sum(v.values()) + cash
            peak = max(peak, E); mdd = min(mdd, E / peak - 1.0)
            rec['E'][k] = E; rec['want'][k] = want
            for a in ASSETS: rec['w'][a][k] = v[a] / E
            rec['wc'][k] = cash / E
        # (6) decision at close t: knee on account drawdown, clip, quantise with hysteresis
        x = Ltg[t]
        if math.isnan(x): x = 0.0
        dd = E / peak - 1.0
        mult = min(max((dd - d1) / (d0 - d1), 0.0), 1.0)
        if iu[t] and mult < KFLOOR: mult = KFLOOR
        x = min(max(x * mult, 0.0), 3.0)
        step = hi if (x >= 1.0 or held >= 1.0) else lo
        if abs(x - held) >= step or (x == 0 and held > 0):
            held = float(np.round(x / step) * step)
        held_at[t] = held
        if t >= WARM: rec['raw'][t - WARM] = 0.0 if math.isnan(Ltg[t]) else Ltg[t]; rec['mult'][t - WARM] = mult; rec['held'][t - WARM] = held
    unr = sum(v[a] - bs[a] for a in ASSETS)
    fin = E - TAX * max(real + unr - DED, 0.0)
    yrs = (T - WARM) / 252.0
    cagr = max(fin, 1e-9) ** (1.0 / yrs) - 1.0
    return dict(cagr=cagr, mdd=mdd, fin=fin, ntr=rec['ntr'], rec=rec)


def date_of(m, k):
    c = m['ctx']; return str(m['X_index'][c.ii[0, WARM + k]].date())


def main():
    G = json.load(open('/mnt/project-files/research/df1/results/grid.json'))['configs']
    G2 = json.load(open('/mnt/project-files/research/df1/results/grid_df2.json'))['configs']
    res = dict(target_check={}, vol20_check={}, compare={}, sensitivity={}, gap={}, au_df2_dd={})
    maxdiff = 0.0
    for mk in MARKETS:
        m = DC.market(mk)
        # vol20 definition check (informational): annualised rolling std of r
        vv = m['vol20'][0]; myv = my_vol20(m['r'][0])
        res['vol20_check'][mk] = dict(max_abs_diff=float(np.nanmax(np.abs(vv - myv))), nan_rows_same=bool(np.array_equal(np.isnan(vv), np.isnan(myv))))
        for pk, P in PICKS.items():
            mine_L = my_target(m['st_v1'][0], myv, P['sig'], P['Lmax'])      # own vol20, input-layer st_v1
            dc_L = DC.target(m, P['k'], P['sig'], P['Lmax'])[0]
            res['target_check'].setdefault(pk, {})[mk] = float(np.max(np.abs(mine_L - dc_L)))
            o = simulate(m, mine_L, P['mapping'], P['lo'], P['hi'], P['knee'])
            st = (G if P['src'] == 'grid' else G2)[P['id']][mk]
            dc, dm = abs(o['cagr'] - st['cagr']), abs(o['mdd'] - st['mdd'])
            maxdiff = max(maxdiff, dc, dm)
            res['compare'].setdefault(pk, {})[mk] = dict(id=P['id'], mine_cagr=o['cagr'], stored_cagr=st['cagr'], abs_diff_cagr=dc,
                                                         mine_mdd=o['mdd'], stored_mdd=st['mdd'], abs_diff_mdd=dm,
                                                         mine_ntr=o['ntr'], stored_ntr=st.get('ntr'))
            # convention sensitivity (spec-ambiguous choices): harvest order, coupon-basis accrual on post-return value
            o2 = simulate(m, mine_L, P['mapping'], P['lo'], P['hi'], P['knee'], harvest_order=('B', 'Q', 'T'))
            o3 = simulate(m, mine_L, P['mapping'], P['lo'], P['hi'], P['knee'], cpn_basis_post=True)
            res['sensitivity'].setdefault(pk, {})[mk] = dict(harvest_bond_first_dcagr=o2['cagr'] - o['cagr'], harvest_bond_first_dmdd=o2['mdd'] - o['mdd'],
                                                             cpn_basis_post_dcagr=o3['cagr'] - o['cagr'], cpn_basis_post_dmdd=o3['mdd'] - o['mdd'])
            rec = o['rec']; E = rec['E']
            effx = 3 * rec['w']['T'] + rec['w']['Q']           # end-of-day effective NDX exposure after drift
            res.setdefault('drift_exposure', {}).setdefault(pk, {})[mk] = dict(max_eff=float(effx.max()), date_max=date_of(m, int(effx.argmax())),
                                                                             frac_days_eff_gt_Lmax=float(np.mean(effx > P['Lmax'] + 1e-9)))
            dr_all = E[1:] / E[:-1] - 1.0; jw = int(np.argmin(dr_all)) + 1
            res.setdefault('worst_day_all', {}).setdefault(pk, {})[mk] = dict(ret=float(dr_all[jw - 1]), date=date_of(m, jw),
                                                                            idx_ret=float(m['r'][0, WARM + jw]), eff_exposure_prev=float(effx[jw - 1]))
            if mk == 'real_ndx_86_14':
                dr = E[1:] / E[:-1] - 1.0; j = int(np.argmin(dr)) + 1
                notax = dr.copy(); notax[rec['tax'][1:] > 0] = np.inf; j2 = int(np.argmin(notax)) + 1
                res['gap'][pk] = dict(worst_day_ret=float(dr[j - 1]), k=j, row_t=WARM + j, date=date_of(m, j),
                                      ndx_ret=float(m['r'][0, WARM + j]), executed_L_during_day=float(rec['want'][j - 1]),
                                      w_prev={a: round(float(rec['w'][a][j - 1]), 4) for a in ASSETS},
                                      tax_paid_that_day=float(rec['tax'][j]),
                                      worst_non_tax_day=dict(ret=float(dr[j2 - 1]), k=j2, date=date_of(m, j2)))
            if mk == 'AU' and pk == 'tier40':
                pk_run = np.maximum.accumulate(E); dd = E / pk_run - 1; tr = int(np.argmin(dd)); p0 = int(np.argmax(E[:tr + 1]))
                rng = slice(p0 + 1, tr + 1); Ep = E[p0]
                contrib = {a: float(rec['pnl'][a][rng].sum() / Ep) for a in ASSETS}
                contrib.update(tax=float(-rec['tax'][rng].sum() / Ep), cost=float(-rec['cost'][rng].sum() / Ep))
                # recovery
                rec_k = next((kk for kk in range(tr, len(E)) if E[kk] >= Ep), None)
                wsum = lambda a, i: round(float(rec['w'][a][i]), 3)
                res['au_df2_dd'] = dict(mdd=float(dd[tr]), peak_k=p0, peak_date=date_of(m, p0), trough_k=tr, trough_date=date_of(m, tr),
                                        recovered_date=(date_of(m, rec_k) if rec_k is not None else None),
                                        contrib_frac_of_peak=contrib, sum_check=float(sum(contrib.values())), dd_check=float(E[tr] / Ep - 1),
                                        weights_at_peak={a: wsum(a, p0) for a in ASSETS}, weights_at_trough={a: wsum(a, tr) for a in ASSETS},
                                        L_exec_mean=float(rec['want'][rng].mean()), L_exec_max=float(rec['want'][rng].max()),
                                        days_L_ge1=int((rec['want'][rng] >= 1).sum()), n_days=int(tr - p0),
                                        index_ret=float(np.prod(1 + m['r'][0, WARM + p0 + 1:WARM + tr + 1]) - 1),
                                        bond_ret=float(np.prod(1 + m['rb'][0, WARM + p0 + 1:WARM + tr + 1]) - 1),
                                        trades=int((np.diff(rec['want'][p0:tr + 1]) != 0).sum()))
                # daily path of the episode (row labels are the input calendar's; AU has Sunday-stamped rows)
                ys = []
                for kk in range(p0, tr + 1):
                    ys.append(dict(date=date_of(m, kk), k=kk, idx_r=round(float(m['r'][0, WARM + kk]), 4), E_rel=round(float(E[kk] / Ep), 4),
                                   L_exec=float(rec['want'][kk]), wT=wsum('T', kk), wB=wsum('B', kk), raw_target=round(float(rec['raw'][kk]), 3),
                                   knee_mult=round(float(rec['mult'][kk]), 3), decided=float(rec['held'][kk])))
                res['au_df2_dd']['daily'] = ys
        print(mk, 'done', flush=True)
    res['max_abs_diff_all'] = maxdiff
    json.dump(res, open(OUTDIR + 'numbers.json', 'w'), indent=1, default=float)
    for pk in PICKS:
        for mk in MARKETS:
            c = res['compare'][pk][mk]
            print('%-7s %-15s cagr %.6f vs %.6f (d %.1e)  mdd %.6f vs %.6f (d %.1e)  ntr %d/%s' % (
                pk, mk, c['mine_cagr'], c['stored_cagr'], c['abs_diff_cagr'], c['mine_mdd'], c['stored_mdd'], c['abs_diff_mdd'], c['mine_ntr'], c['stored_ntr']))
    print('max abs diff', maxdiff)
    print('target check', res['target_check']); print('vol20', res['vol20_check'])
    print('gap', json.dumps(res['gap'], indent=1)); print('worst_all', json.dumps(res['worst_day_all'])); print('drift', json.dumps(res['drift_exposure']))
    print('au', json.dumps({k: v for k, v in res['au_df2_dd'].items() if k != 'daily'}, indent=1))
    for row in res['au_df2_dd']['daily']: print(row)


if __name__ == '__main__':
    main()
