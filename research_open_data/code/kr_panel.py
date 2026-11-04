import pandas as pd, numpy as np, glob
fs = sorted(glob.glob('/mnt/project-files/research/data/kr_stocks/marcap_raw/marcap-*.parquet'))
D = pd.concat([pd.read_parquet(f, columns=['Code', 'Date', 'ChangesRatio', 'Close', 'Amount', 'Volume', 'Market']) for f in fs])
D = D[(D.Date <= '2014-12-31')]; D['Code'] = D.Code.astype(str).str.zfill(6)
dates = np.sort(D.Date.unique()); codes = np.sort(D.Code.unique())
di = pd.Index(dates).get_indexer(D.Date); ci = pd.Index(codes).get_indexer(D.Code)
def mat(col, fill=np.nan):
    M = np.full((len(dates), len(codes)), fill, np.float32); M[di, ci] = D[col].values.astype(np.float32); return M
np.savez_compressed('/tmp/kr_panel.npz', dates=dates.astype('datetime64[D]'), codes=codes, cr=mat('ChangesRatio'), close=mat('Close'), amt=mat('Amount'), vol=mat('Volume'))
print(len(dates), len(codes), str(dates[0])[:10], str(dates[-1])[:10])
