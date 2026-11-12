"""GX1 data v2: re-fetch every index with LOCAL exchange dates (timestamp + meta.gmtoffset), request period2 = 2015-01-01 UTC.
Replaces the UTC-dated files of gx1data.py (AU/NZ sessions were stamped on the previous UTC day). Also copies the six AT2 markets
into gx1/data with local dates. Rates are unchanged (gx1data.py, AT2 data)."""
import json, subprocess, datetime as dt, pandas as pd, time
DD = '/mnt/project-files/research/gx1/data/'; END = pd.Timestamp('2014-12-31')
SYM = {'HK': '^HSI', 'TW': '^TWII', 'KR': '^KS11', 'SG': '^STI', 'IN': '^BSESN', 'ID': '^JKSE', 'MY': '^KLSE', 'CN': '000001.SS',
       'NZ': '^NZ50', 'JP': '^N225', 'NL': '^AEX', 'ES': '^IBEX', 'IT': 'FTSEMIB.MI', 'BE': '^BFX', 'AT': '^ATX', 'SE': '^OMX',
       'IE': '^ISEQ', 'PT': 'PSI20.LS', 'GR': 'GD.AT', 'TR': 'XU100.IS', 'MX': '^MXX', 'BR': '^BVSP', 'IL': '^TA125.TA', 'ZA': '^J200.JO',
       'UK': '^FTSE', 'CA': '^GSPTSE', 'AU': '^AORD', 'DE': '^GDAXI', 'FR': '^FCHI', 'CH': '^SSMI'}
meta = {}
for m, sym in SYM.items():
    time.sleep(1.2)
    out = subprocess.run(['curl', '-s', '--http1.1', '--max-time', '40', '-A', 'Mozilla/5.0',
                          'https://query1.finance.yahoo.com/v8/finance/chart/%s?period1=0&period2=1420070400&interval=1d' % sym.replace('^', '%5E')], capture_output=True).stdout
    j = json.loads(out)['chart']['result'][0]; off = j['meta'].get('gmtoffset', 0); tz = j['meta'].get('exchangeTimezoneName')
    # local session date: shift by the exchange's CURRENT offset is wrong across DST; use the tz database instead
    loc = pd.to_datetime(j['timestamp'], unit='s', utc=True).tz_convert(tz)
    idx = pd.DatetimeIndex(loc.date)
    s = pd.Series(j['indicators']['quote'][0]['close'], index=idx, name='close').dropna()
    s = s[(s.index <= END) & (s > 0)]; s = s[~s.index.duplicated(keep='last')]
    s.to_csv(DD + '%s_index_le2014.csv' % m, index_label='date')
    meta[m] = dict(symbol=sym, tz=tz, first=str(s.index[0].date()), last=str(s.index[-1].date()), n=len(s),
                   weekend=int((s.index.dayofweek >= 5).sum()))
    print(m, meta[m], flush=True)
S = json.load(open(DD + 'SOURCES.json'))
for m, v in meta.items(): S.setdefault(m, {}).update(v); S[m]['dates'] = 'local exchange date (gx1data_local.py)'
json.dump(S, open(DD + 'SOURCES.json', 'w'), indent=1)
