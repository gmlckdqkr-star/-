"""X30 (or other world/horizon) static-mix frontier with my own simulator. Mix spec: NDX exposure e via TQQQ a=(e-1+c)/2,
QQQ b=1-c-a (A3 parametrisation, extended to e<1), sleeve weight c split equally across sleeve assets; forced rebalance 63d."""
import sys, json, numpy as np
sys.path.insert(0, '/tmp/df5v/repro')
from sim import sim, summ, WARM
wn = sys.argv[1]; h = int(sys.argv[2]); specs = json.loads(open(sys.argv[3]).read()); tag = sys.argv[4]
mode = sys.argv[5] if len(sys.argv) > 5 else 'neutral'; cmul = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
Z = np.load('/tmp/df5v/repro/data/%s.npz' % wn)
r = np.nan_to_num(Z['r']); rf = np.nan_to_num(Z['rf']); P, T = r.shape
ERQ = 0.002 - 0.0055 * (1 - 0.154)
A = {'QQQ': (r - ERQ / 252, 0.0, 1), 'QLD': (2 * r - rf - 0.017 / 252, 0.0, 1), 'TQQQ': (3 * r - 2 * rf - 0.0245 / 252, 0.0, 1)}
for k in ['TBILL', 'B10', 'LTT', 'GOLD', 'DEF3', 'SPX', 'VALUE']: A[k] = (Z['RET_' + k], Z['INC_' + k], int(Z['HV_' + k]))
Th = None if wn == 'REAL' else WARM + h * 252
if mode != 'neutral':
    SH = json.load(open('/mnt/project-files/research/df1/results/df5_main.json'))['shifts'][wn]
    net = A['DEF3'][0]
    if mode == 'raw':      # undo the equity-neutral mean shift (keep expense)
        net2 = net + SH['DEF3'] / 252
    elif mode == 'sharpe': # DEF3 mean set so that its excess/vol equals SPX excess/vol in this world (sampled days t>=WARM)
        sel = np.s_[:, WARM:]
        g = net + 0.0015 / 252; spx = Z['spx_raw']; rfm = rf[sel].mean()
        tgt = rfm + (spx[sel].mean() - rfm) * g[sel].std() / spx[sel].std()
        net2 = net + (tgt - g[sel].mean())
        print('sharpe-neutral DEF3 shift %.4f/yr vs SPX-mean neutral' % ((tgt - g[sel].mean()) * 252))
    A['DEF3'] = (net2, A['DEF3'][1], A['DEF3'][2])
    print('DEF3 mode', mode, 'arith mean %.4f/yr' % (A['DEF3'][0][:, WARM:].mean() * 252))
def run(wts, reb=63):
    ids = [k for k in wts if wts[k] > 1e-12]
    RET = np.empty((P, T, len(ids))); INC = np.zeros((P, T, len(ids))); HV = []
    for j, k in enumerate(ids):
        a, inc, hv = A[k]; RET[:, :, j] = a; INC[:, :, j] = inc; HV.append(hv)
    Wt = np.zeros((P, T, len(ids)))
    for j, k in enumerate(ids): Wt[:, :, j] = wts[k]
    return sim(RET, INC, np.array(HV), Wt, reb_every=reb, Th=Th, twr=True, cost=0.003 * cmul)
qcg, qmd, qfin, qtw = run({'QQQ': 1.0}, reb=0)
q = summ(qcg, qmd); qtw10 = float(np.percentile(qtw, 10))
print('%s%d QQQ med %.4f p10 %.4f p10MDD %.4f (TWR p10MDD %.4f)' % (wn, h, q['cagr'], q['p10'], q['mdd_p10'], qtw10), flush=True)
out = []
for sp in specs:
    e, c, sl = sp['e'], sp['c'], sp['sleeve']; reb = sp.get('reb', 63)
    a = (e - 1 + c) / 2; b = 1 - c - a
    if a < -1e-12 or b < -1e-12: print('skip infeasible', sp); continue
    wts = {'TQQQ': max(a, 0), 'QQQ': max(b, 0)}
    for s in sl: wts[s] = wts.get(s, 0) + c / len(sl)
    cg, md, fin, tw = run(wts, reb)
    s = summ(cg, md, qcg); ddrel = 1 - abs(s['mdd_p10']) / abs(q['mdd_p10']); tw10 = float(np.percentile(tw, 10))
    twrel = 1 - abs(tw10) / abs(qtw10)
    ok0 = s['pair'] > 0 and s['cagr'] > q['cagr'] and ddrel > 0
    ok10 = s['pair'] > 0 and s['cagr'] > q['cagr'] and s['p10'] >= q['p10'] and ddrel >= 0.1
    row = dict(sp, a=a, b=b, **s, ddrel=ddrel, twr_p10=tw10, twr_rel=twrel, both0=ok0, G4=ok10)
    out.append(row)
    print('e%.2f c%.2f %-16s reb%-3d TQQQ %.3f QQQ %.3f | med %+.2fpp pair %+.2fpp p10 %+.2fpp | p10MDD %.4f rel %+.3f | TWR rel %+.3f | both0 %s G4 %s' % (
        e, c, '+'.join(sl), reb, a, b, (s['cagr'] - q['cagr']) * 100, s['pair'] * 100, (s['p10'] - q['p10']) * 100, s['mdd_p10'], ddrel, twrel, ok0, ok10), flush=True)
json.dump(dict(qqq=dict(q, twr_p10=qtw10), rows=out), open('/tmp/df5v/repro/front_%s_%s%d_%s_c%.0f.json' % (tag, wn, h, mode, cmul), 'w'), indent=1)
