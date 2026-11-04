"""Run one W3 hypothesis with a custom cross-stock score: python3 run_custom.py H1 monthly 30 [--cut]
Writes results/<H>.json and the stream to the scratchpad (for H4 / combos)."""
import sys, json, time
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/multi_cand/w3_stock_new/code')
import w3lib as w

kind, cad, top = sys.argv[1], sys.argv[2], int(sys.argv[3])
t0 = time.time()
P = w.panel()
tg, S_all = w.targets(P, kind, cad, top, want_scores=True)
print(kind, 'targets', round(time.time() - t0, 1), 's', flush=True)
res = dict(hypothesis=kind, cadence=cad, top=top, npeer=w.NPEER, ic21=w.ic(P, S_all))
print('IC', res['ic21'], flush=True)
ev, S, share = w.evaluate(P, tg, 'mc1_w3_' + kind)
res.update(ev)
S.to_pickle(f'{w.SCR}/stream_{kind}.pkl')
res['corr'] = w.corr_s085(S)
res['combo'] = w.combos(S, share)
if '--cut' in sys.argv:
    res['causality'] = w.cut_check(P, kind, cad, top)
res['elapsed_total_s'] = round(time.time() - t0, 1)
json.dump(res, open(f'{w.W3}/results/{kind}.json', 'w'), indent=1, default=float)
m = res['ms1']; p = m.get('dev250_path') or {}; r = m.get('real_ndx_86_14') or {}
print(json.dumps(dict(k=kind, after_tax_cons=res['cons_cagr_at'], base=res['base_cagr_at'], sharpe=res['sharpe_pretax'],
                      sharpe_at=res['sharpe_aftertax'], ms1_path=p.get('cagr'), ms1_real=r.get('cagr'),
                      null_top=res['null']['top'], corr=res['corr']['corr_all'], combo=res['combo'],
                      caus=res.get('causality', {}).get('ok'), t=res['elapsed_total_s']), default=float), flush=True)
