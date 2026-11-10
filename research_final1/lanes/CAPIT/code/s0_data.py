"""CAPIT s0: cut the RNG1 Nasdaq volume series (panel `_NDX`) to <= 2014-12-31 and save it in the lane data/ folder.
No outcome is computed here. Rows after 2014 are dropped by the timestamp key before any value is looked at.
Source: /mnt/project-files/research/data/panel_f32.npz.xz key `_NDX|ts`, `_NDX|v` (float32 [open, high, low, close, adjclose, volume]);
same file / key / column 5 as research/rng1/code/rng.py panel('_NDX')."""
import io, json, lzma, hashlib, numpy as np, pandas as pd
SRC = '/mnt/project-files/research/data/panel_f32.npz.xz'
LANE = '/mnt/project-files/research/final1/lanes/CAPIT/'
END = pd.Timestamp('2014-12-31')
raw = open(SRC, 'rb').read(); sha_src = hashlib.sha256(raw).hexdigest()
assert sha_src == 'fa2c35b295642ddf27924e1125a50c823ea464a0f6b47e54c0b3b254fd35242c', sha_src
z = np.load(io.BytesIO(lzma.decompress(raw)), allow_pickle=True)
t = pd.to_datetime(z['_NDX|ts'], unit='s').normalize()
n = int((t <= END).sum()); assert (t[:n] <= END).all() and t[:n].is_monotonic_increasing
v = z['_NDX|v'][:n].astype(float); t = t[:n]                      # cut BEFORE any value is used
df = pd.DataFrame(v[:, [3, 5]], columns=['close', 'volume'], index=t); df.index.name = 'date'
df = df[~df.index.duplicated()]
out = LANE + 'data/ndx_close_volume_le2014.csv'
df.to_csv(out, float_format='%.6g')
sha_out = hashlib.sha256(open(out, 'rb').read()).hexdigest()
ok = np.isfinite(df.volume) & (df.volume > 0)
by = pd.DataFrame({'rows': df.volume.groupby(df.index.year).size(), 'valid': ok.groupby(df.index.year).sum(),
                   'median_vol': df.volume.where(ok).groupby(df.index.year).median()})
print(by.to_string())
first_valid = str(df.index[ok.values][0].date()) if ok.any() else None
man = dict(lane='CAPIT', written='2026-11-10', files=[dict(
    name='ndx_close_volume_le2014.csv', sha256=sha_out, rows=int(len(df)), first=str(df.index[0].date()), last=str(df.index[-1].date()),
    columns=['date', 'close', 'volume'], label='ACTUAL (vendor index bars; volume as published by the vendor for ^NDX)',
    source_file=SRC, source_sha256=sha_src, source_key='_NDX|ts, _NDX|v columns 3 (close) and 5 (volume)',
    source_origin='Yahoo chart v8 daily bars for ^NDX, fetched 2026-10-08 from the PC (see research/data/EXT_MANIFEST.json format note); '
                  'no network request was made by this lane',
    cut='rows with date <= 2014-12-31 only; later rows dropped by timestamp before use',
    volume_valid_rows=int(ok.sum()), volume_first_valid=first_valid, volume_invalid_rows=int((~ok).sum()))])
json.dump(man, open(LANE + 'data/MANIFEST.json', 'w'), indent=1)
print('saved', out, sha_out, 'rows', len(df), 'first valid volume', first_valid, 'invalid rows', int((~ok).sum()))
