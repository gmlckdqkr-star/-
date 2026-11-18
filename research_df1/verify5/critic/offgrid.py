"""Critic re-check: off-grid static TQQQ/QQQ/DEF3 mixes through the UNCHANGED DF5 engine in all five gate worlds,
plus H1 (cost x2, QQQ too) and H2 (delay 4) on REAL/P30/X30. Prints summary numbers only (all data <= 2014)."""
import os, sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df5run as R, df5lib as L, df5data as DD, df5gate as GT

CFGS = [dict(id='OG|e0.70|c0.60|DEF3', fam='A3', e=0.70, c=0.60, dmix=['DEF3'], gate='none'),
        dict(id='OG|e0.60|c0.75|DEF3', fam='A3', e=0.60, c=0.75, dmix=['DEF3'], gate='none'),
        dict(id='OG|e0.80|c0.45|DEF3', fam='A3', e=0.80, c=0.45, dmix=['DEF3'], gate='none')]
# control: one stored grid config, to prove the harness reproduces df5_main.json
CTRL = dict(id='A3|e1.00|c0.50|DEF3|none', fam='A3', e=1.0, c=0.5, dmix=['DEF3'], gate='none')
D = json.load(open(R.RES + 'df5_main.json'))
out = dict(rows={}, qqq={}, h1={}, h2={}, ctrl={})
for wname in ('REAL', 'P', 'X'):
    X = R.W(wname)
    hs = [None] if wname == 'REAL' else [30, 10]
    for h in hs:
        hh = None if h == 30 else h; key = wname + ('' if h is None else str(h))
        qcg, qmd, _ = R.qqq(X, hh); out['qqq'][key] = R.summ(qcg, qmd)
        for cfg in CFGS + [CTRL]:
            jb = R.job(cfg, X); cg, md, _ = R.run_job(jb, X, hh); s = R.summ(cg, md, qcg)
            (out['ctrl'] if cfg is CTRL else out['rows'].setdefault(cfg['id'], {}))[key] = s
            del jb
        if key in ('REAL', 'P30', 'X30'):
            for tag, over in (('h1', dict(cost=0.006)), ('h2', dict(delay=4))):
                qcg2, qmd2, _ = R.qqq(X, hh, **over); out[tag].setdefault('QQQ', {})[key] = R.summ(qcg2, qmd2)
                for cfg in CFGS[:2]:
                    jb = R.job(cfg, X); cg, md, _ = R.run_job(jb, X, hh, **over)
                    out[tag].setdefault(cfg['id'], {})[key] = R.summ(cg, md, qcg2); del jb
        print(wname, key, 'done', flush=True)
    del X; L._WORLDS.pop(wname, None); DD._P.clear()

# control check vs stored
for k, v in out['ctrl'].items():
    st = D['rows'][CTRL['id']][k]
    print('CTRL', k, {f: round(v[f] - st[f], 10) for f in ('cagr', 'p10', 'mdd_p10', 'pair') if f in v and f in st})
for k, v in out['qqq'].items():
    print('QQQ', k, 'diff vs stored cagr %.2e mddp10 %.2e' % (v['cagr'] - D['qqq'][k]['cagr'], v['mdd_p10'] - D['qqq'][k]['mdd_p10']))
# gates with the unchanged gate code
for cid, r in out['rows'].items():
    g, sc, ddm = GT.gate_row(r, out['qqq'])
    print(cid, 'npass', sum(v['ok'] for v in g.values()), 'score %.4f minddm %.3f' % (sc, ddm))
    for k, v in g.items():
        print('   ', k, 'ok' if v['ok'] else 'FAIL', {a: (round(b * 100, 2) if isinstance(b, float) else b) for a, b in v.items() if a != 'ok'})
for tag in ('h1', 'h2'):
    Q2 = out[tag]['QQQ']
    for cid in [c['id'] for c in CFGS[:2]]:
        r = out[tag][cid]
        for k in ('REAL', 'P30', 'X30'):
            a, q = r[k], Q2[k]
            if k == 'REAL':
                print(tag, cid, k, 'ret %+.2fpp ddm %.3f' % ((a['cagr'] - q['cagr']) * 100, 1 - abs(a['mdd_med']) / abs(q['mdd_med'])))
            else:
                print(tag, cid, k, 'pair %+.2fpp med %+.2fpp p10 %+.2fpp ddm %.3f' % (a['pair'] * 100, (a['cagr'] - q['cagr']) * 100, (a['p10'] - q['p10']) * 100,
                                                                                    1 - abs(a['mdd_p10']) / abs(q['mdd_p10'])))
json.dump(out, open('/tmp/df5v/critic/offgrid.json', 'w'), indent=1)
