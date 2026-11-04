"""M1 final MS1 (PRECOMMIT_M1 sec.9) for a rule row: real-history after-tax rows through lab's ms1eng (this lane's
decisions, one sleeve per non-cash product, inverse = -r + 2rf - 2.45%/yr) and the representative conversion
16.2 + d_stream (lab measure_series method: the rule's real NDX 1986-2014 after-cost pre-tax daily stream and s0.85's
real stream re-sampled with the same dev250 path index matrices, paired path by path; turnover 1)."""
import os, sys, json, numpy as np, pandas as pd
SCR = '/tmp/claude-0/-home-user--/e60ac389-f078-575c-af9f-bad532fab64a/scratchpad/bt1/'
os.environ['NUMBA_CACHE_DIR'] = SCR + 'nb'
sys.path.insert(0, SCR + 'code'); sys.path.insert(0, '/mnt/project-files/research/lab')
from lab import ms1
import m1_engine as EN, m1_search as SE, m1_confirm as CF

WARM = ms1.WARM


def sleeve_ret(r, rf, code):
    if code == 0: return 3 * r - 2 * rf - ms1.ER3 / 252
    if code == 1: return 2 * r - rf - ms1.ER3 / 252
    if code == 2: return r - ms1.FEE1 / 252
    if code == 4: return -r + 2 * rf - ms1.ER3 / 252
    raise ValueError(code)


def real_rows(srv, dec_by_date, codes):
    out = {}
    for bn in ('real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85'):
        c = srv.C[bn]; X = srv.X[srv.src[bn]]
        dts = X.index[c.ii[0]]
        dec = dec_by_date.reindex(dts).fillna(2).astype(int).values      # before this lane's rows: 1x
        sl = [k for k in codes if k != 3]
        R = np.zeros((1, c.T, len(sl))); W = np.zeros((1, c.T, len(sl)))
        for j, k in enumerate(sl):
            R[0, :, j] = sleeve_ret(c.r[0], c.rf[0], k); W[0, :, j] = (dec == k)
        CR = np.ascontiguousarray(np.maximum(c.rf - ms1.CSPR / 252, 0.0) * (1 - ms1.CTAX))
        force = np.zeros((1, c.T), np.bool_)
        fin, EE, ntr = srv.eng.runP(R, CR, W, force, 2, ms1.COST, ms1.TAX, ms1.D_UNITS, 3, 1.0)
        fin0, EE0, _ = srv.eng.runP(R, CR, W, force, 2, ms1.COST, 0.0, 0.0, 3, 1.0)
        yrs = EE.shape[1] / 252
        cagr = float(max(fin[0], 1e-9) ** (1 / yrs) - 1)
        ref = srv.ref(bn)
        mdd = float((EE[0] / np.maximum.accumulate(EE[0]) - 1).min())
        out[bn] = dict(cagr=cagr, pretax_cagr=float(EE0[0, -1] ** (1 / yrs) - 1), mdd=mdd, d_vs_s085=cagr - float(ref['s085']),
                       ref_s085=float(ref['s085']), hold1x=float(ref['hold1x']), trades_yr=float(ntr[0] / yrs))
    return out


def stream_paths(srv, dates, ret, turnover=1.0):
    """lab Server.series() logic, returning per-path after-tax CAGR (fc) and equity for every basis."""
    np_, pd_ = np, pd
    S = pd.Series(np.asarray(ret, float), index=pd.DatetimeIndex(dates)); S = S[S.index <= srv.seal]
    lvl = (1.0 + S).cumprod(); res = {}
    for bn in ms1.BASES:
        c = srv.C[bn]; X = srv.X[srv.src[bn]]
        L = lvl.reindex(X.index, method='ffill')
        v = np.array(L / L.shift(1).fillna(1.0) - 1.0, dtype=float); v[0] = 0.0
        have = np.asarray((X.index >= S.index[0]) & (X.index <= S.index[-1]))
        v = np.where(have, np.nan_to_num(v), 0.0)
        used = c.ii[:, WARM:]; cover = float(have[used].mean())
        if cover < 0.95:
            res[bn] = None; continue
        Mx = v[c.ii]; Mx[:, 0] = 0.0; Mx = np.ascontiguousarray(Mx[:, WARM:])
        Qx = np.zeros_like(Mx)
        fin, E = srv.eng.series_run(Mx, Qx, turnover, ms1.COST, ms1.TAX, ms1.D_UNITS)
        yrs = E.shape[1] / 252
        fc = np.maximum(fin, 1e-9) ** (1 / yrs) - 1
        mdd = (E / np.maximum.accumulate(E, axis=1) - 1).min(1)
        res[bn] = dict(fc=fc, mdd=mdd, cover=cover)
    return res


