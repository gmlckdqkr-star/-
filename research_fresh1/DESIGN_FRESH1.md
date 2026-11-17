# FRESH1 — clean-slate design and pre-registration

Written 2026-11-11 08:2xZ, BEFORE opening any prior research report, closed-lane
registry, lab tool or lab document. Sealed by sha256 in DESIGN_FRESH1.sha256.

## 0. Exposure disclosure (honest)

The project memory index and five memory notes (FINAL1, NP1, frame-break, V002 bar,
TW1) were auto-loaded into my context before I could design. I did not open any
report, registry, code or lab doc. So this design is "independent of the prior
research documents" but NOT "blind to the list of closed lane names". To get truly
blind ideas, part C below uses designers who are given no project history at all.

## 1. Question from the user (11-11 08:12Z)

1. Are the accumulated research rules themselves stopping a breakthrough?
2. Would a completely fresh start find something the user can actually use?
   (Kiwoom spot US/KR, ISA domestic only, KIS futures/options, domestic margin,
   capital under 1억 KRW, free data only.)

## 2. My framing (first principles)

Objective = expected log growth of the user's real account after cost, tax, FX and
delay, over the distribution of possible futures. Not the CAGR of one historical path.

Growth identity: g = cash yield + L(mu - financing) - 0.5 L^2 sigma^2 - cost - tax.
Only five levers exist: (a) signal (Sharpe), (b) underlying, (c) vehicle (financing,
tax), (d) capital-insensitive structural edges, (e) decision rule used to pick
between candidates. Levers (a)-(d) are what research lanes test. Lever (e) is what
the user asks about in question 1: a biased decision rule can reject a truly better
method or keep a lucky incumbent, however many lanes are run.

## 3. Part A — audit of the rules, with numbers (pre-registered method)

A rule is classified KEEP when removing it lets a fake result through
(look-ahead, survivorship, IS/OOS mixing, pre-registration, real cost/tax/delay,
selection deflation, forbidden holdout files).
A rule is classified CHANGE when it is a decision gate whose error rates are bad.
Gate error rates are computed, not argued:

A1. Single-path gate ("must beat v1 on the real 1986-2014 path"). For a challenger
    whose TRUE log-growth edge over v1 is d (pp/yr) with tracking error te (%/yr)
    over T = 29 years, P(win the path) = Phi(d * sqrt(T) / te).
    Report the table d in {-2,-1,0,+1,+2,+3} x te in {5,10,20,30}.
    te is then calibrated from v1 and real challengers' daily series in the lab
    (after this file is sealed). Pre-registered reading:
    - gate is "noise" for a family if P(win | d=+2) < 80% or P(win | d=0) >= 40%.
A2. Incumbent bias. Check how v1's own parameters and its underlying were chosen
    and whether v1's 1986-2014 number was deflated for that choice the same way
    challengers are. Also compute where the real 1986-2014 outcome of v1 sits
    inside v1's own simulated distribution (percentile). If above the 75th
    percentile, the real path is a lucky draw for the incumbent and a hard
    "beat it on that path" gate is incumbent-biased.
A3. Coverage rule ("data must cover 1986-99"). List which instrument and data
    classes it excludes by construction, and which of those the user can trade.
A4. Go-live bar ("30% on the conservative simulation"). Compare with the
    simulation's own ceiling: the Sharpe needed vs the best measured.
A5. Per-lane standalone gate and no-reopen rule. Count (from the registry, after
    sealing) candidates that won the simulation but were closed only by the
    real-path leg or a stress leg; these are the "possibly blocked" set.
    They are re-judged from their recorded numbers only. No re-measurement,
    no new parameter choice.

Proposed fair gate (fixed now, used for A5 and part B/C):
  PASS = (i) paired block-bootstrap of daily log-return difference vs v1
         (block 250 days, 2,000 draws) on all <=2014 history: P(d>0) >= 90%;
         (ii) simulation median not worse than v1;
         (iii) P(-80% drawdown) not higher than v1;
         (iv) delay +5 days keeps at least half the edge;
         (v) all integrity rules unchanged.
The real-path point comparison is reported but is not a veto on its own.

## 4. Part B — my own fresh hypothesis H1 (rule fixed before any data is loaded)

