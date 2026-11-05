# NI1 scouting brief (round 3 of the BT1 breakthrough lane, 2026-11-04)

## Goal
Find a NEW KIND of information (not a new combination of old information) that could let a small Korean retail account beat the current best
strategy "s0.85" (a Nasdaq-100 3x/1x/cash timing system; MS1 representative 16.16%/yr after cost and tax; NDX buy-and-hold 11.6%).
User bar: 30%/yr. Honest reporting: a candidate that probably fails must be described as such.

## What "pass" needs (fixed rules of this project)
- Index timing signal: G1 gate (research/breakthrough/code/gate.py): deflated hit rate >= .65 to keep, >= .70 to build, where the label is
  "Nasdaq 3x beats deposit over t+3..t+23 trading days" and always-long hit = .555. Deflation = hit - 2*SE*sqrt(1+ln trials).
  Realistic need: raw hit rate ~ .70+ on 1986-2014 NDX.
- Stock selection (S&P 500 point-in-time members, long only, monthly): rank IC >= .05 that persists (stable sign by sub-period),
  or a stand-alone after-cost Sharpe ~1.1.
- Data must cover well before 2015 (ideally 1986 or earlier for index timing; at least ~1995-2014 for stock level) and be point-in-time
  (known at the decision date: publication lags, revisions/vintages, no full-sample fitted constructs unless re-estimated in an expanding window).

## Account / universe constraints
- Spot only: US stocks and ETFs (Kiwoom), Korean stocks and ETFs, KIS futures/options. No margin, no short selling of stocks.
- Execution delay: a decision made at close t is executed at close t+2 (scheduled, pre-known events can be positioned in advance).

## Already CLOSED (do not propose again unless you can name what is genuinely different)
Read the registry: /mnt/project-files/tools/idea_check/closed_axes.json (88 axes). Check every candidate with
  python3 /mnt/project-files/tools/idea_check/idea_check.py check "<idea words>"
Highlights: price trend/vol/momentum timing; macro alarms; calendar effects (TOM, holidays, FOMC drift, election cycle); sentiment and option
sentiment; positioning/flows (COT, margin, short interest, insider aggregates, fund flows, TIC, Z.1); ~40 regime detectors; 499 free
signals; event timing (FOMC, earnings season, macro releases, Treasury auctions, Beige Book); news/LLM/search volume/EPU/GPR (forward-record
only); moon/weather/sunspots; breadth; cross-sectional correlation; foreign markets lead-lag; futures basis; patents/FDA/government
spending (blocked by permno->ticker mapping); US stock price-based selection; value/quality; ML stock selection; small caps; EDGAR filing
events and 10-K text; insider/13F/guru cloning; PEAD; index add/delete; spin-offs; CEF discounts; OAP Chen-Zimmermann 168 firm signals
(published anomalies); Goyal-Welch-Zafirov 2024 predictor table; sector/country/style rotation; static mixes; CTA/carry; options
overlays; leverage above 3x; crypto; Korean small caps, DART disclosure events, KR leveraged ETF timing; LPPLS; RSI; DCA schemes;
BT1 (48 new sources: macro release surprises and revisions, panel aggregates, correlation regimes, PIT earnings growth, gold/platinum,
electricity; 156M rules) and SL1 (regime -> stock baskets; 104M rules). All failed.

## Data access facts in this cloud container
- Reachable (checked): fred.stlouisfed.org (FRED/ALFRED vintages), fec.gov, epa.gov, census.gov, treasurydirect.gov, newyorkfed.org,
  philadelphiafed.org, data.nber.org, zenodo.org, dataverse.harvard.edu, openicpsr.org, sites.google.com, uspto.gov, raw.githubusercontent.com,
  opendart API (Korean; financial statements only for business year 2015+, disclosure list from 1999).
- BLOCKED by the proxy (403): sec.gov / data.sec.gov (no EDGAR), bls.gov, ici.org, osha.gov. Unknown: others; test with
  curl -s -o /dev/null -w "%{http_code}" --max-time 10 <url>
- robots.txt disallow (never fetch): Naver, Yahoo query1, Stooq, index.krx.co.kr. data.krx.co.kr needs login (user only). ECOS needs a key
  with identity verification (user only).
- Stock panel available: S&P 500 point-in-time membership and adjusted daily closes 1970-2014, 1503 tickers (ticker symbols only, no
  company names, no CUSIP/permno). Joining firm-level outside data needs a reliable ticker (or name) key valid at the time.

## Hard rules
- No paid data or paid APIs; never use Financial Datasets; do not assume a service is free unless its terms say so.
- Read robots.txt before the first request to a new host. Do not send any personal information (no email in User-Agent; use a generic
  client name). Do not download more than ~5 MB per probe in this scouting step.
- FORBIDDEN, do not open or read: reports/best_results_summary_*, research/deep/, research/audit/, any diag/, research/mass_scan/,
  research/us_mix_sb_oos/, research/user_port/, research/c3_relax/RESULT_RELAX_KO.md + results/holdout_once.csv,
  research/user_v104/RESULT_V104_KO.md + results/, research/user_v107/ (all), research/user_port4/RESULT_KO.md + results/hist.json +
  results_check_actual.json, research/c3_stock_combo/, research/c3_create/fwd/, research/s085_contra/holdout/,
  research/theory_sim/holdout/, tools/s085_now/out/, tools/s085_now/cache/. (All under /mnt/project-files/.)
- Do not look up or quote any strategy performance after 2014-12-31 for candidates (literature results that end before 2015 are fine;
  if a paper's sample extends past 2014 just note the sample span, not post-2014 numbers).
- Do not write files outside your own scratch folder /tmp/claude-0/-home-user--/e60ac389-f078-575c-af9f-bad532fab64a/scratchpad/ni1/scout/.
