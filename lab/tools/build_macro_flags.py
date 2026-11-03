"""Build lab/lab/macro_flags_le2014.csv.gz: the 8 MS1 macro warning flags (ov.flags_hist) on their historical dates.

Run once with an interpreter that can import the MS1 code (numba, scipy, xlrd), e.g. the lab-managed venv:
    ~/.cache/lab/ms1-venv/bin/python -B tools/build_macro_flags.py
Two calendars, exactly as MS1 builds them (research/measure_std/std.py contexts()):
  ndx = jp.calendar('1984-01-03', '2014-12-31')  (real_ndx_86_14, dev250 source)
  spx = jp.calendar('1928-01-03', '1985-12-31')  (real_spx_55_85 / real_spx_70_85)
Both are written (column `cal`); lab.data.macro_flags uses spx rows before 1986-01-02 and ndx rows from then on
(the ndx calendar's first year has rolling-window warm-up, the spx calendar is fully warmed by 1984).
Seal: every row is dated <= 2014-12-31 (checked). The flags are 0/1 values of public yield / credit-spread series
known at the close of each date (crash_overlay/mkt.py conventions); no price or return is stored."""
import gzip, io, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std, jp, ov      # noqa: E402  (std puts the MS1 code folders on sys.path)
import pandas as pd     # noqa: E402

SEAL = pd.Timestamp('2014-12-31')
KEYS = ('inv', 'inv2', 'shock', 'shock10', 'shock6m', 'shock6m75', 'shock3m', 'csj')
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lab', 'macro_flags_le2014.csv.gz')


def main():
    parts = []
    for cal, a, b, s in (('spx', '1928-01-03', '1985-12-31', 'SPX'), ('ndx', '1984-01-03', '2014-12-31', 'NDX')):
        R, M = jp.calendar(a, b); X = jp.mkX(R, M, s); F = ov.flags_hist(X)
        assert X.index[-1] <= SEAL
        D = F[list(KEYS)].astype(int)
        D.insert(0, 'cal', cal)
        D.index.name = 'date'
        parts.append(D)
    T = pd.concat(parts)
    assert T.index.max() <= SEAL
    txt = T.to_csv(date_format='%Y-%m-%d', lineterminator='\n')
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', mtime=0, filename='') as g:     # deterministic bytes
        g.write(txt.encode())
    with open(OUT, 'wb') as fh:
        fh.write(buf.getvalue())
    print(OUT, len(T), 'rows', len(buf.getvalue()), 'bytes', 'last', T.index.max().date())


if __name__ == '__main__':
    main()
