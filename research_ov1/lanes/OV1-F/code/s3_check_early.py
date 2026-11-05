"""Independent re-computation of ON on every early-window block date (direct lookup of the raw DEXJPUS value strictly before each
trading day, brute-force numpy.percentile per day, explicit 21-day hold loop; no ffill/cumsum/numba), compared with the
vectorized sig_f.master_signal used by s2_killA.py. Also v1 daily state shares and ON-day shares in the early window only."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/lanes/OV1-F/code'); sys.path.insert(0, '/mnt/project-files/research/ov1/code')
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code')
import ov1lib as L, gate, sig_f, jp, ov  # noqa
LANE = sig_f.LANE
raw = sig_f.raw().dropna(); rd = raw.index.values; rv = np.log(raw.values)
cal = sig_f.master_cal(); SM = sig_f.master_signal()
def lv(k):                                    # log value usable at close of trading day k: last obs dated strictly before cal[k]
    j = np.searchsorted(rd, cal[k].to_datetime64(), side='left') - 1
    return rv[j] if j >= 0 else np.nan
def y21(k): return -(lv(k) - lv(k - 21))
def fire(k):
    w = np.array([y21(i) for i in range(k - 756, k)]); y = y21(k)
    if np.isnan(w).any() or np.isnan(y): return False
    return bool(y > np.percentile(w, 95))
out = {}
for stream, a, b, st, lo, hi in (('SPX', '1928-01-03', '1985-12-31', '1955-01-03', '1974-02-01', '1985-12-31'),
                                 ('NDX', '1984-01-03', '2014-12-31', '1986-01-02', '1986-01-02', '1999-12-31')):
    R, M = jp.calendar(a, b); X = jp.mkX(R, M, stream); ec = X.index
    lab = gate._frame(stream, a, b, st); pos = ec.get_indexer(lab.index); end = ec[np.minimum(pos + 23, len(ec) - 1)]
    m = (lab.index >= pd.Timestamp(lo)) & (end <= pd.Timestamp(hi)); mism = 0; nchk = 0; nthr = 0; mx = 0.0
    for t in lab.index[m]:
        k = cal.get_loc(t); on_bf = any(fire(j) for j in range(k - 20, k + 1))
        nchk += 1; mism += int(on_bf != bool(SM['on'].iloc[k]))
        w = np.array([y21(i) for i in range(k - 756, k)]); mx = max(mx, abs(np.percentile(w, 95) - SM['thr'].iloc[k])); nthr += 1
    out[stream] = dict(n_checked=nchk, on_mismatches=mism, thr_max_abs_diff=mx)
    F = ov.flags_hist(X); i0 = ec.searchsorted(pd.Timestamp(st)) - ov.WARM
    c = ov.Ctx(X, F, np.arange(i0, len(X))[None, :]); B = pd.Series(L.v1_B(c)[0], index=ec[c.ii[0]])
    Be = B[(B.index >= lo) & (B.index <= hi)]
    out['v1_state_share_%s_%s_%s' % (stream, lo[:4], hi[:4])] = {str(k): float(v) for k, v in Be.value_counts(normalize=True).items()}
    o = SM['on'].reindex(Be.index).astype(bool)
    out['on_day_share_%s' % stream] = float(o.mean()); out['on_day_share_when_v1_3x_%s' % stream] = float(o[np.isclose(Be.values, 3)].mean())
    out['fire_days_%s' % stream] = int(SM['fire'].reindex(Be.index).sum())
print(json.dumps(out, indent=1)); json.dump(out, open(LANE + 'results/s3_check_early.json', 'w'), indent=1)
