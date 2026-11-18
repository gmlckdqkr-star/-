import json, sys
def gate(row, Q, key):
    a, q = row[key], Q[key]
    if key == 'REAL':
        ddm = 1 - abs(a['mdd_med']) / abs(q['mdd_med']); ok = a['cagr'] > q['cagr'] and ddm >= 0.1 - 1e-12
        return ok, dict(exc=round((a['cagr'] - q['cagr']) * 100, 3), ddm=round(ddm, 4))
    ddm = 1 - abs(a['mdd_p10']) / abs(q['mdd_p10'])
    c = dict(pair=a['pair'] > 0, med=a['cagr'] > q['cagr'], p10=a['p10'] >= q['p10'] - 1e-12, dd=ddm >= 0.1 - 1e-12)
    return all(c.values()), dict(pair=round(a['pair'] * 100, 3), med=round((a['cagr'] - q['cagr']) * 100, 3), p10=round((a['p10'] - q['p10']) * 100, 3), ddm=round(ddm, 4),
                                 fail=[k for k, v in c.items() if not v])
if __name__ == '__main__':
    W = {wn: json.load(open('/tmp/df6v/repro/conv_%s.json' % wn)) for wn in ('REAL', 'P', 'X')}
    R = {wn: json.load(open('/tmp/df6v/repro/res_%s.json' % wn)) for wn in ('REAL', 'P', 'X')}
    keys = ['REAL', 'P30', 'P10', 'X30', 'X10']
    def wof(k): return 'REAL' if k == 'REAL' else k[0]
    rows = sorted(set(k for wn in W for k in W[wn] if '|' in k) | {'c252|N1', 'c63|N1', 'c252|N2', 'c63|N2', 'c252|N1-0.5', 'c63|N1-0.5', 'c252|N1-1.0', 'c63|N1-1.0'})
    for rn in rows:
        tot = True; det = {}
        for k in keys:
            src = W[wof(k)] if rn in W[wof(k)] else R[wof(k)][k]
            if rn in W[wof(k)]:
                row = W[wof(k)][rn]; Q = W[wof(k)]['QQQ']
            else:
                row = {k: R[wof(k)][k][rn]}; Q = {k: R[wof(k)][k]['QQQ']}
            ok, d = gate(row, Q, k); tot &= ok; det[k] = ('PASS' if ok else 'FAIL', d)
        print(rn, 'ALL5' if tot else 'fails', json.dumps(det))
