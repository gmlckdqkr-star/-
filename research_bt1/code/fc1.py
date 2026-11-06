"""FC1 forecast-combination lane (PRECOMMIT_FC1, sha256 9cfc7ee8...). 72 pre-registered variants.
stage 'disc'   : discovery stats only (D matrix, SPA/RW/DSR, frozen ranking) -> out/fc1/disc.json
stage 'confirm': one-time 2000-2014 confirmation of the frozen top-5, G1, MS1 of #1 -> out/fc1/confirm.json"""
import os, sys, json, time, itertools, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m1_data as DT, m1_atoms as MA, m1_stats as ST, bt1_evaldec as EV
SCR = MA.SCR; OUT = SCR + 'out/fc1/'; os.makedirs(OUT, exist_ok=True)
MINREG, MINERR, MINPCT, THETA, MINPRED = 120, 60, 60, 0.9, 5
SETS = ('P_new', 'P_all', 'P_allx'); COMBS = ('mean', 'median', 'dmspe'); SCORES = ('S1', 'S2'); MAPS = ('Q1', 'Q2', 'Q3', 'Q4')


def monthly():
    R, M = DT.cal(); idx = R.index
    pos = pd.Series(np.arange(len(idx)), index=idx)
    me = pos.groupby([idx.year, idx.month]).max().values                       # month-end positions
    ld = np.log1p(R['SPX'].fillna(0.0).values) - np.log1p(M['rf'].values)
    cs = np.r_[0.0, np.cumsum(ld)]
    y = np.r_[np.nan, cs[me[1:] + 1] - cs[me[:-1] + 1]]                          # month m excess log return (S&P TR)
    X = {}
    for f, mf in (('prim.npz', 'prim_meta.json'), ('prim_bt1.npz', 'prim_bt1_meta.json')):
        z = np.load(SCR + 'cache/' + f); meta = json.load(open(SCR + 'cache/' + mf))
        for k, m in meta.items():
            if k in MA.DROP: continue
            v = z[k].astype(float)[me]
            if m['kind'] == 'pos': v = np.log(np.where(v > 0, v, np.nan))
            X[k] = (v, f == 'prim_bt1.npz')
    lsp = np.r_[0.0, np.cumsum(np.log1p(R['SPX'].fillna(0.0).values))][1:]
    lv = lsp[me]
    X['px_mom12'] = (np.r_[np.full(12, np.nan), lv[12:] - lv[:-12]], False)
    X['px_r1'] = (np.r_[np.nan, lv[1:] - lv[:-1]], False)
    rv = pd.Series(np.log1p(R['SPX'].fillna(0.0).values)).rolling(252).std().values * np.sqrt(252)
    X['px_rv252'] = (np.log(rv[me]), False)
    own = {}
    for e in ('spx', 'ndx'):
        r = np.log1p(MA.own_index(R, e)); own[e] = (pd.Series(r).rolling(252).var().values * 21)[me]
    dates = idx[me]
    return idx, me, dates, y, X, own


def forecasts(x, y):
    """expanding OLS of y[k+1] on x[k] using k+1 <= m; forecast f[m] = a + b x[m]; DMSPE discounted MSE phi[m], count."""
    n = len(x); y1 = np.r_[y[1:], np.nan]
    v = np.isfinite(x) & np.isfinite(y1)
    xv = np.where(v, x, 0.0); yv = np.where(v, y1, 0.0)
    c = lambda a: np.r_[0.0, np.cumsum(a)][:n]                                   # sums over k <= m-1
    N = c(v.astype(float)); Sx = c(xv); Sy = c(yv); Sxx = c(xv * xv); Sxy = c(xv * yv)
    with np.errstate(all='ignore'):
        mx = Sx / N; my = Sy / N; vx = Sxx / N - mx * mx; cxy = Sxy / N - mx * my
        b = np.where(vx > 1e-18, cxy / vx, 0.0)
        f = my + b * (x - mx)
    f[~((N >= MINREG) & np.isfinite(x))] = np.nan
    # DMSPE: errors e[s] = y[s+1] - f[s], usable at m when s <= m-1
    e2 = (y1 - f) ** 2; ev = np.isfinite(e2)
    num = np.zeros(n); den = np.zeros(n); cnt = np.zeros(n)
    for m in range(1, n):
        num[m] = THETA * num[m - 1] + (e2[m - 1] if ev[m - 1] else 0.0)
        den[m] = THETA * den[m - 1] + (1.0 if ev[m - 1] else 0.0)
        cnt[m] = cnt[m - 1] + (1 if ev[m - 1] else 0)
    with np.errstate(all='ignore'):
        phi = np.where(cnt >= MINERR, num / den, np.nan)
    return f, phi


