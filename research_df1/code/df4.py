"""DF4 (PRECOMMIT_DF4.md sha 5c5565ee): screen all 1,367 DF1-3 configs for "beat QQQ hold AND shallower drawdown"
on real / simulated / extreme bases, every gate on bond-neutral values. <=2014 data only. Writes results/df4.json."""
import os, sys, json, time, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2
RES = '/mnt/project-files/research/df1/results/'
EX = 1.3988294390226633e-4; MG = 0.05
t0 = time.time()
def log(*a): print('[%5.0fs]' % (time.time() - t0), *a, flush=True)

G = json.load(open(RES + 'grid.json')); REF = G['refs']; OLD = dict(G['configs']); OLD.update(json.load(open(RES + 'grid_df2.json'))['configs'])
D3 = json.load(open(RES + 'df3.json')); C3 = D3['configs']; assert len(C3) == 1367
def cfg_of(i):
    if i in OLD: return OLD[i]['cfg']
    _, fam, Mm, k, s, L, kn, ro = i.split('|')
    return dict(id=i, fam='df3', M=Mm, k=k, sig=None if s == 'snone' else float(s[1:]), Lmax=float(L[1:]), knee=kn, roff=ro)
def run_any(cfg, m, **extra):
    if cfg.get('fam') == 'df3':
        L = DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax']); kw = dict(RG.KNEES[cfg['knee']]); kw.update(vmode=0 if cfg['M'] == 'M0' else 2); kw.update(extra)
        return dfe.run(m, L, roff=RG.ROFF[cfg['roff']], **kw)[0]
    if cfg.get('fam') == 'df2': return R2.run_cfg(cfg, m, **extra)
    return RG.run_cfg(cfg, m, **extra)
uses_bond = lambda cfg: cfg.get('fam') == 'static' or cfg.get('roff') in ('RB', 'RBT')

# ---- single-path bases: standard + bond-neutral (own evaluation-window mean excess if positive; NDX 86-14 uses EX)
SB = ('real_ndx_86_14', 'real_spx_29_54', 'real_spx_55_85', 'real_spx_70_85', 'UK', 'CA', 'AU', 'DE', 'FR', 'JP')
W = dfe.WARM; MK = {}; EXB = {}
for bn in SB:
    m = DC.market(bn); ex = EX if bn == 'real_ndx_86_14' else float(np.mean(m['rb'][:, W:] - m['rf'][:, W:]))
    m0 = dict(m); m0['rb'] = m['rb'] - max(ex, 0.0); MK[bn] = (m, m0); EXB[bn] = ex
    log(bn, str(m['X_index'][W].date()), str(m['X_index'][-1].date()), 'bond excess %.2f%%/yr' % (ex * 252 * 100), 'QQQ', REF[bn]['hold1x_QQQ'])
IDS = list(C3.keys()); OUT = {}
for n_, i in enumerate(IDS):
    cfg = cfg_of(i); r = dict(P=C3[i]['P'], P0=C3[i]['P0'], X=C3[i]['X'], X0=C3[i]['X0'])
    for bn in SB:
        m, m0 = MK[bn]; T = m['r'].shape[1]
        cg, md = dfe.stats(run_any(cfg, m), T); s = dict(cagr=float(cg[0]), mdd=float(md[0]))
        if uses_bond(cfg): cg, md = dfe.stats(run_any(cfg, m0), T); s0 = dict(cagr=float(cg[0]), mdd=float(md[0]))
        else: s0 = dict(s)
        r[bn] = s; r[bn + '_bx0'] = s0
    # parity with stored grids (standard values)
    if i in OLD:
        for bn in SB: assert abs(r[bn]['cagr'] - OLD[i][bn]['cagr']) < 1e-9, (i, bn)
    else:
        assert abs(r['real_ndx_86_14']['cagr'] - C3[i]['N']['cagr']) < 1e-9 and abs(r['real_spx_29_54']['cagr'] - C3[i]['S']['cagr']) < 1e-9, i
    OUT[i] = r
    if n_ % 200 == 0: log('screened', n_)
