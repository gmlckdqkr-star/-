"""Final checks asked by the completeness critic (2026-11-18). <=2014 data only; synthetic bonds and bootstrap paths are NON-ACTUAL.
A  decor : stock-bond decorrelation bootstrap (bond leg from an independent block draw; removes the 1986-2014 crisis hedge). 3 bond seeds.
B  adv10 : combined adverse stack with the 10y bond {W0 100M (D .025), cost .45%/side, bond ER .25%, delay 3}; B2 = same + bond excess 0.
C  bxm1  : bond excess -1%/yr (shift = source-period mean + 1%/yr) on all 3 selection bases.
D  bx0   : base engine, bond excess 0 (source-period shift) rows for the adopted picks.
Every block: full re-selection of DF1 u DF2 (1,123 configs) with the tie rule and the gate as fixed by gate_fix.py.
Usage: fc.py A|B|C|D  -> checks/final/fc_<block>.json"""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/checks/costtax')
import ctlib as CT, dfctx as DC, dfe, run_df2 as R2, ov, mkt, jp, iv
OUT = '/mnt/project-files/research/df1/checks/final/'
W = dfe.WARM; SELM = CT.SELM
TIERS = (('A20', -0.20), ('T25', -0.25), ('T30', -0.30), ('T40', -0.40))
PICKS = {'T25': 'v1|s0.1|L1.0|K1|RB', 'T30': 'v1|s0.2|L1.0|K1|RB', 'T40': 'v1|s0.3|L1.0|K2|RB',
         'T30_fallback': 'v1|s0.15|L1.0|K1|RB', 'T25_RT': 'v1|s0.1|L1.0|K1|RT', 'T40_DF2old': 'DF2|M2|b1|v1|s0.3|L1.5|K2|RB'}
C = CT.all_configs()
G = json.load(open('/mnt/project-files/research/df1/results/grid.json'))['configs']; G.update(json.load(open('/mnt/project-files/research/df1/results/grid_df2.json'))['configs'])
EXS = {b: CT.ex_src(b, 20) for b in SELM}           # pre-registered 'bond excess 0' shift (source-period mean), per basis

def pm(o, T): cg, md = dfe.stats(o, T); return dict(cagr=float(np.median(cg)), mdd_p10=float(np.percentile(md, 10)), cagr_p10=float(np.percentile(cg, 10)))
def sm(o, T): cg, md = dfe.stats(o, T); return dict(cagr=float(cg[0]), mdd=float(md[0]))
def shift(m, ex): m2 = dict(m); m2['rb'] = m['rb'] - ex; m2['rb'][:, 0] = 0.0; return m2

def best_of(ids, rows):
    if not ids: return None
    b = max(ids, key=lambda i: rows[i]['dev250_path']['cagr'])
    tie = [i for i in ids if rows[b]['dev250_path']['cagr'] - rows[i]['dev250_path']['cagr'] < 0.0005]
    return max(tie, key=lambda i: rows[i]['real_ndx_86_14']['cagr'])

def select(rows, gate):
    """rows: id -> {dev250_path:{cagr,mdd_p10}, real_ndx_86_14:{cagr,mdd}, real_spx_29_54:{mdd}, wd}; gate(id) -> (bondx0, cost2x)."""
    res = {}
    for tn, bud in TIERS:
        ins = [i for i in rows if rows[i]['wd'] >= bud]
        ub = best_of(ins, rows); d1 = best_of([i for i in ins if C[i].get('fam') != 'df2'], rows)
        t = dict(n_in=len(ins), union_best=ub, df1_best=d1, adopted=ub)
        if ub and C[ub].get('fam') == 'df2' and d1:
            g2, g1 = gate(ub), gate(d1); t['gate'] = dict(df2=g2, df1=g1)
            if not (g2[0] > g1[0] and g2[1] > g1[1]): t['adopted'] = d1
        if t['adopted']:
            a = t['adopted']; t['adopted_path'] = rows[a]['dev250_path']['cagr']; t['adopted_wd'] = rows[a]['wd']; t['adopted_ndx'] = rows[a]['real_ndx_86_14']['cagr']
        res[tn] = t
    return res

