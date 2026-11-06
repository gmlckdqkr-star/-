"""KL1 MS1 representative for the S2-US family #1 (PRECOMMIT_KL1 sec.8), M1 method (research/wx1/m1/code/m1_ms1.py):
rule's real NDX 1986-2014 after-cost pre-tax daily stream and s0.85's real stream re-sampled with lab ms1's dev250 path
index matrices, paired path by path; representative = 16.16% + median d. Also real NDX 2000-2014 pre-tax d vs s0.85."""
import os, sys, json, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/claude-0/-home-user--/e60ac389-f078-575c-af9f-bad532fab64a/scratchpad/kl/nb')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kl_engine as EN, kl_run_s2 as R2
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std, jp  # noqa
sys.path.insert(0, '/mnt/project-files/research/lab')
from lab import ms1
RES = os.path.join(HERE, '..', 'results')


def s085_ndx():
    C = std.contexts(); c = C['real_ndx_86_14']; B, bfn, bp, fs = std.s085(c)
    _, EE = std.engine(c, B, bfn, bp, fs, tax=0.0)
    R, M = jp.calendar('1984-01-03', '2014-12-31'); d = R.index[c.ii[0][std.ov.WARM:]]
    return pd.Series(np.r_[0.0, np.diff(np.log(EE[0]))], index=d)


def stream_paths(srv, dates, ret):
    S = pd.Series(np.asarray(ret, float), index=pd.DatetimeIndex(dates)); S = S[S.index <= srv.seal]
    lvl = (1.0 + S).cumprod(); res = {}
    for bn in ms1.BASES:
        c = srv.C[bn]; X = srv.X[srv.src[bn]]
        L = lvl.reindex(X.index, method='ffill')
        v = np.array(L / L.shift(1).fillna(1.0) - 1.0, dtype=float); v[0] = 0.0
        have = np.asarray((X.index >= S.index[0]) & (X.index <= S.index[-1]))
        v = np.where(have, np.nan_to_num(v), 0.0)
        used = c.ii[:, ms1.WARM:]; cover = float(have[used].mean())
        if cover < 0.95:
            res[bn] = None; continue
        Mx = v[c.ii]; Mx[:, 0] = 0.0; Mx = np.ascontiguousarray(Mx[:, ms1.WARM:]); Qx = np.zeros_like(Mx)
        fin, E = srv.eng.series_run(Mx, Qx, 1.0, ms1.COST, ms1.TAX, ms1.D_UNITS)
        yrs = E.shape[1] / 252
        res[bn] = dict(fc=np.maximum(fin, 1e-9) ** (1 / yrs) - 1, mdd=(E / np.maximum.accumulate(E, axis=1) - 1).min(1))
    return res


if __name__ == '__main__':
    fam = 'S2US'
    top = json.load(open(os.path.join(RES, 'top20_%s.json' % fam)))['top20'][0]
    I = R2.inputs('US'); dates = I['dates']
    t1 = int(np.searchsorted(dates.values, np.datetime64('2014-12-31'), side='right'))
    dec, act, g = EN.one_path(I['A'], I['X'], np.array(top['row'], np.int64), t1, I['cost'])
    lg = pd.Series(g[:t1] + np.log1p(I['X'][2, :t1]), index=dates[:t1])
    x = lg.loc['1986-01-02':'2014-12-31']; s85 = s085_ndx().loc['1986-01-02':'2014-12-31']
    srv = ms1._Server()
    P = stream_paths(srv, x.index, np.expm1(x.values)); Q = stream_paths(srv, s85.index, np.expm1(s85.values))
    out = dict(fam=fam, row=top['row'], bases={})
    for bn in ms1.BASES:
        if P[bn] is None or Q[bn] is None:
            out['bases'][bn] = None; continue
        d = P[bn]['fc'] - Q[bn]['fc']
        out['bases'][bn] = dict(rule_stream=float(np.median(P[bn]['fc'])), s085_stream=float(np.median(Q[bn]['fc'])), d_stream=float(np.median(d)),
                                win=float(np.mean(d > 1e-5)), dd80_rule=float(np.mean(P[bn]['mdd'] <= -0.8)))
    out['representative'] = 0.1616 + out['bases']['dev250_path']['d_stream']
    c0 = '2000-01-03'
    a = lg.loc[c0:'2014-12-31']; b = s85.reindex(a.index).dropna(); a = a.reindex(b.index)
    out['conf_pretax_d_vs_s085_ann'] = float((a - b).mean() * 252)
    out['conf_pretax_cagr_rule'] = float(np.exp(a.sum() / (len(a) / 252)) - 1); out['conf_pretax_cagr_s085'] = float(np.exp(b.sum() / (len(b) / 252)) - 1)
    print(json.dumps(out, indent=1))
    json.dump(out, open(os.path.join(RES, 'ms1_S2US_top1.json'), 'w'), indent=1)
