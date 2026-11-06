import json
G = json.load(open('/mnt/project-files/research/acct3/results/grid.json'))
for W in ('W10', 'W30', 'W100'):
    rows = [(k, v['dev250_path']) for k, v in G.items() if k.startswith(W + '_')]
    base = [p for k, p in rows if '_R1_O1_Z1.00_' in k][0]
    ok = [(k, p) for k, p in rows if p['dd80'] <= 0.732]
    best = max(p['cagr'] for k, p in ok)
    near = sorted([(k, p) for k, p in ok if p['cagr'] >= best - 0.003], key=lambda x: (x[1]['dd80'], -x[1]['cagr']))
    print(W, 'Z-only %.3f dd80 %.3f | best %.3f' % (base['cagr'], base['dd80'], best))
    for k, p in near[:6]:
        g = G[k]; print('   %-30s path %.3f dd80 %.3f p10 %.3f | NDX %.3f SPX55 %.3f SPX70 %.3f glued %.3f' % (k, p['cagr'], p['dd80'], p['p10'],
              g['real_ndx_86_14']['cagr'], g['real_spx_55_85']['cagr'], g['real_spx_70_85']['cagr'], g['dev250_glued']['cagr']))
    # best with F>0
    fk = max([(k, p) for k, p in ok if not k.endswith('F0.00')], key=lambda x: x[1]['cagr'])
    print('   best with futures: %s %.3f dd80 %.3f' % (fk[0], fk[1]['cagr'], fk[1]['dd80']))
