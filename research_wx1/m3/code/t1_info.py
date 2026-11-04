"""M3 (a) stage 1 (PRECOMMIT_M3 sec 2): bond information of each gate, G1-style.
Label of a block starting at close t (every 21 trading days, non-overlapping) = TMF-like synthetic (3*TLT - 2*rf - 2.45%/yr) beats the
MS1 deposit max(rf - 2%, 0)*(1 - 15.4%) over trading days t+3..t+23 (cumulative log). Eras: 1986-2014 (NDX calendar), 1962-1985 (SPX calendar).
Deflated hit = hit - 2*SE*sqrt(1 + ln N), N = 7."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m3/code')
import m3env, m3sig as SG
from scipy import stats
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std, jp
XD = m3env.XD
N_TRIALS = 7


def frame(stream, a, b, start, end):
    R, M = jp.calendar(a, b); X = jp.mkX(R, M, stream)
    tlt = XD.by_date()['TLT'].reindex(X.index)
    ok = tlt.notna()
    tmf = 3 * tlt.fillna(0.0) - 2 * X['rf'] - 0.0245 / 252
    dep = np.maximum(X['rf'] - 0.02 / 252, 0) * 0.846
    ex = np.log1p(tmf) - np.log1p(dep)
    ex1 = np.log1p(tlt.fillna(0.0)) - np.log1p(X['rf'])           # 1x long-bond excess (for the conditional means)
    cs = np.r_[0, np.cumsum(ex.values)]; cs1 = np.r_[0, np.cumsum(ex1.values)]
    i0 = X.index.searchsorted(pd.Timestamp(start)); i1 = X.index.searchsorted(pd.Timestamp(end), side='right')
    rows = []
    for t in range(i0, min(i1, len(X) - 24), 21):
        if not ok.iloc[t + 3:t + 24].all(): continue
        rows.append((X.index[t], cs[t + 24] - cs[t + 3], cs1[t + 24] - cs1[t + 3]))
    return pd.DataFrame(rows, columns=['date', 'ex3', 'ex1']).set_index('date')


def test(gate, F, N=N_TRIALS):
    g = gate.dropna(); g = g.reindex(g.index.union(F.index)).ffill().reindex(F.index)
    ok = g.notna(); F = F[ok]; g = g[ok].astype(bool)
    if len(F) < 30: return None
    y = F['ex3'] > 0; hit = float((g == y).mean()); n = len(F); se = (hit * (1 - hit) / n) ** .5
    base = float(y.mean()); noinfo = max(base, 1 - base)
    on, off = F['ex1'][g.values], F['ex1'][~g.values]
    t, p = stats.ttest_ind(on, off, equal_var=False) if len(on) > 2 and len(off) > 2 else (np.nan, np.nan)
    return dict(start=str(F.index[0].date()), n=n, on_share=float(g.mean()), hit=hit, base_up=base, noinfo=noinfo,
                hit_defl=hit - 2 * se * (1 + np.log(N)) ** .5, hit_minus_noinfo=hit - noinfo,
                tlt_ex_on_pa=float(on.mean() * 252 / 21) if len(on) else None, tlt_ex_off_pa=float(off.mean() * 252 / 21) if len(off) else None,
                tmf_ex_on_pa=float(F['ex3'][g.values].mean() * 252 / 21) if len(on) else None,
                tmf_ex_off_pa=float(F['ex3'][~g.values].mean() * 252 / 21) if len(off) else None,
                welch_t=float(t), welch_p=float(p))


if __name__ == '__main__':
    Fs = {'1986_2014': frame('NDX', '1984-01-03', '2014-12-31', '1986-01-02', '2014-12-31'),
          '1962_1985': frame('SPX', '1928-01-03', '1985-12-31', '1962-01-02', '1985-12-31')}
    G = SG.gates(); out = {}
    for era, F in Fs.items():
        out[era] = {'_always_on': test(pd.Series(1.0, index=F.index), F)}
        for c in SG.ALL: out[era][c] = test(G[c], F)
    json.dump(out, open(m3env.SCR + 'results/t1_info.json', 'w'), indent=1)
    for era in out:
        print('==', era)
        for c, r in out[era].items():
            if r is None: print(c, 'n/a'); continue
            print('%-10s start %s n %3d on %.2f hit %.3f base %.3f noinfo %.3f defl %.3f (hit-noinfo %+.3f) | TLT ex on %+.3f off %+.3f t %.2f | TMF ex on %+.3f off %+.3f'
                  % (c, r['start'], r['n'], r['on_share'], r['hit'], r['base_up'], r['noinfo'], r['hit_defl'], r['hit_minus_noinfo'],
                     r['tlt_ex_on_pa'] or 0, r['tlt_ex_off_pa'] or 0, r['welch_t'], r['tmf_ex_on_pa'] or 0, r['tmf_ex_off_pa'] or 0))
