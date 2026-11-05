# Data-quality check only: does the max-|market-adjusted return| day per firm-quarter recur
# at the same position each year (as earnings dates do)? No forward returns are used.
import lzma, io, sys, numpy as np
b = lzma.open(sys.argv[1]).read()
z = np.load(io.BytesIO(b), allow_pickle=False)
dates = z['dates']; adj = z['adj'].astype(np.float64); T, N = adj.shape
mem = np.unpackbits(z['member'], axis=0)[:T].astype(bool)
d = dates.astype('datetime64[D]')
yr = d.astype('datetime64[Y]').astype(int) + 1970
mo = d.astype('datetime64[M]').astype(int) % 12  # 0..11
r = np.full_like(adj, np.nan); r[1:] = adj[1:] / adj[:-1] - 1
r[~mem] = np.nan
r[np.abs(r) > 0.5] = np.nan
mkt = np.nanmedian(r, axis=1)
ar = np.abs(r - mkt[:, None])
qid = (yr - 1968) * 4 + mo // 3
nq = qid.max() + 1
# position of day within quarter (trading-day index)
pos = np.zeros(T, int); monthpos = mo % 3
for q in range(nq):
    idx = np.where(qid == q)[0]; pos[idx] = np.arange(len(idx))
maxpos = np.full((nq, N), -1); maxmon = np.full((nq, N), -1); ratio = np.full((nq, N), np.nan)
for q in range(nq):
    idx = np.where(qid == q)[0]
    blk = ar[idx]
    ok = (np.isfinite(blk).sum(0) >= 55)
    if not ok.any(): continue
    bb = np.where(np.isfinite(blk), blk, -1)
    am = bb.argmax(0)
    s = np.sort(bb, 0)
    maxpos[q, ok] = pos[idx][am][ok]; maxmon[q, ok] = monthpos[idx][am][ok]
    med = np.nanmedian(np.where(blk >= 0, blk, np.nan), 0)
    ratio[q, ok] = (s[-1] / med)[ok]
qyear = 1968 + np.arange(nq) // 4
print('decade  n_pairs  recur4q(|dpos|<=3)  chance  recur1q  sameMonth4q  chance_month  medianMax/medAbs')
for lo, hi in [(1970,1979),(1980,1989),(1990,1999),(2000,2007),(2008,2014)]:
    rows = []
    for q in range(4, nq):
        if not (lo <= qyear[q] <= hi): continue
        a, p4, p1 = maxpos[q], maxpos[q-4], maxpos[q-1]
        ok = (a >= 0) & (p4 >= 0) & (p1 >= 0)
        rows.append((np.abs(a-p4)[ok] <= 3, np.abs(a-p1)[ok] <= 3, (maxmon[q]==maxmon[q-4])[ok], ratio[q][ok]))
    rec4 = np.concatenate([x[0] for x in rows]); rec1 = np.concatenate([x[1] for x in rows])
    sm = np.concatenate([x[2] for x in rows]); rt = np.concatenate([x[3] for x in rows])
    # chance: shuffle partner firm within the same quarter
    rng = np.random.default_rng(0); ch = []; chm = []
    for q in range(4, nq):
        if not (lo <= qyear[q] <= hi): continue
        a, p4 = maxpos[q], maxpos[q-4]; ok = np.where((a >= 0) & (p4 >= 0))[0]
        if len(ok) < 2: continue
        perm = rng.permutation(ok)
        ch.append(np.abs(a[ok]-p4[perm]) <= 3); chm.append(maxmon[q][ok] == maxmon[q-4][perm])
    ch = np.concatenate(ch); chm = np.concatenate(chm)
    print(f'{lo}-{hi} {len(rec4):8d} {rec4.mean():.3f} {ch.mean():.3f} {rec1.mean():.3f} {sm.mean():.3f} {chm.mean():.3f} {np.nanmedian(rt):.1f}')
