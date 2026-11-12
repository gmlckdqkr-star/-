"""AT2 data: Yahoo daily index closes (request ends 2014-12-31) + FRED OECD monthly 3m / 10y rates (cut at 2014-12-31 before saving)."""
import json, subprocess, datetime as dt, pandas as pd, io, hashlib
DD = '/mnt/project-files/research/at2/data/'; END = pd.Timestamp('2014-12-31')
MK = {'UK': ('^FTSE', 'GB'), 'CA': ('^GSPTSE', 'CA'), 'AU': ('^AORD', 'AU'), 'DE': ('^GDAXI', 'DE'), 'FR': ('^FCHI', 'FR'), 'CH': ('^SSMI', 'CH')}
def get(url, ua=True):
    a = ['curl', '-s', '--max-time', '40'] + (['-A', 'Mozilla/5.0'] if ua else []) + [url]
    return subprocess.run(a, capture_output=True).stdout
src = {}
for m, (sym, cc) in MK.items():
    j = json.loads(get('https://query1.finance.yahoo.com/v8/finance/chart/%s?period1=0&period2=1420070400&interval=1d' % sym.replace('^', '%5E')))['chart']['result'][0]
    idx = pd.to_datetime([dt.datetime.fromtimestamp(t, dt.UTC).date() for t in j['timestamp']])
    s = pd.Series(j['indicators']['quote'][0]['close'], index=idx, name='close').dropna()
    s = s[(s.index <= END) & (s > 0)]; s = s[~s.index.duplicated()]
    s.to_csv(DD + '%s_index_le2014.csv' % m, index_label='date')
    for k in ('IR3TIB01', 'IRLTLT01'):
        sid = '%s%sM156N' % (k, cc)
        f = pd.read_csv(io.BytesIO(get('https://fred.stlouisfed.org/graph/fredgraph.csv?id=' + sid, ua=False)), parse_dates=['observation_date'])
        f = f[f.observation_date <= END]; f.to_csv(DD + '%s_le2014.csv' % sid, index=False)
        src[sid] = dict(first=str(f.observation_date.iloc[0].date()), n=len(f))
    src[m] = dict(symbol=sym, first=str(s.index[0].date()), last=str(s.index[-1].date()), n=len(s))
    print(m, src[m], src['IR3TIB01%sM156N' % cc]['first'], src['IRLTLT01%sM156N' % cc]['first'], flush=True)
json.dump(src, open(DD + 'SOURCES.json', 'w'), indent=1)
