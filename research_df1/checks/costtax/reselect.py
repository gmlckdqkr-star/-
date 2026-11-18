"""Full re-selection (DF1 u DF2, 1,123 configs) under each cost/tax/bond variant: does any tier pick flip or fall out of its tier?
Usage: reselect.py <variant> [...]  -> checks/costtax/resel_<variant>.json. <=2014 only; synthetic bonds NON-ACTUAL."""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/checks/costtax')
import ctlib as CT, dfe, run_df2 as R2
OUT = '/mnt/project-files/research/df1/checks/costtax/'
TIERS = (('A20', -0.20), ('T25', -0.25), ('T30', -0.30), ('T40', -0.40))
PICKS = {'T25': 'v1|s0.1|L1.0|K1|RB', 'T30': 'v1|s0.2|L1.0|K1|RB', 'T40': 'DF2|M2|b1|v1|s0.3|L1.5|K2|RB', 'T40_gatefix': 'v1|s0.3|L1.0|K2|RB'}

def best_of(ids, rows):
    if not ids: return None
    b = max(ids, key=lambda i: rows[i]['dev250_path']['cagr'])
    tie = [i for i in ids if rows[b]['dev250_path']['cagr'] - rows[i]['dev250_path']['cagr'] < 0.0005]
    return max(tie, key=lambda i: rows[i]['real_ndx_86_14']['cagr'])

def gate_vals(cfg, vname, mk, exs, exp):
    n, kw, _ = CT.VARIANTS[vname]; mp = mk['dev250_path']; T = mp['r'].shape[1]
    r = {}
    for nm, ex in (('bondx0_src', exs), ('bondx0_path', exp)):
        m0 = dict(mp); m0['rb'] = mp['rb'] - ex
        r[nm] = float(np.median(dfe.stats(R2.run_cfg(cfg, m0, **kw), T)[0]))
    kw2 = dict(kw); kw2['cost'] = 2 * kw.get('cost', dfe.DEF['cost'])
    r['cost2x'] = float(np.median(dfe.stats(R2.run_cfg(cfg, mp, **kw2), T)[0]))
    return r

def run(vname):
    t0 = time.time(); C = CT.all_configs(); mk = CT.markets(vname); n = CT.VARIANTS[vname][0]
    rows = {i: CT.run_cfg_all(c, vname, mk) for i, c in C.items()}
    mp = mk['dev250_path']; W = CT.W
    exs = CT.ex_src('dev250_path', n); exp = float(np.mean(mp['rb'][:, W:] - mp['rf'][:, W:]))
    res = dict(variant=vname, bond_halfyears=n, engine_kw=CT.VARIANTS[vname][1], N=len(rows), ex_src=exs, ex_path=exp, tiers={}, picks={})
    for tn, bud in TIERS:
        ins = [i for i in rows if rows[i]['wd'] >= bud]
        ub = best_of(ins, rows); d1 = best_of([i for i in ins if C[i].get('fam') != 'df2'], rows)
        t = dict(budget=bud, n_in=len(ins), union_best=ub, df1_best=d1)
        if ub:
            t['union_best_row'] = rows[ub]; t['df1_best_row'] = rows[d1] if d1 else None
            t['adopted_src'] = t['adopted_path'] = ub
            if C[ub].get('fam') == 'df2' and d1:
                g2 = gate_vals(C[ub], vname, mk, exs, exp); g1 = gate_vals(C[d1], vname, mk, exs, exp)
                t['gate'] = dict(df2=g2, df1=g1)
                if not (g2['bondx0_src'] > g1['bondx0_src'] and g2['cost2x'] > g1['cost2x']): t['adopted_src'] = d1
                if not (g2['bondx0_path'] > g1['bondx0_path'] and g2['cost2x'] > g1['cost2x']): t['adopted_path'] = d1
            top = sorted(ins, key=lambda i: -rows[i]['dev250_path']['cagr'])[:5]
            t['top5'] = [(i, round(rows[i]['dev250_path']['cagr'], 5), round(rows[i]['wd'], 5)) for i in top]
        res['tiers'][tn] = t
    for k, i in PICKS.items(): res['picks'][k] = dict(id=i, **rows[i])
    res['compact'] = {i: [round(r['dev250_path']['cagr'], 6), round(r['wd'], 6), round(r['real_ndx_86_14']['cagr'], 6),
                          round(r['dev250_path']['mdd_p10'], 6), round(r['real_ndx_86_14']['mdd'], 6), round(r['real_spx_29_54']['mdd'], 6)] for i, r in rows.items()}
    json.dump(res, open(OUT + 'resel_%s.json' % vname, 'w'))
    print('== %s  %.0fs  ex_src %.3e ex_path %.3e' % (vname, time.time() - t0, exs, exp), flush=True)
    for tn, t in res['tiers'].items():
        print('  %s n_in %d union %s df1 %s adopt_src %s adopt_path %s gate %s' % (tn, t['n_in'], t['union_best'], t['df1_best'], t.get('adopted_src'), t.get('adopted_path'),
              {k: {kk: round(vv, 5) for kk, vv in v.items()} for k, v in t.get('gate', {}).items()}), flush=True)
    for k, p in res['picks'].items():
        print('  pick %-12s path %.5f mddp10 %.5f ndx %.5f/%.5f spx29 %.5f WD %.5f' % (k, p['dev250_path']['cagr'], p['dev250_path']['mdd_p10'], p['real_ndx_86_14']['cagr'],
              p['real_ndx_86_14']['mdd'], p['real_spx_29_54']['mdd'], p['wd']), flush=True)

if __name__ == '__main__':
    for v in sys.argv[1:]: run(v)