def combine(F, PHI, how):
    """F, PHI: (k, n). -> combined forecast (n,) (NaN when < MINPRED usable predictors)."""
    ok = np.isfinite(F); n = F.shape[1]; out = np.full(n, np.nan)
    if how == 'dmspe':
        ok = ok & np.isfinite(PHI) & (PHI > 0)
    for m in range(n):
        j = ok[:, m]
        if j.sum() < MINPRED: continue
        f = F[j, m]
        if how == 'mean': out[m] = f.mean()
        elif how == 'median': out[m] = np.median(f)
        else:
            w = 1.0 / PHI[j, m]; out[m] = (w * f).sum() / w.sum()
    return out


def pct(s):
    """expanding percentile vs strictly-past finite scores (>= MINPCT of them)."""
    p = np.full(len(s), np.nan); past = []
    for m in range(len(s)):
        if np.isfinite(s[m]) and len(past) >= MINPCT:
            a = np.asarray(past); p[m] = float((a <= s[m]).mean())
        if np.isfinite(s[m]): past.append(s[m])
    return p


def mapq(p, q):
    c = np.full(len(p), 2, np.int64); ok = np.isfinite(p)
    if q == 'Q1': c[ok] = np.where(p[ok] >= .5, 0, 2)
    elif q == 'Q2': c[ok] = np.where(p[ok] >= .7, 0, np.where(p[ok] >= .3, 2, 3))
    elif q == 'Q3': c[ok] = np.where(p[ok] >= .5, 0, 3)
    else: c[ok] = np.where(p[ok] >= .7, 0, np.where(p[ok] >= .3, 2, np.where(p[ok] >= .1, 3, 4)))
    return c, ~ok


def build():
    idx, me, dates, y, X, own = monthly()
    names = sorted(X); FC = {}; PH = {}
    for k in names:
        FC[k], PH[k] = forecasts(X[k][0], y)
    for k in list(names):                                                         # 12-month changes for P_allx
        x = X[k][0]; d = np.r_[np.full(12, np.nan), x[12:] - x[:-12]]
        FC[k + '_d12'], PH[k + '_d12'] = forecasts(d, y)
    sets = {'P_new': [k for k in names if X[k][1]], 'P_all': names, 'P_allx': names + [k + '_d12' for k in names]}
    return idx, me, dates, y, own, FC, PH, sets


def variants():
    return list(itertools.product(SETS, COMBS, SCORES, MAPS))


def decisions(ev, idx, me, own, FC, PH, sets):
    pos = {e: idx.get_indexer(ev.era_dates(e)) for e in ('spx', 'ndx')}
    mi = {e: np.searchsorted(me, pos[e], side='right') - 1 for e in pos}
    comb = {}
    for s in SETS:
        F = np.vstack([FC[k] for k in sets[s]]); P = np.vstack([PH[k] for k in sets[s]])
        for c in COMBS: comb[(s, c)] = combine(F, P, c)
    out = {}
    for (s, c, sc, q) in variants():
        dd = {}; ww = {}
        for e in ('spx', 'ndx'):
            f = comb[(s, c)]; score = f if sc == 'S1' else f / own[e]
            code, warm = mapq(pct(score), q)
            dd[e] = code[mi[e]]; ww[e] = warm[mi[e]]
        out[(s, c, sc, q)] = (dd, ww, comb[(s, c)])
    return out


def disc_stage():
    t0 = time.time(); ev = EV.Evaluator()
    idx, me, dates, y, own, FC, PH, sets = build()
    dec = decisions(ev, idx, me, own, FC, PH, sets)
    V = variants(); D = []; info = []
    for v in V:
        dd, ww, f = dec[v]
        d, s = ev.discovery(dd['spx'], dd['ndx']); D.append(d)
        info.append(dict(variant='/'.join(v), **s, share3x_disc=float(np.mean(np.r_[dd['spx'], dd['ndx']] == 0))))
    D = np.vstack(D).astype(np.float32)
    res, aux = ST.spa_rw(D, topM=len(V), verbose=False)
    sr = D.mean(1) / D.std(1, ddof=1); sr_var = float(np.var(sr))
    for i, r in enumerate(info):
        x = D[i]; nz = np.flatnonzero(x != 0); x = x[nz[0]:] if len(nz) else x
        r.update(tstat=float(aux['tstat'][i]), rw_reject=bool(aux['rw_rej'][i]), dsr_N72=ST.dsr(x, sr_var, len(V))[0],
                 defl_q50=float((aux['dbar'][i] - res['maxnull_q50'] * aux['om'][i] / np.sqrt(D.shape[1])) * 12))
    order = sorted(range(len(V)), key=lambda i: -info[i]['adv_all'])
    frozen = ['/'.join(V[i]) for i in order[:5]]
    npred = {s: len(sets[s]) for s in sets}
    json.dump(dict(spa=res, sr_var=sr_var, n_pred=npred, frozen_top5=frozen, rows=[info[i] for i in order], secs=time.time() - t0),
              open(OUT + 'disc.json', 'w'), indent=1, default=float)
    np.save(OUT + 'D.npy', D)
    print('SPA', {k: res[k] for k in ('N', 'Tspa', 'p_c', 'p_l', 'p_u', 'maxnull_q50', 'rw_n')}, 'n_pred', npred)
    for i in order[:10]:
        r = info[i]; print('%-28s adv %.4f (spx %.4f ndx %.4f) t %.2f q50 %.4f DSR72 %.3f 3x %.2f' % (
            r['variant'], r['adv_all'], r['adv_spx'], r['adv_ndx'], r['tstat'], r['defl_q50'], r['dsr_N72'], r['share3x_disc']))


