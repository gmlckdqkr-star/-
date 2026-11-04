"""WS1 B: achievable accuracy of pre-registered price/volume signals per shape (US500, KRALL; h 1,5,21). <=2014.
Signals use data <= decision close t only. US windows read prices only from first S&P 500 membership (lab rule)."""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/wide_shape/code')
import wsdata as D, wsstk as S

univ = sys.argv[1]; hs = [int(x) for x in sys.argv[2].split(',')]
SPLIT = {'US500': '1993-01-01', 'KRALL': '2007-01-01'}[univ]


def roll_max(x, W):
    out = np.full(x.shape, np.nan)
    from numpy.lib.stride_tricks import sliding_window_view
    v = sliding_window_view(x, W, axis=0)          # [T-W+1, N, W]
    out[W - 1:] = np.nanmax(v, axis=-1) if not np.all(np.isnan(x)) else np.nan
    return out


def pct_rank_rows(a):
    """row-wise percentile rank in [0,1], nan stays nan"""
    o = np.full(a.shape, np.nan)
    for b in range(a.shape[0]):
        m = ~np.isnan(a[b])
        if m.sum() > 1:
            v = a[b, m]; r = np.argsort(np.argsort(v + 1e-12 * np.random.default_rng(b).standard_normal(v.shape)))
            o[b, m] = r / (m.sum() - 1)
    return o


def signals_us(U):
    adj = U['adj'].copy(); mem = U['member']
    first = np.where(mem.any(0), np.argmax(mem, axis=0), adj.shape[0])
    rows = np.arange(adj.shape[0])[:, None]
    adj[rows < first[None, :]] = np.nan                     # prices only from first membership
    r1 = adj / np.vstack([np.full((1, adj.shape[1]), np.nan), adj[:-1]]) - 1
    lag = lambda a, k: np.vstack([np.full((k, a.shape[1]), np.nan), a[:-k]])
    sig = {}
    sig['REV1'] = -r1
    sig['REV5'] = -(adj / lag(adj, 5) - 1)
    sig['REV21'] = -(adj / lag(adj, 21) - 1)
    sig['MOM'] = lag(adj, 21) / lag(adj, 252) - 1
    sig['HI52'] = adj / roll_max(adj, 252)
    sig['MAXL'] = -roll_max(r1, 21)
    lr = np.log1p(r1); c = pd.DataFrame(lr).rolling(63, min_periods=60).std().values
    sig['LVOL'] = -c
    return sig


def signals_kr(K, X):
    idx = X['idx']; rc = X['rc']; T, N = idx.shape
    lag = lambda a, k: np.vstack([np.full((k, a.shape[1]), np.nan), a[:-k]])
    sig = {}
    sig['REV1'] = np.where(X['trade'], -rc, np.nan)
    sig['REV5'] = -(idx / lag(idx, 5) - 1)
    sig['REV21'] = -(idx / lag(idx, 21) - 1)
    sig['MOM'] = lag(idx, 21) / lag(idx, 252) - 1
    sig['HI52'] = idx / roll_max(idx, 252)
    sig['MAXL'] = -roll_max(np.where(X['listed'], rc, np.nan), 21)
    sig['LVOL'] = -pd.DataFrame(np.where(X['listed'], np.log1p(rc), np.nan)).rolling(63, min_periods=60).std().values
    amt = np.where(X['listed'], np.nan_to_num(K['amount']), np.nan)
    a5 = pd.DataFrame(amt).rolling(5, min_periods=5).sum().values; a60 = pd.DataFrame(amt).rolling(60, min_periods=60).sum().values
    sig['VSHK'] = a5 / np.where(a60 > 0, a60, np.nan)
    sig['SIZE'] = -np.log(np.where(K['marcap'] > 0, K['marcap'], np.nan))
    hi, lo, cl, op = K['high'], K['low'], K['close'], K['open']
    rng_ = hi - lo
    sig['CLV'] = np.where(X['trade'], -np.where(rng_ > 0, (cl - lo) / np.where(rng_ > 0, rng_, 1), 0.5), np.nan)
    k = idx / np.where(cl > 0, cl, np.nan)
    sig['GAP'] = np.where(X['trade'] & (op > 0), -(op * k / lag(idx, 1) - 1), np.nan)
    lu = X['limup'].astype(float)
    sig['LIMUP'] = np.where(X['listed'], pd.DataFrame(lu).rolling(5, min_periods=1).max().values, np.nan)
    il = np.where(X['trade'] & (amt > 0), np.abs(rc) / np.where(amt > 0, amt, np.nan) * 1e9, np.nan)
    sig['ILLQ'] = pd.DataFrame(il).rolling(21, min_periods=15).mean().values
    return sig


