"""E3 (report-only): search the static family (V in TQQQ/QLD, R in 63/252, e/c on a 0.025 grid) for G1-G5 passers under
N3(k_low) and NA(Delta_s). Stage A: REAL on the whole fine grid (single path). Stage B: X30+X10 on a pruned set.
Stage C: P30+P10 on the best X candidates. One world at a time. <=2014 data only."""
import os, sys, json, numpy as np
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df6v/limit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df6 as D6, df5run as R
WARM = 300; OUT = '/tmp/df6v/limit/'
kd = D6.KV()['DEF3']
CONV = {'N3low': ('N3', {'DEF3': kd['k_low']}), 'NA': ('NA', {'DEF3': kd['delta_ann_all'] / np.sqrt(252)})}
stage = sys.argv[1]

def fine():
    C = []
    for V, m in (('TQQQ', 3), ('QLD', 2)):
        for Rb in (63, 252):
            for ei in range(20, 41):          # e = ei/40
                for ci in range(12, 37):      # c = ci/40
                    a = (ei - 40 + ci) / (40 * (m - 1)); b = 1 - ci / 40 - a
                    if a < -1e-12 or b < -1e-12: continue
                    if a < 1e-12 and V == 'QLD': continue          # a = 0 points identical for both V; keep the TQQQ copy
                    C.append(dict(id='F|%s|R%d|e%.3f|c%.3f' % (V, Rb, ei / 40, ci / 40), V=V, R=Rb, e=ei / 40, c=ci / 40, a=max(a, 0.0), b=max(b, 0.0), S='DEF3'))
    return C

def load(wname):
    X = D6.W6(wname, *CONV['N3low'], sleeves=['DEF3'])
    X.pan['S_N3low'] = X.pan['DEF3']
    X.pan['S_NA'] = D6.panel6(wname, *CONV['NA'], sleeves=['DEF3'])['DEF3']
    return X

def slack(s, q, single):
    if single:
        return dict(ret=(s['cagr'] - q['cagr']) * 100, dd=(1 - abs(s['mdd_med']) / abs(q['mdd_med']) - 0.1) * 100)
    return dict(pair=s['pair'] * 100, med=(s['cagr'] - q['cagr']) * 100, p10=(s['p10'] - q['p10']) * 100,
                dd=(1 - abs(s['mdd_p10']) / abs(q['mdd_p10']) - 0.1) * 100)

def evalw(X, C, keys, conv):
    out = {}
    for h, key in keys:
        qcg, qmd, _ = D6.bench(X, h); q = R.summ(qcg, qmd)
        for c in C:
            cg, md, _ = D6.run(dict(c, S='S_' + conv), X, h); s = R.summ(cg, md, qcg)
            out.setdefault(c['id'], {})[key] = dict(s, slack=slack(s, q, key == 'REAL'))
    return out

C = fine(); IDX = {c['id']: c for c in C}
if stage == 'A':
    X = load('REAL'); res = {}
    for cv in CONV: res[cv] = evalw(X, C, [(None, 'REAL')], cv)
    del X; D6.drop('REAL')
    json.dump(dict(n=len(C), res=res), open(OUT + 'e3A.json', 'w'))
    for cv in CONV:
        ok = [i for i, r in res[cv].items() if min(r['REAL']['slack'].values()) > 0]
        print(cv, 'fine grid', len(C), 'G1 pass', len(ok))
elif stage in ('B', 'C', 'DX', 'DP'):
    ids = json.load(open(OUT + 'e3%s_ids.json' % stage[0]))           # {conv: [ids]}
    wname = 'X' if stage in ('B', 'DX') else 'P'
    X = load(wname); res = {}
    for cv, L_ in ids.items():
        res[cv] = evalw(X, [IDX[i] for i in L_], [(None, wname + '30'), (10, wname + '10')], cv)
        print(cv, wname, len(L_), flush=True)
    del X; D6.drop(wname)
    json.dump(res, open(OUT + 'e3%s.json' % stage, 'w'))
