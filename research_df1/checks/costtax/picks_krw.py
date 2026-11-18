"""Picks + references under every cost/tax/bond variant, plus KRW-terms drawdown/CAGR (FRED DEXKOUS raw, <=2014 rows).
Writes checks/costtax/picks_krw.json. Synthetic bonds (10y, 7y rebuild) NON-ACTUAL; path-KRW (bootstrapped FX) NON-ACTUAL."""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/checks/costtax')
import ctlib as CT, dfctx as DC, dfe, run_grid as RG, run_df2 as R2, std
OUT = '/mnt/project-files/research/df1/checks/costtax/'
W = CT.W
PICKS = {'T25': 'v1|s0.1|L1.0|K1|RB', 'T30': 'v1|s0.2|L1.0|K1|RB', 'T40': 'DF2|M2|b1|v1|s0.3|L1.5|K2|RB', 'T40_gatefix': 'v1|s0.3|L1.0|K2|RB'}
C = CT.all_configs()

def run_rec(cfg, m, **kw):
    if cfg['fam'] == 'df2':
        L = DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax']); k = dict(RG.KNEES[cfg['knee']])
        k.update(step_lo=R2.BANDS[cfg['band']][0], step_hi=R2.BANDS[cfg['band']][1], vmode=0 if cfg['M'] == 'M0' else 2); k.update(kw)
        return dfe.run(m, L, recon=True, roff=RG.ROFF[cfg['roff']], **k)
    L = DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax']); k = dict(RG.KNEES[cfg['knee']]); k.update(kw)
    return dfe.run(m, L, recon=True, roff=RG.ROFF[cfg['roff']], **k)

def kstats(EE, fin, rel, prepend):
    if prepend:
        EE = np.c_[np.ones(EE.shape[0]), EE]; rel = np.c_[np.ones(rel.shape[0]), rel]
    yrs = (EE.shape[1] - (1 if prepend else 0)) / 252
    Ek = EE * rel
    mdk = (Ek / np.maximum.accumulate(Ek, axis=1) - 1).min(axis=1); mdu = (EE / np.maximum.accumulate(EE, axis=1) - 1).min(axis=1)
    cgk = np.maximum(fin * rel[:, -1], 1e-9) ** (1 / yrs) - 1; cgu = np.maximum(fin, 1e-9) ** (1 / yrs) - 1
    return cgu, mdu, cgk, mdk

t0 = time.time()
# ---- FX alignment
mn = DC.market('real_ndx_86_14'); Xn = CT.getX('real_ndx_86_14'); ii_n = mn['ctx'].ii[0]
dn = Xn.index[ii_n[W:]]; fxn, nfill_n = CT.fx_on(dn); rel_n = (fxn / fxn[0])[None, :]
mp = DC.market('dev250_path'); Xp = CT.getX('dev250_path'); ii_p = mp['ctx'].ii
fxp, nfill_p = CT.fx_on(Xp.index); fr = np.r_[0.0, fxp[1:] / fxp[:-1] - 1]
frp = fr[ii_p]; frp[:, 0] = 0.0; lv = np.cumprod(1 + frp, axis=1); rel_p = lv[:, W:] / lv[:, W:W + 1]
fxinfo = dict(source='FRED DEXKOUS raw (KRW per USD), rows <= 2014-12-31, last obs <= day (A10-1 rule); quality gate A10-1 FAIL -> used as stress version (A10-4)',
              ndx_first=str(dn[0].date()), ndx_last=str(dn[-1].date()), fx_first=float(fxn[0]), fx_last=float(fxn[-1]), fx_min=float(fxn.min()), fx_max=float(fxn.max()),
              fx_min_date=str(dn[int(np.argmin(fxn))].date()), fx_max_date=str(dn[int(np.argmax(fxn))].date()), filled_days_ndx=int(nfill_n), filled_days_path_cal=int(nfill_p),
              usd_in_krw_mdd=float((fxn / np.maximum.accumulate(fxn) - 1).min()), usd_in_krw_cagr=float((fxn[-1] / fxn[0]) ** (252 / (len(fxn) - 1)) - 1),
              path_fx_cagr_median=float(np.median(rel_p[:, -1] ** (252 / (rel_p.shape[1] - 1)) - 1)))
print('fx', fxinfo, flush=True)

# v1 decision inputs (independent of cost/tax/bond variants)
V1B = {b: std.s085(DC.market(b)['ctx']) for b in CT.SELM}

