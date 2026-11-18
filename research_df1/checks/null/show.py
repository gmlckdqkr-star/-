import json
R = json.load(open('/mnt/project-files/research/df1/checks/null/result.json'))
MK = R['meta']['markets']
print('state frac (0,1,3) and alarm frac')
for bn in MK: print(' ', bn, {k: [round(x, 3) for x in v] if isinstance(v, list) else round(v, 3) for k, v in R['state_frac'][bn].items()})
for pk, lad in R['ladder'].items():
    print('==== LADDER', pk, R['meta']['picks'][pk]['id'], 'novt const', round(lad['_novt_const_on'], 3))
    print('   %-18s %15s %15s %15s %15s  %8s  lev  ntr' % ('variant', 'path cagr/dd10', 'NDX cagr/mdd', 'SPX29', 'SPX55', 'WD'))
    for v, r in lad.items():
        if v.startswith('_'): continue
        print('   %-18s ' % v + ' '.join('%7.4f/%7.4f' % (r[b]['cagr'], r[b]['dd']) for b in MK) + '  %8.4f  %.2f %4.0f' % (r['WD'], r['dev250_path']['lev'], r['dev250_path']['ntr']))
for pk, d in R['placebo'].items():
    print('==== PLACEBO', pk)
    for bn in MK:
        x = d[bn]; print('   %-15s cagr pick %.4f plc med %.4f [p10 %.4f p90 %.4f] pct %5.1f | dd pick %.4f plc med %.4f [p10 %.4f p90 %.4f] pct %5.1f' % (
            bn, x['pick_cagr'], x['plc_cagr_med'], x['plc_cagr_p10'], x['plc_cagr_p90'], x['pick_cagr_pct'], x['pick_dd'], x['plc_dd_med'], x['plc_dd_p10'], x['plc_dd_p90'], x['pick_dd_pct']))
    print('   WD', {k: round(v, 4) for k, v in d['WD'].items()})
for pk, F in R['frontier'].items():
    print('==== FRONTIER', pk, F['pick'])
    for k, e in F.items():
        if k == 'pick' or e is None: print('  ', k, e if k != 'pick' else ''); continue
        print('   %-40s %-28s WD %.4f path %.4f NDX %.4f SPX29 %.4f SPX55 %.4f(%.3f) %s' % (k, e['id'], e['WD'], e['dev250_path'][0], e['real_ndx_86_14'][0], e['real_spx_29_54'][0], e['real_spx_55_85'][0], e['real_spx_55_85'][1],
              ('d %.4f bx0 %.4f d_bx0 %.4f' % (e['path_minus_pick'], e['bondx0_path'], e['bondx0_minus_pick'])) if 'bondx0_path' in e else ''))
for pk, A in R['attribution'].items():
    print('==== ATTRIB', pk)
    for k, v in A.items(): print('   %-32s' % k, {a: round(b, 4) for a, b in v.items()})
