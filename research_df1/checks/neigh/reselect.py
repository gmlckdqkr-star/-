"""neigh part 2: apply each off-grid perturbation to the WHOLE pre-registered set (483 DF1 + 640 DF2) and re-run the union
selection + DF2 gates (run_df2.py rules; gate bond-excess shift both as originally run (path-day mean) and as audit-fixed
(source-period mean, gate_fix.py)). Question: would the adopted pick flip, or a tier number change, under that alternative?
Usage: python reselect.py name1 name2 ...  -> resel/<name>.json.  <=2014 data only; dev250_path is NON-ACTUAL bootstrap."""
import sys, os, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/checks/neigh')
import neighlib as NL
DC, dfe, RG, R2 = NL.DC, NL.dfe, NL.RG, NL.R2
OD = '/mnt/project-files/research/df1/checks/neigh/resel/'; os.makedirs(OD, exist_ok=True)
FX = json.load(open(NL.RES + 'select_df2_fixed.json')); EX = dict(fixed=FX['ex_src_per_day'], orig=FX['ex_path_per_day'])
TIERS = (('A', -0.20), ('A_fallback_25', -0.25), ('B', -0.30), ('C', -0.40))
CFGS = RG.configs() + R2.configs()
DF1 = {c['id'] for c in RG.configs()}

VARS = {'base': ({}, {}, None)}
for x in (0.8, 1.2): VARS['knee_x%.1f' % x] = ({}, dict(ks=x), None)
for f in (0.0, 0.5): VARS['kfloor_%.2f' % f] = ({}, dict(kfl=f), None)
for n in (10, 40, 60): VARS['volwin_%d' % n] = (dict(vwin=n), {}, None)
for n in (150, 250): VARS['sma_%d' % n] = (dict(sl=n), {}, None)
for b in (0.01, 0.03): VARS['band_%.2f' % b] = (dict(bd=b), {}, None)
for v in (0.35, 0.45): VARS['vcap_%.2f' % v] = (dict(vc=v), {}, None)
for d in (-0.025, 0.025): VARS['sigshift_%+.3f' % d] = ({}, {}, ('sig', d))
for s in (0.05, 0.15): VARS['steplo_%.2f' % s] = ({}, {}, ('steplo', s))

def cfg_kw(cfg, ek, special):
    cfg = dict(cfg); k = dict(ek)
    if special and special[0] == 'sig' and cfg.get('sig') is not None: cfg['sig'] = round(cfg['sig'] + special[1], 4)
    if special and special[0] == 'steplo' and cfg['fam'] in ('grid', 'df2') and (cfg['fam'] == 'grid' or cfg['band'] == 'b1'):
        k['step_lo'] = special[1]
    return cfg, NL.eng_kw(cfg, **k)

def run_variant(name):
    t0 = time.time(); e, ek, special = VARS[name]
    M3 = {bn: NL.env(DC.market(bn), **e) for bn in DC.SEL}
    U = {}
    for cfg0 in CFGS:
        cfg, kw = cfg_kw(cfg0, ek, special); d = NL.run3(cfg, M3, kw); U[cfg0['id']] = NL.flat(d)
    mp = M3['dev250_path']; T = mp['r'].shape[1]
    def gate(i, exk):
        cfg, kw = cfg_kw(next(c for c in CFGS if c['id'] == i), ek, special)
        m0 = dict(mp); m0['rb'] = mp['rb'] - EX[exk]
        a = float(np.median(dfe.stats(R2.run_cfg(cfg, m0, **kw), T)[0]))
        kw2 = dict(kw); kw2['cost'] = 0.006
        b = float(np.median(dfe.stats(R2.run_cfg(cfg, mp, **kw2), T)[0]))
        return a, b
    def best(ids):
        b = max(ids, key=lambda i: U[i]['path'])
        tie = [i for i in ids if U[b]['path'] - U[i]['path'] < 0.0005]
        return max(tie, key=lambda i: U[i]['ndx'])
    res = dict(name=name, env=e, eng=ek, special=special, tiers={})
    for tn, bud in TIERS:
        ins = [i for i in U if U[i]['wd'] >= bud]; t = dict(budget=bud, n_in=len(ins))
        if ins:
            ub = best(ins); d1in = [i for i in ins if i in DF1]; d1 = best(d1in) if d1in else None
            t.update(union_best=ub, df1_best=d1)
            for exk in ('fixed', 'orig'):
                ad = ub
                if ub not in DF1 and d1:
                    g2, g1 = gate(ub, exk), gate(d1, exk); t['gate_' + exk] = dict(df2_bondx0=g2[0], df1_bondx0=g1[0], df2_cost2x=g2[1], df1_cost2x=g1[1])
                    if not (g2[0] > g1[0] and g2[1] > g1[1]): ad = d1
                t['adopted_' + exk] = ad; t['adopted_' + exk + '_row'] = U[ad]
            top = sorted(ins, key=lambda i: -U[i]['path'])[:5]; t['top5'] = [(i, round(U[i]['path'], 4), round(U[i]['wd'], 4)) for i in top]
        res['tiers'][tn] = t
    res['picks_rows'] = {p: U[cid] for p, cid in NL.PICKS.items()}
    res['secs'] = time.time() - t0
    json.dump(res, open(OD + name + '.json', 'w'), indent=1)
    print('%-14s %.0fs' % (name, res['secs']), ' | '.join('%s n%d %s/%s' % (tn, t['n_in'], t.get('adopted_fixed'), t.get('adopted_orig'))
                                                         for tn, t in res['tiers'].items()), flush=True)

if __name__ == '__main__':
    for nm in sys.argv[1:]: run_variant(nm)
