# OV1 brief for every agent (2026-11-05, thread "Find overwhelming strategy beyond v1")

Read this whole file first. It is the only context you get. Work dir: /mnt/project-files/research/ov1/ (network mount: use trailing slash on dir paths,
never search the whole /mnt/project-files tree, write only inside your own lane folder, re-read a file ~10 s after writing it).

## 1. Goal and bar
- v1 = s0.85 = C3 signal (NDX 200-day SMA +-2% gate, 20-day vol 40%, macro alarms: 10y-3m inversion within 378 days, 10y yield +1pp in 6 months,
  credit-spread jump) choosing a daily target of 3x / 1x / cash on Nasdaq-100, plus account drawdown brake av23s(.85). Real-history states 1986-2014:
  3x 77% of days, 1x 9%, cash 14%. Its losing years are sudden shocks while in 3x (1990, 1994, 1997, 2005-06, 2011).
- PASS = beat v1 on BOTH (a) MS1 headline dev250_path median after-tax CAGR 16.16% AND (b) real NDX 1986-2014 31.08%, with real product costs,
  for ONE pre-registered variant, after selection deflation. User wish: MS1 30%+. Report the best honest candidate even if below.
- Locked MS1 conditions (do not change): cost 0.3%/side, 22% yearly tax on net realized gains (2.5M KRW deduction on 10M start, no carry-forward),
  final liquidation tax, 3x product = 3r - 2rf - 2.45%/yr, cash = (rf - 2pp) x (1 - 15.4%), 2-day execution delay, NDX PRICE index (no dividends).
  Bases: dev250_path (HEADLINE: 500 paths x 30y built from 250-day blocks of 1986-2014, macro alarms recomputed ON the path), dev250_glued (upper
  bound), real_ndx_86_14, real_spx_55_85, real_spx_70_85. Same-basis holds: 1x 11.6% path / 11.5% real; 2x 10.5; 3x 4.2. v1 dd80 (path) 73%.
- Key structural facts (measured, <=2014):
  * v1's real-history edge is almost all macro alarms (alarms off: real 86-14 12.5% ~ QQQ 11.5%). It is concentrated in avoiding 2000-02 and 2008.
  * MS1 path cuts slow leading relations at 250-day block joins, so slow level-based signals score low there. Signals built from CHANGES
    over < ~6 months survive the path rebuild; long-run level z-scores do not.
  * Ceiling math (WX1 lead): with a monthly 3x/cash switch, MS1 path ~ 14.6% at signal corr .15, 19.7 at .20, 24.5 at .25, 30.8 at .30
    (monthly R^2 ~9%). v1 ~ corr .165. Published out-of-sample monthly R^2 for equity-premium predictors is ~1-2% (literature).
  * Feasibility: 30% needs after-cost Sharpe ~0.8-0.85 on the combined book at 3x; known spot streams combine below 1.2; 60% needs ~1.75.
  * Mixing a fixed-weight partner sleeve with v1 wins MS1 path slightly but LOSES real history (736 tries) -> do not propose static mixes.

## 2. Hard rules
1. Data <= 2014-12-31 only. Never compute, quote or write any number from 2015 or later. Papers published after 2014: use concept, mechanism,
   data source and sample period only, never their post-2014 numbers or signs.
2. Point-in-time: a value is usable from the first trading day after it was publicly released (use ALFRED first vintages or publication lags).
3. Free data only. NEVER call any Financial_Datasets tool. No paid API. Login / paid / margin / short-selling steps are PROPOSALS only.
   Do not send the user's email or any personal info to any service; generic user agent only; respect robots.txt / terms.
4. FORBIDDEN FILES (never open, never list contents): reports/best_results_summary_*, research/deep/, research/audit/, any diag/ folder,
   research/mass_scan/, research/us_mix_sb_oos/, research/user_port/, research/c3_relax/RESULT_RELAX_KO.md, research/c3_relax/results/holdout_once.csv,
   research/user_v104/RESULT_V104_KO.md + results/, research/user_v107/ (RESULT_V107_KO.md, results/, unseen/, final/, SHARE_V107_vs_s085_KO.md),
   research/user_port4/RESULT_KO.md + results/, research/c3_stock_combo/, research/c3_create/fwd/, research/theory_sim/holdout/,
   research/s085_contra/holdout/, research/v002/holdout/, research/v002/RESULT_V002_KO.md, tools/s085_now/out/, tools/s085_now/cache/,
   research/pc_gpt_inventory/INVENTORY_EXPOSED.md. (Code may import research/deep/lib indirectly through lab/std; never open it yourself.)