t0 = time.time()
if univ == 'US500':
    U = D.load_us(); SIG = signals_us(U); base = ['REV1', 'REV5', 'REV21', 'MOM', 'HI52', 'MAXL', 'LVOL']; cname = 'COMBO7'
else:
    K_ = D.load_kr(); X_ = D.kr_derived(K_); SIG = signals_kr(K_, X_)
    base = ['REV1', 'REV5', 'REV21', 'MOM', 'HI52', 'MAXL', 'LVOL', 'VSHK', 'SIZE', 'CLV', 'GAP', 'LIMUP', 'ILLQ']; cname = 'COMBO13'
print('signals', '%.0fs' % (time.time() - t0), flush=True)
for h in hs:
    B = S.build_us(U, h) if univ == 'US500' else S.build_kr(K_, X_, h)
    split = int(np.searchsorted(B.dates.values, np.datetime64(SPLIT)))
    res = {'univ': univ, 'h': h, 'split_block': split, 'signals': {}}
    P = {}
    for nm in base:
        P[nm] = pct_rank_rows(np.where(B.elig, SIG[nm][B.t_dec], np.nan))
    allr = np.stack([P[nm] for nm in base[:7]]); P['COMBO7'] = np.nanmean(allr, 0) if True else None
    if univ == 'KRALL':
        P['COMBO13'] = np.nanmean(np.stack([P[nm] for nm in base]), 0)
    m10 = np.ceil(0.10 * B.n).astype(int); m1 = np.ceil(0.01 * B.n).astype(int)
    top10 = B.elig & (B.rk >= (B.n - m10)[:, None]); top1 = B.elig & (B.rk >= (B.n - m1)[:, None])
    for nm, s in P.items():
        s = np.where(B.elig, s, np.nan)
        s = s + 1e-9 * np.random.default_rng(7).standard_normal(s.shape)     # random tie-break
        d = {}
        for part, sl in (('all', slice(None)), ('A', slice(0, split)), ('B', slice(split, None))):
            Bp = S.Blocks(); Bp.elig = B.elig[sl]; Bp.rk = B.rk[sl]
            ic, it, nb = S.spearman_ic(Bp, s[sl])
            d['ic_' + part] = ic; d['t_' + part] = it
        pk = S.topk_from_signal(s, 20)
        for K in (5, 20):
            p = pk[:, :K]; v = p >= 0
            rows = np.arange(p.shape[0])[:, None]
            d['prec10_K%d' % K] = float(np.mean(top10[rows, np.where(v, p, 0)][v]))
            d['prec1_K%d' % K] = float(np.mean(top1[rows, np.where(v, p, 0)][v]))
            r, g, c = S.run_picks(B, p)
            re, rsm, p10 = S.perf(B, r)
            # halves (real path only)
            BA = S.Blocks(); BA.h = h; BA.years = B.years[:split]; BA.tax = B.tax
            BB = S.Blocks(); BB.h = h; BB.years = B.years[split:]; BB.tax = B.tax
            d['K%d' % K] = dict(real=re, res=rsm, gross_yr=float(g.mean() * 252 / h), cost_yr=float(c.mean() * 252 / h),
                                real_A=S.perf(BA, r[:split])[0], real_B=S.perf(BB, r[split:])[0])
        res['signals'][nm] = d
        print(univ, h, '%-8s IC %.4f (A %.4f / B %.4f, t %.1f) prec10 %.3f prec1 %.3f | K5 %.3f (A %.3f B %.3f) K20 %.3f' % (
            nm, d['ic_all'], d['ic_A'], d['ic_B'], d['t_all'], d['prec10_K5'], d['prec1_K5'], d['K5']['real'], d['K5']['real_A'], d['K5']['real_B'], d['K20']['real']),
            '%.0fs' % (time.time() - t0), flush=True)
    # random baseline precision
    res['base_prec10'] = 0.10; res['base_prec1'] = 0.01
    json.dump(res, open('/mnt/project-files/research/wide_shape/results/b_%s_h%d.json' % (univ, h), 'w'), indent=1)
