"""Report-only pre-1986 worlds (S55 real S&P 1955-85, S29 real 1929-54, OLD S&P 1928-85 bootstrap) for the off-grid passers,
neutralized and raw. 'QQQ' there = the world's index held with QQQ conventions (as in df5stress report rows). Data <= 1985."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df5run as R, df5lib as L, df5data as DD
CF = [dict(id='OG|e0.70|c0.60', fam='A3', e=0.70, c=0.60, dmix=['DEF3'], gate='none'),
      dict(id='OG|e0.60|c0.75', fam='A3', e=0.60, c=0.75, dmix=['DEF3'], gate='none'),
      dict(id='A3|e1.00|c0.50|DEF3', fam='A3', e=1.0, c=0.5, dmix=['DEF3'], gate='none')]
out = {}
for wname in ('S55', 'S29', 'OLD'):
    for raw in (False, True):
        X = R.W(wname, raw=raw); key = wname + ('_raw' if raw else '')
        meta = X.pan['meta']
        qcg, qmd, _ = R.qqq(X, None); q = R.summ(qcg, qmd)
        print(key, 'DEF3 shift %.2f%%/yr nanfrac %s gaps %s' % (meta['shift'].get('DEF3', np.nan) * 252 * 100, meta['nanfrac'].get('DEF3'), meta['gaps'].get('DEF3')),
              'QQQ cagr %.2f%% p10 %.2f%% mddp10 %.1f%%' % (q['cagr'] * 100, q['p10'] * 100, q['mdd_p10'] * 100), flush=True)
        for cfg in CF:
            jb = R.job(cfg, X); cg, md, _ = R.run_job(jb, X, None); s = R.summ(cg, md, qcg); del jb
            ddm = 1 - abs(s['mdd_p10']) / abs(q['mdd_p10'])
            print('   ', cfg['id'], 'pair %+.2fpp med %+.2fpp p10 %+.2fpp ddm %+.1f%%' % (s['pair'] * 100, (s['cagr'] - q['cagr']) * 100, (s['p10'] - q['p10']) * 100, ddm * 100), flush=True)
            out.setdefault(key, {})[cfg['id']] = s
        out[key]['QQQ'] = q
        del X; L._WORLDS.pop(wname, None); DD._P.clear()
json.dump(out, open('/tmp/df5v/critic/oos.json', 'w'))
