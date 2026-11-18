"""AUDIT: independent recomputation of DF1/DF2 selection from results/grid*.json (no engine runs).
Writes nothing by itself; prints a JSON blob consumed by the audit report. <=2014 dev numbers only (inputs are <=2014)."""
import sys, json, itertools, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
R = '/mnt/project-files/research/df1/results/'
G1 = json.load(open(R + 'grid.json')); G2 = json.load(open(R + 'grid_df2.json'))
S1 = json.load(open(R + 'select.json')); S2 = json.load(open(R + 'select_df2.json'))
C1 = G1['configs']; C2 = G2['configs']; U = dict(C1); U.update(C2)
VAL = ('real_spx_55_85', 'real_spx_70_85', 'UK', 'CA', 'AU', 'DE', 'FR', 'JP'); FOR = VAL[2:]
out = {}

# ---- 4. grid definition: enumerate from the PRECOMMIT text, compare with JSON ids and with configs()
spec1 = set()
for k, s, L, kn, ro in itertools.product(('v1', 'always'), ('none', 0.1, 0.15, 0.2, 0.3), (1.0, 1.5, 2.0, 3.0), ('K0', 'K1', 'K2'), ('RC', 'RT', 'RB', 'RBT')):
    spec1.add('%s|s%s|L%s|%s|%s' % (k, s, L, kn, ro))
spec1 |= {'static|QQQ%d|bond' % w for w in (30, 50, 70)}
spec2_all = set(); dup = set()
for M, bd, k, s, L, kn, ro in itertools.product(('M0', 'M2'), ('b1', 'b2', 'b3'), ('v1', 'always'), (0.1, 0.15, 0.2, 0.3), (1.0, 1.5, 2.0, 3.0), ('K1', 'K2'), ('RB', 'RBT')):
    i = 'DF2|%s|%s|%s|s%s|L%s|%s|%s' % (M, bd, k, s, L, kn, ro); spec2_all.add(i)
    if M == 'M0' and bd == 'b1': dup.add(i)
spec2 = spec2_all - dup
import run_grid as RG, run_df2 as R2
c1 = RG.configs(); c2 = R2.configs()
out['grid'] = dict(spec1_n=len(spec1), json1_n=len(C1), configs1_n=len(c1), json1_eq_spec=set(C1) == spec1,
                   configs1_eq_spec={c['id'] for c in c1} == spec1, ids_unique1=len({c['id'] for c in c1}) == len(c1),
                   spec2_all=len(spec2_all), dup_n=len(dup), spec2_n=len(spec2), json2_n=len(C2), configs2_n=len(c2),
                   json2_eq_spec=set(C2) == spec2, configs2_eq_spec={c['id'] for c in c2} == spec2,
                   dup_all_in_df1=all('|'.join(d.split('|')[3:]) in C1 for d in dup),
                   N_union=len(U), N_union_expected=483 + 640, N1_field=G1['N'], N2_field=G2['N_new'], N_total_field=S2['N_total'])
# config fields in JSON consistent with ids (catches id/param mismatch)
bad = []
for i, r in U.items():
    c = r['cfg']
    if c['fam'] == 'static': continue
    s = 'none' if c['sig'] is None else c['sig']
    rid = '%s|s%s|L%s|%s|%s' % (c['k'], s, c['Lmax'], c['knee'], c['roff'])
    if c['fam'] == 'df2': rid = 'DF2|%s|%s|' % (c['M'], c['band']) + rid
    if rid != i: bad.append(i)
out['grid']['id_param_mismatch'] = bad

# ---- 3. selection
def wd(r): return min(r['dev250_path']['mdd_p10'], r['real_ndx_86_14']['mdd'], r['real_spx_29_54']['mdd'])
def binding(r):
    d = {'dev250_path_mdd_p10': r['dev250_path']['mdd_p10'], 'real_ndx_86_14_mdd': r['real_ndx_86_14']['mdd'], 'real_spx_29_54_mdd': r['real_spx_29_54']['mdd']}
    return min(d, key=d.get)
def pick(C, bud):
    ins = [i for i in C if wd(C[i]) >= bud]
    if not ins: return None, ins, []
    top = max(C[i]['dev250_path']['cagr'] for i in ins)
    tie = [i for i in ins if top - C[i]['dev250_path']['cagr'] < 0.0005]
    return max(tie, key=lambda i: C[i]['real_ndx_86_14']['cagr']), ins, tie
