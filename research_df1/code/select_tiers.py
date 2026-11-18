"""DF1 selection + validation exactly as PRECOMMIT_DF1.md sections 3-5. Reads results/grid.json, writes results/select.json."""
import json, numpy as np
G = json.load(open('/mnt/project-files/research/df1/results/grid.json'))
C = G['configs']; SEL = ('dev250_path', 'real_ndx_86_14', 'real_spx_29_54')
VAL = ('real_spx_55_85', 'real_spx_70_85', 'UK', 'CA', 'AU', 'DE', 'FR', 'JP'); FOR = VAL[2:]

def wd(r): return min(r['dev250_path']['mdd_p10'], r['real_ndx_86_14']['mdd'], r['real_spx_29_54']['mdd'])
def score(r): return (r['dev250_path']['cagr'], r['real_ndx_86_14']['cagr'])

def pick(budget):
    ins = [i for i, r in C.items() if wd(r) >= budget]
    if not ins: return None, ins
    best = max(ins, key=lambda i: C[i]['dev250_path']['cagr'])
    tie = [i for i in ins if C[best]['dev250_path']['cagr'] - C[i]['dev250_path']['cagr'] < 0.0005]
    best = max(tie, key=lambda i: C[i]['real_ndx_86_14']['cagr'])
    return best, ins

def neighbors(i):
    c = C[i]['cfg']
    if c['fam'] != 'grid': return []
    S = [None, 0.1, 0.15, 0.2, 0.3]; L = [1.0, 1.5, 2.0, 3.0]; out = []
    si = S.index(c['sig']); li = L.index(c['Lmax'])
    for ds, dl in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        a, b = si + ds, li + dl
        if 0 <= a < len(S) and 0 <= b < len(L):
            out.append('%s|s%s|L%s|%s|%s' % (c['k'], 'none' if S[a] is None else S[a], L[b], c['knee'], c['roff']))
    return out

def validate(i, budget, ins):
    r = C[i]; v = {}
    v['V1'] = bool(r['real_spx_55_85']['mdd'] >= budget - 0.10 and r['real_spx_70_85']['mdd'] >= budget - 0.10)
    nf = sum(r[m]['mdd'] >= budget - 0.10 for m in FOR); v['V2'] = bool(nf >= 5); v['V2_count'] = int(nf)
    pct = []
    for m in VAL:
        xs = np.array([C[j][m]['cagr'] for j in ins]); pct.append(float(100.0 * np.mean(xs < r[m]['cagr'] + 1e-12)))
    v['V3_pct_by_series'] = dict(zip(VAL, pct)); v['V3_median_pct'] = float(np.median(pct)); v['V3'] = bool(np.median(pct) >= 50)
    v['defense_pass'] = bool(v['V1'] and v['V2'])
    return v

out = dict(N=G['N'], tiers={})
for name, bud in (('A', -0.20), ('B', -0.30), ('C', -0.40), ('A_fallback_25', -0.25)):
    best, ins = pick(bud)
    t = dict(budget=bud, n_in=len(ins), best=best)
    if best:
        top = sorted(ins, key=lambda i: -C[i]['dev250_path']['cagr'])[:10]
        t['top10'] = [(i, round(C[i]['dev250_path']['cagr'], 4), round(C[i]['real_ndx_86_14']['cagr'], 4), round(wd(C[i]), 4)) for i in top]
        t['top10_median_path'] = float(np.median([C[i]['dev250_path']['cagr'] for i in top]))
        nb = [j for j in neighbors(best) if j in C]; nbi = [j for j in nb if wd(C[j]) >= bud]
        t['neighbors'] = [(j, round(C[j]['dev250_path']['cagr'], 4), round(wd(C[j]), 4)) for j in nb]
        t['neighbors_in_median_path'] = float(np.median([C[j]['dev250_path']['cagr'] for j in nbi])) if nbi else None
        t['wd'] = wd(C[best]); t['rows'] = {b: C[best][b] for b in SEL + VAL}
        t['validation'] = validate(best, bud, ins)
    out['tiers'][name] = t
out['refs'] = G['refs']
json.dump(out, open('/mnt/project-files/research/df1/results/select.json', 'w'), indent=1)
for name, t in out['tiers'].items():
    print('== tier', name, t['budget'], 'n_in', t['n_in'], 'best', t['best'])
    if t['best']:
        R = t['rows']
        print('   path %.4f p10 %.4f mddp10 %.4f | realNDX %.4f mdd %.4f | SPX29 %.4f mdd %.4f | WD %.4f' % (
            R['dev250_path']['cagr'], R['dev250_path']['p10'], R['dev250_path']['mdd_p10'], R['real_ndx_86_14']['cagr'],
            R['real_ndx_86_14']['mdd'], R['real_spx_29_54']['cagr'], R['real_spx_29_54']['mdd'], t['wd']))
        print('   validation', {k: v for k, v in t['validation'].items() if k != 'V3_pct_by_series'})
        print('   top10 median path %.4f, neighbors-in median %s' % (t['top10_median_path'], t['neighbors_in_median_path']))
