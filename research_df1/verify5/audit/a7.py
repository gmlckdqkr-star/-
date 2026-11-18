import json
D = json.load(open('/mnt/project-files/research/df1/results/df5_main.json')); Q = D['qqq']; rows = D['rows']
def row(i):
    s = []
    for k in ['REAL', 'P30', 'P10', 'X30', 'X10']:
        a = rows[i][k]; q = Q[k]; mk = 'mdd_med' if k == 'REAL' else 'mdd_p10'
        s.append('%s pair %+.2f p10 %+.2f ddm %+.1f' % (k, a['pair'] * 100, (a['p10'] - q['p10']) * 100, (1 - abs(a[mk]) / abs(q[mk])) * 100))
    return ' | '.join(s)
# all configs that pass G1-G3 : show X ddm
import sys; sys.path.insert(0, '/mnt/project-files/research/df1/code'); sys.dont_write_bytecode = True
import df5gate as GT
A, G, _ = GT.analyse()
c = [i for i in G if G[i]['g']['G1']['ok'] and G[i]['g']['G2']['ok'] and G[i]['g']['G3']['ok']]
print('pass G1-G3:', len(c))
c.sort(key=lambda i: -min(G[i]['g']['G4']['ddm'], G[i]['g']['G5']['ddm']))
for i in c[:12]:
    print('%-32s G4 fail %s ddm %+.1f | G5 fail %s ddm %+.1f | X30 pair %+.2f X10 pair %+.2f' % (i, G[i]['g']['G4']['fail'], G[i]['g']['G4']['ddm'] * 100, G[i]['g']['G5']['fail'], G[i]['g']['G5']['ddm'] * 100, G[i]['g']['G4']['pair'] * 100, G[i]['g']['G5']['pair'] * 100))
