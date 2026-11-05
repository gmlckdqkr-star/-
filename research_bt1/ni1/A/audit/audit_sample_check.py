# NI1-A audit: list completeness per month, re-derive the seed-20261107 sample from the list files, and check the
# join of docs_parsed rows to list rows (rcept_dt / stock_code). Numbers only.
import sys, json, glob, os
import numpy as np
LIST, DOCS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
NAME = '임원ㆍ주요주주특정증권등소유상황보고서'
bad_month = []; rows = {}
for f in sorted(glob.glob(os.path.join(LIST, 'list_*.json'))):
    d = json.load(open(f))
    if d['total_count'] != len(d['rows']):
        bad_month.append((os.path.basename(f), d['total_count'], len(d['rows'])))
    for r in d['rows']:
        rows[r['rcept_no']] = r
out_of_range = sum(1 for r in rows.values() if not ('20020701' <= r['rcept_dt'] <= '20081231'))
ins = sorted([r for r in rows.values() if NAME in r['report_nm'] and not r['report_nm'].startswith('[')
              and '20020701' <= r['rcept_dt'] <= '20081231'], key=lambda r: r['rcept_no'])
idx = np.random.default_rng(20261107).choice(len(ins), 2500, replace=False)
mine = set(ins[i]['rcept_no'] for i in idx)
docs = [json.loads(l) for l in open(DOCS)]
theirs = set(d['rcept_no'] for d in docs)
join_mismatch = sum(1 for d in docs if d['rcept_no'] in rows and (rows[d['rcept_no']]['rcept_dt'] != d['rcept_dt'] or
                    rows[d['rcept_no']]['stock_code'] != d['stock_code']))
# rcept_dt must equal the date embedded in rcept_no (first 8 digits)
dt_vs_no = sum(1 for d in docs if d['rcept_no'][:8] != d['rcept_dt'])
res = dict(months_with_total_count_ne_rows=bad_month, rows_outside_window=out_of_range, insider_rows=len(ins),
           sample_identical=(mine == theirs), sample_overlap=len(mine & theirs), join_mismatch=join_mismatch,
           rcept_dt_ne_rcept_no_date=dt_vs_no,
           bracket_prefixes_other_than_correction=sorted({r['report_nm'].split(']')[0] + ']' for r in rows.values()
                                                          if NAME in r['report_nm'] and r['report_nm'].startswith('[')}))
print(json.dumps(res, ensure_ascii=False, indent=1))
json.dump(res, open(OUT, 'w'), ensure_ascii=False, indent=1)
