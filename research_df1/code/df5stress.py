"""DF5 robustness H1-H4 for G1-G5 passers, report-only rows, placebo and selection stability (PRECOMMIT_DF5.md sections 4-6)."""
import sys, json, time, itertools, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df5run as R, df5gate as GT, df5fam as F, df5data as DD, df5lib as L
WARM = 300
log = R.log

def cfg_index():
    CA = F.configs(R.ELIG); CB = R.bconfigs(); CV = R.vconfigs()
    idx = {c['id']: c for c in CA + CV}
    for c in CB: idx[c['id']] = c
    return idx

def runner(cfg, X, h=None, held=None, **over):
    if cfg['fam'] == 'B': return R.run_B(cfg['id'], X, h, **over)
    if cfg['fam'] == 'BV':
        if held is None or over.get('delay', 2) != 2 or over.get('cost', 0.003) != 0.003 or 'D' in over:
            held, _ = v1_held_kw(X, **over)
        return R.run_job(R.vjob(cfg, X, held), X, h, **over)
    return R.run_job(R.job(cfg, X), X, h, **over)

def v1_held_kw(X, **over):
    sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std, beng
    c = X.w['ctx']; B, bfn, bp, fs = std.s085(c); feat = std.bk.features(c); P, T = X.P, X.T; held = np.zeros((P, T)); cg = np.zeros(P)
    kw = dict(cspr=10.0, fstep=fs)
    if 'delay' in over: kw['delay'] = over['delay']
    if 'cost' in over: kw['cost'] = over['cost']
    if 'D' in over: kw['W0'] = 2.5e6 / over['D']
    dl = kw.get('delay', 2)
    for p in range(P):
        s, rec = beng.run_path(np.ascontiguousarray(c.r[p]), np.ascontiguousarray(c.rf[p]), np.ascontiguousarray(B[p], dtype=np.float64),
                               np.ascontiguousarray(feat[p]), bfn, np.asarray(bp, dtype=np.float64), **kw)
        cur = rec[:, 1]; hd = np.empty(T); hd[:WARM - 1] = 0.0; hd[WARM - 1] = cur[0]; hd[WARM:T - dl] = cur[dl:]; hd[T - dl:] = cur[-1]
        held[p] = np.maximum(hd, 0.0); cg[p] = s['cagr'][0]
    return held, cg

def assets_of(cfg):
    f = cfg['fam']
    if f in ('A1', 'A2'): return [cfg['roff']] if cfg['roff'] not in ('TBILL',) else []
    if f == 'A7': return ['B10'] if cfg['roff'] == 'B10' else []
    if f == 'A3': return list(cfg['dmix'])
    if f == 'A4':
        if cfg['kind'] == 'GEM': return ['SPX', 'B10']
        return [u for u in cfg['U'] if u != 'NDX']
    if f == 'A5': return [cfg['D']]
    if f == 'A6': return ['LTT']
    if f == 'A9': return ['SPX']
    if f == 'A10': return ['SOX']
    if f == 'BV': return [cfg['D']]
    if f == 'B': return ['B10']
    return []

def avail(cfg, X):
    nf = X.pan['meta'].get('nanfrac', {})
    for a in assets_of(cfg):
        if a in ('SPX', 'B10', 'TBILL'): continue
        if a == 'DEF3' or a in DD.SLEEVES:
            if a not in X.pan or nf.get(a, 0) > 0: return False
    return True

def gate_conds(cg, md, qcg, qmd, single=False):
    if single:
        return bool(cg[0] > qcg[0] and 1 - abs(md[0]) / abs(qmd[0]) >= 0.1 - 1e-12)
    ddm = 1 - abs(np.percentile(md, 10)) / abs(np.percentile(qmd, 10))
    return bool(np.median(cg - qcg) > 0 and np.median(cg) > np.median(qcg) and np.percentile(cg, 10) >= np.percentile(qcg, 10) - 1e-12 and ddm >= 0.1 - 1e-12)

def neighbors(cid, idx, uniq_set):
    c = idx[cid]
    if c['fam'] == 'B': return neighbors_B(cid, idx, uniq_set)
    out = []
    for j, d in idx.items():
        if j == cid or d['fam'] != c['fam'] or d.get('cat') != c.get('cat') or j not in uniq_set: continue
        if set(d['num']) != set(c['num']): continue
        diff = [k for k in c['num'] if d['num'][k][0] != c['num'][k][0]]
        if len(diff) == 1 and abs(d['num'][diff[0]][0] - c['num'][diff[0]][0]) == 1: out.append(j)
    return out

