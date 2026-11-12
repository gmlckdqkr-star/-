"""GX1 data: Yahoo daily index closes (request period2 = 2015-01-01 00:00 UTC, so no post-2014 row is ever received)
+ FRED OECD monthly 3m interbank / long-term rates (cut at 2014-12-31 before saving). Polite: >= 1.2 s between requests."""
import json, subprocess, datetime as dt, pandas as pd, io, time, sys
DD = '/mnt/project-files/research/gx1/data/'; END = pd.Timestamp('2014-12-31')
MK = {  # market: (yahoo symbol, OECD country code or None)
 'HK': ('^HSI', None), 'TW': ('^TWII', None), 'KR': ('^KS11', 'KR'), 'SG': ('^STI', None), 'IN': ('^BSESN', 'IN'),
 'ID': ('^JKSE', 'ID'), 'MY': ('^KLSE', None), 'TH': ('^SET.BK', None), 'PH': ('PSEI.PS', None), 'CN': ('000001.SS', 'CN'),
 'NZ': ('^NZ50', 'NZ'), 'JP': ('^N225', 'JP'), 'NL': ('^AEX', 'NL'), 'ES': ('^IBEX', 'ES'), 'IT': ('FTSEMIB.MI', 'IT'),
 'BE': ('^BFX', 'BE'), 'AT': ('^ATX', 'AT'), 'SE': ('^OMX', 'SE'), 'NO': ('^OSEAX', 'NO'), 'DK': ('^OMXC20.CO', 'DK'),
 'IE': ('^ISEQ', 'IE'), 'PT': ('PSI20.LS', 'PT'), 'GR': ('GD.AT', 'GR'), 'TR': ('XU100.IS', 'TR'), 'RU': ('IMOEX.ME', 'RU'),
 'MX': ('^MXX', 'MX'), 'BR': ('^BVSP', 'BR'), 'AR': ('^MERV', None), 'CL': ('^IPSA', 'CL'), 'IL': ('^TA125.TA', 'IL'),
 'ZA': ('^J203.JO', 'ZA'), 'EG': ('^CASE30', None)}
def get(url, ua=True):
    a = ['curl', '-s', '--http1.1', '--max-time', '40'] + (['-A', 'Mozilla/5.0'] if ua else []) + [url]
    time.sleep(1.2); return subprocess.run(a, capture_output=True).stdout
src = {}
for m, (sym, cc) in MK.items():
    rec = dict(symbol=sym)
    try:
        j = json.loads(get('https://query1.finance.yahoo.com/v8/finance/chart/%s?period1=0&period2=1420070400&interval=1d' % sym.replace('^', '%5E')))['chart']['result'][0]
        idx = pd.to_datetime([dt.datetime.fromtimestamp(t, dt.UTC).date() for t in j['timestamp']])
        s = pd.Series(j['indicators']['quote'][0]['close'], index=idx, name='close').dropna()
        s = s[(s.index <= END) & (s > 0)]; s = s[~s.index.duplicated()]
        s.to_csv(DD + '%s_index_le2014.csv' % m, index_label='date')
        rec.update(first=str(s.index[0].date()), last=str(s.index[-1].date()), n=len(s), tz=j['meta'].get('exchangeTimezoneName'))
    except Exception as e:
        rec['error'] = repr(e)[:200]
    if cc:
        for k in ('IR3TIB01', 'IRLTLT01'):
            sid = '%s%sM156N' % (k, cc)
            try:
                f = pd.read_csv(io.BytesIO(get('https://fred.stlouisfed.org/graph/fredgraph.csv?id=' + sid, ua=False)), parse_dates=['observation_date'])
                f = f[f.observation_date <= END].dropna(); f.to_csv(DD + '%s_le2014.csv' % sid, index=False)
                rec[k] = dict(first=str(f.observation_date.iloc[0].date()), n=len(f))
            except Exception as e:
                rec[k] = dict(error=repr(e)[:120])
    src[m] = rec; print(m, rec, flush=True)
json.dump(src, open(DD + 'SOURCES.json', 'w'), indent=1)