def confirm_stage(n_total):
    sys.path.insert(0, '/mnt/project-files/research/breakthrough/code'); import gate
    ev = EV.Evaluator(); dj = json.load(open(OUT + 'disc.json'))
    idx, me, dates, y, own, FC, PH, sets = build()
    dec = decisions(ev, idx, me, own, FC, PH, sets)
    byname = {r['variant']: r for r in dj['rows']}; rows = []
    for rk, vn in enumerate(dj['frozen_top5']):
        v = tuple(vn.split('/')); dd, ww, f = dec[v]; r = dict(rank=rk + 1, variant=vn, disc=byname[vn])
        r['conf'] = ev.confirm(dd['ndx'])
        disc_d = ev_disc_d(ev, dd)
        r['disc_d_vs_s085'] = disc_d
        r['conf_pass_iii'] = bool(r['conf']['d_vs_s085'] > 0 and r['conf']['d_vs_s085'] >= 0.5 * disc_d and disc_d > 0)
        sg = {}
        for e in ('spx', 'ndx'):
            sg[e] = pd.Series((dd[e] == 0) | ww[e], index=ev.era_dates(e))
        sig = pd.concat([sg['spx'][sg['spx'].index < '1986-01-01'], sg['ndx'][sg['ndx'].index >= '1986-01-01']])
        r['g1'] = {}
        for lab, N in (('N72', 72), ('N_total', n_total)):
            g = gate.test(sig.astype(bool), trials=N, name=vn, verbose=False)
            r['g1'][lab] = {k: (dict(hit=w['hit'], always=w['always_up'], hit_defl=w['hit_deflated']) if isinstance(w, dict) else w)
                            for k, w in g.items() if k in ('ndx_86_14', 'spx_55_85', 'verdict')}
        rows.append(r)
        print(rk + 1, vn, 'disc adv %.4f | conf adv_vs_1x %.4f d_vs_s085 %.4f | disc d85 %.4f | iii %s | G1 %s %.3f' % (
            r['disc']['adv_all'], r['conf']['adv_vs_1x'], r['conf']['d_vs_s085'], disc_d, r['conf_pass_iii'],
            r['g1']['N_total']['verdict'], r['g1']['N_total']['ndx_86_14']['hit_defl']), flush=True)
    v = tuple(dj['frozen_top5'][0].split('/')); dd, ww, f = dec[v]
    ms = ev.ms1(dd['spx'], dd['ndx'], label='FC1 #1 ' + dj['frozen_top5'][0])
    json.dump(dict(rows=rows, ms1=ms, n_total=n_total), open(OUT + 'confirm.json', 'w'), indent=1, default=float)
    print('MS1 representative %.4f' % ms['representative'], {bn: round(x['cagr'], 4) for bn, x in ms['real'].items()})


def ev_disc_d(ev, dd):
    """discovery d vs s0.85 (day-weighted as bt1_final: spx 372 / ndx 168 months)."""
    from m1_confirm import s085_logret
    s85 = s085_logret(); out = {}
    for e, a, b in (('spx', '1955-01-03', '1985-12-31'), ('ndx', '1986-01-02', '1999-12-31')):
        x = ev.daily(e, dd[e]).loc[a:b]; s = s85[e].reindex(x.index); ok = s.notna()
        out[e] = float((x['lg'][ok] - s[ok]).mean() * 252)
    return (out['spx'] * 372 + out['ndx'] * 168) / 540


if __name__ == '__main__':
    if sys.argv[1] == 'disc': disc_stage()
    else: confirm_stage(int(sys.argv[2]))
