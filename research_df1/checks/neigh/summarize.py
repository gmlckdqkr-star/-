"""neigh summary: local.json + resel/*.json -> result.json + REPORT.md. Pure bookkeeping, no new engine runs."""
import sys, json, glob, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/checks/neigh')
D = '/mnt/project-files/research/df1/checks/neigh/'
L = json.load(open(D + 'local.json'))
G = {}
for f in sorted(glob.glob(D + 'resel/*.json')):
    r = json.load(open(f)); G[r['name']] = r
U = json.load(open('/mnt/project-files/research/df1/results/grid.json'))['configs']
U.update(json.load(open('/mnt/project-files/research/df1/results/grid_df2.json'))['configs'])
import neighlib as NL
F = NL.frontier(U)
pc = lambda x: 100 * x

def verdict(s):
    """rule fixed before reading the summary table: PLATEAU = >=60% of core neighbours inside tier AND within 1pp, and >=50% of joint
    draws inside tier; CAGR-PLATEAU/TIER-EDGE = >=80% within 1pp but tier retention below those bars; SPIKE = <60% within 1pp."""
    if s['share_core_within_1pp'] < 0.6: return 'SPIKE'
    if s['share_core_in_tier_and_1pp'] >= 0.6 and s['joint_share_in_tier'] >= 0.5: return 'PLATEAU'
    return 'CAGR-PLATEAU / TIER-EDGE'

res = dict(check='neigh', data='<=2014 only; dev250_path = 500 NON-ACTUAL bootstrap paths; real NDX 1986-2014; real S&P 1929-54 fill A',
           tiers_note='T40 as given in BRIEF_CHECKS = DF2|M2|b1|v1|s0.3|L1.5|K2|RB (original gate). results/select_df2_fixed.json '
                      '(audit-fixed gate, written after the brief) adopts v1|s0.3|L1.0|K2|RB in tier C instead; tested here as T40alt.',
           local={}, reselect={})
for p, P in L['picks'].items():
    b = P['base']; s = dict(P['summary']); base_gap = b['path'] - F(b['wd'])
    core = [r for r in P['rows'] if r['group'] == 'core']
    gaps = [r['path'] - F(r['wd']) for r in core if not np.isnan(F(r['wd']))]
    s['base_gap_vs_grid_frontier'] = base_gap
    s['core_rel_frontier_gap_median'] = float(np.median(gaps) - base_gap) if gaps else None
    jg = [r['path'] - F(r['wd']) for r in P['joint'] if not np.isnan(F(r['wd']))]
    s['joint_rel_frontier_gap_median'] = float(np.median(jg) - base_gap) if jg else None
    s['core_out_of_tier'] = [(r['name'], round(pc(r['wd']), 2)) for r in core if not r['in_tier']]
    s['core_over_1pp'] = [(r['name'], round(pc(r['dpath']), 2)) for r in core if abs(r['dpath']) > 0.01]
    s['wd_binding_out_of_tier'] = {r['name']: min((('path_mdd_p10', r['path_mdd_p10']), ('ndx_mdd', r['ndx_mdd']), ('spx29_mdd', r['spx29_mdd'])),
                                                  key=lambda x: x[1])[0] for r in core if not r['in_tier']}
    s['verdict'] = verdict(s)
    res['local'][p] = dict(id=P['id'], budget=P['budget'], base=b, summary=s,
                           rows=[{k: r[k] for k in ('group', 'fam', 'name', 'path', 'path_p10', 'path_mdd_p10', 'ndx', 'ndx_mdd', 'spx29',
                                                    'spx29_mdd', 'wd', 'in_tier', 'dpath', 'ntr')} for r in P['rows']])
# ---- reselection
base = G.get('base')
TN = {'A': 'T20', 'A_fallback_25': 'T25', 'B': 'T30', 'C': 'T40'}
summ = {}
for tn in ('A', 'A_fallback_25', 'B', 'C'):
    rows = []
    for nm, r in G.items():
        t = r['tiers'][tn]
        row = dict(variant=nm, n_in=t['n_in'])
        for g in ('orig', 'fixed'):
            a = t.get('adopted_' + g)
            row['adopted_' + g] = a
            if a:
                rr = t['adopted_%s_row' % g]; row['%s_path' % g] = rr['path']; row['%s_wd' % g] = rr['wd']; row['%s_ndx' % g] = rr['ndx']
        row['union_best'] = t.get('union_best'); row['df1_best'] = t.get('df1_best')
        rows.append(row)
    sm = {}
    if base:
        bt = base['tiers'][tn]
        for g in ('orig', 'fixed'):
            b0 = bt.get('adopted_' + g); var = [x for x in rows if x['variant'] != 'base']
            sm[g] = dict(base_pick=b0, n_variants=len(var), n_flipped=sum(x['adopted_' + g] != b0 for x in var),
                         flipped=[(x['variant'], x['adopted_' + g], round(pc(x.get(g + '_path', np.nan)), 2), round(pc(x.get(g + '_wd', np.nan)), 2))
                                  for x in var if x['adopted_' + g] != b0],
                         path_min=min((x[g + '_path'] for x in var if x['adopted_' + g]), default=None),
                         path_max=max((x[g + '_path'] for x in var if x['adopted_' + g]), default=None),
                         path_median=float(np.median([x[g + '_path'] for x in var if x['adopted_' + g]])) if any(x['adopted_' + g] for x in var) else None)
        sm['n_in_range'] = [min(x['n_in'] for x in rows), max(x['n_in'] for x in rows)]
    summ[TN[tn]] = dict(rows=rows, summary=sm)