log('single-path bases done; parity with grid.json / grid_df2.json / df3.json exact')

# ---- gates (PRECOMMIT s2), all on bond-neutral values
Q = lambda bn: REF[bn]['hold1x_QQQ']; QP = REF['dev250_path']['hold1x_QQQ']; FOR = ('UK', 'CA', 'AU', 'DE', 'FR', 'JP')
def gates(r):
    g = {}
    a = r['real_ndx_86_14_bx0']; g['R1'] = a['cagr'] > Q('real_ndx_86_14')['cagr'] and a['mdd'] > Q('real_ndx_86_14')['mdd'] + MG
    a = r['real_spx_55_85_bx0']; g['R2'] = a['cagr'] > Q('real_spx_55_85')['cagr'] and a['mdd'] > Q('real_spx_55_85')['mdd'] + MG
    nf = sum(r[f + '_bx0']['cagr'] > Q(f)['cagr'] and r[f + '_bx0']['mdd'] > Q(f)['mdd'] for f in FOR); g['R3'] = nf >= 4; g['R3n'] = nf
    p = r['P0']; g['V1'] = p['cagr'] > QP['cagr']; g['V2'] = p['mdd'] > QP['mdd'] + MG
    g['E1'] = p['p10'] > QP['p10']; g['E2'] = p['mdd_p10'] > QP['mdd_p10'] + MG
    a = r['real_spx_29_54_bx0']; g['E3'] = a['cagr'] > Q('real_spx_29_54')['cagr'] and a['mdd'] > Q('real_spx_29_54')['mdd'] + MG
    return g
GK = ('R1', 'R2', 'R3', 'V1', 'V2', 'E1', 'E2', 'E3')
for i in IDS: OUT[i]['g'] = gates(OUT[i]); OUT[i]['nfail'] = sum(not OUT[i]['g'][k] for k in GK)
pre = [i for i in IDS if OUT[i]['nfail'] == 0]
log('pass R1-R3,V1-V2,E1-E3:', len(pre), 'single-gate pass counts', {k: sum(OUT[i]['g'][k] for i in IDS) for k in GK})

# ---- E4 / E5 stress on the path, bond-neutral (only for configs passing every other gate)
mp = DC.market('dev250_path'); mp0 = dict(mp); mp0['rb'] = mp['rb'] - EX; TP = mp['r'].shape[1]
def pst(cfg, m, **kw):
    cg, md = dfe.stats(run_any(cfg, m, **kw), TP); return dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)),
                                                             mdd=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)))
chk = pst(cfg_of(IDS[0]), mp0 if uses_bond(cfg_of(IDS[0])) else mp); assert abs(chk['cagr'] - OUT[IDS[0]]['P0']['cagr']) < 1e-9
def stress(i):
    cfg = cfg_of(i); m = mp0 if uses_bond(cfg) else mp
    OUT[i]['c2'] = pst(cfg, m, cost=0.006); OUT[i]['d4'] = pst(cfg, m, delay=4)
    g = OUT[i]['g']
    g['E4'] = OUT[i]['c2']['cagr'] > QP['cagr'] and OUT[i]['c2']['mdd_p10'] > QP['mdd_p10'] + MG
    g['E5'] = OUT[i]['d4']['cagr'] > QP['cagr'] and OUT[i]['d4']['mdd_p10'] > QP['mdd_p10'] + MG
for n_, i in enumerate(pre):
    stress(i)
    if n_ % 20 == 0: log('stress', n_, '/', len(pre))
PASS = [i for i in pre if OUT[i]['g']['E4'] and OUT[i]['g']['E5']]
log('pass ALL:', len(PASS))

