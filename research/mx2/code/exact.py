"""MX2 exact re-check on the MS1 engine (F1 costs, 22% tax, liquidation tax, brake s0.85).
Overlay from walk-forward selections -> modified daily target B' on real NDX 1986-2014 and S&P 1966-85."""
import sys, os, json, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/claude-0/nbc')
sys.path.insert(0, '/mnt/project-files/research/measure_std'); sys.path.insert(0, '/mnt/project-files/research/mx2/code')
import std, bk, ov, rx, jp, lib

def ctxs():
    C = dict(std.contexts())
    R, M = jp.calendar('1928-01-03', '1985-12-31'); X = jp.mkX(R, M, 'SPX'); F = ov.flags_hist(X)
    j0 = X.index.searchsorted(pd.Timestamp('1966-01-03')) - ov.WARM
    C['real_spx_66_85'] = ov.Ctx(X, F, np.arange(j0, len(X))[None, :])
    out = {}
    for nm, s, a in (('real_ndx_86_14', 'NDX', '1984-01-03'), ('real_spx_55_85', 'SPX', '1928-01-03'), ('real_spx_66_85', 'SPX', '1928-01-03')):
        R, M = jp.calendar(a, '2014-12-31' if s == 'NDX' else '1985-12-31'); X = jp.mkX(R, M, s)
        c = C[nm]; j0 = int(c.ii[0, 0]); out[nm] = (c, X.index[j0:j0 + c.r.shape[1]])
    return out

WIN = [pd.Period(w) for w in lib.Z['win']]; WPOS = {w: i for i, w in enumerate(WIN)}
ACT = ['CUT1', 'CUT0', 'ADD3', 'ADD1']

def overlay_B(B, dates, plan):
    """plan: dict window_index -> list of codes (rules active-for-year; cond checked per window). B' = mean over rules."""
    n = len(B); Bp = B.copy().astype(float)
    me = pd.Series(np.arange(n), index=dates).groupby(dates.to_period('M')).last()
    # window of decision day u = window containing return day u+3
    win_of_day = np.full(n, -1)
    for M in me.index:
        if (M - 1) not in me.index or M not in WPOS: continue
        a0 = me[M - 1] + 3; b0 = me[M] + 2
        win_of_day[max(a0 - 3, 0):max(b0 - 3 + 1, 0)] = WPOS[M]
    for u in range(n):
        w = win_of_day[u]
        if w < 0 or w not in plan or not plan[w]: continue
        vals = []
        for cd, cond in plan[w]:
            vals.append(lib_act(cd >> 62, B[u]) if cond[w] else B[u])
        Bp[u] = np.mean(vals)
    return Bp

def lib_act(a, h):
    return [min(h, 1.0) if h >= 3 else h, 0.0, 3.0, 1.0 if h <= 0 else h][a]

def run(c, B, **kw):
    fin, E = std.engine(c, B, rx.av23s, rx.P_av23s(.85), 0.1, **kw)
    r, _ = std.row(fin, E); return r['cagr'], r['mdd']

def evaluate(sel_by_year, tag):
    """sel_by_year: dict calendar year -> list of codes (selected with data < that year)."""
    C = ctxs(); res = {}
    for nm, (c, dates) in C.items():
        B = bk.C3sig(c)[0]
        plan = {}
        for w, M in enumerate(WIN):
            if M.year in sel_by_year:
                plan[w] = [(cd, lib.cond_bits(cd)) for cd in sel_by_year[M.year]]
        Bp = overlay_B(B, dates, plan)[None, :]
        for kwn, kw in (('ms1', {}), ('cash0', dict(cspr=10.0))):
            v1 = run(c, B[None, :], **kw); ov_ = run(c, Bp, **kw)
            res['%s_%s' % (nm, kwn)] = dict(v1_cagr=v1[0], v1_mdd=v1[1], mx2_cagr=ov_[0], mx2_mdd=ov_[1], d=ov_[0] - v1[0])
    json.dump(res, open(lib.R + 'results/exact_%s.json' % tag, 'w'), indent=1)
    return res