def neighbors_B(cid, idx, uniq_set):
    c = idx[cid]['cfgB']; out = []
    keys_num = ['sig', 'Lmax', 'knee', 'w']
    grids = {}
    for j, d in idx.items():
        if d['fam'] != 'B': continue
        for k in keys_num:
            if k in d['cfgB'] and d['cfgB'][k] is not None: grids.setdefault((d['cfgB'].get('fam'), k), set()).add(d['cfgB'][k])
    order = {g: sorted(v, key=lambda x: (str(type(x)), x)) for g, v in grids.items()}
    for j, d in idx.items():
        if j == cid or d['fam'] != 'B' or j not in uniq_set: continue
        e = d['cfgB']
        if e.get('fam') != c.get('fam'): continue
        diffs = [k for k in set(c) | set(e) if k != 'id' and c.get(k) != e.get(k)]
        if len(diffs) != 1 or diffs[0] not in keys_num: continue
        k = diffs[0]; o = order.get((c.get('fam'), k))
        if o is None or c.get(k) is None or e.get(k) is None: continue
        if abs(o.index(c[k]) - o.index(e[k])) == 1: out.append(j)
    return out

def stress(passers, G, D):
    idx = cfg_index(); uniq_set = set(G.keys()); res = {}
    H = {p: {} for p in passers}
    for wname in ('REAL', 'P', 'X'):
        X = R.W(wname); single = wname == 'REAL'
        for nm, over in (('H1', dict(cost=0.006)), ('H2', dict(delay=4))):
            qcg, qmd, _ = R.qqq(X, None, **over)
            for p in passers:
                cg, md, _ = runner(idx[p], X, None, **over)
                H[p].setdefault(nm, {})[wname] = gate_conds(cg, md, qcg, qmd, single)
        del X; L._WORLDS.pop(wname, None); DD._P.clear()
        log('stress', wname)
    X = R.W('P125'); qcg, qmd, _ = R.qqq(X)
    for p in passers:
        cg, md, _ = runner(idx[p], X); H[p]['H3'] = gate_conds(cg, md, qcg, qmd)
    del X; L._WORLDS.pop('P125', None); DD._P.clear()
    for p in passers:
        nb = neighbors(p, idx, uniq_set); npass = sum(G[j]['npass'] == 5 for j in nb)
        H[p]['H4'] = dict(nb=nb, npass=npass, ok=bool(len(nb) >= 2 and npass >= 0.5 * len(nb)))
        H[p]['all'] = bool(all(H[p]['H1'].values()) and all(H[p]['H2'].values()) and H[p]['H3'] and H[p]['H4']['ok'])
    return H

def report_rows(ids, horizons=True):
    """5/10/20/30 for P and X, REAL, and report-only worlds; per id"""
    idx = cfg_index(); out = {i: {} for i in ids}; out['QQQ'] = {}
    for wname, hs in (('P', [5, 10, 20, None]), ('X', [5, 10, 20, None]), ('REAL', [None]), ('S55', [None]), ('S29', [None]), ('OLD', [None]),
                      ('XSYM', [None]), ('P500', [None]), ('P125', [None])):
        X = R.W(wname)
        for h in hs:
            key = wname + (str(h) if h else ('30' if wname not in ('REAL', 'S55', 'S29') else ''))
            qcg, qmd, _ = R.qqq(X, h); out['QQQ'][key] = R.summ(qcg, qmd)
            for i in ids:
                c = idx[i]
                if not avail(c, X): out[i][key] = 'N/A'; continue
                cg, md, _ = runner(c, X, h); out[i][key] = R.summ(cg, md, qcg)
        if wname == 'P':
            # account size 100M (deduction 1/10), raw (no neutralization), futures cost
            qcg, qmd, _ = R.qqq(X, None, D=0.025); out['QQQ']['P30_100M'] = R.summ(qcg, qmd)
            for i in ids:
                cg, md, _ = runner(idx[i], X, None, D=0.025); out[i]['P30_100M'] = R.summ(cg, md, qcg)
        del X; L._WORLDS.pop(wname, None); DD._P.clear(); log('report', wname)
    for wname in ('P', 'X', 'REAL'):
        X = R.W(wname, raw=True); key = wname + ('30' if wname != 'REAL' else '') + '_raw'
        qcg, qmd, _ = R.qqq(X); out['QQQ'][key] = R.summ(qcg, qmd)
        for i in ids:
            cg, md, _ = runner(idx[i], X); out[i][key] = R.summ(cg, md, qcg)
        del X; L._WORLDS.pop(wname, None); DD._P.clear()
    return out
