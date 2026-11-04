# raw data (not committed)
Raw downloads live in the project folder research/etf_ext/data/raw/ and are cut at 2014-12-31 on load (etxdata.py).
- kf/: Ken French data library daily zips (6_Portfolios_ME_OP_2x3_daily, 6_Portfolios_ME_Prior_12_2_Daily, Developed_ex_US / Europe / Japan 3 factors daily). Checksums in kf/SHA256SUMS.txt.
- fred/: FRED monthly GS20 and GS10 (Board of Governors H.15), used only to extend Treasury proxies to 1953-61 for the S&P 1955-85 check. Checksums in fred/SHA256SUMS.txt.
