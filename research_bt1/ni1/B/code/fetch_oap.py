# NI1-B step 1: fetch permno, yyyymm, AnnouncementReturn from OpenSourceAP Predictors.parquet (CC-BY 4.0)
# via HTTP range reads; keep only yyyymm <= 201412. No key needed, generic User-Agent, robots.txt allows /.
import io, sys, subprocess, pyarrow.parquet as pq, pyarrow.compute as pc, pyarrow as pa
U = "https://huggingface.co/datasets/OpenSourceAP/CrossSection/resolve/main/Firm%20Level%20Characteristics/Predictors.parquet"
UA = "Mozilla/5.0 (compatible; research-client)"
out_path = sys.argv[1]
# size from HEAD
h = subprocess.run(["curl", "-sSIL", "-A", UA, "--max-time", "60", U], capture_output=True, text=True).stdout
S = int([l for l in h.lower().splitlines() if l.startswith("content-length")][-1].split(":")[1])
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
        for _ in range(4):
            out = subprocess.run(["curl", "-sS", "-L", "-A", UA, "--max-time", "120", "-r", f"{s.p}-{s.p+n-1}", U], capture_output=True).stdout
            if len(out) == n: break
        if len(out) != n: raise IOError("short read")
        b[:len(out)] = out; s.p += len(out); fetched[0] += len(out); return len(out)
f = pq.ParquetFile(io.BufferedReader(RF(), buffer_size=1 << 20))
parts = []
for g in range(f.metadata.num_row_groups):
    t = f.read_row_group(g, columns=['permno', 'yyyymm', 'AnnouncementReturn'])
    t = t.filter(pc.less_equal(t['yyyymm'], 201412))   # nothing after 2014-12 is kept
    parts.append(t)
T = pa.concat_tables(parts)
pq.write_table(T, out_path)
print('file size', S, 'bytes fetched', fetched[0], 'rows kept (<=201412)', T.num_rows,
      'max yyyymm', pc.max(T['yyyymm']).as_py(), 'nonnull AR', T.num_rows - T['AnnouncementReturn'].null_count)
