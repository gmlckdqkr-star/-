"""Re-selection under the stresses (diagnostic, NOT the pre-registered rule): which config would each tier pick if the WD check
had included (a) one synthetic -20%/-25% gap per dev250 path (NON-ACTUAL, seed 23) or (b) execution delay 3/4/5 on all three bases?
Union = DF1 483 + DF2 640 configs (DF2 adoption gates NOT re-run; DF1-only best also reported). <=2014 only."""
import sys, json, time, numpy as np
sys.path.insert(0, '/tmp/chk_tails'); sys.path.insert(0, '/mnt/project-files/research/df1/code')
import tails as TL
import dfctx as DC, dfe, run_df2 as R2
G = TL.G; W = dfe.WARM; OUTD = TL.OUTD
TIERS = (('T25', -0.25), ('T30', -0.30), ('T40', -0.40))

def select(rows, adopted):
    """rows: id -> dict(path, p10, ndx_cagr, ndx_mdd, spx_mdd)."""
    wd = lambda r: min(r['p10'], r['ndx_mdd'], r['spx_mdd']); out = {}
    for tn, bud in TIERS:
        t = dict(budget=bud)
        for fam in ('union', 'df1'):
            ins = [i for i, r in rows.items() if wd(r) >= bud and (fam == 'union' or not i.startswith('DF2'))]
            t['n_in_' + fam] = len(ins)
            if not ins: continue
            best = max(ins, key=lambda i: rows[i]['path']); tie = [i for i in ins if rows[best]['path'] - rows[i]['path'] < 0.0005]
            best = max(tie, key=lambda i: rows[i]['ndx_cagr'])
            t[fam + '_best'] = best; t[fam + '_best_row'] = dict(rows[best], WD=wd(rows[best]))
        a = adopted[tn]; t['adopted'] = a; t['adopted_row'] = dict(rows[a], WD=wd(rows[a])); t['adopted_in'] = bool(wd(rows[a]) >= bud)
        out[tn] = t
        print('  %s adopted %s WD %.4f %s | union best %s path %.4f WD %.4f | df1 best %s path %.4f WD %.4f' % (
            tn, a, wd(rows[a]), 'IN' if t['adopted_in'] else 'OUT', t.get('union_best'), t.get('union_best_row', {}).get('path', np.nan),
            t.get('union_best_row', {}).get('WD', np.nan), t.get('df1_best'), t.get('df1_best_row', {}).get('path', np.nan), t.get('df1_best_row', {}).get('WD', np.nan)), flush=True)
    return out

ADOPT = {'T25': TL.PICKS['T25'], 'T30': TL.PICKS['T30'], 'T40': TL.PICKS['T40']}

def base_rows():
    return {i: dict(path=g['dev250_path']['cagr'], p10=g['dev250_path']['mdd_p10'], ndx_cagr=g['real_ndx_86_14']['cagr'],
                    ndx_mdd=g['real_ndx_86_14']['mdd'], spx_mdd=g['real_spx_29_54']['mdd']) for i, g in G.items()}

def resel_gap():
    m0 = DC.market('dev250_path'); c0 = m0['ctx']; X = TL.X_of('dev250_path'); P, T = c0.r.shape
    days = np.random.default_rng(23).integers(W + 1, T, size=P); res = {}
    print('== base (grid values)'); res['base'] = select(base_rows(), ADOPT)
    for gg in (-0.20, -0.25):
        t0 = time.time(); m = TL.gap_market(c0, X, days, gg); rows = base_rows()
        for i, g in G.items():
            cg, md = dfe.stats(R2.run_cfg(dict(g['cfg']), m), T)
            rows[i]['path'] = float(np.median(cg)); rows[i]['p10'] = float(np.percentile(md, 10))
        print('== gap %.2f seed 23 (%.0fs)' % (gg, time.time() - t0)); res['gap%d_s23' % int(-gg * 100)] = select(rows, ADOPT)
        del m
    json.dump(res, open(OUTD + '/stage_resel_gap.json', 'w'), indent=1)

def resel_delay(ds):
    res = {}
    for d in ds:
        t0 = time.time(); rows = {}
        for bn in TL.SEL:
            m = DC.market(bn); T = m['r'].shape[1]
            for i, g in G.items():
                cg, md = dfe.stats(R2.run_cfg(dict(g['cfg']), m, delay=d), T); r = rows.setdefault(i, {})
                if bn == 'dev250_path': r['path'] = float(np.median(cg)); r['p10'] = float(np.percentile(md, 10))
                elif bn == 'real_ndx_86_14': r['ndx_cagr'] = float(cg[0]); r['ndx_mdd'] = float(md[0])
                else: r['spx_mdd'] = float(md[0])
        print('== delay %d (%.0fs)' % (d, time.time() - t0)); res['delay%d' % d] = select(rows, ADOPT)
    try: old = json.load(open(OUTD + '/stage_resel_delay.json'))
    except Exception: old = {}
    old.update(res); json.dump(old, open(OUTD + '/stage_resel_delay.json', 'w'), indent=1)

if __name__ == '__main__':
    st = sys.argv[1]
    if st == 'gap': resel_gap()
    if st == 'delay': resel_delay([int(x) for x in sys.argv[2:]])
