# FRESH1 amendment A1 (written 2026-11-11 before any H1 number exists)

Reason: after sealing DESIGN_FRESH1.md I read the locked measurement standard MS1
(research/measure_std) and the closed-lane registry. Two things follow.

1. Registry mapping of my own H1: it falls in closed families E01 / E07 / E11 / S25
   (sector and 3x-product rotation). I still run it exactly as sealed, once, because
   it is my pre-registration and it is a different code path and data source
   (Ken French industries 1926-2014). It is an independent replication, not a new lane.

2. Same-basis rules for comparing with v1 (v1 numbers are MS1 basis):
   - Engine terms = MS1: delay 2 days, cost 0.3% per side, 3x fund = 3r - 2rf - 2.45%/yr,
     cash = max(rf - 2pp, 0) x (1 - 15.4%), tax 22% of yearly net realized gain above
     0.25 (2.5M KRW on a 10M KRW start), year-end harvest as in MS1, final liquidation tax.
     This is the "MS1 basis" and is used for every comparison with v1.
   - My sealed harsher terms (cost 0.4%, 3x drag 2.95%/yr, no deduction, no harvest)
     are reported as the "sealed basis" for the phenomenon test, with delay 2 days
     (the harsher of the two, as the sealed text requires).
   - Simulated paths: the same 500 thirty-year paths as MS1 dev250_path, by reusing the
     MS1 block index matrix (same calendar days for v1 and H1, so differences are paired).
     On simulated paths there are no calendar months: signals are taken every 21 trading
     days. On real history the signal is the last trading day of each calendar month.
   - Dividends. MS1 measures v1 on price indices (no dividends, conservative). French
     daily industry returns include dividends. For the comparison with v1 only, I use a
     price basis: each industry's monthly dividend return (French monthly file minus the
     "ex dividends" monthly file) is removed evenly from the daily returns of that month,
     and the market engine is the S&P 500 price index from the MS1 calendar.
     The phenomenon test (H1 vs its own benchmarks B0, B1) uses total returns as sealed
     and also reports the price basis.
   - Engine parity check before use: one asset, always 100% in the 3x fund on the MS1
     real NDX path must reproduce the MS1 "3x hold" value 0.0387128 (real 1986-2014).

No pass line is changed. Fair gate (i) is computed on real <=2014 history as sealed.