H1 "lever what leads" — the underlying is chosen by rule, not by hindsight.
Motivation: v1 levers one index (Nasdaq) that we know, after the fact, led the
world in 1986-2014. The implementable forward version is to lever the sectors that
are leading. If H1 fails, that is evidence the Nasdaq choice is not the weak point.

Data: Ken French library, daily value-weighted returns, 1926-07 to 2014-12 only
(CRSP based, includes delisted firms, so no survivorship bias):
"12 Industry Portfolios [Daily]", "49 Industry Portfolios [Daily]",
"F-F Research Data Factors [Daily]" (Mkt-RF, RF).

Tradable set S7 (each has a 2x-3x US ETF the user can buy at Kiwoom):
BusEq, Enrgy, Hlth, Money, Utils, Shops, Manuf, plus Mkt (total market).
Diagnostic sets: all 12 industries; all 49 industries (phenomenon check only).

Rule (primary variant P):
- Month-end signal, traded at the close one trading day later.
- Momentum M_i = total return over the past 252 trading days excluding the last 21.
- Trend filter: industry total-return index above its own 200-day average.
- Hold the top K = 2 by M_i among those passing the filter, equal weight,
  each through a 3x daily-reset fund. Empty slots sit in cash.
- No stops, no other thresholds.
Variants reported together (all six, no picking): K in {1,2,3} x lookback
{12-1 months, 6 months no skip}.

Cost model (conservative; if the lab's standard is harsher, use the lab's):
- 3x fund daily return = 3 r_i - 2 (rf + 1.0%/yr) - 0.95%/yr fee.
- Trade cost 0.40% per side on switched notional (0.25% fee + 0.15% spread).
- Tax 22% of each calendar year's net realized gain, no deduction, no loss carry.
- Cash earns max(rf - 2pp, 0).
- Stress: delay +5 days; cost x2.

Benchmarks in the same engine and costs:
B0 = Mkt 3x with the same month-end 200-day filter.
B1 = BusEq only 3x with the same filter (the hindsight pick).
v1 = project numbers, same basis, read after sealing.

Pass criteria (fixed now):
- "Phenomenon": P beats B0 after cost and tax in each of 1927-54, 1955-85,
  1986-2014 (3 of 3), AND paired block-bootstrap P(d>0) >= 90% on the full sample,
  AND at least 4 of 6 variants beat B0 on the full sample,
  AND delay +5 keeps at least half the edge.
- "Candidate": phenomenon passes AND the fair gate of section 3 vs v1 passes.
My prior: phenomenon 25%, candidate 7%.
If it fails it is closed and reported as failed. No rescue variants.

## 5. Part C — blank-slate experiment (answers question 2 with evidence)

Seven designers get ONLY the user's real constraints and the integrity rules.
No project memory, no reports, no closed list, no mention of v1's rule.
Lenses: (1) leveraged index timing, (2) Korea-specific tax and instruments,
(3) stock selection with small capital, (4) derivatives and volatility,
(5) events, flows and arbitrage, (6) portfolio / Kelly combination,
(7) assume everything usual failed — what frame is left.
Each returns up to 3 methods with mechanism, counterparty, instruments, exact
rule, free data with start year, expected net numbers, and how it could be fake.

Then every idea is mapped against the closed registry (read only at that point):
SAME (already measured), SAME-IDEA-DIFFERENT-GATE (measured, closed by a gate
part A calls biased), NEW-TESTABLE, NEW-UNTESTABLE (no free bias-free data),
DOOR (needs a user action).
Pre-registered reading of the experiment:
- If 0 ideas are NEW-TESTABLE, a fresh start does not open new ground:
  the limit is information, not the rules.
- NEW-TESTABLE ideas are each pre-registered (rule, costs, pass line fixed in a
  file with sha256 before measuring), measured on <=2014 data, then reproduced
  by an independent verifier. Any pass goes to one post-2014 check stored in
  holdout/ and never fed back into design.

## 6. Integrity rules (unchanged, not up for audit)

No look-ahead, no survivorship bias, real cost/tax/FX/delay, IS and OOS never
blended, pre-registration before measurement, every variant reported, numbers
stay conservative, forbidden files never read: research/onf1/holdout/,
research/s085_contra/holdout/, research/theory_sim/holdout/,
research/v002/holdout/, research/v002/RESULT_V002_KO.md, tools/s085_now/out/,
tools/s085_now/cache/. No paid API, never Financial Datasets.
Reconstructed data is labelled RECON and never mixed with ACTUAL.
