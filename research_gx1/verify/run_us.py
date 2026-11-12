import sys; sys.path.insert(0, '/tmp/claude-0/gx1verify')
from myinv import *
R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX'); F = ov.flags_hist(X)
assert X.index.max() <= END
cal = X.index; W = ov.WARM
share, den, K, units, per = inv_share(cal, 'US', verbose=True)
print('K(US) =', len(K), K)
g = np.nan_to_num(share, nan=-1.0) >= 0.40
i0 = X.index.searchsorted(pd.Timestamp('1986-01-02')) - W; ii = np.arange(i0, len(X))[None, :]
sc = ii[0, W:]
print('scored rows', len(sc), cal[sc[0]].date(), '->', cal[sc[-1]].date())
print('signal on share (scored rows): %.10f' % g[sc].mean(), ' valid (den>=5 & >=1989) share: %.10f' % (~np.isnan(share[sc])).mean(),
      ' den>=5 share (ignoring 1989 gate): %.10f' % (den[sc] >= 5).mean(), ' median den: %.1f' % np.median(den[sc]))
r89 = cal >= ON_FROM
print('on share among rows >=1989: %.4f; among valid rows: %.4f' % (g[r89].mean(), g[~np.isnan(share)].mean()))
first_valid = cal[np.argmax(~np.isnan(share))]; print('first valid signal row', first_valid.date(), 'first ON row', cal[np.argmax(g)].date())
# accounting
def run(Bmod=None):
    c = ov.Ctx(X, F, ii); B, bfn, bp, fs = std.s085(c); B = np.array(B, dtype=np.float64)
    if Bmod is not None: B = Bmod(B)
    cg, E = std.engine(c, B, bfn, bp, fs, cspr=10.0); return float(cg[0]), E
v1, Ev = run(); rl, Er = run(lambda B: np.where(g[ii], np.minimum(B, 1.0), B))
print('real_ndx_86_14 v1 CAGR %.10f   rule24 CAGR %.10f   d %.4fpp' % (v1, rl, 100 * (rl - v1)))
mdd = lambda E: float((E[0] / np.maximum.accumulate(E[0]) - 1).min())
print('mdd v1 %.4f rule %.4f' % (mdd(Ev), mdd(Er)))
# how often CAP actually binds
c = ov.Ctx(X, F, ii); B = np.array(std.s085(c)[0], dtype=np.float64)
bind = g[ii][0, W:] & (B[0, W:] > 1.0); print('scored rows where cap binds (B>1 & on): %.4f; B>1 share %.4f' % (bind.mean(), (B[0, W:] > 1).mean()))
# spells 1989-2014
m = cal >= ON_FROM; d89 = cal[m]; g89 = g[m]
sp = spells(d89, g89)
print('n spells total', len(sp), ' ON spells', sum(1 for s in sp if s[0]), ' ON spells >=20 rows', sum(1 for s in sp if s[0] and s[3] >= 20))
print('ON spells >= 20 rows:')
for s in sp:
    if s[0] and s[3] >= 20: print('  ON  %s .. %s  %4d rows' % s[1:])
print('OFF spells >= 120 rows:')
for s in sp:
    if (not s[0]) and s[3] >= 120: print('  OFF %s .. %s  %4d rows' % s[1:])
# yearly on share and share values
yr = pd.Series(g89, index=d89).groupby(d89.year).mean(); sh = pd.Series(share[m], index=d89).groupby(d89.year).median()
dn = pd.Series(den[m], index=d89).groupby(d89.year).median()
print('year on_share median_share median_den'); print(pd.DataFrame({'on': yr.round(3), 'share_med': sh.round(3), 'den_med': dn}).to_string())
np.save('/tmp/claude-0/gx1verify/us_share.npy', share); np.save('/tmp/claude-0/gx1verify/us_den.npy', den)
json.dump(dict(v1=v1, rule=rl, on_share=float(g[sc].mean()), valid_share=float((~np.isnan(share[sc])).mean())), open('/tmp/claude-0/gx1verify/us_out.json', 'w'))
