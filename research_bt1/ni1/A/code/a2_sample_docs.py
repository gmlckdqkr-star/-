# NI1-A step 2: build insider rows, draw seed-20261107 sample of 2,500, fetch document.xml, parse in memory.
# Only numbers are saved (no names, no raw documents). Key never printed.
import os, sys, json, glob, re, time, collections, urllib.request
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a_parse

KEY = os.environ['OPENDART_API_KEY']
H = {'User-Agent': 'research-client/1.0'}
RUN = sys.argv[1]            # scratchpad run/A
RES = sys.argv[2]            # results dir
NAME = '임원ㆍ주요주주특정증권등소유상황보고서'

rows = {}
months = 0
total_count_sum = 0
for f in sorted(glob.glob(os.path.join(RUN, 'list', 'list_*.json'))):
    d = json.load(open(f))
    months += 1
    total_count_sum += d['total_count']
    for r in d['rows']:
        rows[r['rcept_no']] = r
rows = [r for r in rows.values() if '20020701' <= r['rcept_dt'] <= '20081231']
assert months == 78, months
cand = [r for r in rows if NAME in r['report_nm']]
pref = collections.Counter((re.match(r'(\[[^\]]*\])?', r['report_nm']).group(0) or 'none') for r in cand)
ins = sorted([r for r in cand if '[' not in r['report_nm']], key=lambda r: r['rcept_no'])
rng = np.random.default_rng(20261107)
idx = np.sort(rng.choice(len(ins), 2500, replace=False))
samp = [ins[i] for i in idx]
meta = dict(list_months=months, list_total_count_sum=total_count_sum, list_rows_unique=len(rows),
            insider_name_rows=len(cand), insider_prefix_counts=dict(pref), insider_rows_used=len(ins),
            insider_rows_by_corp_cls_now=dict(collections.Counter(r['corp_cls'] for r in ins)),
            insider_rows_blank_stock_code=sum(1 for r in ins if not r['stock_code'].strip()),
            sample_n=len(samp), sample_first_last=[samp[0]['rcept_no'], samp[-1]['rcept_no']])
json.dump(meta, open(os.path.join(RES, 'A_list_meta.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(meta, ensure_ascii=False))

outf = os.path.join(RUN, 'docs_parsed.jsonl')
done = set()
if os.path.exists(outf):
    for line in open(outf):
        done.add(json.loads(line)['rcept_no'])
fo = open(outf, 'a')
ncalls = 0
for r in samp:
    if r['rcept_no'] in done:
        continue
    rec = {k: r[k] for k in ('rcept_no', 'rcept_dt', 'stock_code', 'corp_cls')}
    b = None
    for i in range(4):
        try:
            ncalls += 1
            b = urllib.request.urlopen(urllib.request.Request(
                'https://opendart.fss.or.kr/api/document.xml?crtfc_key=%s&rcept_no=%s' % (KEY, r['rcept_no']), headers=H), timeout=60).read()
            break
        except Exception as e:
            print('retry', i, str(e).replace(KEY, '***'), flush=True)
            time.sleep(5 * (i + 1))
    if b is None:
        rec.update(status='fetch_fail', parsed=False)
    else:
        try:
            raw, nf = a_parse.unzip(b)
            t, enc = a_parse.decode(raw)
            p = a_parse.parse(t)
            rec.update(status='ok', enc=enc, nfiles=nf, **p)
        except Exception:
            s = b[:300].decode('utf-8', 'replace')
            m = re.search(r'<status>(\d+)</status>', s) or re.search(r'"status"\s*:\s*"(\d+)"', s)
            code = m.group(1) if m else 'unknown'
            rec.update(status='api_' + code, parsed=False)
            if code == '020':
                print('quota reached; stopping', flush=True)
                break
    fo.write(json.dumps(rec, ensure_ascii=False) + '\n'); fo.flush()
    if ncalls % 100 == 0:
        print('calls', ncalls, flush=True)
    time.sleep(0.35)
print('done calls', ncalls)
