import json
d = json.load(open('/mnt/project-files/research/theory_sim/design/L1/work/final_eval.json'))
g = json.load(open('/mnt/project-files/research/theory_sim/design/L1/work/diag_final.json'))
def W(w):
    x = d[w]; o = {'rule': x['rule']}
    for k in ('hold1x', 'hold2x', 'hold3x'): o[k] = x[k]
    o['const_levels_cagr_med'] = {k[5:]: v['cagr_med'] for k, v in x.items() if k.startswith('const')}
    o['best_const'] = x['best_const']
    o['rule_minus_best_const'] = round(x['rule']['cagr_med'] - x['best_const']['cagr_med'], 5)
    o['rule_minus_hold1x'] = round(x['rule']['cagr_med'] - x['hold1x']['cagr_med'], 5)
    for k in ('rule_delay3', 'rule_delay5', 'rule_cost2x'):
        if k in x: o[k] = x[k]
    return o
res = dict(
    lane='TS1-L1', theory='Margin-Ratchet Leverage Cycle (MRLC)',
    rule_file='rule.py', rule_params=d['rule_params'], fixed_constants=dict(kelly_fraction=0.5, variance_floor=0.03 ** 2),
    n_tunable_params=6, n_variants_evaluated=131,
    selection=dict(seeds=[11, 12], criterion='max J = 0.5*ON + 0.5*OFF median after-tax CAGR (own sim) s.t. OFF >= best constant OFF on each selection seed'),
    fresh=dict(seeds=d['seeds'], paths_per_seed=d['paths_per_seed'], T=d['T'], horizon_years=30),
    mechanism_on=W('on_prior1.0'), mechanism_off=W('off_prior1.0'),
    prior_narrowed_0p5=dict(on=W('on_prior0.5'), off=W('off_prior0.5')),
    prior_widened_1p5=dict(on=W('on_prior1.5'), off=W('off_prior1.5')),
    mechanism_off_loss_vs_best_const=round(d['off_prior1.0']['best_const']['cagr_med'] - d['off_prior1.0']['rule']['cagr_med'], 5),
    block250_resampled_on=g['block250_on'],
    edge_by_effective_speculator_footprint_quartile_on=g['edge_by_effective_footprint_quartile'],
    notes='all CAGR numbers are medians over paths of 30-year after-tax CAGR from exec_engine; synthetic data only; '
          'mechanism_off_loss_vs_best_const < 0 means the rule beat the best constant level in the random-walk world.')
json.dump(res, open('/mnt/project-files/research/theory_sim/design/L1/synth_results.json', 'w'), indent=1)
print(json.dumps({k: res[k] for k in ('mechanism_off_loss_vs_best_const',)}, indent=1))
print('ON rule', res['mechanism_on']['rule']['cagr_med'], 'OFF rule', res['mechanism_off']['rule']['cagr_med'])
