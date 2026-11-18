"""Independent gate code for DF7-B (PRECOMMIT_DF7.md section 3). Does not import df5gate / df7.gates.
G1 REAL: rule CAGR > QQQ CAGR and |MDD| <= 0.9 |QQQ MDD|   (single path: median MDD = the MDD)
G2..G5 (P30, P10, X30, X10): median of paired (rule - QQQ) per-path CAGR > 0, median CAGR > QQQ median,
   p10 CAGR >= QQQ p10, |p10 MDD| <= 0.9 |QQQ p10 MDD|."""
GK = [('G1', 'REAL'), ('G2', 'P30'), ('G3', 'P10'), ('G4', 'X30'), ('G5', 'X10')]

def gate(r, Q, eps=0.0):
    """r, Q: summary dicts per key. eps: tolerance (0 = strict spec). Returns dict G -> (ok, failed conditions, margins)"""
    out = {}
    a, q = r['REAL'], Q['REAL']
    ret = a['cagr'] - q['cagr']; ddm = 1.0 - abs(a['mdd_med']) / abs(q['mdd_med'])
    fl = [n for n, ok in (('ret', ret > 0), ('dd', ddm >= 0.1 - eps)) if not ok]
    out['G1'] = dict(ok=not fl, fail=fl, ret=ret, ddm=ddm)
    for g, k in GK[1:]:
        a, q = r[k], Q[k]
        ddm = 1.0 - abs(a['mdd_p10']) / abs(q['mdd_p10'])
        c = (('pair', a['pair'] > 0), ('med', a['cagr'] > q['cagr']), ('p10', a['p10'] >= q['p10'] - eps), ('dd', ddm >= 0.1 - eps))
        fl = [n for n, ok in c if not ok]
        out[g] = dict(ok=not fl, fail=fl, pair=a['pair'], med=a['cagr'] - q['cagr'], p10=a['p10'] - q['p10'], ddm=ddm)
    return out

def margins_min(G):
    """smallest absolute distance of any gate condition to its threshold (to flag borderline cases)"""
    m = []
    m += [abs(G['G1']['ret']), abs(G['G1']['ddm'] - 0.1)]
    for g in ('G2', 'G3', 'G4', 'G5'):
        m += [abs(G[g]['pair']), abs(G[g]['med']), abs(G[g]['p10']), abs(G[g]['ddm'] - 0.1)]
    return min(m)
