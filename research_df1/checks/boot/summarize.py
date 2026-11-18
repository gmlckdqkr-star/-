"""Summarise check 'boot' (reads the per-pool caches written by boot_pools.py) -> result.json. <=2014 data only; all bootstrap
paths are NON-ACTUAL. Verdict rule (from the check brief): a pick 'changes' if, on any of the 6 asked pools, the tier's adopted
config differs from it, or its own path median after-tax CAGR moves by more than 0.5pp vs the stored headline."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boot_pools as BP

base = json.load(open(BP.CACHE + 'pool_base_s7_b250.json'))
pools = {nm: json.load(open(BP.CACHE + 'pool_%s.json' % nm)) for nm in BP.POOLS if os.path.exists(BP.CACHE + 'pool_%s.json' % nm)}
STORED = {'T25': 0.08971865877854601, 'T30': 0.10176786261808246, 'T40': 0.13239235115204007}
BUD = dict(BP.TIERS)
wd = BP.wd

def rank_in(p, tab, bud):
    ins = [i for i in BP.CFG if wd(i, tab) >= bud]
    pool_ = ins if p in ins else ins + [p]
    order = sorted(pool_, key=lambda i: -tab[i]['cagr'])
    return order.index(p) + 1, len(ins)

out = dict(check='boot', note='bootstrap pools are NON-ACTUAL resamples of 1986-01-02..2014-12-31 NDX (<=2014 only)',
           repro_base=dict(max_abs_dcagr=max(abs(base['tab'][i]['cagr'] - BP.G[i]['dev250_path']['cagr']) for i in BP.CFG),
                           max_abs_dmddp10=max(abs(base['tab'][i]['mdd_p10'] - BP.G[i]['dev250_path']['mdd_p10']) for i in BP.CFG)),
           pools={}, picks={}, tiers={}, robust_posthoc={})
for nm, r in pools.items():
    out['pools'][nm] = dict(seed=r['seed'], block=r['block'], asked=nm in BP.ASKED,
                            tiers={t: {k: v for k, v in s.items() if k != 'budget'} for t, s in r['sel'].items()})

for tn, p in BP.PICKS.items():
    bud = BUD[tn]; rows = {}
    for nm, r in pools.items():
        tab = r['tab']; rk, nin = rank_in(p, tab, bud); s = r['sel'][tn]
        rows[nm] = dict(path=tab[p]['cagr'], d_pp=100 * (tab[p]['cagr'] - STORED[tn]), mdd_p10=tab[p]['mdd_p10'], wd=wd(p, tab),
                        in_tier=bool(wd(p, tab) >= bud), rank=rk, n_in=nin, tier_adopted=s.get('adopted'),
                        tier_adopted_path=s.get('adopted_cagr'), tier_union_best=s.get('union_best'), still_picked=s.get('adopted') == p)
    ask = [rows[n] for n in BP.ASKED if n in rows]
    changed = [n for n in BP.ASKED if n in rows and not rows[n]['still_picked']]
    moved = [n for n in BP.ASKED if n in rows and abs(rows[n]['d_pp']) > 0.5]
    out['picks'][tn] = dict(id=p, stored_path=STORED[tn], rows=rows,
                            asked_path_min=min(x['path'] for x in ask), asked_path_med=float(np.median([x['path'] for x in ask])),
                            asked_path_max=max(x['path'] for x in ask), asked_out_of_tier=[n for n in BP.ASKED if n in rows and not rows[n]['in_tier']],
                            asked_pick_changed=changed, asked_moved_gt_0p5pp=moved,
                            verdict='material_change' if (changed or moved) else 'no_change')

for tn, bud in BP.TIERS:
    out['tiers'][tn] = {nm: dict(n_in=r['sel'][tn]['n_in'], adopted=r['sel'][tn].get('adopted'), path=r['sel'][tn].get('adopted_cagr'),
                                 union_best=r['sel'][tn].get('union_best'), gate=r['sel'][tn].get('gate')) for nm, r in pools.items()}
    # post-hoc reference only (not a selection rule): configs inside the tier on base + every asked pool
    use = ['base_s7_b250'] + [n for n in BP.ASKED if n in pools]
    allin = [i for i in BP.CFG if all(wd(i, pools[n]['tab']) >= bud for n in use)]
    sc = sorted(allin, key=lambda i: -np.median([pools[n]['tab'][i]['cagr'] for n in use]))[:5]
    out['robust_posthoc'][tn] = dict(n_in_all_pools=len(allin), top=[dict(id=i, med_path=float(np.median([pools[n]['tab'][i]['cagr'] for n in use])),
                                     min_path=float(min(pools[n]['tab'][i]['cagr'] for n in use)), base_path=pools['base_s7_b250']['tab'][i]['cagr'],
                                     worst_wd=float(min(wd(i, pools[n]['tab']) for n in use))) for i in sc])
    # how often each config is in-tier, for the pick
# knife-edge margins on the headline basis (base pool = stored dev250_path)
bt = base['tab']
out['margins_base'] = dict(
    T25_pick_wd_minus_budget_pp=100 * (wd(BP.PICKS['T25'], bt) + 0.25), T30_pick_wd_minus_budget_pp=100 * (wd(BP.PICKS['T30'], bt) + 0.30),
    T40_pick_wd_minus_budget_pp=100 * (wd(BP.PICKS['T40'], bt) + 0.40),
    T30_DF2_M2_s02_mddp10=bt['DF2|M2|b1|v1|s0.2|L1.0|K1|RB']['mdd_p10'],
    T40_gate_bondx0_margin_pp={nm: 100 * (r['sel']['T40']['gate']['df2_bondx0'] - r['sel']['T40']['gate']['df1_bondx0'])
                               for nm, r in pools.items() if r['sel']['T40'].get('union_best') == BP.PICKS['T40']})
if os.path.exists(BP.OUT + 'pooled_b250.json'):
    out['pooled_b250'] = json.load(open(BP.OUT + 'pooled_b250.json'))
    g = out['pooled_b250']['tiers']['T40'].get('gate')
    if g: out['margins_base']['T40_gate_bondx0_margin_pp']['pooled_b250'] = 100 * (g['df2_bondx0'] - g['df1_bondx0'])
json.dump(out, open(BP.OUT + 'result.json', 'w'), indent=1)
print('margins', json.dumps(out['margins_base']))

for tn, d in out['picks'].items():
    print('== %s %s stored %.4f  verdict %s  changed %s  moved>0.5 %s  out-of-tier %s' % (tn, d['id'], d['stored_path'], d['verdict'],
          d['asked_pick_changed'], d['asked_moved_gt_0p5pp'], d['asked_out_of_tier']))
    for nm, x in d['rows'].items():
        print('   %-14s path %.4f (%+.2fpp) mddp10 %.4f wd %.4f in %d rank %d/%d | tier adopts %s %.4f' % (
            nm, x['path'], x['d_pp'], x['mdd_p10'], x['wd'], x['in_tier'], x['rank'], x['n_in'], x['tier_adopted'], x['tier_adopted_path'] or 0))
for tn in out['tiers']:
    print('== tier', tn, {nm: (v['n_in'], v['adopted'], round(v['path'], 4) if v['path'] else None) for nm, v in out['tiers'][tn].items()})
    print('   robust post-hoc:', out['robust_posthoc'][tn])
