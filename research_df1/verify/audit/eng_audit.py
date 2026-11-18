"""AUDIT engine/leakage checks for DF1/DF2 (<=2014 inputs only; prints only diffs/booleans, few dev numbers).
 A  data checks: date range, cpn == carry part of mkt.bond10, rb == source rb, bondup / idxup recomputed, st_v1 == bk.C3sig
 B  causality: perturb every input after day j0 -> all signals and the engine equity up to j0 unchanged; delay test (t+2)
 C  independent reference engine (pure python, written from PRECOMMIT_DF1 s1 / DF2 + beng conventions) vs dfe
Usage: python -B eng_audit.py OUT.json"""
import sys, os, json, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2
import std, ov, jp, mkt, bk
import px1lib as PX, lh1run as LH
W = dfe.WARM
OUT = {}
def neq(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    return int(np.sum(~((a == b) | (np.isnan(a) & np.isnan(b)))))

# ------------------------------------------------------------------ A. data checks
A = {}
for bn in ('real_ndx_86_14', 'real_spx_29_54', 'real_spx_55_85', 'UK', 'JP', 'AU', 'dev250_path'):
    m = DC.market(bn); c = m['ctx']; d = {}
    d['X_index_max'] = str(pd.Timestamp(m['X_index'].max()).date()); d['le_2014'] = bool(m['X_index'].max() <= pd.Timestamp('2014-12-31'))
    if bn == 'real_spx_29_54': d['le_1954'] = bool(m['X_index'].max() <= pd.Timestamp('1954-12-31'))
    ii = c.ii
    d['ii_max_lt_len'] = bool(ii.max() < len(m['X_index']))
    # rebuild X the same way to get y10 / rb columns
    if bn in ('real_ndx_86_14',):
        X = jp.mkX(*jp.calendar('1984-01-03', '2014-12-31'), 'NDX')
    elif bn == 'dev250_path':
        a, b, P, blk, seed = __import__('iv').POOLS['dev250']; X = jp.mkX(*jp.calendar(a, b), 'NDX')
    elif bn.startswith('real_spx_55') :
        X = jp.mkX(*jp.calendar('1928-01-03', '1985-12-31'), 'SPX')
    elif bn == 'real_spx_29_54':
        X = LH.build(LH.END, 'A')
    else:
        X, _ = PX.build(bn)
    y = X['y10'].values / 100.0
    carry = np.r_[np.nan, y[:-1]] / 252.0                       # mkt.bond10 coupon part y_{t-1}/252 on source rows
    cp_exp = np.nan_to_num(carry[ii], nan=0.0); cp_exp[:, 0] = 0.0
    d['cpn_vs_bond10_carry_maxabs'] = float(np.max(np.abs(m['cpn'] - cp_exp)))
    rb_exp = np.nan_to_num(X['rb'].values[ii], nan=0.0); rb_exp[:, 0] = 0.0
    d['rb_vs_source_maxabs'] = float(np.max(np.abs(m['rb'] - rb_exp)))
    # carry part really is the coupon inside rb: rb - carry = -D dy + .5 C dy^2 -> zero on days with dy == 0
    dy0 = np.r_[0.0, np.diff(y)][ii] == 0
    d['rb_eq_cpn_on_dy0_days_maxabs'] = float(np.max(np.abs((m['rb'] - m['cpn'])[:, 1:][dy0[:, 1:]]))) if dy0[:, 1:].any() else None
    bl = np.cumprod(1 + m['rb'], axis=1); sm = pd.DataFrame(bl.T).rolling(200).mean().values.T
    bu = np.where(np.isnan(sm), False, bl > sm); d['bondup_mismatch'] = neq(bu, m['bondup'])
    lv = np.cumprod(1 + np.where(np.arange(c.T)[None, :] == 0, 0.0, c.r), axis=1); s2 = pd.DataFrame(lv.T).rolling(200).mean().values.T
    iu = np.where(np.isnan(s2), False, lv > s2); d['idxup_mismatch'] = neq(iu, m['idxup'])
    d['st_v1_vs_C3sig_mismatch'] = neq(m['st_v1'], bk.C3sig(c))
    d['st_values'] = sorted(set(np.unique(m['st_v1'][:, W:]).tolist()) | set(np.unique(m['st_al'][:, W:]).tolist()))
    d['n_days_scored'] = int(c.T - W); d['P'] = int(c.P)
    A[bn] = d; print('A', bn, d, flush=True)
OUT['A_data'] = A

# ------------------------------------------------------------------ B. causality
def ctx_ndx(X):
    i0 = X.index.searchsorted(pd.Timestamp('1986-01-02')) - ov.WARM
    c = ov.Ctx(X, ov.flags_hist(X), np.arange(i0, len(X))[None, :]); return DC._finish(c, X), i0
def ctx_lh(X):
    c = ov.Ctx(X, ov.flags_hist(X), np.arange(0, len(X))[None, :]); return DC._finish(c, X), 0
def ctx_px(X, i0):
    c = PX.ctx(X, i0); return DC._finish(c, X), i0
def perturb(X, j0, seed, px=False):
    g = np.random.default_rng(seed); X2 = X.copy(); n = len(X2) - j0 - 1
    X2.iloc[j0 + 1:, X2.columns.get_loc('r')] = g.normal(0, 0.03, n)
    for col, sc in (('y10', 0.5), ('y3m', 0.5), ('cs', 0.2)):
        if col in X2: X2.iloc[j0 + 1:, X2.columns.get_loc(col)] = X2[col].values[j0 + 1:] + np.cumsum(g.normal(0, sc, n))
    if px: X2['rf'] = X2['y3m'] / 100 / 252
    else: X2.iloc[j0 + 1:, X2.columns.get_loc('rf')] = np.abs(g.normal(0.0002, 0.0001, n))
    X2['rb'] = mkt.bond10(X2); X2['p'] = (1 + X2['r']).cumprod()
    return X2
CFGS = [dict(fam='grid', k='v1', sig=0.1, Lmax=1.0, knee='K1', roff='RB'), dict(fam='grid', k='always', sig=None, Lmax=3.0, knee='K2', roff='RBT'),
        dict(fam='df2', M='M2', band='b1', k='v1', sig=0.3, Lmax=1.5, knee='K2', roff='RB'), dict(fam='df2', M='M2', band='b3', k='always', sig=0.2, Lmax=3.0, knee='K1', roff='RBT'),
        dict(fam='static', w=0.5)]
def tgt(m, cfg):
    if cfg['fam'] == 'static': return np.full(m['r'].shape, cfg['w'])
    return DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax'])
def kw_of(cfg):
    if cfg['fam'] == 'static': return dict(roff=2, reb_every=252)
    kw = dict(RG.KNEES[cfg['knee']]); kw['roff'] = RG.ROFF[cfg['roff']]
    if cfg['fam'] == 'df2': kw.update(step_lo=R2.BANDS[cfg['band']][0], step_hi=R2.BANDS[cfg['band']][1], vmode=0 if cfg['M'] == 'M0' else 2)
    return kw
B = {}
XN = jp.mkX(*jp.calendar('1984-01-03', '2014-12-31'), 'NDX'); XL = LH.build(LH.END, 'A'); XJ, iJ = PX.build('JP')
for nm, X, mk, px in (('real_ndx_86_14', XN, ctx_ndx, False), ('real_spx_29_54', XL, ctx_lh, False), ('JP', XJ, lambda X: ctx_px(X, iJ), True)):
    m, i0 = mk(X)
    ref = DC.market(nm)
    same_as_dc = {k: neq(m[k], ref[k]) for k in ('r', 'rf', 'rb', 'cpn', 'idxup', 'bondup', 'st_v1', 'st_al', 'vol20')}
    for frac in (0.35, 0.7):
        j0 = int(i0 + W + frac * (len(X) - i0 - W)); t0 = j0 - i0
        X2 = perturb(X, j0, 11, px); m2, _ = mk(X2)
        sig = {k: neq(m[k][:, :t0 + 1], m2[k][:, :t0 + 1]) for k in ('r', 'rf', 'rb', 'cpn', 'idxup', 'bondup', 'st_v1', 'st_al', 'vol20')}
        sig_after_changed = {k: neq(m[k][:, t0 + 1:], m2[k][:, t0 + 1:]) for k in ('r', 'rb', 'st_v1', 'vol20')}
        eng = {}
        for cfg in CFGS:
            L1 = tgt(m, cfg); L2 = tgt(m2, cfg); kw = kw_of(cfg)
            _, E1 = dfe.run(m, L1, recon=True, **kw); _, E2 = dfe.run(m2, L2, recon=True, **kw)
            dif = np.nonzero(np.abs(E1[0] - E2[0]) > 0)[0]
            eng[str(cfg)] = dict(L_prefix_mismatch=neq(L1[:, :t0 + 1], L2[:, :t0 + 1]), E_prefix_maxabs=float(np.max(np.abs(E1[0, :t0 - W + 1] - E2[0, :t0 - W + 1]))),
                                 first_E_diff_minus_t0=int(dif[0] - (t0 - W)) if len(dif) else None)
        B['%s|frac%.2f' % (nm, frac)] = dict(signals_prefix_mismatch=sig, after_changed=sig_after_changed, engine=eng)
    # delay test: change the pre-brake target from day t1 on -> E identical through t1+1, first difference at t1+2 (rebalance cost)
    dl = {}
    for cfg in CFGS[:4]:
        L1 = tgt(m, cfg); kw = kw_of(cfg); kw['kon'] = 0
        _, E1 = dfe.run(m, L1, recon=True, **kw)
        res = []
        for t1 in range(W + 800, m['r'].shape[1] - 10, 997):
            L2 = L1.copy(); L2[:, t1:] = np.where(L1[:, t1:] > 0.5, 0.0, 3.0)
            _, E2 = dfe.run(m, L2, recon=True, **kw); dif = np.nonzero(np.abs(E1[0] - E2[0]) > 0)[0]
            res.append(int(dif[0] - (t1 - W)) if len(dif) else None)
        dl[str(cfg)] = res
    B['%s|delay_first_diff_offsets' % nm] = dl
    B['%s|rebuilt_equals_dfctx' % nm] = same_as_dc
    print('B', nm, json.dumps({k: v for k, v in B.items() if k.startswith(nm)}, default=str)[:3000], flush=True)
OUT['B_causality'] = B

# ------------------------------------------------------------------ C. independent reference engine
NM = ('T', 'Q', 'B', 'S')
def ref_run(r, rf, rb, cpn, iu, bu, Lt, P):
    T = len(r); delay = P['delay']; cost = P['cost']; tax = P['tax']; D = P['D']
    val = dict.fromkeys(NM, 0.0); bas = dict.fromkeys(NM, 0.0); cash = 0.0; real = 0.0
    E = 1.0; peak = 1.0; mdd = 0.0; held = 0.0; dec = [None] * T; cur = None; cura = None; ntr = 0
    for t in range(T):
        if t >= W:
            k = t - W
            if k > 0 and k % 252 == 0:                       # yearly 22% tax on last year's net realised gain over D, proportional sale
                due = tax * max(real - D, 0.0); real = 0.0
                if due > 0:
                    tot = sum(val.values()) + cash; f = min(due / tot, 1.0)
                    for n in NM: real += f * (val[n] - bas[n]); val[n] *= 1 - f; bas[n] *= 1 - f
                    cash *= 1 - f
            L, a = dec[max(t - delay, W - 1)]
            if k > 0:
                val['T'] *= 1 + 3 * r[t] - 2 * rf[t] - P['er3'] / 252
                val['Q'] *= 1 + r[t] - P['erq'] / 252
                bas['B'] += val['B'] * cpn[t] * (1 - 0.154); val['B'] *= 1 + rb[t] - P['erb'] / 252 - 0.154 * cpn[t]
                y = rf[t] - P['ertb'] / 252; y = y * (1 - 0.154) if y > 0 else y
                bas['S'] += val['S'] * y; val['S'] *= 1 + y
                cash *= 1 + max(rf[t] - P['cspr'] / 252, 0.0) * (1 - 0.154)
            w = dict.fromkeys(NM, 0.0)
            if P['vmode'] == 2: w['T'] = L / 3; rest = 1 - L / 3
            elif L <= 1: w['Q'] = L; rest = 1 - L
            else: w['T'] = (L - 1) / 2; w['Q'] = 1 - w['T']; rest = 0.0
            eff = a if rest > 0 else None
            if a is not None: w[a] = rest
            forced = P['reb_every'] > 0 and k > 0 and k % P['reb_every'] == 0
            if k == 0 or L != cur or eff != cura or forced:
                if k == 0: tot = 1.0; cash = 1.0
                else: tot = sum(val.values()) + cash
                tc = 0.0; new = {}
                for n in NM:
                    tg = w[n] * tot; d = tg - val[n]; tc += cost * abs(d)
                    if d < 0 and val[n] > 0:
                        fr = min(-d / val[n], 1.0); real += fr * (val[n] - bas[n]); bas[n] *= 1 - fr
                    if d > 0: bas[n] += d
                    new[n] = tg
                sc = (tot - tc) / tot
                cash = (tot - sum(new.values())) * sc
                for n in NM: val[n] = new[n] * sc
                cur = L; cura = eff; ntr += 1
            if k % 252 == 251:                                   # year-end harvest to D, asset by asset (T, Q, bond)
                for n in ('T', 'Q', 'B'):
                    if val[n] > 1e-12:
                        tgt_ = D - real; U = val[n] - bas[n]; f = 0.0
                        if tgt_ < 0 and U < 0: f = min(1.0, tgt_ / U)
                        if tgt_ > 0 and U > 0: f = min(1.0, tgt_ / U)
                        rz = f * U; sv = f * val[n]
                        if sv > 0 and tax * abs(rz) > 2 * cost * sv:
                            tc = 2 * cost * sv; real += rz; bas[n] = bas[n] - (sv - rz) + (sv - tc); val[n] -= tc
            E = sum(val.values()) + cash; peak = max(peak, E); mdd = min(mdd, E / peak - 1)
        tg = Lt[t]; tg = 0.0 if np.isnan(tg) else tg
        if P['kon']:
            mm = min(max((E / peak - 1 - P['d1']) / (P['d0'] - P['d1']), 0.0), 1.0)
            if iu[t] and mm < P['kfl']: mm = P['kfl']
            tg *= mm
        tg = min(max(tg, 0.0), 3.0)
        stp = P['step_hi'] if (tg >= 1.0 or held >= 1.0) else P['step_lo']
        if abs(tg - held) >= stp or (tg == 0 and held > 0): held = float(np.round(tg / stp) * stp)
        ro = P['roff']; a = None if ro == 0 else ('S' if ro == 1 else ('B' if ro == 2 else ('B' if bu[t] else 'S')))
        dec[t] = (held, a)
    unr = sum(val[n] - bas[n] for n in NM)
    return E - tax * max(real + unr - D, 0.0), mdd, ntr
C = {}
CF2 = CFGS + [dict(fam='grid', k='v1', sig=0.2, Lmax=1.0, knee='K1', roff='RB'), dict(fam='grid', k='v1', sig=0.15, Lmax=2.0, knee='K0', roff='RT'),
              dict(fam='grid', k='always', sig=0.3, Lmax=1.5, knee='K1', roff='RC'), dict(fam='df2', M='M0', band='b2', k='v1', sig=0.2, Lmax=3.0, knee='K2', roff='RBT'),
              dict(fam='static', w=0.3)]
for bn in ('real_ndx_86_14', 'real_spx_29_54', 'JP', 'real_spx_70_85'):
    m = DC.market(bn); rows = {}
    for cfg in CF2:
        L = tgt(m, cfg); kw = kw_of(cfg); P = dict(dfe.DEF); P.update(kw)
        o, _ = dfe.run(m, L, **kw)
        for extra in ({}, dict(cost=0.006), dict(delay=3), dict(cspr=0.02)):
            P2 = dict(P); P2.update(extra); o2 = o if not extra else dfe.run(m, L, **dict(kw, **extra))[0]
            f, md, nt = ref_run(m['r'][0], m['rf'][0], m['rb'][0], m['cpn'][0], m['idxup'][0], m['bondup'][0], L[0], P2)
            rows['%s|%s' % (cfg, extra)] = dict(fin_absdiff=abs(f - o2[0, 0]), fin_reldiff=abs(f / o2[0, 0] - 1), mdd_absdiff=abs(md - o2[0, 1]), ntr_diff=nt - o2[0, 4])
    mx = dict(fin_reldiff=max(v['fin_reldiff'] for v in rows.values()), mdd_absdiff=max(v['mdd_absdiff'] for v in rows.values()),
              ntr_absdiff=max(abs(v['ntr_diff']) for v in rows.values()))
    C[bn] = dict(max=mx, n=len(rows)); print('C', bn, mx, flush=True)
OUT['C_reference_engine'] = C
json.dump(OUT, open(sys.argv[1], 'w'), indent=1, default=str)
