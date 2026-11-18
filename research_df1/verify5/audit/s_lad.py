import os, sys, numpy as np
sys.dont_write_bytecode = True
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df5v/audit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df5run as R, df5fam as F
CF = {c['id']: c for c in F.configs(R.ELIG)}
X = R.W('X'); WARM = 300; NP = 6
def mine(cfg, p):
    lv = X.sig.lv[p]; t2 = X.sig.T(200)[p]
    RQ, R2, R3, RD = (X.pan[k][0][p] for k in ('QQQ', 'QLD', 'TQQQ', cfg['D']))
    up, dn = cfg['up'], cfg['dn']
    w = np.array([1 - cfg['d0'], 0, 0, cfg['d0']], float); T = len(lv)
    W = np.zeros((T, 4)); EV = np.zeros(T, bool); W[WARM - 1] = w; EV[WARM - 1] = True
    ref = lv[WARM - 1]; peak = lv[WARM - 1]; crisis = False; step = 0; Dstart = 0; crisis_peak = None
    for t in range(WARM, T):
        g = w * (1 + np.array([RQ[t], R2[t], R3[t], RD[t]])); w = g / g.sum()
        x = lv[t]; peak = max(peak, x); ev = False
        if up and not crisis and x >= ref * (1 + up[0]):
            mv = up[1] * w[0]; w[0] -= mv; w[3] += mv; ref = x; ev = ev or mv > 0
        if dn:
            dd = x / peak - 1
            if not crisis and dd <= -dn[0]: crisis = True; crisis_peak = peak; Dstart = w[3]; step = 0
            if crisis and (cfg['cf'] == 'now' or t2[t]):
                while step < 3 and dd <= -dn[step] if False else (step < 3 and min(lv[WARM:t+1][np.argmax(lv[:t+1][WARM:] >= 0):] / peak - 1).min() <= -dn[step] if False else False):
                    pass
            # armed = deepest drawdown seen during this crisis reached the step threshold
            if crisis:
                if not hasattr(mine, 'mind'): pass
        if ev: EV[t] = True
        W[t] = w
    return W, EV
# simpler: independent ladder written fresh with explicit state
def mine2(cfg, p):
    lv = X.sig.lv[p]; t2 = X.sig.T(200)[p]
    RQ, R2, R3, RD = (X.pan[k][0][p] for k in ('QQQ', 'QLD', 'TQQQ', cfg['D']))
    up, dn = cfg['up'], cfg['dn']
    w = np.array([1 - cfg['d0'], 0, 0, cfg['d0']], float); T = len(lv)
    W = np.zeros((T, 4)); EV = np.zeros(T, bool); W[WARM - 1] = w; EV[WARM - 1] = True
    ref = lv[WARM - 1]; peak = lv[WARM - 1]; crisis = False; done = 0; Dstart = 0.0; cpeak = 0.0; mindd = 0.0
    for t in range(WARM, T):
        g = w * (1 + np.array([RQ[t], R2[t], R3[t], RD[t]])); w = g / max(g.sum(), 1e-300)
        x = lv[t]; peak = max(peak, x); ev = False
        if up and not crisis and x >= ref * (1 + up[0]):
            mv = up[1] * w[0]; w[0] -= mv; w[3] += mv; ref = x; ev = mv > 0
        if dn:
            dd = x / peak - 1
            if crisis: mindd = min(mindd, dd)
            if not crisis and dd <= -dn[0]: crisis = True; cpeak = peak; Dstart = w[3]; done = 0; mindd = dd
            if crisis and (cfg['cf'] == 'now' or t2[t]):
                while done < 3 and mindd <= -dn[done]:
                    mv = min(Dstart / 3, w[3])
                    if mv > 0: w[3] -= mv; w[done] += mv; ev = True
                    done += 1
            if crisis and x >= cpeak:
                if w[1] > 0 or w[2] > 0: ev = True
                w[0] += w[1] + w[2]; w[1] = w[2] = 0.0; crisis = False; ref = x
        if ev: EV[t] = True
        W[t] = w
    return W, EV
for cid in ['A5|DEF3|U1|D1|now|d0.3', 'A5|DEF3|U0|D2|T200|d0.3', 'A5|TBILL|U3|D2|T200|d0.0', 'A5|GOLD|U2|D1|now|d0.3']:
    jb = R.job(CF[cid], X); Wt, EV = jb[2], jb[3]
    mx = 0; evd = 0
    for p in range(NP):
        W2, E2 = mine2(CF[cid], p)
        mx = max(mx, np.abs(W2[WARM - 1:] - Wt[p, WARM - 1:]).max()); evd += int((E2[WARM - 1:] != EV[p, WARM - 1:]).sum())
    print('%-28s max|W diff| %.2e  EV mismatches %d  (events on path0: %d)' % (cid, mx, evd, int(EV[0].sum())))
