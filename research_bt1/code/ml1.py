"""ML1 nonlinear walk-forward lane (PRECOMMIT_ML1, sha256 3ff574b2...). 48 pre-registered variants.
stage 'scores' : walk-forward annual refits -> out/ml1/scores.npz (monthly scores per model x set)
stage 'disc'   : discovery stats + frozen ranking -> out/ml1/disc.json
stage 'confirm': one-time 2000-2014 confirmation of frozen top-5, G1, MS1 of #1 -> out/ml1/confirm.json"""
import os, sys, json, time, itertools, warnings, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fc1, m1_stats as ST, bt1_evaldec as EV
warnings.filterwarnings('ignore')
OUT = fc1.SCR + 'out/ml1/'; os.makedirs(OUT, exist_ok=True)
MODELS = ('logit', 'ridge', 'gbm', 'rf'); SETS = ('F_new', 'F_all', 'F_allx'); MAPS = fc1.MAPS
MINTRAIN, COVER = 240, 0.6


def features():
    idx, me, dates, y, X, own = fc1.monthly()
    names = sorted(X)
    base = {k: X[k][0] for k in names}
    d12 = {k + '_d12': np.r_[np.full(12, np.nan), base[k][12:] - base[k][:-12]] for k in names}
    sets = {'F_new': [k for k in names if X[k][1]], 'F_all': names, 'F_allx': names + sorted(d12)}
    allf = dict(base, **d12)
    return idx, me, dates, y, own, allf, sets


def fit_predict(model, Xtr, ytr, Xte):
    if model in ('logit', 'ridge'):
        cov = np.isfinite(Xtr).mean(0); keep = cov >= COVER
        if keep.sum() == 0: return np.full(len(Xte), np.nan)
        A = Xtr[:, keep]; B = Xte[:, keep]
        mu = np.nanmean(A, 0); sd = np.nanstd(A, 0); sd[~(sd > 0)] = 1.0
        A = np.nan_to_num((A - mu) / sd); B = np.nan_to_num((B - mu) / sd)
        if model == 'logit':
            from sklearn.linear_model import LogisticRegression
            m = LogisticRegression(C=0.1, max_iter=2000).fit(A, (ytr > 0).astype(int)); return m.predict_proba(B)[:, 1]
        from sklearn.linear_model import Ridge
        return Ridge(alpha=10.0).fit(A, ytr).predict(B)
    if model == 'gbm':
        import lightgbm as lgb
        m = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.03, num_leaves=7, min_child_samples=30, colsample_bytree=0.5,
                               subsample=0.8, subsample_freq=1, random_state=1, n_jobs=1, verbose=-1)
        m.fit(Xtr, (ytr > 0).astype(int)); return m.predict_proba(Xte)[:, 1]
    from sklearn.ensemble import RandomForestClassifier
    med = np.nanmedian(Xtr, 0); med = np.where(np.isfinite(med), med, 0.0)
    A = np.where(np.isfinite(Xtr), Xtr, med); B = np.where(np.isfinite(Xte), Xte, med)
    m = RandomForestClassifier(n_estimators=300, max_depth=4, min_samples_leaf=20, max_features='sqrt', random_state=1, n_jobs=1)
    m.fit(A, (ytr > 0).astype(int)); return m.predict_proba(B)[:, 1]


def scores_stage():
    t0 = time.time(); idx, me, dates, y, own, allf, sets = features()
    n = len(me); y1 = np.r_[y[1:], np.nan]; yr = dates.year.values; out = {}
    for s in SETS:
        F = np.column_stack([allf[k] for k in sets[s]])
        for mdl in MODELS:
            sc = np.full(n, np.nan)
            for Y in range(int(yr.min()) + 1, int(yr.max()) + 1):
                te = np.flatnonzero(yr == Y)
                # training pairs: label month k+1 <= Dec of Y-1  <=>  k+1 index <= last index of year Y-1
                last = np.flatnonzero(yr == Y - 1)[-1]
                tr = np.arange(0, last)                                   # k in [0, last-1] -> label index k+1 <= last
                tr = tr[np.isfinite(y1[tr]) & np.isfinite(F[tr]).any(1)]
                if len(tr) < MINTRAIN: continue
                sc[te] = fit_predict(mdl, F[tr], y1[tr], F[te])
            out[s + '|' + mdl] = sc
            print(s, mdl, 'first score', str(dates[np.flatnonzero(np.isfinite(sc))[0]].date()) if np.isfinite(sc).any() else None, '%.0fs' % (time.time() - t0), flush=True)
    np.savez(OUT + 'scores.npz', **out)


def variants():
    return list(itertools.product(MODELS, SETS, MAPS))


def decisions(ev, idx, me):
    z = np.load(OUT + 'scores.npz')
    pos = {e: idx.get_indexer(ev.era_dates(e)) for e in ('spx', 'ndx')}
    mi = {e: np.searchsorted(me, pos[e], side='right') - 1 for e in pos}
    out = {}; P = {}
    for (mdl, s, q) in variants():
        key = s + '|' + mdl
        if key not in P: P[key] = fc1.pct(z[key])
        code, warm = fc1.mapq(P[key], q)
        out[(mdl, s, q)] = ({e: code[mi[e]] for e in pos}, {e: warm[mi[e]] for e in pos})
    return out


