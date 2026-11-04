"""List and download original 13F-HR filings (filed <= 2014-12-31) for the PRECOMMIT_GT2 giants.
User-Agent comes from env SEC_UA only (never stored)."""
import os, json, time, urllib.request
UA = os.environ['SEC_UA']; OUT = os.environ.get('GT2_RAW', '/tmp/gt2raw')
CIKS = {'BRK': [1067983], 'SOROS': [1029160], 'TIGER': [1011440, 1027451], 'RUANE': [85624, 728014, 1720792],
        'SOUTHEASTERN': [807985], 'TWEEDY': [732905, 100314], 'DAVIS': [1036325], 'LMCM': [710134],
        'BAUPOST': [1061768, 1054420], 'APPALOOSA': [1006438], 'MAVERICK': [934639, 928617], 'ICAHN': [921669, 813762]}
def get(url):
    for k in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Encoding': 'identity'})
            return urllib.request.urlopen(req, timeout=60).read()
        except Exception as e:
            time.sleep(2 ** k)
    return None
def filings(cik):
    out = []; d = json.loads(get(f'https://data.sec.gov/submissions/CIK{cik:010d}.json')); time.sleep(.15)
    blocks = [d['filings']['recent']] + [json.loads(get('https://data.sec.gov/submissions/' + f['name'])) for f in d['filings'].get('files', [])]
    for r in blocks:
        for i in range(len(r['form'])):
            if r['form'][i] == '13F-HR' and r['filingDate'][i] <= '2014-12-31':
                out.append((r['filingDate'][i], r['accessionNumber'][i], r.get('reportDate', [''] * len(r['form']))[i]))
    return sorted(set(out))
os.makedirs(OUT, exist_ok=True); index = {}
for g, cl in CIKS.items():
    for cik in cl:
        try: fl = filings(cik)
        except Exception as e: print(g, cik, 'ERR', e); continue
        print(g, cik, len(fl), fl[:1], fl[-1:], flush=True)
        for fd, acc, rd in fl:
            fn = f'{OUT}/{g}_{cik}_{fd}_{acc}.txt'
            if not os.path.exists(fn):
                b = get(f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace("-", "")}/{acc}.txt'); time.sleep(.15)
                if b: open(fn, 'wb').write(b)
            index.setdefault(g, []).append(dict(cik=cik, filed=fd, acc=acc, period=rd, file=fn))
json.dump(index, open(f'{OUT}/index.json', 'w'), indent=0)
