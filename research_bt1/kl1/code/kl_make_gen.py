"""Run the locked generator, save rows to CACHE, write results/gen_manifest.json (counts + code sha256) BEFORE any screen."""
import os, sys, json, hashlib, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wsdata as WD, kl_gen as G, kl_sig as SG
CACHE = WD.CACHE; HERE = os.path.dirname(os.path.abspath(__file__))
af = {}
for p in ('KR', 'US'):
    meta = json.load(open(CACHE + '%s_atoms_meta.json' % p.lower()))
    names = sorted(set(m['feat'] for m in meta)); fid = {n: i for i, n in enumerate(names)}
    af[p] = np.array([fid[m['feat']] for m in meta], np.int64)
rows = G.generate_all({'KR': len(SG.KR_DEFS), 'US': len(SG.US_DEFS)}, af)
cnt = {}
for k, v in rows.items():
    np.save(CACHE + 'gen_%s.npy' % k, v); cnt[k] = int(len(v))
sha = {f: hashlib.sha256(open(os.path.join(HERE, f), 'rb').read()).hexdigest() for f in sorted(os.listdir(HERE)) if f.endswith('.py')}
man = dict(time_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), seed=G.SEED, counts=cnt, N_total=int(sum(cnt.values())),
           n_atoms={p: int(len(a)) for p, a in af.items()}, n_feats={p: int(a.max() + 1) for p, a in af.items()}, code_sha256=sha,
           precommit_sha256=open(os.path.join(HERE, '..', 'PRECOMMIT_KL1.sha256')).read().split()[0])
json.dump(man, open(os.path.join(HERE, '..', 'results', 'gen_manifest.json'), 'w'), indent=1)
print(json.dumps({k: man[k] for k in ('counts', 'N_total', 'n_atoms', 'n_feats')}))
