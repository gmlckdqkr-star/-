"""DF5 gates, dedupe, family bests (PRECOMMIT_DF5.md sections 3-5). Reads results/df5_main.json and /tmp/df5w/df5_arr.npz."""
import sys, json, hashlib, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
RES = '/mnt/project-files/research/df1/results/'
KEYS = ['REAL', 'P30', 'P10', 'X30', 'X10']

def gate_row(r, Q):
    """returns dict key -> (pass, detail) and score / dd margin"""
    g = {}; ret_m = []; dd_m = []
    if 'REAL' in r:
        a, q = r['REAL'], Q['REAL']
        ok_r = a['cagr'] > q['cagr']; ddm = 1 - abs(a['mdd_med']) / abs(q['mdd_med'])
        g['G1'] = dict(ok=bool(ok_r and ddm >= 0.1 - 1e-12), ret=a['cagr'] - q['cagr'], ddm=ddm)
        ret_m.append(a['cagr'] - q['cagr']); dd_m.append(ddm)
    for gi, k in zip(['G2', 'G3', 'G4', 'G5'], KEYS[1:]):
        if k not in r: continue
        a, q = r[k], Q[k]
        ddm = 1 - abs(a['mdd_p10']) / abs(q['mdd_p10'])
        cond = dict(pair=a['pair'] > 0, med=a['cagr'] > q['cagr'], p10=a['p10'] >= q['p10'] - 1e-12, dd=ddm >= 0.1 - 1e-12)
        g[gi] = dict(ok=bool(all(cond.values())), fail=[c for c, v in cond.items() if not v], pair=a['pair'], med=a['cagr'] - q['cagr'],
                     p10=a['p10'] - q['p10'], ddm=ddm)
        dd_m.append(ddm)
    score = min(r['P30']['pair'], r['X30']['pair'], r['REAL']['cagr'] - Q['REAL']['cagr'])
    return g, score, min(dd_m)

def dedupe(ids, arr):
    seen = {}; dup = {}
    for i in ids:
        f = arr.get('%s||finP30' % i)
        if f is None: continue
        h = hashlib.sha1(np.round(f.astype(np.float64), 12).tobytes()).hexdigest()
        if h in seen: dup[i] = seen[h]
        else: seen[h] = i
    return dup

def analyse():
    D = json.load(open(RES + 'df5_main.json')); Q = D['qqq']; rows = D['rows']
    arr = dict(np.load('/tmp/df5w/df5_arr.npz'))
    ids = list(rows.keys()); dup = dedupe(ids, arr)
    uniq = [i for i in ids if i not in dup]
    G = {}
    for i in uniq:
        g, sc, ddm = gate_row(rows[i], Q); G[i] = dict(g=g, score=sc, ddm=ddm, npass=sum(v['ok'] for v in g.values()), fam=rows[i]['fam'], track=rows[i]['track'])
    passers = [i for i in uniq if G[i]['npass'] == 5]
    fams = sorted(set(v['fam'] for v in G.values()))
    best = {}
    for f in fams:
        c = [i for i in uniq if G[i]['fam'] == f]
        b = max(c, key=lambda i: (G[i]['npass'], G[i]['score']))
        best[f] = dict(id=b, npass=G[b]['npass'], score=G[b]['score'], ddm=G[b]['ddm'], gates=G[b]['g'], n_unique=len(c),
                       n_pass_each={k: sum(G[i]['g'][k]['ok'] for i in c) for k in ('G1', 'G2', 'G3', 'G4', 'G5')})
    # X-world: any config beating QQQ in both return and drawdown (x30 and x10)
    xboth = [i for i in uniq if G[i]['g']['G4']['ok'] and G[i]['g']['G5']['ok']]
    return dict(N_raw=len(ids), N_unique=len(uniq), dups=len(dup), passers=passers, best=best, xboth=xboth,
                single={k: sum(G[i]['g'][k]['ok'] for i in uniq) for k in ('G1', 'G2', 'G3', 'G4', 'G5')}), G, D

if __name__ == '__main__':
    A, G, D = analyse()
    print(json.dumps({k: v for k, v in A.items() if k != 'best'}, indent=0)[:3000])
    for f, b in A['best'].items():
        print(f, b['id'], 'npass', b['npass'], 'score %.4f' % b['score'], 'ddm %.3f' % b['ddm'], {k: (v['ok'], v.get('fail')) for k, v in b['gates'].items()})
