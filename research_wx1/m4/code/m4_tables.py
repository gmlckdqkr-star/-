"""WX1-M4 descriptive tables from the discovery matrix (no new trials): per family best / median, era split of the best,
count of rules above s0.85 in discovery. Out: results/tables.json"""
import json, numpy as np
S = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m4/'
D = np.load(S + 'results/disc_D.npy'); D85 = np.load(S + 'results/disc_D085.npy')
meta = json.load(open(S + 'results/disc_meta.json')); st = json.load(open(S + 'results/stats.json'))
rules = [json.loads(l) for l in open(S + 'results/rules.jsonl')]
fam = np.array([r['rule']['fam'] for r in rules])
m1 = 12 * D.mean(axis=0); m85 = 12 * D85.mean(axis=0)
t = np.load(S + 'results/disc_t.npy')
spx = slice(0, 264); ndx = slice(264, 432)       # 1964-01..1985-12 (264 months), 1986-01..1999-12 (168)
out = {}
for f in sorted(set(fam)):
    k = np.flatnonzero(fam == f); b = k[np.argmax(m1[k])]; b85 = k[np.argmax(m85[k])]
    out[f] = dict(n=int(len(k)), best_id=int(b), best_vs1x=float(m1[b]), best_vs1x_t=float(t[b, 0]), med_vs1x=float(np.median(m1[k])),
                  best85_id=int(b85), best_vs085=float(m85[b85]), med_vs085=float(np.median(m85[k])),
                  n_pos_vs085=int((m85[k] > 0).sum()), best_era_vs1x=[float(12 * D[spx, b].mean()), float(12 * D[ndx, b].mean())],
                  best85_era_vs085=[float(12 * D85[spx, b85].mean()), float(12 * D85[ndx, b85].mean())],
                  best_cagr_pretax=meta['cagr'][b], best_mdd=meta['mdd'][b])
# era split vs s0.85 over all rules
out['_all'] = dict(n_pos_vs085_spx_era=int((D85[spx].mean(axis=0) > 0).sum()), n_pos_vs085_ndx_era=int((D85[ndx].mean(axis=0) > 0).sum()),
                   n_pos_vs085_both=int(((D85[spx].mean(axis=0) > 0) & (D85[ndx].mean(axis=0) > 0)).sum()),
                   best_ndx_era_vs085=float(12 * D85[ndx].mean(axis=0).max()), best_spx_era_vs085=float(12 * D85[spx].mean(axis=0).max()),
                   ndx_era_vs085_quant=[float(12 * np.quantile(D85[ndx].mean(axis=0), q)) for q in (0.5, 0.9, 0.99, 1.0)])
json.dump(out, open(S + 'results/tables.json', 'w'), indent=1)
for f, v in out.items(): print(f, json.dumps(v)[:400])
