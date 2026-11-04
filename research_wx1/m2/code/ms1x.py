"""MS1 stream re-sampling with path-level output (same code path as lab ms1.measure_series / _Server.series: std.contexts,
jp source calendars, lab.ms1eng.series_run, std.row; lab code imported, not edited) so that a candidate stream and the
s0.85 real-history stream can be paired path by path (master PRECOMMIT_WX1 §3: 대표 환산 = 16.2 + d_stream).
s0.85 real stream = std.engine on real_ndx_86_14 with tax 0 (after MS1 cost, before the 22% tax), daily equity -> returns.
argv: out_json stream1.npz [stream2.npz ...]   (npz: dates, ret, q, turnover)"""
import sys, os, json, numpy as np, pandas as pd
import importlib.util
_sp = importlib.util.spec_from_file_location('lab_ms1eng', '/mnt/project-files/research/lab/lab/ms1eng.py')
ms1eng = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(ms1eng)   # lab's sleeve/stream kernel, unedited
sys.path.insert(0, '/mnt/project-files/research/measure_std/')
import std, jp, ov
WARM, SEAL = 300, pd.Timestamp('2014-12-31')
COST, TAX, DU = 0.003, 0.22, 2.5e6 / 10e6
BASES = ('dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85')
C = std.contexts()
R_, M_ = jp.calendar('1984-01-03', '2014-12-31'); Xn = jp.mkX(R_, M_, 'NDX')
R_, M_ = jp.calendar('1928-01-03', '1985-12-31'); Xs = jp.mkX(R_, M_, 'SPX')
a, b = std.iv.POOLS['dev250'][:2]
R_, M_ = jp.calendar(a, b); Xd = jp.mkX(R_, M_, 'NDX')
X = dict(ndx=Xn, spx=Xs, dev=Xd)
SRC = {'dev250_path': 'dev', 'dev250_glued': 'dev', 'real_ndx_86_14': 'ndx', 'real_spx_55_85': 'spx', 'real_spx_70_85': 'spx'}


def series(dates, ret, q, share, min_cover=0.95):
    """-> {basis: (fc [P], row dict) or None} exactly as lab _Server.series."""
    S = pd.DataFrame(dict(r=np.asarray(ret, float), q=np.asarray(q, float)), index=pd.DatetimeIndex(pd.to_datetime(dates)))
    S = S[~S.index.duplicated(keep='last')].sort_index()
    S = S[(S.index <= SEAL) & S['r'].notna()]
    s = S['r']
    lvl = (1.0 + s).cumprod()
    cc = (S['q'].fillna(0.0) * lvl.shift(1).fillna(1.0)).cumsum()
    out = {}
    for bn in BASES:
        c = C[bn]; Xb = X[SRC[bn]]
        L = lvl.reindex(Xb.index, method='ffill')
        v = np.array(L / L.shift(1).fillna(1.0) - 1.0, dtype=float); v[0] = 0.0
        have = np.asarray((Xb.index >= s.index[0]) & (Xb.index <= s.index[-1]))
        v = np.where(have, np.nan_to_num(v), 0.0)
        Cc = cc.reindex(Xb.index, method='ffill').fillna(0.0)
        qv = np.array((Cc - Cc.shift(1).fillna(0.0)) / L.shift(1).fillna(1.0), dtype=float); qv[0] = 0.0
        qv = np.where(have, np.nan_to_num(qv), 0.0)
        used = c.ii[:, WARM:]
        cover = float(have[used].mean())
        if cover < min_cover:
            out[bn] = None
            continue
        Mx = v[c.ii]; Mx[:, 0] = 0.0; Mx = np.ascontiguousarray(Mx[:, WARM:])
        Qx = qv[c.ii]; Qx[:, 0] = 0.0; Qx = np.ascontiguousarray(Qx[:, WARM:])
        fin, E = ms1eng.series_run(Mx, Qx, share, COST, TAX, DU)
        yrs = E.shape[1] / 252
        fc = np.maximum(fin, 1e-9) ** (1 / yrs) - 1
        row, _ = std.row(fc, E)
        row['cover'] = cover
        out[bn] = (fc, row)
    return out


def main():
    outp = sys.argv[1]
    res = {}
    # s0.85 path-recomputed reference (lab's d_vs_s085) and real-history stream
    ref = {}
    for bn in BASES:
        c = C[bn]
        fr, Er = std.engine(c, *std.s085(c))
        ref[bn] = fr
    c = C['real_ndx_86_14']
    f0, E0 = std.engine(c, *std.s085(c), tax=0.0)
    sd = Xn.index.values[c.ii[0]]
    e = E0[0]
    dts = pd.DatetimeIndex(sd[-len(e):])
    r85 = e[1:] / e[:-1] - 1.0
    s85 = series(dts[1:], r85, np.zeros(len(r85)), 1.0)
    res['s085_stream'] = {bn: (None if v is None else v[1]) for bn, v in s85.items()}
    res['s085_stream_meta'] = dict(start=str(dts[0].date()), end=str(dts[-1].date()), n=len(e), Elen=int(E0.shape[1]),
                                   ii_len=int(c.ii.shape[1]))
    res['s085_ref_median'] = {bn: float(np.median(v)) for bn, v in ref.items()}
    # s0.85 stream annual log growth by era (for the confirmation rule d vs s0.85)
    sr = pd.Series(r85, index=dts[1:])
    for nm, (a_, b_) in dict(disc=('1986-01-01', '1999-12-31'), conf=('2000-01-01', '2014-12-31'), all=('1986-01-01', '2014-12-31')).items():
        x = sr[a_:b_]
        res.setdefault('s085_stream_loggrowth', {})[nm] = float(np.log1p(x).sum() / (len(x) / 252.0))
    np.savez(os.path.splitext(outp)[0] + '_s085stream.npz', dates=np.array([t.strftime('%Y-%m-%d') for t in dts[1:]]), ret=r85)
    for f in sys.argv[2:]:
        z = np.load(f)
        o = series(z['dates'], z['ret'], z['q'], float(z['turnover']))
        rr = {}
        for bn in BASES:
            if o[bn] is None:
                rr[bn] = None
                continue
            fc, row = o[bn]
            row = dict(row)
            dd = fc - ref[bn]
            row.update(d_vs_s085_pathref=float(np.median(dd)), pw_vs_s085_pathref=float(np.mean(dd > 1e-5)))
            if s85.get(bn) is not None:
                ds = fc - s85[bn][0]
                row.update(d_stream=float(np.median(ds)), pw_stream=float(np.mean(ds > 1e-5)),
                           s085_stream=float(s85[bn][1]['cagr']), s085_stream_dd80=s85[bn][1].get('dd80'))
            rr[bn] = row
        p = rr.get('dev250_path')
        rr['HEADLINE_stream'] = None if p is None else p['cagr']
        rr['REP_CONVERTED'] = None if (p is None or 'd_stream' not in p) else 0.162 + p['d_stream']
        res[os.path.basename(f)] = rr
    json.dump(res, open(outp, 'w'), indent=1, default=float)
    print(json.dumps(res, indent=1, default=float)[:6000])


main()