def measure(row, label):
    srv = ms1._Server()
    E = SE.era_inputs()
    A = {e: np.ascontiguousarray(np.load(SCR + 'cache/atoms_%s.npy' % e)) for e in ('spx', 'ndx')}
    df = {e: CF.rule_daily(E, A, row, e) for e in ('spx', 'ndx')}
    dec = pd.concat([df['spx']['dec'][df['spx'].index < '1985-01-02'], df['ndx']['dec']])
    codes = sorted(set([int(row[4]), int(row[5]), 2]))
    out = dict(label=label, row=list(map(int, row)), real=real_rows(srv, dec, codes))
    # representative conversion: real NDX 1986-2014 streams (after cost, pre-tax)
    x = df['ndx'].loc['1986-01-02':'2014-12-31']
    rule_ret = np.expm1(x['lg'].values)
    s85 = CF.s085_logret()['ndx'].loc['1986-01-02':'2014-12-31']
    s85_ret = np.expm1(s85.values)
    P = stream_paths(srv, x.index, rule_ret); Q = stream_paths(srv, s85.index, s85_ret)
    conv = {}
    for bn in ms1.BASES:
        if P[bn] is None or Q[bn] is None:
            conv[bn] = None; continue
        d = P[bn]['fc'] - Q[bn]['fc']
        conv[bn] = dict(rule_stream=float(np.median(P[bn]['fc'])), s085_stream=float(np.median(Q[bn]['fc'])),
                        d_stream=float(np.median(d)), win=float(np.mean(d > 1e-5)),
                        dd80_rule=float(np.mean(P[bn]['mdd'] <= -0.8)), dd80_s085=float(np.mean(Q[bn]['mdd'] <= -0.8)),
                        mdd_med_rule=float(np.median(P[bn]['mdd'])))
    out['stream'] = conv
    out['representative'] = 0.1616 + conv['dev250_path']['d_stream']
    # cross-check: lab's own measure_series on the rule stream (headline number of the stream itself)
    out['lab_measure_series_rule'] = {k: (v['cagr'] if isinstance(v, dict) else v) for k, v in srv.series(dict(
        ret=rule_ret.tolist(), dates=[t.strftime('%Y-%m-%d') for t in x.index], label=label, turnover=1.0)).items()
        if k in ms1.BASES or k == 'HEADLINE_MS1'}
    return out


if __name__ == '__main__':
    which = sys.argv[1]
    if which == 'disc1':
        S = json.load(open(SCR + 'out/search.json')); r = S['top50'][0]
        res = measure(r['row'], 'discovery #1 (failure reference): ' + r['rule'])
    elif which == 't1':
        r = json.load(open(SCR + 'out/top20t_frozen.json'))['top20_t'][0]
        res = measure(r['row'], 'secondary reference (ADDENDUM_M1_1, SPA-t #1): ' + r['rule'])
    else:
        C = json.load(open(SCR + 'out/confirm.json'))
        r = [x for x in C['rows'] if x['id'] == int(which)][0]
        rows = json.load(open(SCR + 'out/top20_frozen.json'))['top20']
        row = [x for x in rows if x['id'] == int(which)][0]['row']
        res = measure(row, r['rule'])
    print(json.dumps(res, indent=1, default=float))
    json.dump(res, open(SCR + 'out/ms1_%s.json' % which, 'w'), indent=1, default=float)
