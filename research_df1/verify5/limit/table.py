import json
O = json.load(open('/tmp/df5v/limit/exp_main.json'))
tags = ['base', 'E1div', 'E2cost0', 'E2cost0_d1', 'E2c_tax0', 'ALL_neutral', 'E3raw', 'ALL_raw']
print('QQQ', {t: (round(O['QQQ'][t]['cagr'] * 100, 2), round(O['QQQ'][t]['mdd_p10'] * 100, 1)) for t in O['QQQ']})
for t in tags + ['E1div_spx']:
    print('\n==', t, ' QQQ med %.2f%% p10MDD %.1f%%' % (O['QQQ'][t]['cagr'] * 100, O['QQQ'][t]['mdd_p10'] * 100))
    for c, v in O.items():
        if c in ('QQQ', 'shift_raw') or t not in v: continue
        d = v[t]
        print('  %-36s med %6.2f%%  pair %+6.2fpp  p10 %6.2f%%  p10MDD %6.1f%%  ddm %+6.1f%%  %s%s' % (c, d['cagr'] * 100, d['pair'] * 100, d['p10'] * 100,
              d['mdd_p10'] * 100, d['ddm'] * 100, 'GATE ' if d['gate'] else '', 'both0' if d['both0'] else ''))
if 'shift_raw' in O: print(O['shift_raw'])
