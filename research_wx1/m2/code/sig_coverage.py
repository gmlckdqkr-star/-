"""Signal coverage among eligible S&P 500 members (no returns read). Writes coverage.csv"""
import numpy as np, pandas as pd, sys
z = np.load(sys.argv[1])
SR, elig = z['SR'], z['elig']; cols = z['cols']; year = z['year']
dd = pd.to_datetime(z['ddate'].astype('datetime64[D]'))
yr = dd.year.values
ne = elig.sum(1)
rows = []
for s, c in enumerate(cols):
    have = np.isfinite(SR[:, :, s]).sum(1) / ne
    us = yr >= year[s] + 1
    w = us & (yr >= 1986)
    disc = us & (yr >= 1986) & (yr <= 1999)
    conf = us & (yr >= 2000)
    rows.append(dict(sig=c, econ=z['econ'][s], data=z['datac'][s], pub=int(year[s]), sign=z['sign'][s], pq=z['pq'][s],
                     usable_from=int(year[s]) + 1, cov_usable=float(have[w].mean()) if w.any() else np.nan,
                     cov_disc=float(have[disc].mean()) if disc.any() else np.nan, cov_conf=float(have[conf].mean()) if conf.any() else np.nan,
                     cov_all_8614=float(have[(yr >= 1986)].mean()), first_cov=str(dd[np.argmax(have > 0.2)].date()) if (have > 0.2).any() else None,
                     last_cov=str(dd[len(have) - 1 - np.argmax(have[::-1] > 0.2)].date()) if (have > 0.2).any() else None))
df = pd.DataFrame(rows); df.to_csv(sys.argv[2], index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
print(df.sort_values('cov_usable').head(40).to_string())
print('usable in discovery (pub<=1998):', int((df.pub <= 1998).sum()), ' usable by 2014 (pub<=2013):', int((df.pub <= 2013).sum()))
