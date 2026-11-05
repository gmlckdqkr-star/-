"""OV1-G step 0: data cut + FOMC calendar parse + MANIFEST (data only; no returns, labels or v1 states are read).
Inputs (raw, as fetched 2026-11-05 ~09:15Z via the agent proxy, curl -A curl/8.0):
  data/raw_DFEDTAR.csv, raw_DFEDTARU.csv, raw_DFEDTARL.csv  <- https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>
  data/raw_fomc/fomchistorical<YYYY>.htm (1982..2014)        <- https://www.federalreserve.gov/monetarypolicy/fomchistorical<YYYY>.htm
  data/raw_fomc/fomc_historical_year.htm                     <- https://www.federalreserve.gov/monetarypolicy/fomc_historical_year.htm
Outputs: data/cut_DFEDTAR.csv, cut_DFEDTARU.csv, cut_DFEDTARL.csv (rows <= 2014-12-31 only),
         data/fomc_events_1982_2014.csv (one row per listed FOMC event day: date, kind, heading), data/MANIFEST.json.
Rows after 2014-12-31 are dropped by date comparison on read; their values are never printed or used."""
import csv, datetime as dt, hashlib, json, os, re
D = '/mnt/project-files/research/ov1/lanes/OV1-G/data/'
CUT = dt.date(2014, 12, 31)
MON = {m: i for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
                                   'October', 'November', 'December'], 1)}
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()

def cut_fred(sid):
    rows = list(csv.reader(open(D + 'raw_%s.csv' % sid)))
    hdr, body = rows[0], rows[1:]
    keep = [r for r in body if dt.date.fromisoformat(r[0]) <= CUT]
    with open(D + 'cut_%s.csv' % sid, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(hdr); w.writerows(keep)
    vals = [r[1] for r in keep]
    return dict(source_url='https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s' % sid, raw_file='raw_%s.csv' % sid,
                raw_sha256=sha(D + 'raw_%s.csv' % sid), raw_rows=len(body), cut_file='cut_%s.csv' % sid,
                cut_sha256=sha(D + 'cut_%s.csv' % sid), cut_rows=len(keep), header=','.join(hdr),
                first_date=keep[0][0] if keep else None, last_date_cut=keep[-1][0] if keep else None,
                missing_value_rows_in_cut=sum(1 for v in vals if v in ('', '.')))

def parse_heading(h, year):
    """'February 1-2 Meeting - 1982' | 'June 30-July 1 Meeting - 1982' | 'October 21, 22, ... and 30  Conference Calls - 1987'
       | 'October 16 (unscheduled) - 2013'  -> (kind, [dates])"""
    h = re.sub(r'\s+', ' ', h).strip()
    body = re.sub(r'\s*-\s*%d$' % year, '', h)
    if 'Conference Call' in body: kind = 'conference_call'; body = re.sub(r'\s*Conference Calls?$', '', body)
    elif 'unscheduled' in body.lower(): kind = 'unscheduled'; body = re.sub(r'\s*\(unscheduled\)\s*(Meeting)?$', '', body, flags=re.I)
    elif body.endswith('Meeting'): kind = 'meeting'; body = re.sub(r'\s*Meeting$', '', body)
    else: raise ValueError('unknown heading: %r' % h)
    m = re.fullmatch(r'([A-Z][a-z]+) (\d+)-([A-Z][a-z]+) (\d+)', body)          # June 30-July 1
    if m:
        a = dt.date(year, MON[m[1]], int(m[2])); b = dt.date(year, MON[m[3]], int(m[4]))
        return kind, [a + dt.timedelta(days=k) for k in range((b - a).days + 1)]
    m = re.fullmatch(r'([A-Z][a-z]+)/([A-Z][a-z]+) (\d+)-(\d+)', body)        # April/May 30-1
    if m:
        a = dt.date(year, MON[m[1]], int(m[3])); b = dt.date(year, MON[m[2]], int(m[4]))
        return kind, [a + dt.timedelta(days=k) for k in range((b - a).days + 1)]
    m = re.fullmatch(r'([A-Z][a-z]+) (\d+)-(\d+)', body)                       # February 1-2
    if m:
        a = dt.date(year, MON[m[1]], int(m[2])); b = dt.date(year, MON[m[1]], int(m[3]))
        return kind, [a + dt.timedelta(days=k) for k in range((b - a).days + 1)]
    m = re.fullmatch(r'([A-Z][a-z]+) (\d+)', body)                             # May 18
    if m: return kind, [dt.date(year, MON[m[1]], int(m[2]))]
    m = re.fullmatch(r'([A-Z][a-z]+) ([\d, and]+)', body)                      # October 21, 22, ..., and 30
    if m: return kind, [dt.date(year, MON[m[1]], int(x)) for x in re.findall(r'\d+', m[2])]
    raise ValueError('unparsed heading: %r' % h)

def fomc():
    out, pages = [], []
    for y in range(1982, 2015):
        p = D + 'raw_fomc/fomchistorical%d.htm' % y; html = open(p, encoding='utf-8', errors='replace').read()
        hs = [re.sub(r'<[^>]+>', '', x) for x in re.findall(r'<h5[^>]*>(.*?)</h5>', html, flags=re.S)]
        hs = [x for x in hs if re.search(r'-\s*%d\s*$' % y, x.strip())]
        assert hs, y
        for h in hs:
            kind, days = parse_heading(h.strip(), y)
            for i, d in enumerate(days):
                out.append(dict(date=d.isoformat(), kind=kind, day_of_event=i + 1, n_days=len(days), heading=re.sub(r'\s+', ' ', h.strip())))
        pages.append(dict(year=y, file='raw_fomc/fomchistorical%d.htm' % y, sha256=sha(p), n_headings=len(hs),
                          source_url='https://www.federalreserve.gov/monetarypolicy/fomchistorical%d.htm' % y))
    with open(D + 'fomc_events_1982_2014.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['date', 'kind', 'day_of_event', 'n_days', 'heading']); w.writeheader(); w.writerows(out)
    return out, pages

if __name__ == '__main__':
    man = dict(lane='OV1-G', fetched_at_utc='2026-11-05T09:15Z',
               fetch_note='curl -A curl/8.0 via agent proxy, all HTTP 200. federalreserve.gov/robots.txt returns 404 (no restrictions). '
                          'FRED fredgraph.csv is the public CSV endpoint.', files={})
    for sid in ('DFEDTAR', 'DFEDTARU', 'DFEDTARL'): man['files'][sid] = cut_fred(sid)
    ev, pages = fomc()
    man['files']['FOMC_pages'] = dict(index_url='https://www.federalreserve.gov/monetarypolicy/fomc_historical_year.htm',
                                      index_file='raw_fomc/fomc_historical_year.htm', index_sha256=sha(D + 'raw_fomc/fomc_historical_year.htm'),
                                      pages=pages)
    man['files']['fomc_events'] = dict(file='fomc_events_1982_2014.csv', sha256=sha(D + 'fomc_events_1982_2014.csv'), rows=len(ev),
                                       derived_from='raw_fomc/fomchistorical1982..2014.htm (h5 headings)',
                                       kinds={k: sum(1 for e in ev if e['kind'] == k) for k in ('meeting', 'conference_call', 'unscheduled')})
    json.dump(man, open(D + 'MANIFEST.json', 'w'), indent=1)
    print(json.dumps({k: (v if k != 'FOMC_pages' else '%d pages' % len(v['pages'])) for k, v in man['files'].items()}, indent=1))
