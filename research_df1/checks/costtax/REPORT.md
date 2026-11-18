# costtax check: costs, tax, account size, bond model, KRW (data <= 2014-12-31; synthetic 10y/7y bond = NON-ACTUAL)
Code: ctlib.py, reselect.py (all 1,123 configs re-selected per variant, both DF2 gate versions), picks_krw.py, krw_reselect.py, summarize.py -> result.json.
Base run reproduces grid.json for all 1,123 configs (max |diff| 5e-7, rounding). Variants: W0 30M/100M/300M (D 0.0833/0.025/0.0083), 7y bond (n=14), bond ER 0.25%, harvest off, cost 0.2%/0.45% per side, 2 combos.
- T25 v1|s0.1|L1.0|K1|RB (path 8.97%, WD -24.06%): biggest headline cut W0 300M 8.04% (-0.93pp), cost 0.45% 8.09%. cost 0.45% -> WD -25.67% = OUT of tier;
  re-selection then picks v1|s0.1|L1.0|K1|RC at 4.43%. 7y bond: pick stays in tier but the tier pick flips to DF2|M2|b1|v1|s0.15|L1.0|K1|RB 10.79%.
- T30 v1|s0.2|L1.0|K1|RB (10.18%, WD -29.97%): on the boundary; OUT of tier under W0 30M/100M/300M, bond ER 0.25%, harvest off, cost 0.45% (6/8 single variants).
  Largest cut cost 0.45% -> 8.87%. Re-selected tier headline 9.34%-11.75% across variants (4 different configs win).
- T40 DF2|M2|b1|v1|s0.3|L1.5|K2|RB (13.24%, WD -39.26%): in tier under all variants (worst WD -39.57%); largest cut W0 300M -> 12.40%.
  Adoption is fragile: corrected gate (select_df2_fixed.json) rejects it at base -> v1|s0.3|L1.0|K2|RB 11.42%; original gate rejects it at W0>=30M and bond ER 0.25%.
- KRW (FRED DEXKOUS raw <=2014, ACTUAL FX but A10-1 quality gate FAIL -> stress version): real NDX 86-14 MDD in KRW T25 -27.73% (USD -19.05%), T30 -32.40% (-21.02%),
  T40 -37.56% (-30.90%), QQQ -81.02% (-82.99%), v1 -65.72% (-69.97%). KRW CAGR about +0.7-0.9pp higher (KRW 892.5 -> 1090.9).
  T25 and T30 leave their tiers in KRW terms (drawdowns from KRW appreciation 2004-01..2006-07 and 1997-12..1998-08 while mostly in USD bonds).
- KRW re-selection: real-NDX leg in KRW -> -25% tier empty, -30% pick DF2|M0|b2|v1|s0.2|L1.0|K1|RB 10.85%. FX also bootstrapped on paths (NON-ACTUAL) -> only static QQQ30/bond in any tier.
- References: QQQ 1x hold moves <= 0.08pp; v1 15.18% -> 14.74% (W0 300M), 14.87% (cost 0.45%), 14.89% (harvest off). Tier -20% stays empty in every variant.
Caveats: KRW conversion multiplies the USD after-tax account by KRW/USD (Korean tax on KRW-denominated gains not modelled); D is the 2.5M KRW deduction for this account alone.
