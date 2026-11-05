"""Independent re-computation of ON on every early-window block date (loop over raw change events, no cumsum/ffill),
compared with the vectorized sig_c.on_matrix used by s2_killA.py. Also v1 daily state shares in the early window only."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/lanes/OV1-C/code'); sys.path.insert(0, '/mnt/project-files/research/ov1/code')
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code')
import ov1lib as L, gate, sig_c, jp, ov  # noqa
LANE = '/mnt/project-files/research/ov1/lanes/OV1-C/'
S = sig_c.raw_sources()
def ev_monthly(s): d = s.diff().dropna(); return [(a + pd.offsets.MonthBegin(1), float(v)) for a, v in d.items() if abs(v) > 1e-12]
def ev_daily(s): d = s.diff().dropna(); return [(a + pd.Timedelta(days=1), float(v)) for a, v in d.items() if abs(v) > 1e-12]
EV = dict(JP=ev_monthly(S['jp_disc']) + ev_monthly(S['jp_call']),       # diff() within each source only: splice change excluded
          DE_EZ=ev_monthly(S['de']) + ev_daily(S['ez']), UK=ev_monthly(S['uk']))
first = dict(JP=S['jp_disc'].index[0] + pd.offsets.MonthBegin(1), DE_EZ=S['de'].index[0] + pd.offsets.MonthBegin(1),
             UK=S['uk'].index[0] + pd.offsets.MonthBegin(1))
XC = sig_c.change_index(); out = {}
for stream, a, b, st, lo, hi in (('SPX', '1928-01-03', '1985-12-31', '1955-01-03', '1960-01-04', '1985-12-31'),
                                 ('NDX', '1984-01-03', '2014-12-31', '1986-01-02', '1986-01-02', '1999-12-31')):
    R, M = jp.calendar(a, b); X = jp.mkX(R, M, stream); cal = X.index
    V = {k: x.reindex(cal.union(x.index)).ffill().reindex(cal).values[None, :].astype(float) for k, x in XC.items()}
    on, cnt, ok = sig_c.on_matrix(V)
    lab = gate._frame(stream, a, b, st); pos = cal.get_indexer(lab.index); end = cal[np.minimum(pos + 23, len(cal) - 1)]
    m = (lab.index >= pd.Timestamp(lo)) & (end <= pd.Timestamp(hi)); mism = 0; nchk = 0
    for t in lab.index[m]:
        j = cal.get_loc(t); t0 = cal[j - 126]; ups = 0; valid = True
        for k, ev in EV.items():
            if first[k] > t0: valid = False
            d = sum(v for (aa, v) in ev if t0 < aa <= t); ups += d >= 0.25 - 1e-9
        on_bf = bool(valid and ups >= 2); nchk += 1; mism += int(on_bf != bool(on[0, j]))
    out[stream] = dict(n_checked=nchk, mismatches=mism)
    if stream == 'NDX':
        F = ov.flags_hist(X); i0 = cal.searchsorted(pd.Timestamp('1986-01-02')) - ov.WARM
        c = ov.Ctx(X, F, np.arange(i0, len(X))[None, :]); B = pd.Series(L.v1_B(c)[0], index=cal[c.ii[0]])
        Be = B[(B.index >= '1986-01-02') & (B.index <= '1999-12-31')]
        out['v1_state_share_NDX_1986_1999'] = {str(k): float(v) for k, v in Be.value_counts(normalize=True).items()}
        ONs = pd.Series(on[0], index=cal); o = ONs[(ONs.index >= '1986-01-02') & (ONs.index <= '1999-12-31')]
        out['on_day_share_NDX_1986_1999'] = float(o.mean()); out['on_day_share_when_v1_3x_NDX_1986_1999'] = float(o[Be.reindex(o.index) == 3].mean())
    else:
        ONs = pd.Series(on[0], index=cal); o = ONs[(ONs.index >= '1960-01-04')]; out['on_day_share_SPX_1960_1985'] = float(o.mean())
print(json.dumps(out, indent=1)); json.dump(out, open(LANE + 'results/s3_check_early.json', 'w'), indent=1)
