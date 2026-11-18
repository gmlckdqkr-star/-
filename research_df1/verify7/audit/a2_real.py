"""DF7 audit step 2: REAL-world checks of panel7 conventions, product formulas, trend shift, F3 timing; synthetic dfk timing test.
<=2014 only (REAL = 1986-2014 single path)."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df7 as D, df5data as DD, df5lib as L, dfk
out = {}
# ---- pool dates and calendars
a, b, P_, blk, seed = L.iv.POOLS['dev250']; out['dev250_pool'] = [str(a), str(b), int(P_), int(blk)]
tr = D.trend_by_date()['tr']; out['trend_index'] = [str(tr.index.min().date()), str(tr.index.max().date()), int(len(tr))]
fnz = tr.ne(0).idxmax(); out['trend_first_nonzero'] = str(fnz.date())
w = L.world('REAL'); idx = w['S'].index; ii = w['ii']
out['REAL_S_index'] = [str(idx.min().date()), str(idx.max().date()), int(len(idx))]
d0 = idx[ii[0, D.WARM]]; out['REAL_first_eval_date'] = str(pd.Timestamp(d0).date()); out['REAL_T'] = int(ii.shape[1])
miss_w = idx.difference(tr.index); miss_t = tr.index.difference(idx)
out['world_dates_not_in_trend'] = int(len(miss_w[miss_w >= fnz])); out['trend_dates_not_in_world'] = int(len(miss_t[miss_t >= fnz]))
out['trend_nonzero_ret_lost_on_missing_world_dates'] = float(tr.reindex(miss_t[miss_t >= fnz]).abs().sum())
# pool (P/X) source calendar: same _src(a,b,'NDX')
Xp, Sp = L._src(a, b, 'NDX'); out['pool_S_index'] = [str(Sp.index.min().date()), str(Sp.index.max().date()), int(len(Sp))]
mp = Sp.index.difference(tr.index); out['pool_dates_not_in_trend_total'] = int(len(mp)); out['pool_dates_before_trend_first_nonzero'] = int((Sp.index < fnz).sum())
out['pool_dates_not_in_trend_after_fnz'] = int((mp >= fnz).sum())
# ---- panel conventions on REAL
rf = np.nan_to_num(w['m']['rf']); sel = np.zeros(rf.shape, bool); sel[:, D.WARM:] = True
base_n = DD.panel('REAL', raw=False); base_r = DD.panel('REAL', raw=True)
pans = {cv: D.panel7('REAL', cv) for cv in ('PRIM', 'Q', 'RAW', 'ZERO', 'HALF', 0.3, 1.0)}
TRs = {}
chk = {}
for cv, p in pans.items():
    raw, frac = D.conv_of(cv); base = base_r if raw else base_n
    TR = p['DBMF'][0] + 0.0085 / 252 - rf; TRs[str(cv)] = TR
    spx = base['SPX'][0] + 0.001 / 252; gold = base['GOLD'][0] + 0.004 / 252
    c = dict(raw=raw, frac=frac, meta=p['meta'],
             trend_mean_ann=float(TR[sel].mean() * 252), trend_std_ann=float(TR[sel].std() * np.sqrt(252)),
             ratio_to_proxy=float(TR[sel].mean() / (p['meta']['trend_mean_ann_proxy'] / 252)),
             TREND_vs_DBMF=float(np.abs(p['TREND'][0] - p['DBMF'][0] - 0.0085 / 252).max()),
             RSST_err=float(np.abs(p['RSST'][0] - (spx + TR - 0.0099 / 252)).max()), RSST_inc=float(p['RSST'][1] * 252),
             GDE_err=float(np.abs(p['GDE'][0] - (0.9 * spx + 0.1 * rf + 0.9 * (gold - rf) - 0.002 / 252)).max()), GDE_inc=float(p['GDE'][1] * 252),
             GLD_eq_panelGOLD=float(np.abs(p['GOLD'][0] - base['GOLD'][0]).max()),
             GOLD_gross_excess_ann=float((gold - rf)[sel].mean() * 252),
             LTT_eq_panel=float(np.abs(p['LTT'][0] - base['LTT'][0]).max()),
             LTT_gross_excess_ann=float((p['LTT'][0] + 0.0015 / 252 - rf)[sel].mean() * 252),
             QLD_err=float(np.abs(p['QLD'][0] - (2 * np.nan_to_num(w['m']['r']) - rf - 0.017 / 252)).max()),
             SPX_excess_ann=float((spx - rf)[sel].mean() * 252),
             HV={k: p[k][2] for k in ('DBMF', 'RSST', 'GDE', 'GOLD', 'LTT', 'QLD', 'TBILL')},
             same_obj_as_base={k: p[k] is base[k] for k in ('QLD', 'GOLD', 'LTT', 'TBILL', 'QQQ', 'B10')})
    chk[str(cv)] = c
# variance unchanged across conventions (same TR up to a constant)
dev = {k: float(np.abs((v - TRs['RAW']) - (v - TRs['RAW'])[sel].mean())[sel].max()) for k, v in TRs.items()}
out['panel'] = chk; out['TR_minus_RAW_nonconstant_max'] = dev
# ---- F3 timing on REAL (PRIM)
X = D.W7('REAL', 'PRIM'); C = {c['id']: c for c in D.configs()}
t2 = X.sig.T(200); m2 = X.sig.M(252)
lv = X.sig.lv; s200 = pd.Series(lv[0]).rolling(200).mean().values
t2chk = np.where(np.isnan(s200), False, lv[0] > s200)
out['T200_recompute_mismatch'] = int((t2chk != t2[0]).sum())
k252 = np.r_[np.full(252, np.nan), lv[0, 252:] / lv[0, :-252] - 1]; rfl = X.sig.rfl[0]; r252 = np.r_[np.full(252, np.nan), rfl[252:] / rfl[:-252] - 1]
m2chk = np.where(np.isnan(k252), False, k252 > r252); out['M252_recompute_mismatch'] = int((m2chk != m2[0]).sum())
f3 = {}
for cid in ('F3|T200|Q100|M100', 'F3|M252|Q50M50|BILL', 'F3|T200|Q50M50|MGT'):
    jb = D.job7(C[cid], X); _, ids, Wt, EV, kw = jb
    sig = (t2 if 'T200' in cid else m2)[0]
    flips = int(np.sum(sig[D.WARM:] != sig[D.WARM - 1:-1]))
    evn = int(EV[0, D.WARM:].sum())
    RET, INC, HV = DD.stack(X.pan, ids)
    o, _ = dfk.run(RET, INC, Wt, EV, HV, **kw)
    T = X.T; nk = T - D.WARM
    # expected trades: k=0, each EV day dec in [WARM, T-3] traded at dec+2, plus forced k%252==0 not coinciding
    trade_k = set([0]); evd = np.where(EV[0])[0]
    for d in evd:
        if d >= D.WARM and d + 2 < T: trade_k.add(d + 2 - D.WARM)
    for k in range(252, nk, 252): trade_k.add(k)
    f3[cid] = dict(ids=ids, reb_every=kw['reb_every'], signal_flips_eval=flips, EV_days_eval=evn, ntr_engine=float(o[0, 2]), ntr_expected=len(trade_k),
                   W_on=Wt[0, np.argmax(sig[D.WARM:]) + D.WARM].tolist(), W_off=Wt[0, np.argmin(sig[D.WARM:]) + D.WARM].tolist(),
                   W_matches_signal=bool(np.all((Wt[0, :, ids.index('QLD')] > 0) == sig)))
out['F3'] = f3
# static config: EV only at WARM-1, forced trades every 252
c = C['F2|q0.3|r0.2|g0.3|m0.2']; _, ids, Wt, EV, kw = D.job7(c, X)
RET, INC, HV = DD.stack(X.pan, ids); o, _ = dfk.run(RET, INC, Wt, EV, HV, **kw)
out['static_P2'] = dict(ids=ids, w=Wt[0, 0].tolist(), EV_true_at=np.where(EV[0])[0].tolist(), reb_every=kw['reb_every'], ntr=float(o[0, 2]),
                        expected=1 + len(range(252, X.T - D.WARM, 252)))
# ---- synthetic dfk timing test: 2 assets, switch target at decision day d; check the day the new weights earn returns
T = 340; K = 2; RET = np.zeros((1, T, K)); INC = np.zeros((1, T, K)); HV = np.array([0, 0])
d = 310; W = np.zeros((1, T, K)); W[0, :, 0] = 1.0; W[0, d:, 0] = 0.0; W[0, d:, 1] = 1.0
EV = np.zeros((1, T), bool); EV[0, D.WARM - 1] = True; EV[0, d] = True
res = {}
for day in range(d, d + 5):
    R2 = RET.copy(); R2[0, day, 1] = 0.10
    o, E = dfk.run(R2, INC, W, EV, HV, recon=True, cost=0.0, tax=0.0, harvest=0)
    res[day - d] = float(o[0, 5] - 1)
out['synthetic_asset1_gain_by_day_offset_from_decision'] = res      # gain shows only if held: decision d -> trade close d+2 -> first return d+3
# forced rebalance with reb_every: weights drift then reset at k%252==0
T = D.WARM + 600; RET = np.zeros((1, T, 2)); RET[0, D.WARM + 10, 0] = 1.0       # asset0 doubles early
W = np.full((1, T, 2), 0.5); EV = np.zeros((1, T), bool); EV[0, D.WARM - 1] = True
o, E = dfk.run(RET, np.zeros_like(RET), W, EV, np.array([0, 0]), recon=True, cost=0.0, tax=0.0, harvest=0, reb_every=252)
out['synthetic_reb_every_ntr'] = float(o[0, 2])
json.dump(out, open('/tmp/df7v_audit/a2_out.json', 'w'), indent=1, default=str)
print(json.dumps(out, indent=1, default=str)[:12000])
