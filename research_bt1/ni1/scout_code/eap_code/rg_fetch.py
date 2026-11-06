# Read 3 columns of selected row groups from the remote parquet via HTTP range requests (small sample).
import io, sys, subprocess, pyarrow.parquet as pq, numpy as np
U = "https://huggingface.co/datasets/OpenSourceAP/CrossSection/resolve/main/Firm%20Level%20Characteristics/Predictors.parquet"
S = 1934347395; UA = "Mozilla/5.0 (compatible; research-client)"
fetched = [0]
class RF(io.RawIOBase):
    def __init__(s): s.p = 0
    def seekable(s): return True
    def readable(s): return True
    def tell(s): return s.p
    def seek(s, o, w=0):
        s.p = o if w == 0 else (s.p + o if w == 1 else S + o); return s.p
    def readinto(s, b):
        n = min(len(b), S - s.p)
        if n <= 0: return 0
        out = subprocess.run(["curl", "-sS", "-L", "-A", UA, "--max-time", "60", "-r", f"{s.p}-{s.p+n-1}", U], capture_output=True).stdout
        b[:len(out)] = out; s.p += len(out); fetched[0] += len(out); return len(out)
f = pq.ParquetFile(io.BufferedReader(RF(), buffer_size=1 << 20))
groups = [int(x) for x in sys.argv[1].split(',')]
t = f.read_row_groups(groups, columns=['permno', 'yyyymm', 'AnnouncementReturn'])
df = t.to_pandas(); print('bytes fetched', fetched[0], 'rows', len(df))
df.to_csv(sys.argv[2], index=False)
