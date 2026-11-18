import json, sys
OUT = '/mnt/project-files/research/df1/verify7/repro/'
for w in sys.argv[1:]:
    S = json.load(open(OUT + 's2_%s.json' % w))
    print('==', w, S.get('real_dates'), S['sig_check'])
    for conv, q in S['qqq'].items():
        for k, v in q.items(): print(' QQQ', conv, k, 'max|d|=%.2e' % max(abs(x) for x in v['d_stored'].values()), 'dfk parity cg %.2e md %.2e' % (v['dfk_parity_cg'], v['dfk_parity_md']))
    mx = {}; bad = []
    for i, kk in S['prim'].items():
        for k, v in kk.items():
            for f, d in v['d'].items():
                mx[f] = max(mx.get(f, 0), abs(d))
                if f in ('cagr', 'p10', 'mdd_med', 'mdd_p10', 'pair') and abs(d) > 1e-6: bad.append((i, k, f, d))
    print(' PRIM rows rerun:', len(S['prim']), 'max|d| per field', {f: '%.2e' % v for f, v in mx.items()}, 'mismatches>1e-6:', len(bad))
    for b in bad[:30]: print('   ', b)
    for conv, R in S['report'].items():
        print(' report', conv, 'qqq', {k: '%.2e' % max(abs(x) for x in v['d'].values()) for k, v in R['qqq'].items()})
        for i, kk in R['rows'].items():
            for k, v in kk.items():
                m = max(abs(x) for f, x in v['d'].items())
                print('   ', conv, i, k, 'cagr %.4f mdd_med %.4f mdd_p10 %.4f' % (v['mine']['cagr'], v['mine']['mdd_med'], v['mine']['mdd_p10']), 'max|d| %.2e' % m)
