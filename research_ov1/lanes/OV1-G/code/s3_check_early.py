"""OV1-G implementation check, EARLY data only (<=1999-12-31). Diagnostic only (no new variant, not in N).
(1) Independent re-derivation of the off-meeting events from the raw CSVs in plain Python (no sig_g), compared with sig_g.events.
(2) Brute-force ON at every early block date (SPX 1982-85, NDX 1986-99) from the usable dates, compared with sig_g.on_series.
(3) v1_B from era() equals std.contexts() real contexts on the early block dates."""
import sys, csv, json, datetime as dtm, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/lanes/OV1-G/code'); sys.path.insert(0, '/mnt/project-files/research/ov1/code')
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code')
import ov1lib as L, gate, sig_g, jp, ov, std  # noqa
D = '/mnt/project-files/research/ov1/lanes/OV1-G/data/'; E = pd.Timestamp('1999-12-31')
# (1) plain re-derivation
rows = [(dtm.date.fromisoformat(a), float(b)) for a, b in list(csv.reader(open(D + 'cut_DFEDTAR.csv')))[1:]]
fe = list(csv.DictReader(open(D + 'fomc_events_1982_2014.csv')))
mtg = {r['date'] for r in fe if r['kind'] == 'meeting'}; call = {r['date'] for r in fe if r['kind'] != 'meeting'}
after = set()
for r in fe:
    if r['kind'] == 'meeting' and r['day_of_event'] == r['n_days']:
        d = dtm.date.fromisoformat(r['date']) + dtm.timedelta(days=1)
        while d.weekday() >= 5: d += dtm.timedelta(days=1)
        after.add(d.isoformat())
ev = [d for (d, v), (_, v0) in zip(rows[1:], rows[:-1]) if v < v0 and d.isoformat() not in mtg and (d.isoformat() not in after or d.isoformat() in call)]
ev_e = [d for d in ev if d <= dtm.date(1999, 12, 31)]
R, M = jp.calendar('1984-01-03', '2014-12-31'); XN = jp.mkX(R, M, 'NDX'); ncal = XN.index
R2, M2 = jp.calendar('1928-01-03', '1985-12-31'); XS = jp.mkX(R2, M2, 'SPX'); scal = XS.index
sg = [x.date() for x in sig_g.cuts().query("kind == 'off'").date if x <= E]
print('(1) plain events <=1999:', len(ev_e), 'sig_g:', len(sg), 'equal:', ev_e == sg)
# (2) brute-force ON on early block dates
res = {}
for nm, cal, stream, a, b, st, lo, hi in (('SPX', scal, 'SPX', '1928-01-03', '1985-12-31', '1955-01-03', '1982-09-27', '1985-12-31'),
                                          ('NDX', ncal, 'NDX', '1984-01-03', '2014-12-31', '1986-01-02', '1986-01-02', '1999-12-31')):
    lab = gate._frame(stream, a, b, st); pos = cal.get_indexer(lab.index); end = cal[np.minimum(pos + 23, len(cal) - 1)]
    blk = lab[(lab.index >= pd.Timestamp(lo)) & (end <= pd.Timestamp(hi))]
    us = []
    for d in ev_e:
        d = pd.Timestamp(d)
        if d < cal[0] or d >= cal[-1]: continue
        later = cal[cal > d]; us.append(later[0])          # all early events are pre-1994 except 1998-10-15
        if d >= pd.Timestamp('1994-02-04'): us[-1] = cal[cal >= d][0]
    upos = [cal.get_loc(u) for u in us]
    br = pd.Series([any(p <= cal.get_loc(t) <= p + 41 for p in upos) for t in blk.index], index=blk.index)
    on = sig_g.on_series(cal).reindex(blk.index)
    res[nm] = dict(n_blocks=len(blk), on_blocks_brute=int(br.sum()), mismatches=int((br != on).sum()))
    print('(2)', nm, res[nm])
# (3) v1 B vs std.contexts()
C = std.contexts(); chk = {}
for nm, bn, X, st in (('NDX', 'real_ndx_86_14', XN, '1986-01-02'), ('SPX', 'real_spx_55_85', XS, '1955-01-03')):
    c = C[bn]; Bstd = pd.Series(L.v1_B(c)[0], index=c.X.index[c.ii[0]] if hasattr(c, 'X') else X.index[c.ii[0]])
    F = ov.flags_hist(X); i0 = X.index.searchsorted(pd.Timestamp(st)) - ov.WARM
    c2 = ov.Ctx(X, F, np.arange(i0, len(X))[None, :]); B2 = pd.Series(L.v1_B(c2)[0], index=X.index[c2.ii[0]])
    m = (B2.index <= E) & (B2.index >= pd.Timestamp('1982-09-27'))
    chk[nm] = dict(days=int(m.sum()), mismatches=int((Bstd.reindex(B2.index[m]) != B2[m]).sum()))
    print('(3)', nm, chk[nm])
json.dump(dict(plain_events_le1999=len(ev_e), sig_g_events_le1999=len(sg), events_equal=bool(ev_e == sg), on_check=res, v1B_check=chk),
          open('/mnt/project-files/research/ov1/lanes/OV1-G/results/s3_check_early.json', 'w'), indent=1)
