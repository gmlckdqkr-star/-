import json
OUT = '/mnt/project-files/research/df1/checks/null/'
R = json.load(open(OUT + 'result.json'))
R['verdict'] = {
 'T25': dict(verdict='material_change', text='v1 alarm earns nothing net: alarm-free twin vt|M0|s0.1|L1.0|K1|RB (same sigma/knee/bond) has path 9.20% vs 8.97%, WD -23.96% vs -24.06%, bondx0 7.26% vs 6.87%, cost2x 7.58% vs 7.20%; paired path win rate of pick 35.8%. Alarm beats rolled-alarm placebo (+0.75pp, pct 100) only because random gating costs 0.98pp. Defense = knee (+16.9pp WD), return = bonds (+2.40pp vs T-bill, of which 2.10pp bond-bull premium). Pre-registered selection unchanged (twin not in grid).'),
 'T30': dict(verdict='minor_change', text='alarm buys +3.2pp WD (always-on twin -33.19%, out of tier) at -0.20pp path; +1.50pp path vs placebo (pct 100 on dev250/NDX, 30 on SPX29, 77.5 on SPX55). Best naive at same WD vt|M2|s0.1|L1.5|K2|RB 10.47% (WD -28.08%) beats headline +0.30pp but loses bondx0 (7.54% vs 8.08%) and SPX55 (6.89%/-31.6% vs 8.20%/-21.8%); no naive beats all 3 gates. Return mostly bonds (+3.28pp vs T-bill).'),
 'T40': dict(verdict='material_change', text='DF2 pick fails the DF2 bondx0 gate with source-period excess (9.55% vs DF1 tier-C 9.82%; reproduces select_df2_fixed.json) and vs naive vt|M0|s0.3|L1.0|K2|RB (10.65%). Alarm info only in NDX-1986-2014-derived data: placebo pct SPX29 cagr 35 / dd 7.5, SPX55 cagr 40 / dd 7.5. Bond-bull premium 3.69pp of 13.24%. Adopted tier-C pick should be v1|s0.3|L1.0|K2|RB.'),
 'T40fix': dict(verdict='minor_change', text='at its own WD (-34.78%) beats best naive vt|M2|s0.15|L1.5|K2|RB (11.29%, bondx0 8.35% vs 9.82%). But its alarm-free twin vt|M0|s0.3|L1.0|K2|RB is in the -40 tier (WD -38.34%) with path 12.17% (+0.74), bondx0 10.65% (+0.84), cost2x 11.23% (+2.11); the alarm buys +3.56pp WD for -0.74pp path (paired CAGR win rate 26%, MDD win rate 81%).')}
json.dump(R, open(OUT + 'result.json', 'w'), indent=1)
print(sorted(R.keys()))
