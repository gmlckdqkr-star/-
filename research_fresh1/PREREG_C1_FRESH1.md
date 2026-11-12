# FRESH1 Part C pre-registration, batch 1 (written before any measurement of these two candidates)

Source: blank-slate designers (no access to project memory, reports or registry). Rules below are the designers' own text,
fixed here before measuring. Data <= 2014-12-31 only. All rows are reported, pass or fail.

Exposure disclosure (mine, not the designers'): before writing this I had read registry rows T02 (volatility target closed),
X10 (continuous weights closed), X42 (US night premium futures, 0/12), S10 (KR small-stock overnight faded 2011-14) and the
ONF1 note that adding the Korean night leg lowered the uploaded strategies' returns in 2010-03..2014-12. Prior for both < 15%.

## C-KN  Korean night hold (designer "Korea structure", idea 2). Registry: not measured as an ETF strategy (nearest X42, S10, T16)
Rule P0 (no signal, no parameter): every KRX day buy KODEX 레버리지 (122630) in the closing auction, sell all in the next
opening auction, hold KRW cash (0% interest) during the day.
Data (already cut, no new download): /mnt/project-files/research/onf1/data_cut/kr_le2014.csv
  lev_n  = actual 2x ETF prev close -> open, 2010-02-23..2014-12-30 (PRIMARY, actual product)
  k_n,k_d = KODEX 200 prev close -> open and open -> close, 2007-01-30..2014-12-30; synthetic 2x night = 2*k_n - 0.64%/252
  k_n is not adjusted for ETF distributions, which lowers the night return on ex-dates (conservative, size unverified).
Cost per night (round trip), three levels, all reported:
  LOW 0.030% (commission 0.015% a side, auction fill, no slippage) / DESIGN 0.046% (designer's) / STD 0.26% (project standard 13bp a side)
Gates (designer's, year count scaled from 12 to the 8 years available). Judged at DESIGN cost:
  G1  mean(k_n) - mean(k_d), daily log returns 2007-2014, Newey-West (5 lags) t >= 3
  G2  night-only 2x net growth >= 8%/yr AND >= buy-and-hold of the same 2x series, on BOTH lev_n (2010-14) and synthetic (2007-14)
  G3  synthetic 2x night-only net return positive in >= 6 of 8 calendar years (2007..2014)
  Stress: result at 2x DESIGN cost (0.092%) must stay positive.
PASS = G1 and G2 and G3 and stress. A pass is only "candidate for one post-2014 check"; it cannot be put on the MS1 basis
(no pre-2007 data), so it can never be called a v1 beater from this test alone.
Reported, not selectable: P1 (hold the night only when KODEX 200 close is above its 200-day mean, 1-day lag),
P2 (3x on kr_n futures proxy at 0.02% per night), halves 2007-10 / 2011-14, mean night return by year.

## C-VT  Volatility-scaled trend ladder (designer "leveraged index timing", ideas 1-2 engine; "Korea structure" idea 1 uses the same body)
Registry: SAME family as T02 / X10. Run once as an independent replication because two blank designers converged on it.
Rule, decided at each close t on the index of the basis, data up to t only:
  T = mean of 3 flags: level > 200-day mean; 126-day return > 126-day cash return; 252-day return > 252-day cash return
  v_t = lam*v_(t-1) + (1-lam)*r_t^2, lam = 0.5^(1/20), seed = mean r^2 of first 60 days; sigma = sqrt(252*v)
  L* = T * min(CAP, 0.40 / sigma); 0 before 252 days of history. Trade only when |L* - held| >= band (or L* = 0).
  PRIMARY: CAP 3, target 0.40, half-life 20, band 0.25.
Measurement: locked MS1 engine (std.engine, MS1 terms, delay 2, step = fstep = band, no brake), the four price bases
  dev250_path (500 paths), real_ndx_86_14, real_spx_55_85, real_spx_70_85. v1 = locked s0.85 on the same paths.
Sensitivity (designer's declared grid): target .30/.40/.50 x half-life 10/20/40 x band .15/.25/.35 = 27 cells; plus CAP 2 at primary.
PASS = all of:
  (i)   paired block bootstrap (250-day blocks, 2000 draws) of daily log-return difference vs v1 on S&P 1955-85 + NDX 1986-2014: P(d>0) >= 90%
  (ii)  path median > v1 path median (16.16%)
  (iii) share of paths with a -80% drawdown <= v1's (73.2%)
  (iv)  with delay 7 the path edge over v1 keeps at least half
  (v)   at least 18 of 27 grid cells have path median > v1
Also reported: the project rule (real NDX > 31.08% AND path > 16.16%).
