# NI1-B audit: spot-check the implementer's OAP subset against the public file (2 row groups, 3 columns, range reads).
# Usage: python -I audit_oap_spot.py <local_subset_parquet> <out_json>
import sys, json, subprocess, io
import pyarrow.parquet as pq, pandas as pd, numpy as np
U = "https://huggingface.co/datasets/OpenSourceAP/CrossSection/resolve/main/Firm%20Level%20Characteristics/Predictors.parquet"
UA = "research-client"
h = subprocess.run(["curl", "-sSIL", "-A", UA, "--max-time", "60", U], capture_output=True, text=True).stdout
S = int([l for l in h.lower().splitlines() if l.startswith("content-length")][-1].split(":")[1])
got = [0]
class RF(io.RawIOBase):
    p = 0
    def seekable(s): return True
    def readable(s): return True
    def tell(s): return s.p
    def seek(s, o, w=0): s.p = o if w == 0 else (s.p + o if w == 1 else S + o); return s.p
    def readinto(s, b):
        n = min(len(b), S - s.p)
        if n <= 0: return 0
        out = subprocess.run(["curl", "-sS", "-L", "-A", UA, "--max-time", "120", "-r", f"{s.p}-{s.p+n-1}", U], capture_output=True).stdout
        assert len(out) == n
        b[:n] = out; s.p += n; got[0] += n; return n
f = pq.ParquetFile(io.BufferedReader(RF(), buffer_size=1 << 16))
loc = pd.read_parquet(sys.argv[1])
res = dict(remote_rows=f.metadata.num_row_groups and f.metadata.num_rows, row_groups=f.metadata.num_row_groups, checks=[])
for g in [7, 40]:
    t = f.read_row_group(g, columns=['permno', 'yyyymm', 'AnnouncementReturn']).to_pandas()
    t = t[t.yyyymm <= 201412]
    m = t.merge(loc, on=['permno', 'yyyymm'], how='left', suffixes=('_r', '_l'), indicator=True)
    same = ((m.AnnouncementReturn_r == m.AnnouncementReturn_l) | (m.AnnouncementReturn_r.isna() & m.AnnouncementReturn_l.isna()))
    res['checks'].append(dict(group=g, rows=len(t), missing_in_local=int((m._merge != 'both').sum()), value_mismatch=int((~same).sum())))
res['bytes_fetched'] = got[0]
json.dump(res, open(sys.argv[2], 'w'), indent=1); print(res)
