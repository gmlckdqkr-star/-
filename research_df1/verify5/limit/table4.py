import json
O = json.load(open('/tmp/df5v/limit/exp_e4.json'))
for wn in ('X', 'P'):
    R = O[wn]; q = R['QQQ_frictionless']
    print('\n== %s30 frictionless QQQ: med %.2f%%  p10 %.2f%%  p10MDD %.1f%%  medMDD %.1f%%  ndx vol %.1f%%' % (wn, q['cagr']*100, q['p10']*100, q['mdd_p10']*100, q['mdd_med']*100, R['ndx_vol_median_path']*100))
    for k, d in R.items():
        if not isinstance(d, dict) or 'pair' not in d: continue
        print('  %-20s med %6.2f%% pair %+6.2fpp p10 %6.2f%% p10MDD %6.1f%% ddm %+6.1f%% %s %s %s' % (k, d['cagr']*100, d['pair']*100, d['p10']*100, d['mdd_p10']*100, d['ddm']*100,
              ('avgL %.2f' % d['avgL']) if 'avgL' in d else '', 'GATE' if d['gate'] else '', 'both0' if d['both0'] else ''))
