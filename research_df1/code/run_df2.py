"""DF2 grid (PRECOMMIT_DF2.md): 640 new configs on selection + validation bases; then union selection with the two gates.
Writes results/grid_df2.json and results/select_df2.json. <=2014 only."""
import sys, json, itertools, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG

BANDS = {'b1': (0.1, 0.25), 'b2': (0.2, 0.5), 'b3': (0.3, 0.5)}
def configs():
    C = []
    for M, bd, k, s, L, kn, ro in itertools.product(('M0', 'M2'), BANDS, RG.KS, (0.10, 0.15, 0.20, 0.30), RG.LMAX, ('K1', 'K2'), ('RB', 'RBT')):
        if M == 'M0' and bd == 'b1': continue
        C.append(dict(id='DF2|%s|%s|%s|s%s|L%s|%s|%s' % (M, bd, k, s, L, kn, ro), fam='df2', M=M, band=bd, k=k, sig=s, Lmax=L, knee=kn, roff=ro))
    return C

def run_cfg(cfg, m, **extra):
    if cfg.get('fam') != 'df2': return RG.run_cfg(cfg, m, **extra)
    L = DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax']); kw = dict(RG.KNEES[cfg['knee']])
    kw.update(step_lo=BANDS[cfg['band']][0], step_hi=BANDS[cfg['band']][1], vmode=0 if cfg['M'] == 'M0' else 2); kw.update(extra)
    o, _ = dfe.run(m, L, roff=RG.ROFF[cfg['roff']], **kw); return o

if __name__ == '__main__':
    t0 = time.time(); C = configs(); out = dict(N_new=len(C), configs={})
    for bn in RG.BASES:
        m = DC.market(bn); T = m['r'].shape[1]; path = m['r'].shape[0] > 1
        for cfg in C: out['configs'].setdefault(cfg['id'], dict(cfg=cfg))[bn] = RG.summ(run_cfg(cfg, m), T, path)
        print('%-16s done %.0fs' % (bn, time.time() - t0), flush=True)
    json.dump(out, open('/mnt/project-files/research/df1/results/grid_df2.json', 'w'))
    # ---- union selection + gates
    G1 = json.load(open('/mnt/project-files/research/df1/results/grid.json'))['configs']; U = dict(G1); U.update(out['configs'])
    S1 = json.load(open('/mnt/project-files/research/df1/results/select.json'))['tiers']
    wd = lambda r: min(r['dev250_path']['mdd_p10'], r['real_ndx_86_14']['mdd'], r['real_spx_29_54']['mdd'])
    VAL = DC.VAL; FOR = VAL[2:]
    mp = DC.market('dev250_path'); T = mp['r'].shape[1]; W = dfe.WARM
    ex = float(np.mean(mp['rb'][:, W:] - mp['rf'][:, W:])); m0 = dict(mp); m0['rb'] = mp['rb'] - ex
    def gate_vals(i):
        cfg = U[i]['cfg']
        a = float(np.median(dfe.stats(run_cfg(cfg, m0), T)[0])); b = float(np.median(dfe.stats(run_cfg(cfg, mp, cost=0.006), T)[0]))
        return a, b
    res = dict(N_total=len(U), ex_removed_path=ex, tiers={})
    for name, bud in (('A', -0.20), ('A_fallback_25', -0.25), ('B', -0.30), ('C', -0.40)):
        ins = [i for i, r in U.items() if wd(r) >= bud]; t = dict(budget=bud, n_in=len(ins))
        if ins:
            best = max(ins, key=lambda i: U[i]['dev250_path']['cagr'])
            tie = [i for i in ins if U[best]['dev250_path']['cagr'] - U[i]['dev250_path']['cagr'] < 0.0005]
            best = max(tie, key=lambda i: U[i]['real_ndx_86_14']['cagr']); t['union_best'] = best
            d1 = S1.get(name, {}).get('best') if name != 'A' else None
            t['df1_best'] = d1; adopt = best
            if U[best]['cfg'].get('fam') == 'df2' and d1:
                gb, g1 = gate_vals(best), gate_vals(d1)
                t['gate'] = dict(df2_bondx0=gb[0], df1_bondx0=g1[0], df2_cost2x=gb[1], df1_cost2x=g1[1])
                if not (gb[0] > g1[0] and gb[1] > g1[1]): adopt = d1
            t['adopted'] = adopt; r = U[adopt]; t['wd'] = wd(r); t['rows'] = {b: r[b] for b in RG.BASES}
            v = dict(V1=bool(r['real_spx_55_85']['mdd'] >= bud - 0.10 and r['real_spx_70_85']['mdd'] >= bud - 0.10))
            nf = sum(r[mm]['mdd'] >= bud - 0.10 for mm in FOR); v.update(V2=bool(nf >= 5), V2_count=int(nf))
            pct = [float(100.0 * np.mean(np.array([U[j][mm]['cagr'] for j in ins]) < r[mm]['cagr'] + 1e-12)) for mm in VAL]
            v.update(V3_pct=dict(zip(VAL, pct)), V3_median_pct=float(np.median(pct)), V3=bool(np.median(pct) >= 50))
            t['validation'] = v
            top = sorted(ins, key=lambda i: -U[i]['dev250_path']['cagr'])[:10]
            t['top10'] = [(i, round(U[i]['dev250_path']['cagr'], 4), round(wd(U[i]), 4)) for i in top]
            t['top10_median_path'] = float(np.median([U[i]['dev250_path']['cagr'] for i in top]))
        res['tiers'][name] = t
        print('==', name, bud, 'n_in', t['n_in'], 'union best', t.get('union_best'), 'adopted', t.get('adopted'), 'gate', t.get('gate'))
        if 'adopted' in t:
            R = t['rows']; print('   path %.4f mddp10 %.4f | realNDX %.4f mdd %.4f | SPX29 %.4f mdd %.4f | WD %.4f | V %s' % (
                R['dev250_path']['cagr'], R['dev250_path']['mdd_p10'], R['real_ndx_86_14']['cagr'], R['real_ndx_86_14']['mdd'],
                R['real_spx_29_54']['cagr'], R['real_spx_29_54']['mdd'], t['wd'], {k: v for k, v in t['validation'].items() if k != 'V3_pct'}))
            print('   top10 median %.4f' % t['top10_median_path'], t['top10'][:4])
    json.dump(res, open('/mnt/project-files/research/df1/results/select_df2.json', 'w'), indent=1)
