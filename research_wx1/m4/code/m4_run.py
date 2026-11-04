"""WX1-M4 discovery run: every rule of results/rules.jsonl on Env(end=1999-12-31) (no post-1999 row is read), monthly
log-growth difference vs always-1x NDX (and vs s0.85 real pre-tax stream) for 1964-01..1999-12.
Also a causality check (truncate at 1990-12-31, the overlapping months must be identical) on a fixed sample.
Out: results/disc_D.npy (months x N, vs 1x), results/disc_D085.npy (vs s0.85), results/disc_meta.json"""
import os, sys, json, time, numpy as np, pandas as pd
from multiprocessing import Pool
S = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m4/'
sys.path.insert(0, S + 'code'); os.environ['NUMBA_CACHE_DIR'] = S + 'nb'
END = '1999-12-31'
_E = None; _REF = None


def s085_aligned(env):
    s = pd.read_pickle(S + 'data/s085_stream.pkl')
    d = env.idx[env.t0:]
    return s.reindex(d).fillna(0.0).values


def init(end):
    global _E, _REF
    import warnings; warnings.filterwarnings('ignore')
    from m4eng import Env
    _E = Env(end=end, start_eval='1964-01-02'); _REF = s085_aligned(_E)


def one(x):
    import m4rules as MR
    try:
        r, ntr = MR.run_rule(_E, x['rule'])
        d1 = _E.monthly_diff(r); d2 = _E.monthly_diff(r, _REF)
        yrs = len(r) / 252
        eq = np.cumprod(1 + r); mdd = float(np.min(eq / np.maximum.accumulate(eq) - 1))
        return x['id'], d1.astype(np.float32), d2.astype(np.float32), float(eq[-1] ** (1 / yrs) - 1), mdd, ntr / yrs, None
    except Exception as e:
        return x['id'], None, None, None, None, None, repr(e)[:200]


def run(rules, end, procs=4):
    with Pool(procs, initializer=init, initargs=(end,)) as p:
        out = p.map(one, rules, chunksize=20)
    return out


if __name__ == '__main__':
    import warnings; warnings.filterwarnings('ignore')
    if not os.path.exists(S + 'data/s085_stream.pkl'):
        import m4ms1 as MS
        MS.s085_stream().to_pickle(S + 'data/s085_stream.pkl')
    rules = [json.loads(l) for l in open(S + 'results/rules.jsonl')]
    t = time.time()
    # causality: 200 fixed rules (every 73rd) at end 1990-12-31 vs 1999-12-31, compare common months
    samp = rules[::73]
    a = run(samp, '1990-12-31'); b = run(samp, END)
    worst = 0.0
    for (i, d1, *_), (j, e1, *_) in zip(a, b):
        if d1 is None or e1 is None: continue
        worst = max(worst, float(np.max(np.abs(d1 - e1[:len(d1)]))))   # 1990-12-31 closes a full month
    print('causality worst abs diff (monthly):', worst, 'n', len(samp), round(time.time() - t), 's', flush=True)
    out = run(rules, END)
    N = len(rules); errs = [(i, e) for i, *_, e in out if e]
    M = len(next(o[1] for o in out if o[1] is not None))
    D = np.zeros((M, N), np.float32); D85 = np.zeros((M, N), np.float32)
    meta = dict(N=N, months=M, errors=errs[:50], n_err=len(errs), causality_worst=worst, cagr=[None] * N, mdd=[None] * N, tpy=[None] * N)
    for i, d1, d2, cg, mdd, tpy, e in out:
        if e: continue
        D[:, i] = d1; D85[:, i] = d2; meta['cagr'][i] = cg; meta['mdd'][i] = mdd; meta['tpy'][i] = tpy
    np.save(S + 'results/disc_D.npy', D); np.save(S + 'results/disc_D085.npy', D85)
    json.dump(meta, open(S + 'results/disc_meta.json', 'w'))
    print('done N', N, 'months', M, 'errors', len(errs), round(time.time() - t), 's')