5. Exhausted, do not repeat in any renamed form: every axis in work/CLOSED_REGISTRY_DETAIL.txt (99 rows; run the checker below), static mixing
   (736 tries), same-information complexity search (BT1: 272.6M rules over 48 sources incl. ALFRED surprises PAYEMS/UNRATE/INDPRO/TCU/HOUST/PERMIT/
   NEWORDER/RETAIL/RSAFS/CPI/PCE/CP/PNFI, S&P 500 panel aggregates, cross-asset correlations, Shiller earnings growth; WX1-M1 66 raw signals,
   see research/wx1/m1/PRECOMMIT_M1.md section 2), bottleneck/laggard industry sleeves (PR #15), adaptive weights (PR #16), short-history signals
   VXN/VIX, NDX VRP, SMH/QQQ, XLY/XLP (VN2), and C3 VARIANTS: no new lane may re-mix NDX price, the macro alarms, brakes or overlays of v1 without a
   genuinely NEW information input (user decision 11-03). A parameter, ticker, or weight change is the same family.
6. Pick on early data, confirm once on unseen data. Write PRECOMMIT.md (+ sha256 file) BEFORE running the test. Count every variant (N).
7. Never inflate. If a caveat could lower a number, measure it before reporting.

## 3. Tools (all verified 2026-11-05)
- Idea precheck: `python3 -I /mnt/project-files/tools/idea_check/idea_check.py check "<one-line idea in Korean or English>"` -> matching closed axis
  or a new-axis checklist. Full registry dump: /mnt/project-files/research/ov1/work/CLOSED_REGISTRY_DETAIL.txt.
- MS1 interpreter: `~/.cache/lab/ms1-venv/bin/python -B` (has numpy, pandas, scipy, numba). System python3 pandas is BROKEN; use the venv.
- OV1 helper: /mnt/project-files/research/ov1/code/ov1lib.py (sha 8104ad4a..). `sys.path.insert(0,'/mnt/project-files/research/ov1/code'); import ov1lib as L`.
  L.dates() calendars per basis; L.gather(series, basis) glued (P,T) values; L.path_series(series, basis) path-rebuilt (P,T) values (HEADLINE way);
  L.v1_B(c) v1 daily target; L.v1_parts(c) v1 brake; L.measure2(name, make2) with make2(c, basis)->(B, bfn, bp, fstep) prints all 5 bases and
  returns HEADLINE_MS1, REAL_NDX, BEATS_V1_BOTH. Self-check reproduces 0.1616 / 0.3108 (~30 s per measure2 call, ~1-2 GB RAM).
  Where an external series has no data (e.g. SPX 1955-85) fall back to v1's B and say "not covered".
- Info gate G1 for timing signals: `sys.path.insert(0,'/mnt/project-files/research/breakthrough/code'); import gate; gate.test(sig, trials=N)` with
  sig = pandas bool Series by trading date (value at t uses only info known at close t). Label = 3x NDX beats deposit over t+3..t+23, blocks every
  21 days; always-in base hit 55.5% (NDX 86-14). Deflated hit <.65 CLOSE, .65-.70 HOLD, >=.70 BUILD. Non-timing streams: standalone after-cost
  Sharpe ~1.1 is the same gate.
- MS1 price frame: `import jp; R,M=jp.calendar('1984-01-03','2014-12-31'); X=jp.mkX(R,M,'NDX')` -> columns r (NDX daily price return), rf (daily),
  y10, y3m, cs (credit spread), vix, rb, p. SPX frame: jp.calendar('1928-01-03','1985-12-31'), jp.mkX(R,M,'SPX').
- lab (strategy DSL, ETF panel 22 US ETFs + 4 KR ETFs + S&P 500 PIT single stocks 1970-2014): /mnt/project-files/research/lab/USAGE_FOR_THREADS_KO.md.
  Use lab first when the idea is expressible there; every lane result carries one line `lab 사용: 예/아니오 (이유)`.
- Existing local data (<=2014 cuts; check manifests): /mnt/project-files/research/data/INDEX.md lists sets (ALFRED vintages a27_macro_vintage/,
  macro_n/ (Moody's spreads, claims), cape_vintage/, ipo_ritter/, optsent/ (SKEW, put/call), ken_french/, oap/ (Chen-Zimmermann signals), kr_dart/,
  kr_stocks/, us_stocks/ (S&P 500 PIT panel), margin/, gold/, fx_dexkous/). Do not move or redistribute us_stocks data.
- Network from this cloud (checked 07:03Z): REACHABLE fred.stlouisfed.org (fredgraph.csv?id=..; ALFRED needs `-A curl/8.0 --http1.1`),
  mba.tuck.dartmouth.edu (Ken French), philadelphiafed.org, federalreserve.gov, newyorkfed.org, census.gov, apps.bea.gov, cboe.com,
  semiconductors.org, data.nasdaq.com, pypi. BLOCKED: sec.gov (403), web.archive.org (timeout), Yahoo (429), stooq, bls.gov (403; use FRED copies).
  Other hosts: test with `curl -s -o /dev/null -m 12 -w "%{http_code}" -A "curl/8.0" URL` before relying on them.
- CPU: 4 cores shared by 2 concurrent agents. Keep any job to <=2 processes and <=20 minutes; always use `timeout`.

## 4. Kill-test types (choose one per lane in PRECOMMIT; thresholds are fixed, do not relax)
- Early window = series start (or 1986) .. 1999-12-31 (plus SPX 1955-85 where data exists). Unseen window = 2000-01-03 .. 2014-12-31, opened ONCE.
- A CUT overlay on v1 (move v1 3x -> 1x/cash when the signal fires): in 21-day blocks where v1 is at 3x, P(3x beats deposit | signal on) must be
  >= 10pp BELOW the base rate of v1-3x blocks, with >= 8 'on' blocks, in BOTH windows. (VN2 used this; all 4 failed.)
- B ADD overlay (raise v1 1x/cash -> 3x when the signal fires): in v1 non-3x blocks, P(3x beats deposit | on) >= base + 10pp AND >= 60%, >= 8 'on'
  blocks, both windows.
- C Standalone timing: G1 deflated hit >= .65 on early data to continue; unseen hit must stay >= .60 and above the unseen always-in rate.
- D Non-timing return stream (Korean retail spot account, long-only, no margin/short): standalone after-cost after-tax Sharpe >= 1.1 early,
  >= 0.8 unseen; then MS1 with v1.
- E Cross-sectional selection (stocks/ETFs): rank IC >= .05 with t >= 3 early; same sign and IC >= .03 unseen.
- F Structural mechanism with no prediction (vehicle, execution, account structure): measure2 directly; parameters fixed from early data or theory;
  pass needs path d_vs_s085 > +0.5pp AND real NDX d > 0.
- Survivors of A-F go to measure2 (v1 combined): FINAL PASS = HEADLINE_MS1 > 0.1616 AND REAL_NDX > 0.3108 for the pre-registered variant, path
  pw_vs_s085 >= .55, real SPX 55-85 not worse than v1 by > 1pp where covered, with N and the deflation stated. Report glued as upper bound only.

## 5. Output conventions
- Ideas: one JSON object per idea (schema given in your prompt). Korean title + English mechanism is fine.
- Lanes: /mnt/project-files/research/ov1/lanes/<LANE_ID>/ with data/ (raw files + MANIFEST.json with sha256 and source URLs), PRECOMMIT.md +
  PRECOMMIT.sha256, code/, results/*.json, RESULT_<LANE_ID>_KO.md (Korean, short: 결론/결과/검증/남은 문제, N, `lab 사용` line).
- Ledger: append one CSV line per counted variant to /mnt/project-files/research/ov1/lanes/<LANE_ID>/ledger.csv (lane,variant,window,metric,value).
