"""NP1-KF s0: download KOSPI foreign net buying (802Y001/0030000, 억원) and KOSPI market cap (802Y001/0183000, 억원), daily,
2003-01-02..2014-12-31 ONLY (end date in the request itself; no post-2014 value is ever fetched). Key from env ECOS_API_KEY (never printed/saved)."""
import os, json, urllib.request, hashlib, pandas as pd
K = os.environ['ECOS_API_KEY']; OUT = '/mnt/project-files/research/np1/data/'
def fetch(item):
    u = f"https://ecos.bok.or.kr/api/StatisticSearch/{K}/json/kr/1/20000/802Y001/D/20030101/20141231/{item}"
    with urllib.request.urlopen(u, timeout=120) as r: d = json.loads(r.read().decode('utf-8'))
    rows = d['StatisticSearch']['row']
    s = pd.Series({pd.Timestamp(r['TIME']): float(r['DATA_VALUE']) for r in rows}).sort_index()
    assert s.index.max() <= pd.Timestamp('2014-12-31'); return s
df = pd.DataFrame({'fnet_eok': fetch('0030000'), 'mcap_eok': fetch('0183000')})
df.index.name = 'krdate'; df.to_csv(OUT + 'kospi_foreign_le2014.csv')
h = hashlib.sha256(open(OUT + 'kospi_foreign_le2014.csv', 'rb').read()).hexdigest()
json.dump(dict(source='ECOS 802Y001 items 0030000 (외국인 순매수 유가증권시장, 억원) and 0183000 (시가총액 유가증권시장, 억원), daily',
               request_window='20030101-20141231', fetched_utc=pd.Timestamp.utcnow().isoformat(), rows=len(df),
               first=str(df.index.min().date()), last=str(df.index.max().date()), sha256=h,
               missing=dict(fnet=int(df.fnet_eok.isna().sum()), mcap=int(df.mcap_eok.isna().sum()))),
          open(OUT + 'MANIFEST.json', 'w'), indent=1, ensure_ascii=False)
print(open(OUT + 'MANIFEST.json').read())
