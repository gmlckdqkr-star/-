# FINAL1 brief for every agent (2026-11-10, thread "Find final best trading method")

Read this whole file first. It is the only shared context you get. Work dir: /mnt/project-files/research/final1/ (network mount: use a trailing
slash on dir paths, never search or list the whole /mnt/project-files tree, write only inside your own lane folder
/mnt/project-files/research/final1/lanes/<LANE_ID>/, re-read a file about 10 s after writing it).

## 0. What you must NOT touch (hard)
- Do not use any `mcp__remote-devices__*`, `mcp__hearthbot__*`, Kiwoom, GitHub (`mcp__github__*`), Figma, Google Drive, or `Financial_Datasets` tool.
  Do not message the user or any other thread. Do not write project memory files. Do not spawn sub-agents or workflows. Do not git commit/push.
- Do not send any personal data (names, e-mail) to any service. Generic user agent only. Read robots.txt before the first request to a new host.
- Free sources only. Never sign up for anything. Login / paid / margin / short-selling steps are PROPOSALS only (write them down, do not do them).
- The user rejects any method that needs their own manual action (IPO subscription, manual tenders, manual transfers). Only methods an automated
  program can run end to end through the Kiwoom REST / KIS APIs count. US market first.

## 1. Goal and bar
- v1 = s0.85 = C3 signal (NDX 200-day SMA +-2% gate, 20-day vol > 40% -> 1x, macro alarms: 10y-3m inversion within 378 days, 10y yield +1pp in
  6 months -> cap 1x / crisis gate to cash) choosing a daily target of 3x / 1x / cash on Nasdaq-100 (TQQQ + USD cash), plus account drawdown brake
  av23s(.85). Real-history states 1986-2014: 3x 77% of days, 1x 9%, cash 14%. 1986-99 it earned about 52%/yr, so anything that takes capital
  away from v1 while it is at 3x loses on real history.
- PASS = beat v1 on BOTH (a) MS1 headline dev250_path median after-tax CAGR 16.16% AND (b) real NDX 1986-2014 31.08%, for ONE pre-registered
  variant, after selection deflation, with real product costs. User wish: MS1 30%+. Report the best honest candidate even if below.
- Locked MS1 conditions (do not change the reference): cost 0.3%/side, 22% yearly tax on net realized gains (2.5M KRW deduction on a 10M KRW start,
  no carry-forward), final liquidation tax, 3x product = 3r - 2rf - 2.45%/yr, cash = (rf - 2pp) x (1 - 15.4%), 2-day execution delay, NDX PRICE
  index. Bases: dev250_path (HEADLINE: 500 paths x 30y from 250-day blocks of 1986-2014, macro alarms recomputed ON the path), dev250_glued (upper
  bound only), real_ndx_86_14, real_spx_55_85, real_spx_70_85. Same-basis holds: 1x 11.6% path / 11.5% real; 2x 10.5; 3x 4.2. v1 dd80 (path) 73%.
- Structural facts already measured (<=2014), use them, do not re-derive:
  * v1's real-history edge is almost all macro alarms (alarms off: real 86-14 12.5%). MS1 path cuts slow leading relations at block joins, so
    only signals built from changes over < ~6 months survive the path rebuild.
  * Ceiling: with a monthly 3x/cash switch, MS1 path ~ 14.6% at signal corr .15, 19.7 at .20, 24.5 at .25, 30.8 at .30. v1 ~ .165. Published
    out-of-sample monthly R^2 of equity-premium predictors ~1-2%.
  * A stand-alone uncorrelated stream with after-cost Sharpe 1.0 at 20% weight adds only ~+2pp path; fixed-weight partner sleeves win path a
    little but LOSE real NDX (1,000+ tries). Static mixes are closed. Only ADDITIVE changes (execution, account terms, uses of v1's idle cash,
    overlays that act only when v1 is not at 3x) have ever been positive on both bases, and all were small (+0.1..+0.5pp).
  * 108 axes are closed (registry below): price/vol timing, ~40 regime detectors, 499 free signals, 272.6M-rule search over 48 info sources, ML,
    forecast combination, calendar, FOMC, breadth, sentiment, flows, options (covered calls, put-writes, spreads, LEAPS), >3x leverage, futures as
    the v1 vehicle, sector/3x rotation, single stocks (price, value/quality, PEAD, EDGAR events, OAP 168 anomalies), KR small caps, KR DART events,
    index add/delete, merger arb, tax/fee structures, idle-cash fills (bonds, gold, DBMF, PSQ, SGOV at 0.3% fee), bottom-buying ladders (NDX, SOX),
    take-profit/profit-lock, pyramiding, parameter ensembles and continuous sizing on the raw chassis.
  * A parallel thread (ONF1) is testing a night-only MNQ futures tilt on top of v1. Do NOT work on overnight / close-to-open futures ideas.

