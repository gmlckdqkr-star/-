"""C3: restart / late start (brake memory) + C2 impact (a line frozen at its last level).
Real NDX 1986-2014: each month start m (1988-01..2009-12): (A) fresh model account from m (what the app does on a new line / a re-added
line / lost app data) vs (B) model account continuing from 1986 (research). Account m -> 2014-12-31 (app model, cash 0, no harvest).
dev250_path: restart at years 5, 10, 15: fresh vs continuing, account to year 30.
Freeze (C2 impact): real NDX, level frozen at month f (1988-01..2009-12) for 5 years vs continuing."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/acct3/code'); sys.path.insert(0, '/mnt/project-files/research/ru1/code')
import ac3, ru, std, bk, rx
from std import jp, ov
PP = ac3.PP; W = ru.WARM
def levels_of(c):
    Bs = np.ascontiguousarray(bk.C3sig(c), dtype=np.float64); feat = np.ascontiguousarray(bk.features(c))
    L, _ = ac3.levels(np.ascontiguousarray(c.r), np.ascontiguousarray(c.rf), Bs, feat, int(PP['delay']), PP['cost'], PP['tax'], 0.25,
                      int(PP['harvest']), PP['hthr'], PP['cspr'], PP['er3'], PP['step'], rx.av23s, rx.P_av23s(.85), 0.1)
    return L
def acct1(r, rf, L):
    P = r.shape[0]; n = L.shape[1]; T = r.shape[1]
    o, EU, _ = ru.acctP(np.ascontiguousarray(r), np.ascontiguousarray(rf), np.ascontiguousarray(L), np.ones((P, T)), np.zeros((P, n)),
                        0, 0, 0.0, .003, .22, .25, .0245, 1.0)
    return ru.cagr(o[:, 0], n / 252), o, EU
out = {}
# ---------------- real NDX
C = std.contexts(); c = C['real_ndx_86_14']; X = c.X if hasattr(c, 'X') else None
R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX'); F = ov.flags_hist(X)
i86 = X.index.searchsorted(pd.Timestamp('1986-01-02'))
Lfull = ac3.prep()['real_ndx_86_14']['L'][0]          # executed levels from 1986-01-02 (continuing model)
months = pd.date_range('1988-01-01', '2009-12-01', freq='MS'); rows = []
for m in months:
    im = X.index.searchsorted(m); k = im - i86
    cf = ov.Ctx(X, F, np.arange(im - W, len(X))[None, :]); Lf = levels_of(cf)
    r = cf.r; rf = cf.rf
    gA, oA, _ = acct1(r, rf, Lf); gB, oB, _ = acct1(r, rf, Lfull[k:][None, :])
    # freeze at m for 5 years (then continuing levels resume is irrelevant: we score the 5 years)
    n5 = 5 * 252; Lz = np.full((1, n5), Lfull[k]); rr = r[:, :W + n5]; rff = rf[:, :W + n5]
    gZ, _, _ = acct1(rr, rff, Lz); gC, _, _ = acct1(rr, rff, Lfull[k:k + n5][None, :])
    rows.append(dict(m=m.strftime('%Y-%m'), fresh=float(gA[0]), cont=float(gB[0]), d_cont_minus_fresh=float(gB[0] - gA[0]),
                     same_level_share=float(np.mean(np.abs(Lf[0] - Lfull[k:]) < 1e-9)), frozen_level=float(Lfull[k]),
                     freeze5=float(gZ[0]), cont5=float(gC[0]), d_freeze5=float(gZ[0] - gC[0])))
d = np.array([x['d_cont_minus_fresh'] for x in rows]); z = np.array([x['d_freeze5'] for x in rows])
out['real_ndx_start_months'] = dict(n=len(rows), d_med=float(np.median(d)), p_cont_better=float(np.mean(d > 1e-6)), p_equal=float(np.mean(np.abs(d) <= 1e-6)),
    d_p10=float(np.percentile(d, 10)), d_p90=float(np.percentile(d, 90)), same_level_share_med=float(np.median([x['same_level_share'] for x in rows])))
out['real_ndx_freeze5'] = dict(n=len(rows), d_med=float(np.median(z)), d_p10=float(np.percentile(z, 10)), d_min=float(z.min()),
    worst=min(rows, key=lambda x: x['d_freeze5']), p_worse=float(np.mean(z < -1e-6)))
out['real_ndx_rows'] = rows
print('real start months', out['real_ndx_start_months'], flush=True); print('freeze5', {k: v for k, v in out['real_ndx_freeze5'].items() if k != 'worst'}, out['real_ndx_freeze5']['worst'], flush=True)
# ---------------- dev250 paths
cp = C['dev250_path']; Lp = ac3.prep()['dev250_path']['L']; Rp = ac3.prep()['dev250_path']['R']; RFp = ac3.prep()['dev250_path']['RF']
out['dev250_restart'] = {}
for y in (5, 10, 15):
    s = y * 252
    a, b, P, blk, seed = std.iv.POOLS['dev250']; Rd, Md = jp.calendar(a, b); Xd = jp.mkX(Rd, Md, 'NDX'); Fd = ov.flags_hist(Xd)
    cf = ov.Ctx(Xd, Fd, cp.ii[:, s:]); cf.F = {k: v[:, s:] for k, v in cp.F.items()}; cf._c = {}
    Lf = levels_of(cf)
    gA, oA, EA = acct1(Rp[:, s:], RFp[:, s:], Lf); gB, oB, EB = acct1(Rp[:, s:], RFp[:, s:], Lp[:, s:])
    dd = gB - gA; mA = (EA / np.maximum.accumulate(EA, 1) - 1).min(1); mB = (EB / np.maximum.accumulate(EB, 1) - 1).min(1)
    out['dev250_restart']['year%d' % y] = dict(horizon=30 - y, fresh_p50=float(np.median(gA)), cont_p50=float(np.median(gB)), d_med=float(np.median(dd)),
        p_cont_better=float(np.mean(dd > 1e-6)), fresh_p10=float(np.percentile(gA, 10)), cont_p10=float(np.percentile(gB, 10)),
        fresh_dd80=float(np.mean(mA <= -0.8)), cont_dd80=float(np.mean(mB <= -0.8)), level_same_share=float(np.mean(np.abs(Lf - Lp[:, s:]) < 1e-9)))
    print('dev250 restart', y, out['dev250_restart']['year%d' % y], flush=True)
json.dump(out, open('/mnt/project-files/research/ru1/results/c3_restart.json', 'w'), indent=1)