def pick_rows(rows): return {k: dict(id=i, path=rows[i]['dev250_path']['cagr'], path_p10=rows[i]['dev250_path'].get('cagr_p10'), mddp10=rows[i]['dev250_path']['mdd_p10'],
                                    ndx=rows[i]['real_ndx_86_14']['cagr'], ndx_mdd=rows[i]['real_ndx_86_14']['mdd'], spx29_mdd=rows[i]['real_spx_29_54']['mdd'], wd=rows[i]['wd']) for k, i in PICKS.items()}

def report(tag, sel, pr):
    print('==', tag, flush=True)
    for tn, t in sel.items():
        print('  %s n_in %4d adopted %-34s path %s WD %s | union %s gate %s' % (tn, t['n_in'], t['adopted'], '%.4f' % t['adopted_path'] if t.get('adopted_path') else '-',
              '%.4f' % t['adopted_wd'] if t.get('adopted_wd') else '-', t['union_best'], {k: [round(x, 5) for x in v] for k, v in t.get('gate', {}).items()}), flush=True)
    for k, p in pr.items():
        print('  pick %-13s path %.4f mddp10 %.4f ndx %.4f/%.4f spx29 %.4f WD %.4f' % (k, p['path'], p['mddp10'], p['ndx'], p['ndx_mdd'], p['spx29_mdd'], p['wd']), flush=True)

def block_A():
    mp = DC.market('dev250_path'); T = mp['r'].shape[1]; c = mp['ctx']
    a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX')
    rb_src = mkt.bond10(X).values; y10 = X['y10'].astype(float).values; cp_src = np.r_[np.nan, y10[:-1]] / 100.0 / 252.0
    assert np.allclose(np.nan_to_num(rb_src[c.ii]), np.nan_to_num(c.rb), atol=1e-14)    # the stored bond leg is bond10(X)[ii]
    out = dict(note='bond leg (rb, cpn, bondup) from an independent block-250 draw; stock leg, rf, flags, vol from seed 7 (dev250_path)', seeds={})
    for bs in (1007, 2007, 3007):
        t0 = time.time(); ib = ov.boot_idx(len(X), P=P, years=30, block=blk, seed=bs, lo=1); assert ib.shape == c.ii.shape
        rb = np.nan_to_num(rb_src[ib], nan=0.0); rb[:, 0] = 0.0; cp = np.nan_to_num(cp_src[ib], nan=0.0); cp[:, 0] = 0.0
        bl = np.cumprod(1 + rb, axis=1); s = DC._sma(bl, 200)
        m = dict(mp); m['rb'] = rb; m['cpn'] = cp; m['bondup'] = np.where(np.isnan(s), False, bl > np.nan_to_num(s, nan=np.inf))
        corr = float(np.mean([np.corrcoef(mp['r'][p, W:], rb[p, W:])[0, 1] for p in range(0, P, 25)]))
        corr0 = float(np.mean([np.corrcoef(mp['r'][p, W:], mp['rb'][p, W:])[0, 1] for p in range(0, P, 25)]))
        rows = {}
        for i, cfg in C.items():
            r = pm(R2.run_cfg(cfg, m), T)
            rows[i] = {'dev250_path': r, 'real_ndx_86_14': G[i]['real_ndx_86_14'], 'real_spx_29_54': G[i]['real_spx_29_54']}
            rows[i]['wd'] = min(r['mdd_p10'], G[i]['real_ndx_86_14']['mdd'], G[i]['real_spx_29_54']['mdd'])
        m0 = shift(m, EXS['dev250_path'])
        gate = lambda i: (float(np.median(dfe.stats(R2.run_cfg(C[i], m0), T)[0])), float(np.median(dfe.stats(R2.run_cfg(C[i], m, cost=0.006), T)[0])))
        sel = select(rows, gate); pr = pick_rows(rows)
        bx0 = {k: float(np.median(dfe.stats(R2.run_cfg(C[i], m0), T)[0])) for k, i in PICKS.items()}
        out['seeds'][bs] = dict(corr_stock_bond=corr, corr_stock_bond_base=corr0, tiers=sel, picks=pr, picks_bondx0=bx0)
        report('A decor bond seed %d (corr %.3f vs base %.3f) %.0fs' % (bs, corr, corr0, time.time() - t0), sel, pr)
        print('  bondx0 picks', {k: round(v, 4) for k, v in bx0.items()}, flush=True)
    json.dump(out, open(OUT + 'fc_A.json', 'w'), indent=1)