res = dict(fx=fxinfo, picks=PICKS, rows={})
for vn, (n, kw, v1kw) in CT.VARIANTS.items():
    mk = CT.markets(vn)
    strat = dict(PICKS); strat['hold1x_QQQ'] = None; strat['v1_s085'] = None
    for sname, cid in strat.items():
        r = {}
        for b in CT.SELM:
            m = mk[b]; T = m['r'].shape[1]; path = b == 'dev250_path'
            if sname == 'v1_s085':
                B, bfn, bp, fs = V1B[b]; cg, EE = std.engine(m['ctx'], B, bfn, bp, fs, cspr=10.0, **v1kw)
                fin = (1 + cg) ** (EE.shape[1] / 252); prepend = False
                md = (EE / np.maximum.accumulate(EE, axis=1) - 1).min(axis=1)
            else:
                if sname == 'hold1x_QQQ': o, EE = dfe.run(m, np.full(m['r'].shape, 1.0), recon=True, **kw)
                else:
                    o, EE = run_rec(C[cid], m, **kw)
                    o2 = R2.run_cfg(C[cid], m, **kw); assert np.array_equal(o, o2)
                cg, md = dfe.stats(o, T); fin = o[:, 0]; prepend = True
            if path: r[b] = dict(cagr=float(np.median(cg)), mdd_p10=float(np.percentile(md, 10)), mdd_med=float(np.median(md)))
            else: r[b] = dict(cagr=float(cg[0]), mdd=float(md[0]))
            if b != 'real_spx_29_54':
                rel = rel_n if b == 'real_ndx_86_14' else rel_p
                cgu, mdu, cgk, mdk = kstats(EE, fin, rel, prepend)
                assert np.allclose(mdu, md, atol=1e-9), (sname, b, float(np.abs(mdu - md).max()))
                if path: r[b].update(krw_cagr=float(np.median(cgk)), krw_mdd_p10=float(np.percentile(mdk, 10)), krw_mdd_med=float(np.median(mdk)))
                else:
                    r[b].update(krw_cagr=float(cgk[0]), krw_mdd=float(mdk[0]))
                    Ek = np.r_[1.0, EE[0] * rel_n[0]] if prepend else EE[0] * rel_n[0]
                    dd = Ek / np.maximum.accumulate(Ek) - 1; j = int(np.argmin(dd)); pk = int(np.argmax(Ek[:j + 1]))
                    off = 1 if prepend else 0
                    r[b].update(krw_mdd_peak=str(dn[max(pk - off, 0)].date()), krw_mdd_trough=str(dn[max(j - off, 0)].date()))
                    Eu = np.r_[1.0, EE[0]] if prepend else EE[0]; du = Eu / np.maximum.accumulate(Eu) - 1; ju = int(np.argmin(du)); pu = int(np.argmax(Eu[:ju + 1]))
                    r[b].update(usd_mdd_peak=str(dn[max(pu - off, 0)].date()), usd_mdd_trough=str(dn[max(ju - off, 0)].date()))
        r['wd'] = min(r['dev250_path']['mdd_p10'], r['real_ndx_86_14']['mdd'], r['real_spx_29_54']['mdd'])
        r['wd_krw'] = min(r['dev250_path']['krw_mdd_p10'], r['real_ndx_86_14']['krw_mdd'], r['real_spx_29_54']['mdd'])
        res['rows']['%s|%s' % (sname, vn)] = r
        print('%-10s %-12s path %.4f p10mdd %.4f | ndx %.4f/%.4f | spx29 %.4f/%.4f | WD %.4f | KRW ndx %.4f/%.4f path %.4f/%.4f WDkrw %.4f' % (
            vn, sname, r['dev250_path']['cagr'], r['dev250_path']['mdd_p10'], r['real_ndx_86_14']['cagr'], r['real_ndx_86_14']['mdd'],
            r['real_spx_29_54']['cagr'], r['real_spx_29_54']['mdd'], r['wd'], r['real_ndx_86_14']['krw_cagr'], r['real_ndx_86_14']['krw_mdd'],
            r['dev250_path']['krw_cagr'], r['dev250_path']['krw_mdd_p10'], r['wd_krw']), flush=True)
json.dump(res, open(OUT + 'picks_krw.json', 'w'), indent=1)
print('done %.0fs' % (time.time() - t0))
