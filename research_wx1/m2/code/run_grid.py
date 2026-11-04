"""M2 generated grid (PRECOMMIT_M2 §4-5): 17 subsets x 3 weightings x 2 sector-neutral x 2 crash filter x
[C0/C1/C2 gates x 5 K x 3 rebalance + C3/C4/C5 x 5 K x 3 rebalance] = 18,360 variants.
mode 'disc': decisions 1986-01..1999-12 only -> X [168, N] monthly excess log return vs EW (pre-tax, after cost).
mode 'conf': recompute only the variant ids listed in argv[4] on decisions 2000-01..2014-12 (one shot).
argv: code_dir mode out_npz [ids_json]"""
import sys, json, time, itertools, numpy as np, pandas as pd
sys.path.insert(0, sys.argv[1])
import m2lib as M
mode, outp = sys.argv[2], sys.argv[3]
t0 = time.time()
log = lambda *a: print(f'[{time.time() - t0:6.0f}s]', *a, flush=True)
d = M.load()
z = np.load(M.SCR + '/ic_cache.npz'); ic, C = z['ic'], z['C']
if mode == 'disc':
    j0 = int(np.searchsorted(d.dd, pd.Timestamp('1986-01-01'))); j1 = int(np.searchsorted(d.dd, pd.Timestamp('2000-01-01')))
else:
    j0 = int(np.searchsorted(d.dd, pd.Timestamp('2000-01-01'))); j1 = d.nd
rows = range(j0, j1); rs = slice(j0, j1)
SUBS = list(M.subsets(d).keys()); sub = M.subsets(d); DEF = M.def_mask(d)
WK = ['EQ', 'ICW', 'RIDGE']; KS = [5, 10, 20, 30, 50]; RB = ['M', 'Q', 'T']
VAR = []
for S, W, SN, CF in itertools.product(SUBS, WK, (0, 1), (0, 1)):
    for Cn in ('C0', 'C1', 'C2', 'C3', 'C4', 'C5'):
        for K, Rb in itertools.product(KS, RB):
            VAR.append(dict(S=S, W=W, SN=SN, CF=CF, C=Cn, K=K, Rb=Rb))
NV = len(VAR)
VIX = {tuple(v.values()): i for i, v in enumerate(VAR)}
log('variants', NV)
want = None
if mode == 'conf':
    want = set(json.load(open(sys.argv[4])))
est_U = M.past_means(ic, C)
est_T = M.past_means(ic, C, regime=d.up)
est_M = M.past_means(ic, C, regime=d.moff)
rew = M.ew_returns(d, j0, j1)
ones = np.ones(d.nd, np.bool_); gates = {'C0': ones, 'C1': d.up.astype(np.bool_), 'C2': (~d.moff).astype(np.bool_)}
X = np.full((j1 - j0, NV), np.nan); RAW = np.full((j1 - j0, NV), np.nan)
scD = {}
vid = 0
for S, W in itertools.product(SUBS, WK):
    if want is not None and not any(VAR[i]['S'] == S and VAR[i]['W'] == W for i in want):
        continue
    eU = None if W == 'EQ' else est_U
    sc = {}
    sc['U'] = M.composite(d, M.weights(d, sub[S], W, eU, rows=rows), rs)
    if W not in scD:
        scD[W] = M.composite(d, M.weights(d, DEF, W, eU, rows=rows), rs)
    sc['SW'] = np.where(d.up[:, None], sc['U'], scD[W])
    sc['RT'] = M.composite(d, M.weights(d, sub[S], W, est_T, None if W == 'EQ' else est_U, rows=rows), rs)
    sc['RM'] = M.composite(d, M.weights(d, sub[S], W, est_M, None if W == 'EQ' else est_U, rows=rows), rs)
    for SN, CF in itertools.product((0, 1), (0, 1)):
        for cs, cl in (('U', ('C0', 'C1', 'C2')), ('SW', ('C3',)), ('RT', ('C4',)), ('RM', ('C5',))):
            s1 = M.sector_neutral(d, sc[cs], rs) if SN else sc[cs]
            s2 = np.where(d.crash, np.nan, s1) if CF else s1
            pk = None
            for Cn in cl:
                g = gates.get(Cn, ones)
                for K, Rb in itertools.product(KS, RB):
                    i = VIX[(S, W, SN, CF, Cn, K, Rb)]
                    if want is not None and i not in want:
                        continue
                    if pk is None:
                        pk = M.top_picks(s2, 50, rows=rs)
                    r = M.book_returns(pk, K, d.HR, d.CR, g, d.mo, j0, j1, Rb)
                    RAW[:, i] = r
                    X[:, i] = np.log1p(r) - np.log1p(rew)
    log(S, W, 'done')
np.savez(outp, X=X, RAW=RAW, rew=rew, j0=j0, j1=j1, var=json.dumps(VAR))
log('saved', outp)
