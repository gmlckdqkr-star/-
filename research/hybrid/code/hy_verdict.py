"""PRECOMMIT_HY1 section 3 verdicts for the 29 switching rules, from results/info_le2014.json and results/ladder_le2014.json.
p* follows the PRECOMMIT wording (smallest grid p whose dev250_path median CAGR reaches the target); the interpolated value is
reported alongside for information. Rule (lower of the two eras): BUILD = deflated hit >= p*(+1pp) of the rule's set AND gain > 0
in both eras AND min gain t >= sqrt(2 ln 29); 30%-CAND = BUILD and deflated hit >= p*(30%); else CLOSE.
The SPXH_L1 pair has no ladder set ({s0.85, SPXH_L1} was not pre-registered), so its hit threshold is undefined; those rules are
judged on the gain gate only (recorded as thr_undefined). Output results/verdict_le2014.json. Reads JSON only (imports nothing
that reruns experiments)."""
import json, math

R = '/mnt/project-files/research/hybrid/results/'
L = json.load(open(R + 'ladder_le2014.json')); I = json.load(open(R + 'info_le2014.json'))
_ST = json.load(open(R + 'struct_le2014.json'))
S085 = {bn: _ST['%s|S085' % bn]['cagr'] for bn in ('dev250_path', 'real_ndx_86_14', 'real_spx_55_85')}   # same-engine standalone s0.85
TT = math.sqrt(2 * math.log(29))


def pstar(bn, s, tgt):
    xs = sorted((float(k.split('|')[2]), v['cagr']) for k, v in L.items() if k.startswith('%s|%s|' % (bn, s)))
    grid = next((p for p, c in xs if c >= tgt), None)
    interp = None
    for (p0, c0), (p1, c1) in zip(xs, xs[1:]):
        if c0 < tgt <= c1: interp = p0 + (p1 - p0) * (tgt - c0) / (c1 - c0); break
    if interp is None and grid is not None: interp = grid
    return grid, interp


PS = {}
for bn in S085:
    for s in ('B2V', 'B2B', 'BK4'):
        g1, i1 = pstar(bn, s, S085[bn] + 0.01); g3, i3 = pstar(bn, s, 0.30)
        PS['%s|%s' % (bn, s)] = dict(p1_grid=g1, p1_interp=i1, p30_grid=g3, p30_interp=i3)
SET = {'VALPROF4_L1': 'B2V', 'BOND10_L3': 'B2B', 'SPXH_L1': None, 'BK4': 'BK4'}
out = dict(pstar=PS, rules={})
for key in I:
    bn, X, rule = key.split('|')
    if bn != 'real_ndx_86_14': continue
    a = I[key]; b = I['real_spx_55_85|%s|%s' % (X, rule)]
    h = min(a['hit_defl'], b['hit_defl']); tmin = min(a['gain_t'], b['gain_t'])
    both = a['gain_mean'] > 0 and b['gain_mean'] > 0
    st = SET[X]; ps = PS['dev250_path|%s' % st] if st else None
    hit_ok = (ps is not None and h >= ps['p1_grid'])
    build = (hit_ok or ps is None) and both and tmin >= TT
    cand = build and ps is not None and h >= ps['p30_grid']
    out['rules']['%s|%s' % (X, rule)] = dict(hit_defl_lower=h, thr_p1=ps['p1_grid'] if ps else None, thr_undefined=ps is None,
                                             gain_ndx=a['gain_mean'], t_ndx=a['gain_t'], gain_spx=b['gain_mean'], t_spx=b['gain_t'],
                                             verdict='30%-CAND' if cand else ('BUILD' if build else 'CLOSE'))
json.dump(out, open(R + 'verdict_le2014.json', 'w'), indent=1)
for k, v in PS.items(): print(k, v)
n = {}
for k, v in out['rules'].items(): n[v['verdict']] = n.get(v['verdict'], 0) + 1
print(n, 'max lower deflated hit %.4f' % max(v['hit_defl_lower'] for v in out['rules'].values()))
