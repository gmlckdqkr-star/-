# NI1-A audit: verify that marcap ChangesRatio is the corporate-action-adjusted daily return on split dates.
# Compares raw Close/prevClose-1, ChangesRatio, and Close/(prevClose*Stocks_prev/Stocks)-1. Prints codes and numbers only.
import json, sys
import numpy as np, pandas as pd
MC = '/mnt/project-files/research/data/kr_stocks/marcap_raw/marcap-%d.parquet'
m = pd.concat([pd.read_parquet(MC % y, columns=['Code', 'Date', 'Close', 'Changes', 'ChangesRatio', 'Stocks', 'Market'])
               for y in range(2002, 2010)]).sort_values(['Code', 'Date'])
g = m.groupby('Code')
m['pc'] = g.Close.shift(1); m['ps'] = g.Stocks.shift(1); m['pd'] = g.Date.shift(1)
m['raw'] = m.Close / m.pc - 1
m['k'] = m.Stocks / m.ps
m['adj'] = m.Close / (m.pc / m.k) - 1
m['cr'] = m.ChangesRatio / 100
sp = m[(m.Market == 'KOSPI') & (m.k >= 1.9) & (m.raw < -0.4)].copy()   # splits / big stock dividends
print('n candidate split rows (KOSPI 2002-2009):', len(sp))
sp['err_cr_vs_adj'] = (sp.cr - sp.adj).abs()
print('median |ChangesRatio - share-count-adjusted return| on these rows:', float(sp.err_cr_vs_adj.median()))
print('share within 1pp:', float((sp.err_cr_vs_adj < 0.01).mean()))
ex = sp.sort_values('Date').iloc[[0, len(sp) // 2, -1]]
out = []
for _, r in ex.iterrows():
    out.append(dict(code=r.Code, date=str(r.Date.date()), split_factor=round(float(r.k), 3), raw_close_ret=round(float(r.raw), 4),
                    changes_ratio=round(float(r.cr), 4), sharecount_adj_ret=round(float(r.adj), 4)))
# also: the 2006-02-23 case cited in A_spec_choices
c = m[(m.Date == '2006-02-23') & (m.raw < -0.8) & (m.Market == 'KOSPI')]
for _, r in c.iterrows():
    out.append(dict(code=r.Code, date='2006-02-23', split_factor=round(float(r.k), 3), raw_close_ret=round(float(r.raw), 4),
                    changes_ratio=round(float(r.cr), 4), sharecount_adj_ret=round(float(r.adj), 4)))
# capital reductions (reverse splits): Stocks falls a lot and raw jumps
rs = m[(m.Market == 'KOSPI') & (m.k <= 0.55) & (m.raw > 0.8)]
print('n candidate reverse-split rows:', len(rs), 'median |cr-adj|', float((rs.cr - rs.adj).abs().median()) if len(rs) else None)
for _, r in rs.head(2).iterrows():
    out.append(dict(code=r.Code, date=str(r.Date.date()), split_factor=round(float(r.k), 3), raw_close_ret=round(float(r.raw), 4),
                    changes_ratio=round(float(r.cr), 4), sharecount_adj_ret=round(float(r.adj), 4), kind='reverse'))
print(json.dumps(out, indent=1))
json.dump(dict(n_split_rows=len(sp), median_abs_cr_minus_adj=float(sp.err_cr_vs_adj.median()),
               share_within_1pp=float((sp.err_cr_vs_adj < 0.01).mean()), n_reverse_rows=len(rs), examples=out),
          open(sys.argv[1], 'w'), indent=1)