res['reselect'] = summ
# where does each adopted pick stand inside its tier under each variant
stand = {}
for p, cid in NL.PICKS.items():
    tn = {'T25': 'A_fallback_25', 'T30': 'B', 'T40': 'C', 'T40alt': 'C'}[p]
    st = []
    for nm, r in G.items():
        pr = r['picks_rows'][p]; st.append(dict(variant=nm, path=pr['path'], wd=pr['wd'], in_tier=bool(pr['wd'] >= NL.BUD[p])))
    stand[p] = st
res['pick_rows_in_reselect'] = stand
json.dump(res, open(D + 'result.json', 'w'), indent=1)

# ---- console + report
lines = []
for p, x in res['local'].items():
    s = x['summary']; b = x['base']
    lines.append('%s %s: base path %.2f WD %.2f | core %d: in-tier %.0f%%, within1pp %.0f%%, both %.0f%% | core path %.2f..%.2f | joint100: in-tier %.0f%%, '
                 'within1pp %.0f%%, path p10/med/p90 %.2f/%.2f/%.2f, WD med %.2f | rel frontier gap core %s joint %s -> %s' % (
                     p, x['id'], pc(b['path']), pc(b['wd']), s['n_core'], pc(s['share_core_in_tier']), pc(s['share_core_within_1pp']),
                     pc(s['share_core_in_tier_and_1pp']), pc(s['core_path_min']), pc(s['core_path_max']), pc(s['joint_share_in_tier']),
                     pc(s['joint_share_within_1pp']), pc(s['joint_path_p10']), pc(s['joint_path_median']), pc(s['joint_path_p90']),
                     pc(s['joint_wd_median']), None if s['core_rel_frontier_gap_median'] is None else round(pc(s['core_rel_frontier_gap_median']), 2),
                     None if s['joint_rel_frontier_gap_median'] is None else round(pc(s['joint_rel_frontier_gap_median']), 2), s['verdict']))
for t, x in res['reselect'].items():
    lines.append('%s reselect: %s' % (t, json.dumps({g: {k: v for k, v in x['summary'].get(g, {}).items()} for g in ('orig', 'fixed')}) if x['summary'] else ''))
print('\n'.join(lines))
print('\n== reselect tables (ids keep pre-shift labels for sigshift variants)')
for t, x in res['reselect'].items():
    print('--', t)
    for r in x['rows']:
        print('  %-16s n_in %4d | orig %-32s %6s %6s | fixed %-32s %6s %6s' % (
            r['variant'], r['n_in'], r['adopted_orig'], '%.2f' % pc(r['orig_path']) if r['adopted_orig'] else '-', '%.2f' % pc(r['orig_wd']) if r['adopted_orig'] else '-',
            r['adopted_fixed'], '%.2f' % pc(r['fixed_path']) if r['adopted_fixed'] else '-', '%.2f' % pc(r['fixed_wd']) if r['adopted_fixed'] else '-'))
print('\n== adopted picks themselves under each global variant (path, WD, in tier)')
for p, st in res['pick_rows_in_reselect'].items():
    print(p, ' '.join('%s:%.2f/%.2f%s' % (s['variant'], pc(s['path']), pc(s['wd']), '' if s['in_tier'] else '*') for s in st))
# ---- DF2 gate margins (pp) per environment: union_best(DF2) minus DF1 best of the same tier; adoption needs both > 0
gm = {}
for nm, r in G.items():
    for tn in ('B', 'C'):
        t = r['tiers'][tn]
        for g in ('orig', 'fixed'):
            x = t.get('gate_' + g)
            if x: gm.setdefault(TN[tn], {}).setdefault(g, {})[nm] = dict(union_best=t['union_best'], df1_best=t['df1_best'],
                                                                          bondx0_margin_pp=round(pc(x['df2_bondx0'] - x['df1_bondx0']), 3),
                                                                          cost2x_margin_pp=round(pc(x['df2_cost2x'] - x['df1_cost2x']), 3))
res['gate_margins'] = gm
res['final_verdicts'] = {
    'T25': 'CAGR-PLATEAU / TIER-EDGE: own CAGR flat (16/17 one-at-a-time neighbours within 1pp, joint median 8.96 vs 8.97) but WD sits on the '
           'favourable edge (10/17 core and 34/100 joint neighbours keep WD>=-25%; joint WD median -25.74). Whole-set reselection: the -25% tier '
           'is EMPTY in 3/17 off-grid environments and its winner drops to 2.55-7.89% in 4 more.',
    'T30': 'CAGR-PLATEAU / TIER-EDGE (knife-edge WD): own CAGR flat (16/17 within 1pp) but WD -29.97 vs budget -30 -> only 7/17 core and '
           '17/100 joint neighbours stay inside; joint WD median -31.48. Reselection: tier winner identity flips in 12-13/17 environments, '
           'tier winner CAGR 9.10-11.62 (median 10.27-10.35), so the tier-level number is ~stable while the pick identity is not.',
    'T40': 'Config itself: mostly plateau (14/17 core in tier, 15/17 within 1pp; joint 38% in tier, joint path median 12.95). ADOPTION is a '
           'SPIKE: DF2 bond-excess-0 gate margin vs v1|s0.3|L1.0|K2|RB is +0.02pp (original gate) / -0.27pp (audit-fixed gate); under 17 '
           'off-grid environments the original-gate rule keeps this config in only 2/17 and the tier-C adopted CAGR median is 11.51% '
           '(audit-fixed gate: 11.42%) instead of 13.24%.',
    'T40alt': 'PLATEAU: v1|s0.3|L1.0|K2|RB (tier-C adopted under the audit-fixed gate) keeps 16/17 core and 92/100 joint neighbours in tier, '
              'all 17 core within 1pp (10.81-11.58); adopted in 13/17 environments under the fixed gate.'}
json.dump(res, open(D + 'result.json', 'w'), indent=1)
print('result.json written with gate margins + verdicts')
