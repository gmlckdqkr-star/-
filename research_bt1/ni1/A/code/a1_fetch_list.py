# NI1-A step 1: OpenDART list.json, pblntf_ty=D, 2002-07..2008-12, all markets (no corp_cls).
# Stores only non-name columns. Key read from env, never printed/saved.
import os, sys, json, time, urllib.request, urllib.parse, calendar

KEY = os.environ['OPENDART_API_KEY']
H = {'User-Agent': 'research-client/1.0'}
OUT = sys.argv[1]  # directory under scratchpad run/A
KEEP = ('rcept_no', 'rcept_dt', 'stock_code', 'corp_code', 'report_nm', 'corp_cls')
os.makedirs(OUT, exist_ok=True)
ncalls = 0


def mask(s):
    return s.replace(KEY, '***')


def get(params, tries=4):
    global ncalls
    q = dict(crtfc_key=KEY, **params)
    u = 'https://opendart.fss.or.kr/api/list.json?' + urllib.parse.urlencode(q)
    for i in range(tries):
        try:
            ncalls += 1
            b = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=60).read()
            return json.loads(b)
        except Exception as e:
            print('retry', i, mask(str(e)), flush=True)
            time.sleep(5 * (i + 1))
    raise RuntimeError('failed ' + mask(u))


months = []
for y in range(2002, 2009):
    for m in range(1, 13):
        if (y, m) < (2002, 7):
            continue
        months.append((y, m))

if len(sys.argv) > 2 and sys.argv[2] == 'rev':
    months = months[::-1]  # second polite worker from the other end

for y, m in months:
    fn = os.path.join(OUT, 'list_%d%02d.json' % (y, m))
    if os.path.exists(fn):
        continue
    last = calendar.monthrange(y, m)[1]
    base = dict(bgn_de='%d%02d01' % (y, m), end_de='%d%02d%02d' % (y, m, last), pblntf_ty='D', page_count=100)
    d = get(dict(base, page_no=1))
    if d.get('status') == '013':
        json.dump(dict(total_count=0, rows=[]), open(fn, 'w'))
        continue
    assert d.get('status') == '000', (d.get('status'), d.get('message'))
    tot, tp = int(d['total_count']), int(d['total_page'])
    rows = [{k: r.get(k, '') for k in KEEP} for r in d['list']]
    for p in range(2, tp + 1):
        time.sleep(0.4)
        dd = get(dict(base, page_no=p))
        assert dd.get('status') == '000', (dd.get('status'), dd.get('message'))
        rows += [{k: r.get(k, '') for k in KEEP} for r in dd['list']]
    uniq = {r['rcept_no']: r for r in rows}
    json.dump(dict(total_count=tot, n_rows=len(rows), n_uniq=len(uniq), rows=list(uniq.values())), open(fn, 'w'), ensure_ascii=False)
    print(y, m, 'total', tot, 'rows', len(rows), 'uniq', len(uniq), 'calls', ncalls, flush=True)
    time.sleep(0.4)
print('done calls', ncalls)
