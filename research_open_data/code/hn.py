import json, time, urllib.request, urllib.parse, sys, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code'); import gate
def n(q, a, b):
    u = 'https://hn.algolia.com/api/v1/search?' + urllib.parse.urlencode(dict(query=q, tags='story', numericFilters=f'created_at_i>={a},created_at_i<{b}', hitsPerPage=0))
    for k in range(4):
        try: time.sleep(0.2); return json.load(urllib.request.urlopen(u, timeout=30))['nbHits']
        except Exception: time.sleep(2 ** k)
months = pd.date_range('2007-02-01', '2015-01-01', freq='MS'); rows = []
for a, b in zip(months[:-1], months[1:]):
    ta, tb = int(a.timestamp()), int(b.timestamp())
    rows.append(dict(m=a + pd.offsets.MonthEnd(0), tot=n('', ta, tb), **{q: n(q, ta, tb) for q in ('recession', 'layoffs', 'bubble')}))
D = pd.DataFrame(rows).set_index('m'); D.to_csv('/mnt/project-files/research/open_data/raw/hn_counts.csv')
res = {}
for q in ('recession', 'layoffs', 'bubble'):
    s = D[q] / D.tot; zz = (s - s.expanding().mean()) / s.expanding().std(); zz[np.arange(len(s)) < 24] = np.nan; zz = zz.dropna()
    g = gate.test(~(zz > 1), trials=3, name=q, verbose=False); e = g['ndx_86_14']
    res[q] = dict(n=e['n'], hit=round(e['hit'], 3), always_up=round(e['always_up'], 3), defl=round(e['hit_deflated'], 3), verdict=g['verdict'], frac_in=float((~(zz > 1)).mean()))
    print(q, res[q])
json.dump(res, open('/mnt/project-files/research/open_data/results/hn.json', 'w'), indent=1)
