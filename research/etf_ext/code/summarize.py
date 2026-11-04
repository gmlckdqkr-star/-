"""ETX1 summary: reads results/*.json, prints compact tables + pass flags (PRECOMMIT_ETX1 (a)-(d) and S3 (f)(g)). No new computation."""
import json, os, glob
R = '/mnt/project-files/research/etf_ext/results/'
BASES = ['dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85']


def J(fn):
    fn = R + fn; return json.load(open(fn)) if os.path.exists(fn) else None


def get(stage, kind, bn, name):
    if stage == 2:
        for fn in ('stage2_stress_%s_%s.json' % (bn, kind), 'stage2_combos_%s_%s.json' % (bn, kind),
                   'stage2_spxext_%s_ext.json' % bn if kind == 'ext' else None, 'screen_%s.json' % bn if kind == 'base' else None):
            if fn is None: continue
            x = J(fn)
            if x and name in x: return x[name]
        return None
    x = J('stage3_%s_%s.json' % (kind, bn)); return x.get(name) if x else None


def flags(stage, name, bond):
    g = lambda kind, bn: get(stage, kind, bn, name)
    out = {}
    p = g('base', 'dev250_path'); out['a'] = bool(p and p['d_ref'] > 0 and p['pw_ref'] >= 0.6)
    eras = [g('base', 'real_ndx_86_14'), g('ext', 'real_spx_55_85') if stage == 2 else g('base', 'real_spx_55_85'), g('base', 'real_spx_70_85')]
    out['b'] = all(e is not None and e['d_ref'] >= -0.01 for e in eras)
    c1, c2 = g('cost2x', 'dev250_path'), g('delay3', 'dev250_path'); out['c'] = bool(c1 and c2 and c1['d_ref'] > 0 and c2['d_ref'] > 0)
    s = g('sgov', 'dev250_path'); out['d'] = bool(s and s['d_ref'] >= 0)
    e1, e2 = g('base', 'pool_e8699'), g('base', 'pool_e0014'); out['f'] = bool(e1 and e2 and e1['d_ref'] >= 0 and e2['d_ref'] >= 0)
    if bond:
        d15 = g('drift15', 'dev250_path'); out['g_drift15'] = bool(d15 and d15['d_ref'] > 0)
    return out


def line(stage, name, bond):
    g = lambda kind, bn: get(stage, kind, bn, name)
    p = g('base', 'dev250_path')
    if p is None: return None
    cells = ['%-22s path %.4f d %+.4f pw %.2f dd80 %.2f' % (name, p['cagr'], p['d_ref'], p['pw_ref'], p['dd80'])]
    for bn, k in (('real_ndx_86_14', 'base'), ('real_spx_55_85', 'ext' if stage == 2 else 'base'), ('real_spx_70_85', 'base'),
                  ('pool_e8699', 'base'), ('pool_e0014', 'base')):
        x = g(k, bn); cells.append('%s %s' % (bn.replace('real_', '').replace('pool_', ''), '%+.4f' % x['d_ref'] if x else '  -   '))
    for k in ('cost2x', 'delay3', 'sgov', 'levx1', 'drift15', 'drift0'):
        x = g(k, 'dev250_path'); cells.append('%s %s' % (k, '%+.4f' % x['d_ref'] if x else '  -  '))
    f = flags(stage, name, bond); cells.append('pass ' + ''.join(k[0] if v else '.' for k, v in f.items()) + (' ALL' if all(f.values()) else ''))
    return ' | '.join(cells)


if __name__ == '__main__':
    print('== s0.85 and same-engine holds')
    for bn in BASES:
        s = J('screen_%s.json' % bn)['s085']; h = J('stage2_holds_%s.json' % bn) or {}
        print('%-15s s085 %.4f p10 %.4f dd80 %.3f | QQQ %s QLD %s TQQQ %s' % (bn, s['cagr'], s['p10'], s['dd80'],
              *['%.4f' % h[k]['cagr'] if k in h else '-' for k in ('QQQ', 'QLD', 'TQQQ')]))
    for bn in ('pool_e8699', 'pool_e0014'):
        x = J('stage2_stress_%s_base.json' % bn); print('%-15s s085 %.4f' % (bn, x['s085']['cagr']))
    print('== implementation levers (s0.85 alone)')
    for bn in ('dev250_path', 'real_ndx_86_14', 'real_spx_70_85'):
        print(bn, ' '.join('%s %.4f' % (k, J('stage2_stress_%s_%s.json' % (bn, k))['s085']['cagr']) for k in ('base', 'fee10', 'rp1', 'fee10rp1', 'sgov', 'cost2x')))
    print('== stage 2 (fills + combos); pass letters a b c d f g (f, g = extra checks, not in stage-2 precommit)')
    for n in ['S2_TMF', 'S2_TYD', 'S2_UBT', 'S2_EDV', 'S2_UST', 'S2_TLT', 'C1', 'C2', 'C3', 'C4']:
        l = line(2, n, True)
        if l: print(l)
    print('== stage 2 nulls')
    for fn in sorted(glob.glob(R + 'stage2_null_*.json')):
        x = json.load(open(fn)); print(os.path.basename(fn), 'd_act %+.4f null mean %+.4f p95 %+.4f p %.3f' % (x['d_actual'], x['null_d_mean'], x['null_d_p95'], x['p_value']))
    print('== stage 2 oracles (NOT tradable)')
    for fn in sorted(glob.glob(R + 'stage2_oracle_*.json')):
        x = json.load(open(fn)); r = x['oracle_fill']; print('%-45s %.4f (d %+.4f)' % (os.path.basename(fn), r['cagr'], r['d_ref']))
    st3 = J('stage3_base_dev250_path.json')
    if st3:
        print('== stage 3 (A on-sleeve, B gated fill, C)')
        for n in [k for k in st3 if not k.startswith(('_', 's085'))]:
            l = line(3, n, n.startswith(('B', 'C')))
            if l: print(l)
        for fn in sorted(glob.glob(R + 'stage3_null_*.json')):
            x = json.load(open(fn)); print(os.path.basename(fn), x['cand'], 'd_act %+.4f null mean %+.4f p95 %+.4f p %.3f' % (x['d_actual'], x['null_mean'], x['null_p95'], x['p_value']))
        for fn in sorted(glob.glob(R + 'stage3_oracle_*.json')):
            x = json.load(open(fn)); print(os.path.basename(fn), ' '.join('%s %.4f' % (k, x[k]['cagr']) for k in ('on_only', 'on_and_fill') if k in x))
