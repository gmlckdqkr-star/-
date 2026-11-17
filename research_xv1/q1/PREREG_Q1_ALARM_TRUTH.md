# Q1 alarm-truth test: pre-registration (2026-11-11, written before any account is computed)

Handed over from the thread "Map all research directions visually" (owner's choice of 2026-11-11 13:38Z).
This is NOT an XV1 candidate and selects nothing. It applies v1 UNCHANGED to one foreign market with its own
rates, on data through 2014-12-31 only, to learn whether v1's rate alarms carry timing information outside
the history on which they were chosen.

## 1. Question

v1 = `std.s085`: 3x target, 20-day volatility cap, 200-day trend exit that is obeyed ONLY while a rate alarm
is on (`inv`: 10-year yield below the 3-month rate at any time in the last 378 rows; `shock6m`: 10-year yield
up more than 1.0 pp in 126 rows), `shock6m` also caps the level at 1.0, plus the av23s(0.85) brake.
On the Nasdaq-100 the same rule measures 15.2 %/yr when the alarms keep only block-local information
(MS1 path basis, idle cash 0) and 26.4 %/yr when they line up with the market as in history (glued basis).
Which one to expect depends on whether "alarm on = obey the trend exit" is a real regularity.

## 2. Market, data, period (all fixed here)

- Market: Japan. The only foreign market with a free daily index AND its own free long rate data found on
  2026-11-11 (Germany / UK: rates exist on FRED, no free daily index: Bundesbank index series return 404,
  Stooq unreachable from here, FRED's Nordic indexes start 2008). So N = 1 market, N = 1 configuration.
- Index: Nikkei 225 daily close, FRED `NIKKEI225` (price index, weekdays only). r = close / previous close - 1.
- y10: Ministry of Finance JGB yield, the 10Y column where it exists (from 1986-07-05), otherwise the 9Y
  column (from 1974-09-24); value of day t used from the NEXT index row (one-row publication lag).
- y3m and rf: OECD 3-month certificate-of-deposit rate, FRED `IR3TCD01JPM156N`, monthly; the value of month m
  is used from the first index row of month m+1 (same convention as the US monthly fallback). rf = y3m/100/252.
- No credit spread and no volatility index (v1 reads neither).
- Files: `/mnt/project-files/research/q1_alarm/data/` (cut at 2014-12-31 before being written; sha256 in SOURCES.json).
- Scored period: first index row of 1981 through 2014-12-30, one continuous account; 300 warm-up rows before it
  (engine constant). The 378-row alarm look-back before the first scored row must be fully covered by real
  y10 and y3m values (asserted by the script).

## 3. Account (unchanged v1 account)

`std.engine` with `beng.F1` (delay 2, cost 0.003, tax 0.22 with final liquidation tax, harvest 3, 3x fund model
3r - 2rf - 0.0245/252) and `cspr = 10.0` (idle cash earns nothing: the owner's conservative basis).
The fund is hypothetical (a 3x daily fund on the Nikkei 225 financed at the yen 3-month rate). The test is about
the information in the alarms, not about a tradable Japanese product. Figures are in yen terms.

## 4. Runs

- A: v1 unchanged, real Japanese flags.
- Placebo set: v1 unchanged, but the whole flag table is shifted circularly in time against the market inside
  the account rows (warm-up + scored) by s = 504 + 63 j rows, j = 0, 1, ..., while s <= N - 504. Same alarm
  frequency and clustering, no alignment with the market.
- ALWAYS: `inv` forced on at every row (trend exit always obeyed), `shock6m` as real.
- NEVER: `inv` and `shock6m` forced off at every row (no trend exit, no caution cap; volatility cap and brake only).
- HOLD1, HOLD3: `std.hold(c, 1)` and v1's engine with a constant 3.0 target and no brake (cash basis as above).

## 5. Statistic and verdict (the only decision)

S = CAGR(A) - median CAGR(placebo set);  p = (1 + number of placebo runs with CAGR >= CAGR(A)) / (1 + number of placebo runs).

- "ALARM TRANSFERS": S >= +3.0 pp/yr and p <= 0.10.
- "ALARM DOES NOT TRANSFER": S <= 0 or p >= 0.50.
- otherwise "INCONCLUSIVE".

Reading for the owner (fixed wording):
- TRANSFERS: the alarm regularity held on an independent market; the range above 15.2 % (up to the glued 26.4 %)
  stays open. The planning figure remains 15.2 % (conservative rule), nothing is revised upward on one market.
- DOES NOT TRANSFER: the glued 26.4 % must not be used even as a range; 15.2 % is the figure, and it still
  contains block-local alarm information, so it is not a floor.
- INCONCLUSIVE: one market cannot tell; nothing changes.

One market with a handful of alarm episodes has low power; the thresholds above are deliberately loose on p and
the verdict is reported with that caveat. No number from this test is used to tune v1 or any candidate here.

## 6. Secondary figures (reported, no decision)

CAGR and maximum drawdown of A, ALWAYS, NEVER, HOLD1, HOLD3; A minus ALWAYS and A minus NEVER; the same for the
three sub-periods 1981-1989, 1990-2002, 2003-2014 (accounts restarted at each sub-period start with their own
warm-up); number of rows with `inv` on, with `shock6m` on, and with v1 at level 0; placebo quantiles (5, 25, 50, 75, 95 %).

## 7. Rules

- Data checks run BEFORE any account: row counts per year, absolute daily returns above 12 % listed with dates,
  largest one-row change of y10 (incl. the 9Y to 10Y splice), months without y3m. A defect found there is fixed
  and noted before the accounts run. After the first account run nothing in sections 2-5 changes.
- No other Japanese series, period, lag or v1 parameter is tried afterwards. A failed or passed verdict stands.
- Only data through 2014-12-31 exist in the files; no sealed XV1 year can be touched by this test.
- Forbidden files of the project are not opened; nothing here reads an XV1 candidate or an XV1 result.
- Data-check note (2026-11-11, before any account run): the FRED file carries the previous close forward on Japanese
  holidays in 1981-1986 (10 to 16 rows a year with an unchanged close; 0 to 3 in every other year). Fix applied to the
  whole sample: a row whose close equals the previous row's close exactly is treated as a non-trading day and removed.
- Script: `research_xv1/q1/q1_japan.py`; results: `/mnt/project-files/research/q1_alarm/results/q1.json`.
