# AQR Time Series Momentum factors (monthly), public dataset — cut at 2014-12

- Source page: https://www.aqr.com/Insights/Datasets/Time-Series-Momentum-Factors-Monthly
- File: https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Time-Series-Momentum-Factors-Monthly.xlsx (downloaded 2026-11-18, no login)
- raw/Time-Series-Momentum-Factors-Monthly.xlsx sha256 33470930e2269c0d97be4732ec2d9c27ddbc69ac8133b059a263e27400263eeb
  The raw file CONTAINS rows after 2014. Never print, compute or save them. Read only through the cut file below.
- tsmom_monthly_le2014.csv sha256 c509307bc752101236f945778cf9501e797bb813a9f905b14c274b053c902e41
  rows 1985-01 .. 2014-12 (360), columns date, TSMOM, CM, EQ, FI, FX (monthly excess returns, decimal). Rows after 2014-12 dropped at load.
- Nature: hypothetical factor of Moskowitz, Ooi, Pedersen (2012), 58 futures/forwards, GROSS of fees and transaction costs. Not a fund record.
- Use in DF7: calibration reference only (1986-2014 Sharpe 1.28 vs DF7 own proxy 0.78; monthly corr 0.57). Gates use the DF7 proxy at 50% (PRIM) / 25% (Q).
- Actual CTA fund indices were not obtainable as public files: BarclayHedge returned 403; SG CTA index pages are behind bot protection (not bypassed).