def pcts(C, i, ins, mode):
    res = []
    for m in VAL:
        x = C[i][m]['cagr']; xs = np.array([C[j][m]['cagr'] for j in ins]); oth = np.array([C[j][m]['cagr'] for j in ins if j != i])
        if mode == 'code': p = 100 * np.mean(xs < x + 1e-12)                       # as in select_tiers / run_df2 (self + ties count as below)
        elif mode == 'strict_others': p = 100 * np.mean(oth < x - 1e-12) if len(oth) else 100.0
        elif mode == 'midrank_others': p = 100 * (np.mean(oth < x - 1e-12) + 0.5 * np.mean(np.abs(oth - x) <= 1e-12)) if len(oth) else 100.0
        res.append(float(p))
    return dict(zip(VAL, res)), float(np.median(res))
def validate(C, i, bud, ins):
    r = C[i]
    v = dict(V1=bool(r['real_spx_55_85']['mdd'] >= bud - 0.10 and r['real_spx_70_85']['mdd'] >= bud - 0.10),
             V1_margins={m: r[m]['mdd'] - (bud - 0.10) for m in VAL[:2]},
             V2_count=int(sum(r[m]['mdd'] >= bud - 0.10 for m in FOR)), V2_margins={m: r[m]['mdd'] - (bud - 0.10) for m in FOR})
    v['V2'] = v['V2_count'] >= 5
    for mode in ('code', 'strict_others', 'midrank_others'):
        p, med = pcts(C, i, ins, mode); v['V3_' + mode] = dict(median=med, by=p, pass_=med >= 50)
    # exact behavioural twins of the pick inside the tier (same numbers on every basis) -> inflate code-mode percentile
    keyf = lambda j: tuple(round(C[j][b]['cagr'], 12) for b in ('dev250_path', 'real_ndx_86_14', 'real_spx_29_54') + VAL)
    v['twins_in_tier'] = [j for j in ins if j != i and keyf(j) == keyf(i)]
    return v
def neighbors(C, i):
    c = C[i]['cfg']; S = [None, 0.1, 0.15, 0.2, 0.3]; L = [1.0, 1.5, 2.0, 3.0]; nb = []
    if c['fam'] == 'static': return nb
    si = S.index(c['sig']); li = L.index(c['Lmax'])
    for ds, dl in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        a, b = si + ds, li + dl
        if 0 <= a < 5 and 0 <= b < 4:
            s = 'none' if S[a] is None else S[a]
            j = '%s|s%s|L%s|%s|%s' % (c['k'], s, L[b], c['knee'], c['roff'])
            if c['fam'] == 'df2':
                if c['M'] == 'M0' and c['band'] == 'b1': pass
                j = 'DF2|%s|%s|' % (c['M'], c['band']) + j
                if c['M'] == 'M0' and c['band'] == 'b1': j = j.split('|', 3)[3]
            nb.append(j)
    return [j for j in nb if j in C]

sel = {}
for setname, C, S in (('DF1', C1, S1['tiers']), ('UNION', U, S2['tiers'])):
    T = {}
    for name, bud in (('A', -0.20), ('A_fallback_25', -0.25), ('B', -0.30), ('C', -0.40)):
        b, ins, tie = pick(C, bud); t = dict(n_in=len(ins), best=b, tie_set=tie)
        if b:
            t['wd'] = wd(C[b]); t['wd_binding'] = binding(C[b]); t['wd_margin'] = wd(C[b]) - bud
            srt = sorted(ins, key=lambda i: -C[i]['dev250_path']['cagr'])
            t['runner_up'] = [(j, C[j]['dev250_path']['cagr'], wd(C[j])) for j in srt[1:4]]
            t['gap_to_runner_up'] = C[srt[0]]['dev250_path']['cagr'] - C[srt[1]]['dev250_path']['cagr'] if len(srt) > 1 else None
            t['top10_median'] = float(np.median([C[j]['dev250_path']['cagr'] for j in srt[:10]]))
            nb = neighbors(C, b); nbi = [j for j in nb if wd(C[j]) >= bud]
            t['neighbors'] = [(j, C[j]['dev250_path']['cagr'], wd(C[j])) for j in nb]
            t['neighbors_in_median'] = float(np.median([C[j]['dev250_path']['cagr'] for j in nbi])) if nbi else None
            # near-boundary configs that would beat the pick if the bound moved by 0.5pp (fragility)
            t['near_out_beating_pick'] = sorted([(j, C[j]['dev250_path']['cagr'], wd(C[j])) for j in C if bud - 0.005 <= wd(C[j]) < bud and C[j]['dev250_path']['cagr'] > C[b]['dev250_path']['cagr']], key=lambda x: -x[1])[:5]
            t['in_within_0p1pp_of_bound'] = [(j, wd(C[j])) for j in ins if wd(C[j]) - bud < 0.001]
            # code-recorded pick
            rec = S[name].get('best') if setname == 'DF1' else S[name].get('union_best')
            t['recorded'] = rec; t['match_recorded'] = (rec == b)
        T[name] = t
    sel[setname] = T