def run_world(tag, kw, shift_ex=None):
    """all configs on the 3 selection bases under engine kw, optionally with rb shifted by shift_ex[basis]/day; gate a = bond excess 0 world
    (if the world is already shifted to <= 0 excess, gate a = the world itself)."""
    t0 = time.time(); mk = {}
    for b in SELM:
        m = DC.market(b); mk[b] = shift(m, shift_ex[b]) if shift_ex else m
    rows = {}
    for i, cfg in C.items():
        row = {}
        for b in SELM:
            m = mk[b]; T = m['r'].shape[1]; o = R2.run_cfg(cfg, m, **kw)
            row[b] = pm(o, T) if b == 'dev250_path' else sm(o, T)
        row['wd'] = min(row['dev250_path']['mdd_p10'], row['real_ndx_86_14']['mdd'], row['real_spx_29_54']['mdd']); rows[i] = row
    mp = mk['dev250_path']; T = mp['r'].shape[1]; m0 = mp if shift_ex else shift(mp, EXS['dev250_path'])
    kw2 = dict(kw); kw2['cost'] = 2 * kw.get('cost', dfe.DEF['cost'])
    gate = lambda i: (float(np.median(dfe.stats(R2.run_cfg(C[i], m0, **kw), T)[0])), float(np.median(dfe.stats(R2.run_cfg(C[i], mp, **kw2), T)[0])))
    sel = select(rows, gate); pr = pick_rows(rows)
    report('%s %.0fs' % (tag, time.time() - t0), sel, pr)
    return dict(engine_kw=kw, shift_per_day=shift_ex, tiers=sel, picks=pr,
                compact={i: [round(r['dev250_path']['cagr'], 6), round(r['wd'], 6), round(r['real_ndx_86_14']['cagr'], 6)] for i, r in rows.items()})

ADV = dict(D=0.025, cost=0.0045, erb=0.0025, delay=3)
if __name__ == '__main__':
    blk = sys.argv[1]
    if blk == 'A': block_A()
    if blk == 'B':
        res = dict(adv10=run_world('B adv10', ADV), adv10_bx0=run_world('B2 adv10 + bond excess 0', ADV, EXS))
        json.dump(res, open(OUT + 'fc_B.json', 'w'))
    if blk == 'C':
        sh = {b: EXS[b] + 0.01 / 252 for b in SELM}
        json.dump(dict(bxm1=run_world('C bond excess -1%/yr', {}, sh)), open(OUT + 'fc_C.json', 'w'))
    if blk == 'D':
        out = {}
        for k, i in PICKS.items():
            out[k] = dict(id=i)
            for b in SELM + ('real_spx_55_85',):
                m = DC.market(b); T = m['r'].shape[1]; ex = EXS[b] if b in EXS else CT.ex_src('real_ndx_86_14', 20)
                if b == 'real_spx_55_85': continue
                o = R2.run_cfg(C[i], shift(m, ex)); out[k][b] = pm(o, T) if b == 'dev250_path' else sm(o, T)
            print('D bondx0', k, i, {b: round(v['cagr'], 4) for b, v in out[k].items() if b != 'id'}, flush=True)
        out['ex_src_per_day'] = EXS
        json.dump(out, open(OUT + 'fc_D.json', 'w'), indent=1)
