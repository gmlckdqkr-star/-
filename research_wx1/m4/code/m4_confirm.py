"""WX1-M4 one-shot confirmation (2000-01..2014-12) for the discovery top-20 (by mean monthly d vs 1x NDX), then MS1 rows.
Out: results/confirm.json, results/top20_streams.pkl"""
import os, sys, json, numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m4/'
sys.path.insert(0, S + 'code'); os.environ['NUMBA_CACHE_DIR'] = S + 'nb'
import warnings; warnings.filterwarnings('ignore')
from m4eng import Env
import m4rules as MR
from m4_run import s085_aligned

st = json.load(open(S + 'results/stats.json'))
rules = {json.loads(l)['id']: json.loads(l) for l in open(S + 'results/rules.jsonl')}
D = np.load(S + 'results/disc_D.npy'); D85 = np.load(S + 'results/disc_D085.npy')
env = Env(end='2014-12-31', start_eval='1964-01-02'); ref = s085_aligned(env)
months = env.months[env.mid[env.t0]:]
nd = D.shape[0]
assert str(months[nd]) == '2000-01', months[nd]
out, streams = [], {}
for rank, i in enumerate(st['top20']):
    r, ntr = MR.run_rule(env, rules[i]['rule'])
    d1 = env.monthly_diff(r); d2 = env.monthly_diff(r, ref)
    cons = float(np.max(np.abs(d1[:nd] - D[:, i])))
    a1, b1 = 12 * d1[:nd].mean(), 12 * d1[nd:].mean(); a2, b2 = 12 * d2[:nd].mean(), 12 * d2[nd:].mean()
    ok = bool(a2 > 0 and b2 > 0 and b2 >= 0.5 * a2)
    yrs_d = nd / 12; yrs_c = (len(d1) - nd) / 12
    eqd = np.prod(1 + r[:np.searchsorted(env.idx[env.t0:], pd.Timestamp('2000-01-01'))])
    out.append(dict(rank=rank + 1, id=i, fam=rules[i]['rule']['fam'], rule=rules[i]['rule'],
                    disc_vs1x_ann=float(a1), conf_vs1x_ann=float(b1), decay_vs1x=float(b1 / a1) if a1 else None,
                    disc_vs085_ann=float(a2), conf_vs085_ann=float(b2), decay_vs085=float(b2 / a2) if a2 else None,
                    conf_pass=ok, disc_consistency_maxabs=cons, trades_per_year=float(ntr / (len(r) / 252))))
    streams[i] = pd.Series(r, index=env.idx[env.t0:])
    print(rank + 1, i, rules[i]['rule']['fam'], 'disc/conf vs1x %.3f/%.3f  vs085 %.3f/%.3f pass=%s cons=%.1e' % (a1, b1, a2, b2, ok, cons), flush=True)
pd.to_pickle(streams, S + 'results/top20_streams.pkl')
json.dump(dict(top20=out, n_conf_pass=sum(o['conf_pass'] for o in out)), open(S + 'results/confirm.json', 'w'), indent=1)
print('conf pass', sum(o['conf_pass'] for o in out))
