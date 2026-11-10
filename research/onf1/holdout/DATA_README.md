# Full dataset through 2026 (holdout: design threads must not open this folder)
Built by holdout/code/build_data.py from the project price panel research/data/panel_f32.npz.xz (daily bars the project fetched on 2026-10-08), extended to 2026-11-09 by holdout/code/extend_us.py (us_ext.csv = us.csv plus the rows 2026-10-08..2026-11-09, same columns; inputs td_qqq_20260925_20261109.csv = QQQ daily bars from a second provider, av_y10_tail.csv and av_y3m_tail.csv = Treasury yields for those days), cut to <=2014 by holdout/code/cut_data.py (../../data_cut/).
In the project folder this directory is research/onf1/holdout/data/ (the paths below written as data/... refer to it). Python needs pandas, numpy, numba. Load: pd.read_csv(path, index_col=0, parse_dates=True)

## data/us.csv  (US trading days 1985-10-01..2026-10-07; QQQ columns start 1999-03-10)
ndx, ndx_open, ndx_high, ndx_low : ^NDX index (index OPEN is not a tradable print; do not use for overnight returns)
rf   : 13-week T-bill (^IRX close)/100, forward-filled (annual rate, decimal)
y10, y3m : ^TNX and ^IRX closes in percent (10y yield, 13w bill)
qqq_open, qqq_close, qqq_high, qqq_low : split-adjusted, NOT dividend-adjusted;  qqq_adj : split+dividend adjusted close
r_cc = qqq_adj_t/qqq_adj_{t-1}-1 (total return close->close);  r_id = qqq_close/qqq_open-1 (open->close);
r_on = (1+r_cc)/(1+r_id)-1 (prev close->open, ex-dividend drop removed, i.e. the dividend is credited to the night)
ndx_cc = ndx_t/ndx_{t-1}-1 (index close->close, price index)
caldays : calendar days since previous US trading day;  dt_on=(caldays-1+17.5/24)/365, dt_id=(6.5/24)/365
f_on = r_on - rf_{t-1}*dt_on ;  f_id = r_id - rf_{t-1}*dt_id   (futures-style excess returns: night ending at t's open, day t)
tqqq_adj, spy_open, spy_close, spy_adj, tlt_adj, ief_adj : extra series (NaN before listing)

## data/kr.csv  (KR trading days 2007-01-29..2026-10-08)
k_*   : 069500.KS KODEX 200 (spot ETF)   lev_* : 122630.KS KODEX Leverage (2x, from 2010-02-22)   inv_* : 114800.KS KODEX Inverse (-1x futures, from 2009-09-16)
*_n = open_t/close_{t-1}-1 (night ending at t's 09:00 open; NaN if either day's row is missing)   *_d = close_t/open_t-1
kr_n = (lev_n - inv_n)/3 : KOSPI200 futures night-return proxy (15:30 KST close -> next 09:00 open). With lev=2f+p and inv=-f+p the ETF opening premium p cancels.
kr_d = (lev_d - inv_d)/3 ; kr_spot_n = k_n ; usdkrw = KRW=X close (ffill)
29 KR rows between 2015 and 2024 have missing prices in the source (NaN); nights touching them are NaN.
Not available here: 252670.KS (inverse 2X), ^KS11/^KS200 index, actual KOSPI200 futures prices, KR data after 2026-10-08. US rows after 2026-10-07 exist only in us_ext.csv.

## Real-time order of events on calendar date D (UTC): KR open 00:00 -> KR close 06:30 -> US open 13:30/14:30 -> US close 20:00/21:00.
So the KR night that ENDS at D's 09:00 KST open was ENTERED at 15:30 KST on the previous KR day, i.e. BEFORE the US session of D-1 (US date) even opened.
