# Check "tails": execution delay, synthetic gap, exposure creep (data <= 2014-12-31; gap rows are NON-ACTUAL stress)
Code: tails.py (stages delay/creep/gap/scan), tails_resel.py (re-selection), tails_merge.py -> result.json. The recording engine is the dfe.run1 source verbatim plus a weight record, and its output matches dfe.run exactly (max abs diff 0). The delay-2 rows reproduce grid.json exactly.
1. Delay (WD; pick in tier?): T25 d1 -23.93 / d2 -24.06 / d3 -24.30 IN; d4 -25.50, d5 -26.24 OUT (SPX29 binds). T30 d1 -28.80 / d3 -29.91 IN; d4 -30.82, d5 -33.31 OUT (path p10).
   T40 (DF2 M2 L1.5) d1 -38.08 / d3 -39.86 IN; d4 -40.53, d5 -42.67 OUT. Path median CAGR barely moves (T25 8.97 -> 8.57..8.97; T40 13.24 -> 13.49..13.84).
   T40alt (DF1 v1|s0.3|L1.0|K2|RB) stays in tier at every delay (d5 WD -38.71).
2. Gap (one random scoring day per dev250 path is overwritten with an NDX return of -20% / -25%, seed 23; seed 2026 within 0.3pp):
   T25 path 8.97 -> 8.59 / 8.41; MDD p10 -24.06 -> -27.48 / -29.78; P(MDD < -25%) 7.4% -> 18.2% / 29.0%. OUT.
   T30 10.18 -> 9.66 / 9.37; p10 -29.97 -> -32.89 / -34.50; P(< -30%) 9.8% -> 19.8% / 33.6%. OUT.
   T40 13.24 -> 12.09 / 11.57; p10 -39.26 -> -44.23 / -50.09; P(< -40%) 7.8% -> 29.8% / 52.8%. OUT. T40alt: p10 -36.29 / -38.64, IN.
   QQQ 1x: 11.72 -> 10.96 / 10.74, p10 -85.0 -> -85.6 / -85.9. v1: 15.18 -> 12.62 / 11.12, p10 -87.6 -> -88.1 / -88.6.
   Gap at a random date on the REAL bases (every 10th day; 732 NDX dates, 645 SPX29 dates): P(MDD breaches tier) is T25 7.4/19.3% (NDX) and 11.5/27.1% (SPX29), T30 9.6/26.9% and 2.3/8.7%, T40 28.0/57.4% and 23.3/41.1%, T40alt 0.4/1.5% and 0/0.8%.
   Actual 1987-10-19 (NDX -15.08% in the data) overwritten with -20% or -25%: no pick's real NDX MDD changes, because the picks held only 0.31 / 0.31 / 0.45 exposure that day.
3. Exposure creep for T40 (M2, nominal Lmax 1.5): the effective exposure 3 x TQQQ weight is above 1.5 on 26.3% of path-days (max 2.56; 88.8% of paths exceed 2.0 at some point). It is above 1.5 on 39.7% of real NDX days (max 2.15 on 1995-07-17) and on 26.3% of real SPX29 days (max 2.41; above 2.0 on 9.3% of days). The worst real-NDX gap date (1995-07-17) found the pick at 2.13x exposure and gave an MDD of -53.0% / -59.8%. The L1.0 picks cannot exceed 1.0.
4. Re-selection with the stress added to WD (diagnostic only; DF2 gates not re-run):
   Gap-20: T25 -> v1|s0.1|L1.0|K1|RT at 6.12% on the gap paths (6.57% base). T30 -> DF2|M2|b1|v1|s0.1|L1.0|K2|RB at 9.68% (10.14% base). T40 -> DF2|M2|b1|v1|s0.2|L1.0|K2|RB at 11.87% (12.68% base).
   Gap-25: tier -25% is empty. Delay 4: T25 -> v1|s0.1|L1.0|K1|RC at 4.85%. Tier -25% holds only 8 of 1,123 configs at base, 5 under gap-20 and 2 at delay 5.
Verdict: all three adopted picks sit just inside their limits (margins of 0.94 / 0.03 / 0.74pp), so any of these stresses pushes all three out: one synthetic -20% gap per 30-year path, or execution slower than 3 days.
The pre-registered numbers are unchanged, and delays 1 and 3 keep every pick in its tier. T40 (DF2 L1.5) is the least robust because exposure creeps to 2.1-2.6x. The DF1 T40alt (11.42%) survives every stress tested.
