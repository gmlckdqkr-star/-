"""E5 support: arithmetic excess means / vols / correlations of the X-world assets (neutralized and raw), tangency Sharpe vs QQQ Sharpe.
Daily pooled over all paths, t >= WARM (the same sample the neutralization uses). Post-hoc diagnostic."""
import os, sys, json
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df5v/limit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import numpy as np
import df5run as R, df5lib as L, df5data as DD
WARM = 300
IDS = ['QQQ', 'TQQQ', 'SPX', 'DEF3', 'VALUE', 'B10', 'LTT', 'GOLD']
OUT = {}
for raw in (False, True):
    X = R.W('X', raw=raw); rf = np.nan_to_num(X.m['rf'])[:, WARM:].ravel()
    E = np.stack([(X.pan[k][0][:, WARM:].ravel() - rf) for k in IDS], 1)
    mu = E.mean(0) * 252; C = np.cov(E.T) * 252; sd = np.sqrt(np.diag(C)); corr = C / np.outer(sd, sd)
    res = {'mu_ann': dict(zip(IDS, mu.round(4).tolist())), 'vol_ann': dict(zip(IDS, sd.round(4).tolist())),
           'sharpe': dict(zip(IDS, (mu / sd).round(3).tolist())), 'corr_with_QQQ': dict(zip(IDS, corr[0].round(3).tolist()))}
    for name, sub in (('QQQ+B10+LTT+GOLD', ['QQQ', 'B10', 'LTT', 'GOLD']), ('QQQ+DEF3', ['QQQ', 'DEF3']), ('QQQ+SPX+DEF3+VALUE', ['QQQ', 'SPX', 'DEF3', 'VALUE']),
                      ('all_unlev', ['QQQ', 'SPX', 'DEF3', 'VALUE', 'B10', 'LTT', 'GOLD'])):
        j = [IDS.index(s) for s in sub]; m_ = mu[j]; Cs = C[np.ix_(j, j)]
        wt = np.linalg.solve(Cs, m_); sh = float(np.sqrt(m_ @ wt))
        wt = wt / wt.sum() if abs(wt.sum()) > 1e-9 else wt
        res['tangency|' + name] = dict(sharpe=round(sh, 3), ratio_vs_QQQ=round(sh / (mu[0] / sd[0]), 3), w=dict(zip(sub, wt.round(3).tolist())))
    OUT['raw' if raw else 'neutral'] = res
    print('raw' if raw else 'neutral', json.dumps(res, indent=0), flush=True)
    del X; DD._P.clear()
L._WORLDS.pop('X', None)
json.dump(OUT, open('/tmp/df5v/limit/exp_sharpe.json', 'w'))
