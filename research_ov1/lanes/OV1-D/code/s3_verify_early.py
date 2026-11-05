"""OV1-D independent re-check of the EARLY kill test (no unseen data). Re-parses the RAW BoJ csv (not the cut file),
recomputes thresholds with a hand-written linear percentile and finds the latest release per block by a plain loop,
then recounts universe / on-blocks / hits and compares with results/killA_early.json. Also reports v1 day shares in the
early window, release-level on counts (<= 1999 only) and how many <= 1999 releases a 100/3 percentile would flip (info).
Run: ~/.cache/lab/ms1-venv/bin/python -B s3_verify_early.py"""
import sys, io, json, math, numpy as np, pandas as pd
CODE = '/mnt/project-files/research/ov1/lanes/OV1-D/code'; LANE = '/mnt/project-files/research/ov1/lanes/OV1-D/'
for p in (CODE, '/mnt/project-files/research/ov1/code', '/mnt/project-files/research/breakthrough/code'): sys.path.insert(0, p)
import ov1lib as L, gate, jp, ov  # noqa
E = json.load(open(LANE + 'results/killA_early.json')); assert E['early_pass'] is False

lines = open(LANE + 'data/boj_tankan_raw.csv', encoding='utf-8').read().splitlines()
k = [i for i, l in enumerate(lines) if l.startswith('SERIES_CODE,')][0]
vals = {}
for l in lines[k + 1:]:
    f = l.split(','); code, q, v = f[0], int(f[-2]), f[-1]
    vals[(code, q)] = float('nan') if v == 'null' else float(v)
qs = sorted({q for (_, q) in vals})
cal = jp.calendar('1928-01-03', '2014-12-31')[0].index
rels = []
for q in qs:
    y, n = divmod(q, 100); m = 3 * n + 2; yy, mm = (y, m) if m <= 12 else (y + 1, m - 12)
    u0 = pd.Timestamp(yy, mm, 1)
    if u0 > cal[-1]: continue
    u = cal[cal >= u0][0]
    s = ((vals[('TK99F1000601GCQ01000', q)] - vals[('TK99F1000601GCQ11000', q)]) +
         (vals[('TK99F1150601GCQ01000', q)] - vals[('TK99F1150601GCQ11000', q)])) / 2
    if q == 200401: s = float('nan')
    rels.append([q, u, s])

def pct(xs, qq):
    x = sorted(xs); h = (len(x) - 1) * qq / 100; lo = int(math.floor(h))
    return x[lo] if lo + 1 >= len(x) else x[lo] + (h - lo) * (x[lo + 1] - x[lo])

for qq, key in ((33.33, 'on'), (100 / 3, 'on_alt')):
    for r in rels:
        prior = [x[2] for x in rels if x[1] < r[1] and not math.isnan(x[2])]
        thr = pct(prior, qq) if len(prior) >= 20 and not math.isnan(r[2]) else float('nan')
        r.append((not math.isnan(thr)) and r[2] <= thr)

def on_at(t):
    last = None
    for r in rels:
        if r[1] <= t: last = r
    return bool(last[3]) if last is not None else False

def v1(stream, a, b, start):
    R, M = jp.calendar(a, b); X = jp.mkX(R, M, stream); F = ov.flags_hist(X)
    i0 = X.index.searchsorted(pd.Timestamp(start)) - ov.WARM
    c = ov.Ctx(X, F, np.arange(i0, len(X))[None, :]); return pd.Series(L.v1_B(c)[0], index=X.index[c.ii[0]]), X.index

out = {}
Bs, cs = v1('SPX', '1928-01-03', '1985-12-31', '1955-01-03'); Bn, cn = v1('NDX', '1984-01-03', '2014-12-31', '1986-01-02')
ls = gate._frame('SPX', '1928-01-03', '1985-12-31', '1955-01-03'); ln = gate._frame('NDX', '1984-01-03', '2014-12-31', '1986-01-02')
eras = [('SPX_1979_1985', [t for t in ls.index if pd.Timestamp('1979-08-01') <= t <= pd.Timestamp('1985-12-31')], ls, Bs),
        ('NDX_1986_1999', [t for t in ln.index if t >= pd.Timestamp('1986-01-02') and cn[cn.get_loc(t) + 23] <= pd.Timestamp('1999-12-31')], ln, Bn)]
num = den = 0; ok = True
for name, ts, lab, B in eras:
    uni = [t for t in ts if B[t] == 3]; on = [t for t in uni if on_at(t)]
    base = float(np.mean([lab[t] for t in uni])); hit = float(np.mean([lab[t] for t in on]))
    ref = [r for r in E['eras'] if r['era'] == name][0]
    same = (len(uni) == ref['n_universe'] and len(on) == ref['n_on'] and abs(base - ref['base']) < 1e-12 and abs(hit - ref['hit_on']) < 1e-12)
    ok &= same; num += len(on) * (base - hit); den += len(on)
    sh = B[(B.index >= ts[0]) & (B.index <= ts[-1])].value_counts(normalize=True)
    out[name] = dict(n_universe=len(uni), n_on=len(on), base=base, hit_on=hit, matches_killA=same,
                     v1_day_share={str(k): float(v) for k, v in sh.items()})
out['drop_recomputed'] = num / den; out['drop_matches'] = abs(num / den - E['drop_era_matched']) < 1e-12 and ok
er = [r for r in rels if r[1] <= pd.Timestamp('1999-12-31')]
out['releases_le1999'] = dict(with_threshold=sum(1 for r in er if r[1] >= pd.Timestamp('1979-11-01')),
                              on=sum(1 for r in er if r[3]), on_quarters=[r[0] for r in er if r[3]],
                              flipped_by_100_3=sum(1 for r in er if r[3] != r[4]))
# v1 share over 1988-01-04..1999-12-31 for comparison with OV1-A's independently built v1 (82.4% 3x, 7.6% 1x, 10.0% cash)
s = Bn[(Bn.index >= pd.Timestamp('1988-01-04')) & (Bn.index <= pd.Timestamp('1999-12-31'))].value_counts(normalize=True)
out['v1_share_1988_1999'] = {str(k): float(v) for k, v in s.items()}
print(json.dumps(out, indent=1))
json.dump(out, open(LANE + 'results/s3_verify_early.json', 'w'), indent=1)
