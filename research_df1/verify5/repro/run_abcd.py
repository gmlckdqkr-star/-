import sys, json, time, numpy as np
sys.path.insert(0, '/tmp/df5v/repro')
from sim import sim, summ, t200, WARM
from ladder import ladder
wn = sys.argv[1]; hs = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else [30]
Z = np.load('/tmp/df5v/repro/data/%s.npz' % wn)
r = np.nan_to_num(Z['r']); rf = np.nan_to_num(Z['rf']); P, T = r.shape
ERQ = 0.002 - 0.0055 * (1 - 0.154)
A = {}
A['QQQ'] = (r - ERQ / 252, 0.0, 1)
A['QLD'] = (2 * r - rf - 0.017 / 252, 0.0, 1)
A['TQQQ'] = (3 * r - 2 * rf - 0.0245 / 252, 0.0, 1)
for k in ['TBILL', 'B10', 'LTT', 'GOLD', 'DEF3', 'SPX', 'VALUE']:
    A[k] = (Z['RET_' + k], Z['INC_' + k], int(Z['HV_' + k]))
# sanity vs panel for NDX family
for k in ['QQQ', 'QLD', 'TQQQ']:
    print('panel diff', k, float(np.max(np.abs(A[k][0] - Z['RET_' + k]))))
def stack(ids):
    RET = np.empty((P, T, len(ids))); INC = np.zeros((P, T, len(ids))); HV = []
    for j, k in enumerate(ids):
        a, inc, hv = A[k]; RET[:, :, j] = a; INC[:, :, j] = inc; HV.append(hv)
    return RET, INC, np.array(HV)
def const(ids, wts):
    Wt = np.zeros((P, T, len(ids)))
    for j, k in enumerate(ids): Wt[:, :, j] = wts.get(k, 0.0)
    return Wt
D = json.load(open('/mnt/project-files/research/df1/results/df5_main.json'))
res = {}
lv = np.cumprod(1 + r, axis=1); on = t200(lv)
for h in hs:
    Th = WARM + h * 252; key = (wn + str(h)) if wn != 'REAL' else 'REAL'
    if wn == 'REAL': Th = None
    RET, INC, HV = stack(['QQQ'])
    qcg, qmd, qfin = sim(RET, INC, HV, const(['QQQ'], {'QQQ': 1.0}), Th=Th)
    res[(key, 'QQQ')] = summ(qcg, qmd)
    print(key, 'QQQ mine', {a: round(b, 5) for a, b in res[(key, 'QQQ')].items()}, '| stored', {a: round(b, 5) for a, b in D['qqq'][key].items() if a in ('cagr', 'p10', 'mdd_med', 'mdd_p10')}, flush=True)
    jobs = {}
    jobs['A3|e1.00|c0.50|DEF3|none'] = ('static', {'TQQQ': 0.25, 'QQQ': 0.25, 'DEF3': 0.5})
    jobs['A3|e1.00|c0.20|GOLD+LTT+DEF3|none'] = ('static', {'TQQQ': 0.1, 'QQQ': 0.7, 'GOLD': 0.2 / 3, 'LTT': 0.2 / 3, 'DEF3': 0.2 / 3})
    jobs['A3|e1.00|c0.20|DEF3|none'] = ('static', {'TQQQ': 0.1, 'QQQ': 0.7, 'DEF3': 0.2})
    jobs['A5|DEF3|U0|D2|T200|d0.3'] = ('ladder', dict(D='DEF3', up=None, dn=(0.25, 0.40, 0.55), conf=1, d0=0.3))
    jobs['A5|DEF3|U0|D2|now|d0.3'] = ('ladder', dict(D='DEF3', up=None, dn=(0.25, 0.40, 0.55), conf=0, d0=0.3))
    for name, (kind, spec) in jobs.items():
        t0 = time.time()
        if kind == 'static':
            ids = list(spec.keys()); RET, INC, HV = stack(ids)
            cg, md, fin = sim(RET, INC, HV, const(ids, spec), reb_every=63, Th=Th)
        else:
            ids = ['QQQ', 'QLD', 'TQQQ', spec['D']]; RET, INC, HV = stack(ids)
            Wl, EVl = ladder(lv, on, A['QQQ'][0], A['QLD'][0], A['TQQQ'][0], A[spec['D']][0], up=spec['up'], dn=spec['dn'], conf=spec['conf'], d0=spec['d0'])
            cg, md, fin = sim(RET, INC, HV, Wl, EVl, reb_every=0, Th=Th)
            print('   ladder events/path median', float(np.median(EVl[:, WARM:Th].sum(1))))
        s = summ(cg, md, qcg); res[(key, name)] = s
        st = D['rows'].get(name, {}).get(key)
        print(' %-36s mine' % name, {a: round(b, 5) for a, b in s.items()}, '%.0fs' % (time.time() - t0))
        if st: print(' %-36s strd' % '', {a: round(st[a], 5) for a in s})
        print('   p10DD rel to QQQ mine %.4f' % (1 - abs(s['mdd_p10']) / abs(res[(key, 'QQQ')]['mdd_p10'])), flush=True)
        np.save('/tmp/df5v/repro/data/cg_%s_%s.npy' % (key, name.replace('|', '_')), np.stack([cg, md]))
    np.save('/tmp/df5v/repro/data/cg_%s_QQQ.npy' % key, np.stack([qcg, qmd]))