out['selection'] = sel
# fallback: main tier
for setname in ('DF1', 'UNION'):
    T = sel[setname]; main = 'A' if T['A']['best'] else ('A_fallback_25' if T['A_fallback_25']['best'] else 'B')
    out.setdefault('main_tier', {})[setname] = main

# validations of the ADOPTED picks per pre-registration (DF2: union tier set)
adopted = {'A_fallback_25': ('v1|s0.1|L1.0|K1|RB', -0.25), 'B': ('v1|s0.2|L1.0|K1|RB', -0.30), 'C': ('DF2|M2|b1|v1|s0.3|L1.5|K2|RB', -0.40)}
val = {}
for name, (i, bud) in adopted.items():
    _, ins_u, _ = pick(U, bud); _, ins_1, _ = pick(C1, bud)
    val[name] = dict(pick=i, union=validate(U, i, bud, ins_u))
    if i in C1: val[name]['df1_set'] = validate(C1, i, bud, ins_1)
    # recorded
    val[name]['recorded_union'] = {k: v for k, v in S2['tiers'][name]['validation'].items()}
out['validation'] = val
# DF2 recorded gate + adoption logic replay
gl = {}
for name in ('A_fallback_25', 'B', 'C'):
    t = S2['tiers'][name]; g = t.get('gate')
    if g: gl[name] = dict(gate=g, a_margin=g['df2_bondx0'] - g['df1_bondx0'], b_margin=g['df2_cost2x'] - g['df1_cost2x'],
                         adopt_by_rule=(t['union_best'] if (g['df2_bondx0'] > g['df1_bondx0'] and g['df2_cost2x'] > g['df1_cost2x']) else t['df1_best']),
                         recorded_adopted=t['adopted'], df1_best_matches_select=t['df1_best'] == S1['tiers'][name]['best'])
    else: gl[name] = dict(no_gate=True, union_best=t.get('union_best'), adopted=t.get('adopted'))
out['gates_recorded'] = gl
# robust.json / robust_df2 cross-check: base rows equal grid rows (consistency)
rb = json.load(open(R + 'robust.json')); rb2 = json.load(open(R + 'robust_df2.json'))
cc = {}
for t, i in rb['picks'].items():
    for b in ('dev250_path', 'real_ndx_86_14', 'real_spx_29_54'):
        cc['%s|%s' % (t, b)] = abs(rb['rows']['%s|%s|base' % (t, b)]['cagr'] - U[i][b]['cagr'])
for t, i in rb2['picks'].items():
    for b in ('dev250_path', 'real_ndx_86_14', 'real_spx_29_54'):
        cc['df2:%s|%s' % (t, b)] = abs(rb2['rows']['%s|%s|base' % (t, b)]['cagr'] - U[i][b]['cagr'])
out['robust_base_vs_grid_absdiff'] = cc
out['robust_picks'] = dict(df1=rb['picks'], df2=rb2['picks'])
# bondx0 / cost2x rows in robust files vs gate numbers (same definitions?)
out['gate_vs_robust'] = dict(
    df1_B_bondx0_robust=rb['rows']['B|dev250_path|bondx0']['cagr'], df1_B_cost2x_robust=rb['rows']['B|dev250_path|cost2x']['cagr'],
    df1_C_bondx0_robust=rb['rows']['C|dev250_path|bondx0']['cagr'], df1_C_cost2x_robust=rb['rows']['C|dev250_path|cost2x']['cagr'],
    df2_C_bondx0_robust=rb2['rows']['C_df2|dev250_path|bondx0']['cagr'], df2_C_cost2x_robust=rb2['rows']['C_df2|dev250_path|cost2x']['cagr'],
    ex_robust_path=rb['rows']['B|dev250_path|bondx0_excess']['excess_removed'])
json.dump(out, open(sys.argv[1], 'w'), indent=1, default=str)
print(json.dumps(out, indent=1, default=str)[:20000])
