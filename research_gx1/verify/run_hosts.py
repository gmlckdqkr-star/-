import sys; sys.path.insert(0, '/tmp/claude-0/gx1verify')
from myinv import *
W = ov.WARM
HOSTS = ['UK', 'CA', 'AU', 'DE', 'FR', 'CH', 'JP', 'KR', 'NL', 'ES', 'IT', 'BE', 'AT', 'IE', 'GR', 'MX', 'ZA', 'NZ']
def build(m):
    s = load_index(m); X = pd.DataFrame(index=s.index); X['r'] = s.pct_change().fillna(0.0)
    s3, sl = rate_ids(m)
    X['y3m'] = rate_on(s3, X.index, False); X['y10'] = rate_on(sl, X.index, False)   # AT2: plain ffill, no stale rule
    ok = X[['y3m', 'y10']].notna().all(axis=1); first = ok.idxmax()
    # cross-check: first row with both rates also under the signal stale rule
    ok2 = ~np.isnan(rate_on(s3, X.index, True)) & ~np.isnan(rate_on(sl, X.index, True)); assert X.index[np.argmax(ok2)] == first
    X[['y3m', 'y10']] = X[['y3m', 'y10']].fillna(0.0); X['rf'] = X['y3m'] / 100 / 252; X['cs'] = 0.0; X['vix'] = np.nan
    X['rb'] = mkt.bond10(X); X['p'] = (1 + X['r']).cumprod()
    i0 = max(0, X.index.get_loc(first) + 378 - W)
    return X, i0
def acct(X, F, rows, g=None):
    c = ov.Ctx(X, F, rows[None, :]); B, bfn, bp, fs = std.s085(c); B = np.array(B, dtype=np.float64)
    if g is not None: B = np.where(g[c.ii], np.minimum(B, 1.0), B)
    cg, E = std.engine(c, B, bfn, bp, fs, cspr=10.0); return float(cg[0])
lens = {}
for h in HOSTS:
    X, i0 = build(h); lens[h] = (len(X) - i0, len(X) - i0 - W)
Nmin = min(v[0] for v in lens.values()); J = (Nmin - 1008) // 63 + 1
print('rows per host (acct, scored):', lens); print('N_min', Nmin, 'J', J, 'min scored', min(v[1] for v in lens.values()))
ref = json.load(open('/mnt/project-files/research/gx1/results/foreign_le2014.json'))
out = {}
for h in ['CH', 'IE']:
    X, i0 = build(h); F = ov.flags_hist(X); n = len(X); rows = np.arange(i0, n)
    share, den, K, units, per = inv_share(X.index, h, verbose=True)
    g = np.nan_to_num(share, nan=-1.0) >= 0.40
    v1 = acct(X, F, rows); r24 = acct(X, F, rows, g); d = r24 - v1
    ds = []
    for j in range(J):
        s = 504 + 63 * j; gs = g.copy(); gs[rows] = g[np.roll(rows, s)]; ds.append(acct(X, F, rows, gs) - v1)
    e = d - float(np.median(ds))
    sc = slice(i0 + W, n)
    H = ref['hosts'][h]
    print('%s scored_from %s rows %d | mine: v1 %.10f rule24 %.10f d24 %.10f e24 %.10f on %.6f valid %.4f medden %.1f'
          % (h, X.index[i0 + W].date(), n - i0 - W, v1, r24, d, e, g[sc].mean(), (~np.isnan(share[sc])).mean(), np.median(den[sc])))
    print('%s json : scored_from %s rows %d v1 %.10f d24 %.10f e24 %.10f on %.6f valid %.4f'
          % (h, H['scored_from'], H['rows'], H['v1'], H['d'][24], H['e'][24], H['signal_on_share'][11], H['signal_valid_share']['INV']))
    print('   diff v1 %.2e d24 %.2e e24 %.2e on %.2e' % (v1 - H['v1'], d - H['d'][24], e - H['e'][24], g[sc].mean() - H['signal_on_share'][11]))
    print('   max |shift d| diff vs json d_shift[24]: %.2e' % np.max(np.abs(np.array(ds) - np.array(H['d_shift'][24]))))
    sp = spells(X.index[i0 + W:], g[i0 + W:])
    print('   ON spells >=20 rows (scored):', [(a, b, c) for (o, a, b, c) in sp if o and c >= 20])
    r = X['r'].values[i0 + W:]; k = np.argsort(np.abs(r))[-4:]
    print('   largest |daily r| on scored rows:', [(str(X.index[i0 + W + q].date()), round(float(r[q]), 4)) for q in k])
    out[h] = dict(v1=v1, r24=r24, d24=d, e24=e)
json.dump(out, open('/tmp/claude-0/gx1verify/hosts_out.json', 'w'), indent=1)