## 2. Hard research rules
1. Data <= 2014-12-31 only. Never compute, quote or write any number from 2015 or later. Papers published after 2014: concept, mechanism, data
   source and sample period only, never their post-2014 numbers or signs.
2. Point-in-time: a value is usable from the first trading day after its public release (ALFRED first vintages or publication lags).
3. FORBIDDEN FILES (never open, never list contents): reports/best_results_summary_*, research/deep/, research/audit/, any diag/ folder,
   research/mass_scan/, research/us_mix_sb_oos/, research/user_port/, research/c3_relax/RESULT_RELAX_KO.md, research/c3_relax/results/holdout_once.csv,
   research/user_v104/RESULT_V104_KO.md + results/, research/user_v107/ (RESULT_V107_KO.md, results/, unseen/, final/, SHARE_V107_vs_s085_KO.md),
   research/user_port4/RESULT_KO.md + results/, research/c3_stock_combo/, research/c3_create/fwd/, research/theory_sim/holdout/,
   research/s085_contra/holdout/, research/v002/holdout/, research/v002/RESULT_V002_KO.md, research/onf1/holdout/, tools/s085_now/out/,
   tools/s085_now/cache/, research/pc_gpt_inventory/INVENTORY_EXPOSED.md, research/ov1/lanes/*/data/raw_* (+ Noise_Measure_2025.xlsx,
   qqq_td_raw.json), any file or folder named holdout*. Any results file whose name does not end in `_le2014` in research/onf1/ is off limits.
   (Code may import research/deep/lib indirectly through lab/std; never open it yourself.)
4. Closed axes may not be repeated under a new name. A parameter, ticker or weight change is the same family. C3 variants (re-mixing NDX price,
   the macro alarms, brakes or overlays of v1 with no genuinely new information or structure) are closed by user decision.
5. Pre-register before computing: PRECOMMIT.md + PRECOMMIT.sha256 in your lane folder, variants fixed, every variant counted (N).
   Pick on early data, confirm ONCE on unseen data. Never relax a threshold after seeing a result.
6. Never inflate. If a caveat could lower a number, measure it before reporting. Synthetic or reconstructed data is labelled NON-ACTUAL.

## 3. Tools (verified 2026-11-10 in this container)
- Python: `~/.cache/lab/ms1-venv/bin/python -B` (numpy, pandas, scipy, numba, xlrd, pyarrow, pyyaml). Before running:
  `export NUMBA_CACHE_DIR=/home/claude/nbcache_std` and `cd /tmp` (or your own scratch dir under /tmp/final1_<LANE_ID>/).
  NEVER run python with the current directory at or under /mnt/project-files/research/ (a folder there named `bottleneck` shadows a pandas
  dependency and the import fails). Keep scripts in your lane's code/ folder and call them by absolute path from /tmp.
- Idea precheck (mandatory for every idea): `python3 -I /mnt/project-files/tools/idea_check/idea_check.py check "<one-line idea>"`; full list
  `... idea_check.py list`. Registry dump with details: /mnt/project-files/research/ov1/work/CLOSED_REGISTRY_DETAIL.txt (99 rows; rows T39, X41
  and later only via `list`).
- MS1 helper: /mnt/project-files/research/ov1/code/ov1lib.py. `sys.path.insert(0,'/mnt/project-files/research/ov1/code'); import ov1lib as L`.
  L.dates() calendars per basis; L.gather(series, basis) glued (P,T) values; L.path_series(series, basis) path-rebuilt (P,T) values (HEADLINE way);
  L.v1_B(c) v1 daily target 0/1/3; L.v1_parts(c) v1 brake (bfn, bp, fstep); L.measure2(name, make2) with make2(c, basis) ->
  (B, bfn, bp, fstep[, engine_kw]) prints all 5 bases and returns HEADLINE_MS1, REAL_NDX, BEATS_V1_BOTH. Self-check reproduces 0.1616 / 0.3108
  (about 25 s per call, 1-2 GB RAM). engine_kw may override beng.F1 keys (delay, cost, cspr, er3, tax, harvest, step) for sensitivity rows only.
  `C = L.std.contexts()` gives {basis: Ctx} with c.r (P,T) daily NDX returns, c.rf, c.lvl, c.sma(n), c.vol(n), c.hi(n), c.F flags, c.ii indices.
- Info gate G1 for timing signals: `sys.path.insert(0,'/mnt/project-files/research/breakthrough/code'); import gate; gate.test(sig, trials=N)`
  (sig = pandas bool Series by trading date; label = 3x NDX beats deposit over t+3..t+23; always-in base hit 55.5%). Deflated hit < .65 CLOSE.
- MS1 price frame: `import jp; R,M=jp.calendar('1984-01-03','2014-12-31'); X=jp.mkX(R,M,'NDX')` -> r, rf, y10, y3m, cs, vix, rb, p (after importing
  ov1lib). SPX frame: jp.calendar('1928-01-03','1985-12-31'), jp.mkX(R,M,'SPX').
- lab (strategy DSL; 22 US ETFs, 4 KR ETFs, S&P 500 PIT single stocks 1970-2014): /mnt/project-files/research/lab/USAGE_FOR_THREADS_KO.md.
  Every lane result carries one line `lab 사용: 예/아니오 (이유)`.
- Local data (<=2014 cuts; read the manifest of a set before using it): /mnt/project-files/research/data/INDEX.md.
- Network: test a host with `curl -s -o /dev/null -m 12 -w "%{http_code}" -A "curl/8.0" URL` first. On 11-05 fred.stlouisfed.org, Ken French,
  federalreserve.gov, newyorkfed.org, census.gov, cboe.com, data.nasdaq.com, pypi were reachable; sec.gov, web.archive.org, Yahoo, stooq, bls.gov
  were not. Naver finance, index.krx.co.kr, Yahoo query1 and Stooq disallow robots: never fetch them. data.krx.co.kr JSON needs a login: do not
  use internal endpoints to get around it.
- CPU: 4 cores shared by 2 agents and the main session. At most 2 processes per agent, every job under `timeout 1200`.

## 4. Kill-test types (pick one per lane in PRECOMMIT; thresholds fixed)
- Early window = series start (or 1986) .. 1999-12-31 (plus SPX 1955-85 where data exists). Unseen window = 2000-01-03 .. 2014-12-31, opened ONCE.
- A CUT overlay (v1 3x -> 1x/cash when on): in 21-day blocks where v1 is at 3x, P(3x beats deposit | on) >= 10pp BELOW the base rate of v1-3x
  blocks, >= 8 'on' blocks, BOTH windows.
- B ADD overlay (v1 1x/cash -> 3x when on): in v1 non-3x blocks, P(3x beats deposit | on) >= base + 10pp AND >= 60%, >= 8 'on' blocks, both windows.
- C Stand-alone timing: G1 deflated hit >= .65 early; unseen hit >= .60 and above the unseen always-in rate.
- D Non-timing return stream (Korean retail account, long-only or defined-risk, automated): after-cost after-tax Sharpe >= 1.1 early, >= 0.8 unseen.
- E Cross-sectional selection: rank IC >= .05 with t >= 3 early; same sign and IC >= .03 unseen.
- F Structural mechanism with no prediction (vehicle, execution, account terms): measure2 directly; parameters from theory or early data; pass needs
  path d_vs_s085 > +0.5pp AND real NDX d > 0.
- Survivors go to measure2 (v1 combined): FINAL PASS = HEADLINE_MS1 > 0.1616 AND REAL_NDX > 0.3108 for the pre-registered variant, path
  pw_vs_s085 >= .55, real SPX 55-85 not worse than v1 by > 1pp where covered, N and deflation stated. Glued = upper bound only.

## 5. Output conventions
- Lane folder /mnt/project-files/research/final1/lanes/<LANE_ID>/ : data/ (raw files + MANIFEST.json with sha256 and source URLs),
  PRECOMMIT.md + PRECOMMIT.sha256, code/, results/*.json, RESULT_<LANE_ID>_KO.md (Korean, short: 결론 / 결과 / 검증 / 남은 문제, N, `lab 사용` line,
  every number labelled 확인됨 / 추론 / 미검증 and ACTUAL / NON-ACTUAL).
- Delete scratch files you no longer need. Do not leave large raw downloads that contain rows after 2014 (cut them, record sha of the raw file).
- Your final answer is data for the orchestrator, not a message to a person: return exactly the structure your prompt asks for.
