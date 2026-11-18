"""Aggregate walkfwd result.json across seeds -> result.json['summary'] + printed table. <=2014 only; pool numbers NON-ACTUAL."""
import json, numpy as np
F = '/mnt/project-files/research/df1/checks/walkfwd/result.json'
o = json.load(open(F)); S = {}
for d in ('A2B', 'B2A'):
    S[d] = {}
    keys = [k for k in o['runs'] if k.endswith(d)]
    for tn in ('T25', 'T30', 'T40'):
        rows = []
        for k in keys:
            t = o['runs'][k][tn]
            if 'pick' not in t: rows.append(dict(seed=k.split('_')[0], pick=None)); continue
            p, a, q, v = t['pick_test'], t['adopted_test'], o['runs'][k]['QQQ1x_test'], o['runs'][k]['v1_test']
            rows.append(dict(seed=k.split('_')[0], pick=t['pick'], n_in_sel=t['n_in_sel'], is_pool=t['pick_in_sample']['pool_cagr'], is_wd=t['pick_in_sample']['wd'],
                             gate=bool(t['gate']), oot_real=(p['real_cagr'], p['real_mdd']), oot_pool=(p['pool_cagr'], p['pool_mdd_p10']),
                             def_real=p['defensive_real'], def_pool=p['defensive_pool'], pct=p.get('pctile_pool_cagr_among_test_in_tier'),
                             oracle=t.get('oracle'), oracle_pool=t['oracle_test']['pool_cagr'], oracle_real=t['oracle_test']['real_cagr'],
                             adopted_real=(a['real_cagr'], a['real_mdd']), adopted_pool=(a['pool_cagr'], a['pool_mdd_p10']),
                             adopted_selperiod_wd=t['adopted_sel_period']['wd'], adopted_selperiod_in=t['adopted_sel_period']['in_tier'],
                             qqq_real=(q['real_cagr'], q['real_mdd']), qqq_pool=(q['pool_cagr'], q['pool_mdd_p10']),
                             v1_real=(v['real_cagr'], v['real_mdd']), v1_pool=(v['pool_cagr'], v['pool_mdd_p10'])))
        ok = [r for r in rows if r['pick']]
        agg = dict(n_seeds=len(rows), n_empty=len(rows) - len(ok), picks=sorted(set(r['pick'] for r in ok)),
                   frac_def_real=float(np.mean([r['def_real'] for r in ok])) if ok else None,
                   frac_def_pool=float(np.mean([r['def_pool'] for r in ok])) if ok else None,
                   med_oot_real_cagr=float(np.median([r['oot_real'][0] for r in ok])) if ok else None,
                   worst_oot_real_mdd=float(min(r['oot_real'][1] for r in ok)) if ok else None,
                   med_oot_pool_cagr=float(np.median([r['oot_pool'][0] for r in ok])) if ok else None,
                   worst_oot_pool_mddp10=float(min(r['oot_pool'][1] for r in ok)) if ok else None,
                   med_adopted_pool_cagr=float(np.median([r['adopted_pool'][0] for r in ok])) if ok else None,
                   med_oracle_pool_cagr=float(np.median([r['oracle_pool'] for r in ok])) if ok else None,
                   med_keep_vs_oracle_pool_pp=float(np.median([r['oot_pool'][0] - r['oracle_pool'] for r in ok])) if ok else None,
                   med_keep_vs_adopted_pool_pp=float(np.median([r['oot_pool'][0] - r['adopted_pool'][0] for r in ok])) if ok else None,
                   med_pct_among_test_in_tier=float(np.median([r['pct'] for r in ok if r['pct'] is not None])) if ok else None,
                   adopted_selperiod_in_tier=[r['adopted_selperiod_in'] for r in rows], adopted_selperiod_wd=[round(r['adopted_selperiod_wd'], 4) for r in rows])
        S[d][tn] = dict(rows=rows, agg=agg)
o['summary'] = S; json.dump(o, open(F, 'w'), indent=1)
for d in S:
    print('=====', d, '(select on', 'A=1986-99' if d == 'A2B' else 'B=2000-14', ', test on the other)')
    for tn, x in S[d].items():
        print(' ', tn, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in x['agg'].items()}))
        for r in x['rows']:
            if not r['pick']: print('    %s empty' % r['seed']); continue
            print('    %-7s %-34s nIn %3d IS %.4f WD %.4f gate %d | OOT real %.4f/%.4f pool %.4f/%.4f defR %d defP %d pct %5.1f | adopted real %.4f/%.4f pool %.4f/%.4f selWD %.4f | oracle %-34s pool %.4f real %.4f' % (
                r['seed'], r['pick'], r['n_in_sel'], r['is_pool'], r['is_wd'], r['gate'], r['oot_real'][0], r['oot_real'][1], r['oot_pool'][0], r['oot_pool'][1],
                r['def_real'], r['def_pool'], r['pct'] if r['pct'] is not None else -1, r['adopted_real'][0], r['adopted_real'][1], r['adopted_pool'][0], r['adopted_pool'][1],
                r['adopted_selperiod_wd'], r['oracle'], r['oracle_pool'], r['oracle_real']))
    r = S[d]['T25']['rows'][0]
    print('  refs (seed %s): QQQ real %.4f/%.4f pool %.4f/%.4f | v1 real %.4f/%.4f pool %.4f/%.4f' % (r['seed'], *r['qqq_real'], *r['qqq_pool'], *r['v1_real'], *r['v1_pool']))
