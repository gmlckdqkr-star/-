import os, sys, json, numpy as np
sys.dont_write_bytecode = True
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df5v/audit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df5run as R, df5fam as F
CF = [c for c in F.configs(R.ELIG) if c['fam'] == 'A4']
X = R.W('REAL'); S = X.w['S']; ii = X.w['ii']
d = S.index.values[ii[0]]; pre = d < np.datetime64('1985-10-01')
print('pre-1985-10 days in REAL path', int(pre.sum()), 'of WARM 300')
q = X.pan['QQQ'][0]; print('QQQ zero returns pre:', int((q[0, pre] == 0).sum()))
D = json.load(open('/mnt/project-files/research/df1/results/df5_main.json')); Q = D['qqq']['REAL']
base = {}
for c in CF:
    cg, md, _ = R.run_job(R.job(c, X), X); base[c['id']] = (cg[0], md[0])
# signal-only fill: QQQ level for momentum/SMA uses S&P (price proxy) before 1985-10-01
spx = np.nan_to_num(S['SPX'].values.astype(float)[ii]) - 0.02 / 252
rq = q.copy(); rq[0, pre] = spx[0, pre]; X._lv['QQQ'] = np.cumprod(1 + rq, axis=1)
for c in CF:
    cg, md, _ = R.run_job(R.job(c, X), X); b = base[c['id']]; st = D['rows'][c['id']]['REAL']
    g1 = lambda cg_, md_: cg_ > Q['cagr'] and abs(md_) <= 0.9 * abs(Q['mdd_med'])
    if abs(cg[0] - b[0]) > 1e-6 or abs(md[0] - b[1]) > 1e-6:
        print('%-28s stored %.4f/%.3f  base %.4f/%.3f  filled %.4f/%.3f  G1 %s->%s' % (c['id'], st['cagr'], st['mdd_med'], b[0], b[1], cg[0], md[0], g1(*b), g1(cg[0], md[0])))
