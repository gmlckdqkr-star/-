"""Q1 alarm-truth test: fetch the three public Japan series, cut at 2014-12-31 BEFORE anything is written to disk.
  python q1_fetch.py OUT_DIR
Sources (robots.txt read 2026-11-11: FRED allows /graph/fredgraph.csv with crawl-delay 1; mof.go.jp has no robots.txt):
  NIKKEI225          FRED, daily close of the Nikkei 225 (price index; copyright Nikkei Inc., private research use, not redistributed)
  IR3TCD01JPM156N    FRED / OECD, 3-month certificate-of-deposit rate, monthly
  jgbcme_all.csv     Ministry of Finance Japan, JGB yields by maturity, daily from 1974-09-24 (PDL 1.0)
No personal information is sent; the user agent is a generic name."""
import sys, os, time, json, hashlib, urllib.request
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True); UA = {'User-Agent': 'research-bot'}; CUT = 2014
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode('utf-8', 'replace')
meta = {}
for sid in ('NIKKEI225', 'IR3TCD01JPM156N'):
    u = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s&cosd=1900-01-01&coed=%d-12-31' % (sid, CUT)
    t = get(u); rows = t.strip().splitlines(); assert all(int(l[:4]) <= CUT for l in rows[1:]), 'row after the cut'
    open('%s/%s_le2014.csv' % (OUT, sid), 'w').write('\n'.join(rows) + '\n'); meta[sid] = dict(url=u, rows=len(rows) - 1); time.sleep(1.2)
u = 'https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv'
keep = []
for l in get(u).splitlines():
    p = l.split(',')[0].strip().split('/')
    if len(p) == 3 and p[0].isdigit():
        if int(p[0]) <= CUT: keep.append(l)
    else: keep.append(l)
open(OUT + '/mof_jgb_le2014.csv', 'w').write('\n'.join(keep) + '\n'); meta['mof_jgb'] = dict(url=u, rows=len(keep) - 2)
for f in sorted(os.listdir(OUT)):
    if f.endswith('.csv'): meta.setdefault('sha256', {})[f] = hashlib.sha256(open(OUT + '/' + f, 'rb').read()).hexdigest()
meta['fetched'] = time.strftime('%FT%TZ', time.gmtime()); json.dump(meta, open(OUT + '/SOURCES.json', 'w'), indent=1); print(json.dumps(meta, indent=1))
