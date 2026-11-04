import sys, json, numpy as np, pandas as pd, os
os.environ['NUMBA_CACHE_DIR'] = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/verify/numba_cache'
sys.path.insert(0, '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/verify/m2/code')
import m2lib as M
M.SCR = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m2'
d = M.load(os.path.join(M.SCR, 'm2data.npz'), os.path.join(M.SCR, 'coverage.csv'))
z = np.load(M.SCR + '/ic_cache.npz'); ic, C = z['ic'], z['C']
g = np.load(M.SCR + '/grid_disc.npz'); RAW = g['RAW']; rew = g['rew']; VAR = json.loads(str(g['var']))
j0 = int(np.searchsorted(d.dd, pd.Timestamp('1986-01-01'))); j1 = int(np.searchsorted(d.dd, pd.Timestamp('2000-01-01')))
rows = range(j0, j1); rs = slice(j0, j1)
sub = M.subsets(d); est = M.past_means(ic, C)
def my_book(picks, K, gate, sched):
    # verifier: value-tracking book, equal 1/K target at each scheduled decision, cost 0.3% x |trade| (drifted weights)
    hold = {}; cash = 1.0; out = []
    for j in range(j0, j1):
        v0 = cash + sum(hold.values())          # value before this decision's trades (cost belongs to this month)
        if sched[j]:
            tot = cash + sum(hold.values())
            tgt = {} if not gate[j] else {p: None for p in picks[j, :K] if p >= 0}
            tr = sum(abs(tot / K - hold.get(p, 0.0)) for p in tgt) + sum(v for p, v in hold.items() if p not in tgt)
            tot -= 0.003 * tr
            hold = {p: tot / K for p in tgt}; cash = tot - sum(hold.values())
        cash *= 1 + d.CR[j]; hold = {p: v * (1 + d.HR[j, p]) for p, v in hold.items()}
        out.append((cash + sum(hold.values())) / v0 - 1)
    return np.array(out)
def my_ew():
    r = []; wprev = None
    for j in range(j0, j1):
        e = d.elig[j]; w = e / e.sum(); g_ = np.where(e, d.HR[j], 0.0)
        tr = w.sum() if wprev is None else np.abs(w - wprev).sum(); rp = (w * g_).sum()
        r.append((1 - 0.003 * tr) * (1 + rp) - 1); wprev = w * (1 + g_) / (1 + rp)
    return np.array(r)
print('EW max abs diff', np.abs(my_ew() - rew).max())
for vid in (1560, 151, 6):
    v = VAR[vid]; assert v['C'] in ('C0', 'C2') or vid == 151, v
    W = M.weights(d, sub[v['S']], v['W'], None if v['W'] == 'EQ' else est, rows=rows)
    if v['C'] == 'C4':
        est_T = M.past_means(ic, C, regime=d.up)
        W = M.weights(d, sub[v['S']], v['W'], est_T, None if v['W'] == 'EQ' else est, rows=rows)
    sc = M.composite(d, W, rs)
    if v['SN']: sc = M.sector_neutral(d, sc, rs)
    if v['CF']: sc = np.where(d.crash, np.nan, sc)
    pk = M.top_picks(sc, 50, rows=rs)
    gate = (~d.moff) if v['C'] == 'C2' else np.ones(d.nd, bool)
    sched = np.ones(d.nd, bool) if v['Rb'] == 'M' else np.isin(d.mo, [1, 4, 7, 10])
    if v['Rb'] == 'T': continue
    r = my_book(pk, v['K'], gate, sched)
    print(vid, v, 'max abs monthly diff vs worker RAW %.2e' % np.abs(r - RAW[:, vid]).max(), 'ann x %.4f' % ((np.log1p(r) - np.log1p(rew)).mean() * 12))