def disc_stage():
    t0 = time.time(); ev = EV.Evaluator(); idx, me, dates, y, own, allf, sets = features()
    dec = decisions(ev, idx, me); V = variants(); D = []; info = []
    for v in V:
        dd, ww = dec[v]; d, s = ev.discovery(dd['spx'], dd['ndx']); D.append(d)
        info.append(dict(variant='/'.join(v), **s, share3x_disc=float(np.mean(np.r_[dd['spx'], dd['ndx']] == 0))))
    D = np.vstack(D).astype(np.float32)
    res, aux = ST.spa_rw(D, topM=len(V), verbose=False)
    sr = D.mean(1) / D.std(1, ddof=1); sr_var = float(np.var(sr))
    for i, r in enumerate(info):
        x = D[i]; nz = np.flatnonzero(x != 0); x = x[nz[0]:] if len(nz) else x
        r.update(tstat=float(aux['tstat'][i]), rw_reject=bool(aux['rw_rej'][i]), dsr_N48=ST.dsr(x, sr_var, len(V))[0],
                 defl_q50=float((aux['dbar'][i] - res['maxnull_q50'] * aux['om'][i] / np.sqrt(D.shape[1])) * 12))
    order = sorted(range(len(V)), key=lambda i: -info[i]['adv_all'])
    frozen = ['/'.join(V[i]) for i in order[:5]]
    json.dump(dict(spa=res, sr_var=sr_var, frozen_top5=frozen, rows=[info[i] for i in order], secs=time.time() - t0),
              open(OUT + 'disc.json', 'w'), indent=1, default=float)
    np.save(OUT + 'D.npy', D)
    print('SPA', {k: res[k] for k in ('N', 'Tspa', 'p_c', 'p_l', 'p_u', 'maxnull_q50', 'rw_n')})
    for i in order[:10]:
        r = info[i]; print('%-22s adv %.4f (spx %.4f ndx %.4f) t %.2f q50 %.4f DSR48 %.3f 3x %.2f' % (
            r['variant'], r['adv_all'], r['adv_spx'], r['adv_ndx'], r['tstat'], r['defl_q50'], r['dsr_N48'], r['share3x_disc']))


def confirm_stage(n_total):
    sys.path.insert(0, '/mnt/project-files/research/breakthrough/code'); import gate
    ev = EV.Evaluator(); dj = json.load(open(OUT + 'disc.json')); idx, me, dates, y, own, allf, sets = features()
    dec = decisions(ev, idx, me); byname = {r['variant']: r for r in dj['rows']}; rows = []
    for rk, vn in enumerate(dj['frozen_top5']):
        v = tuple(vn.split('/')); dd, ww = dec[v]; r = dict(rank=rk + 1, variant=vn, disc=byname[vn])
        r['conf'] = ev.confirm(dd['ndx']); disc_d = fc1.ev_disc_d(ev, dd); r['disc_d_vs_s085'] = disc_d
        r['conf_pass_iii'] = bool(r['conf']['d_vs_s085'] > 0 and r['conf']['d_vs_s085'] >= 0.5 * disc_d and disc_d > 0)
        sg = {e: pd.Series((dd[e] == 0) | ww[e], index=ev.era_dates(e)) for e in ('spx', 'ndx')}
        sig = pd.concat([sg['spx'][sg['spx'].index < '1986-01-01'], sg['ndx'][sg['ndx'].index >= '1986-01-01']])
        r['g1'] = {}
        for lab, N in (('N48', 48), ('N_total', n_total)):
            g = gate.test(sig.astype(bool), trials=N, name=vn, verbose=False)
            r['g1'][lab] = {k: (dict(hit=w['hit'], always=w['always_up'], hit_defl=w['hit_deflated']) if isinstance(w, dict) else w)
                            for k, w in g.items() if k in ('ndx_86_14', 'spx_55_85', 'verdict')}
        rows.append(r)
        print(rk + 1, vn, 'disc adv %.4f | conf adv_vs_1x %.4f d_vs_s085 %.4f | disc d85 %.4f | iii %s | G1 %s raw %.3f defl %.3f' % (
            r['disc']['adv_all'], r['conf']['adv_vs_1x'], r['conf']['d_vs_s085'], disc_d, r['conf_pass_iii'],
            r['g1']['N_total']['verdict'], r['g1']['N_total']['ndx_86_14']['hit'], r['g1']['N_total']['ndx_86_14']['hit_defl']), flush=True)
    v = tuple(dj['frozen_top5'][0].split('/')); dd, ww = dec[v]
    ms = ev.ms1(dd['spx'], dd['ndx'], label='ML1 #1 ' + dj['frozen_top5'][0])
    json.dump(dict(rows=rows, ms1=ms, n_total=n_total), open(OUT + 'confirm.json', 'w'), indent=1, default=float)
    print('MS1 representative %.4f' % ms['representative'], {bn: round(x['cagr'], 4) for bn, x in ms['real'].items()})


if __name__ == '__main__':
    st = sys.argv[1]
    if st == 'scores': scores_stage()
    elif st == 'disc': disc_stage()
    else: confirm_stage(int(sys.argv[2]))
