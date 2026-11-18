"""DF7 audit step 3: neighbour sets (informational; 0 passers so H4 / selection are vacuous)."""
import sys, json
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df7 as D
C = D.configs(); idx = {c['id']: c for c in C}
M = json.load(open(D.RES + 'df7_main.json')); G = M['gates']
cnt = {}
for c in C:
    nb = D.nbrs7(c, C); cnt.setdefault(c['fam'], []).append(len(nb))
    assert all(n in idx for n in nb)
out = {f: dict(min=min(v), max=max(v), n_lt4=sum(x < 4 for x in v)) for f, v in cnt.items()}
for i in ('F2|q0.2|r0.7|g0.1|m0.0', 'F2|q0.2|r0.5|g0.3|m0.0', 'F2|q0.3|r0.2|g0.3|m0.2', 'F3|M252|Q100|M100'):
    nb = D.nbrs7(idx[i], C)
    out[i] = dict(nb=nb, n=len(nb), npass=sum(G[j]['npass'] == 5 for j in nb), nscore=min([G[i]['score']] + [G[j]['score'] for j in nb]), score=G[i]['score'])
json.dump(out, open('/tmp/df7v_audit/a3_out.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
