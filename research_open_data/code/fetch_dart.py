"""Fetch OpenDART disclosure list (metadata only) for one pblntf_ty, 2001-01..2014-12, 1-month windows.
Key read from env OPENDART_API_KEY; never written or printed. Output: raw/dart_<ty>.jsonl (one row per disclosure)."""
import os, sys, json, time, urllib.request, datetime as dt
ty = sys.argv[1]; y0, y1 = int(sys.argv[2]), int(sys.argv[3]); out = f'/mnt/project-files/research/data/kr_dart/dart_{ty}_{y0}.jsonl'
K = os.environ['OPENDART_API_KEY']; done = set()
if os.path.exists(out):
    for l in open(out): done.add(json.loads(l)['_win'])
f = open(out, 'a'); calls = 0
def get(params):
    global calls
    q = '&'.join(f'{k}={v}' for k, v in params.items())
    for a in range(5):
        try:
            calls += 1; time.sleep(0.25)
            return json.load(urllib.request.urlopen(f'https://opendart.fss.or.kr/api/list.json?crtfc_key={K}&{q}', timeout=60))
        except Exception as e:
            time.sleep(2 ** a)
    raise RuntimeError('fetch failed ' + q)
d = dt.date(y0, 1, 1)
while d <= dt.date(y1, 12, 1):
    e = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    win = d.strftime('%Y%m')
    if win not in done:
        p = 1; rows = []
        while True:
            r = get(dict(bgn_de=d.strftime('%Y%m%d'), end_de=e.strftime('%Y%m%d'), pblntf_ty=ty, page_no=p, page_count=100))
            if r.get('status') == '013': break
            if r.get('status') != '000': raise RuntimeError(f"status {r.get('status')} {r.get('message')} {win}")
            rows += r['list']
            if p >= r['total_page']: break
            p += 1
        for x in rows: x['_win'] = win; f.write(json.dumps(x, ensure_ascii=False) + '\n')
        f.flush(); print(win, len(rows), 'calls', calls, flush=True)
    d = e + dt.timedelta(days=1)
print('DONE calls', calls)
