import lzma, io, numpy as np, pandas as pd
END = pd.Timestamp('2014-12-31')
d = np.load(io.BytesIO(lzma.open('/mnt/project-files/research/data/panel_f32.npz.xz').read()), allow_pickle=True)
def ser(t):
    ts = pd.to_datetime(d[t + '|ts'], unit='s').normalize(); v = d[t + '|v'].astype(float)
    m = ts <= END; df = pd.DataFrame(v[m], index=ts[m]); df = df[~df.index.duplicated()]
    return df
P = {t: ser(t) for t in ('QQQ', 'QLD', 'TQQQ', '_NDX', '_IRX', 'SPY', 'SSO', 'UPRO')}
for t, df in P.items(): print(t, df.shape, str(df.index.min())[:10], str(df.index.max())[:10], df.iloc[0].round(4).tolist())
np.save('/tmp/df5v/audit/dummy.npy', np.zeros(1))
import pickle; pickle.dump(P, open('/tmp/df5v/audit/lev_le2014.pkl', 'wb'))