# ---- selection (PRECOMMIT s3)
def worst_dd(i): r = OUT[i]; return min(r['real_ndx_86_14_bx0']['mdd'], r['P0']['mdd_p10'], r['real_spx_29_54_bx0']['mdd'])
SEL = {}
if PASS:
    top = max(OUT[i]['P0']['cagr'] for i in PASS)
    tied = [i for i in PASS if OUT[i]['P0']['cagr'] >= top - 0.0005]
    SEL['answer'] = max(tied, key=lambda i: OUT[i]['P0']['mdd_p10'])
    alt = [i for i in PASS if OUT[i]['P0']['cagr'] >= QP['cagr'] + 0.01]
    SEL['alt'] = max(alt, key=worst_dd) if alt else None
else:
    near = sorted(IDS, key=lambda i: (OUT[i]['nfail'], -OUT[i]['P0']['cagr']))[:10]
    SEL['near_miss'] = [(i, [k for k in GK if not OUT[i]['g'][k]]) for i in near]
log('SEL', SEL)

# ---- neighbours of the picks (one sigma step / one Lmax step within the same family), report only
SIG = (None, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50); LM = (1.0, 1.5, 2.0, 3.0)
def neigh(i):
    c = cfg_of(i); out = []
    if c.get('fam') == 'static': return out
    def nid(sig, L):
        parts = i.split('|'); j = [n for n, p in enumerate(parts) if p.startswith('s') and (p == 'snone' or p[1:2].isdigit())][0]
        parts[j] = 'snone' if sig is None else 's%s' % sig; parts[j + 1] = 'L%s' % L; return '|'.join(parts)
    si = SIG.index(c['sig']); li = LM.index(c['Lmax'])
    for ds, dl in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        if 0 <= si + ds < len(SIG) and 0 <= li + dl < len(LM):
            k = nid(SIG[si + ds], LM[li + dl])
            if k in OUT: out.append(k)
    return out
NB = {}
for key in ('answer', 'alt'):
    i = SEL.get(key)
    if not i: continue
    rows = []
    for k in neigh(i):
        if OUT[k]['nfail'] == 0 and 'E4' not in OUT[k]['g']: stress(k)
        ok = OUT[k]['nfail'] == 0 and OUT[k]['g'].get('E4', False) and OUT[k]['g'].get('E5', False)
        rows.append(dict(id=k, pass_all=bool(ok), P0=OUT[k]['P0']['cagr'], fails=[g for g in GK if not OUT[k]['g'][g]]))
    NB[key] = rows
log('neighbours', json.dumps(NB))

res = dict(precommit_sha='5c5565eefccbb3b26a9ed0be166c49a1566f54db3234f3fe1daae8dbaba1088f', N=len(IDS), margin=MG, bond_excess=EXB,
           refs={bn: REF[bn] for bn in ('dev250_path',) + SB}, n_pre=len(pre), n_pass=len(PASS), pass_ids=PASS, sel=SEL, neighbours=NB,
           gate_counts={k: int(sum(OUT[i]['g'][k] for i in IDS)) for k in GK}, configs=OUT)
json.dump(res, open(RES + 'df4.json', 'w')); log('saved df4.json')
for key in ('answer', 'alt'):
    i = SEL.get(key)
    if not i: continue
    r = OUT[i]; log(key, i, 'P %.4f P0 %.4f p10 %.4f mddp10 %.4f | NDX0 %.4f/%.4f | SPX55 %.4f/%.4f | SPX29 %.4f/%.4f | R3 %d | c2 %.4f/%.4f d4 %.4f/%.4f | X %.4f'
                    % (r['P']['cagr'], r['P0']['cagr'], r['P0']['p10'], r['P0']['mdd_p10'], r['real_ndx_86_14_bx0']['cagr'], r['real_ndx_86_14_bx0']['mdd'],
                       r['real_spx_55_85_bx0']['cagr'], r['real_spx_55_85_bx0']['mdd'], r['real_spx_29_54_bx0']['cagr'], r['real_spx_29_54_bx0']['mdd'],
                       r['g']['R3n'], r['c2']['cagr'], r['c2']['mdd_p10'], r['d4']['cagr'], r['d4']['mdd_p10'], r['X0']['cagr']))
