# PREREG XV1: interleaved design / validation block structure

Registered text, version 5 (2026-11-11). Version 1 was a candidate text that went through four independent reviews
(sealing, causality, statistics, engine), a refutation pass on every finding and a final critic (15 further findings);
versions 2 to 4 carry the fixes that survived. Version 4 and its evaluator then went through an independent verification
with five lenses (engine, sealing, statistics, causality, text against code) on synthetic worlds and on the <= 2014
calendar: 50 findings, 3 of them critical. Version 5 and evaluator version 5 carry the fixes; the changed parts were
verified once more before registration. Versions 1 to 4 were never registered and scored nothing.

Status and owner decision. On 2026-11-11 the owner was shown a decision card in the thread (switch to the interleaved
structure, recommended, with the note that the step cannot be undone) and answered at 12:49:08Z (message id
cmsg_013GuJ2gSecTDkpekhQ7SWhg47X7ADtvr4d67q4nBbKHKk), verbatim: "A 가 추천이라는 말은 지금 까지의 방법으로는 지금이 최선일
확률이 99.9%라는 거지? 그렇다면 방법을 바꾸긴 해야지". The card was closed on that answer. This text is the method put in
place in answer to it; the registration line in the ledger carries that message id. Every G3 opening needs a further
message of the owner. One-way step: once the first output from a row after 2014-12-31 exists, the years 2015, 2019-21 and
2025-26 cannot be a holdout again for any lane.

Nothing in this file is a performance number from a day after 2014-12-31; the only figure is the recorded <= 2014 parity
value 30.53%. "Reading a row after 2014" means computing on it: the loaders of the chain read whole files into memory
whatever the end date. Before registration the only code that computed on real rows after 2014-12-31 was an early causality
self-test of dummy candidates (noise rules, planted leaks, a constant sleeve), which ran on the full calendar inside the
evaluator and returned PASS / FAIL and counts of cuts; no growth figure, level or position after 2014 was produced. From
evaluator version 4 on, every self-test and the whole independent verification ran in a declared test world (the calendar
cut at 2014-12-31, or the full calendar dates with every market value after 2014 replaced by old rows before anything is
computed), in which the evaluator cannot build a real calendar after 2014.

## 0. What changes, what does not, and what this structure cannot give

- Old rule: design and measurement use data <= 2014-12-31 only; 2015+ is a one-time holdout.
- New rule: the calendar 1986-01-02 .. 2026-08-31 is cut into fixed 3-year blocks. DESIGN blocks may be used for design, also
  the ones after 2014. SEALED blocks (2016-18 and 2022-24) stay unseen until a logged G3 opening.
- The locked simulation standard MS1 (research/measure_std/std.py, source <= 2014) is not changed.
- Who may read rows after 2014-12-31: only the evaluator (research_xv1/code/xv1.py and the scripts that call it). Outside the
  evaluator, design and fitting may use (1) the evaluator's outputs for DESIGN blocks and (2) MS1 objects whose source ends
  2014-12-31 (std.contexts, std.measure, iv.POOLS through iv.load / iv.run, ig.HIST). Evaluator outputs for WEAK blocks are
  read once per configuration under G2 and are not design material.
- Banned under XV1 outside the evaluator's own chain, because they take no end date and always read to 2026-10-07:
  common.market, common.hist_ctx, common.boot_ctx, mkt.ndx, mkt.spx, mkt.etf_market, bk.build_ctx, bk.ensure, bk.pool, bk.run,
  bk.ref, bk.evalS, bk.evalP, bk.hist_run, bk.suite, the bk F_KEYS pools, every holdout pool behind IV_ROLE=verifier, and the
  caches /home/claude/c3b_cache, /home/claude/c3c_cache, /home/claude/iv_cache for any pool whose source ends after
  2014-12-31. jp.build, jp.load, iv.load, iv.run, ig.load, ig.run and std.hold are allowed only with an end date <=
  2014-12-31. With a later end date only the evaluator calls jp.calendar. Every array that holds a row after 2014-12-31 lives
  in memory only.
- The forbidden-file list (section 6) is part of this text.
- The reference is not out of sample on the sealed blocks. By code, the lanes that selected v1's base signal and brake drew
  their search pools from the whole 1985-2026 history and gated on the real 1986-2026 path. "Sealed" therefore means sealed
  for candidates registered under XV1. The bias runs against candidates (the reference may look better on the sealed blocks
  than it truly is), so a pass is conservative and a fail may partly reflect it.
- General public knowledge of post-2014 market history held by any designer cannot be removed. A family that was conceived
  with evident hindsight about a sealed period (for example semiconductor 3x funds after 2022) carries that sentence in every
  G3 report.
- Scope. XV1 scores one kind of candidate: one account that holds the 3x NDX fund, cash that earns nothing and registered
  extra instruments, under the engine terms of section 2. The brake is v1's brake or none, so a new input acts only through
  the base level or through the weights of extra instruments. Anything that cannot be written that way (another brake,
  another account mapping, several accounts) is outside XV1 and reads no row after 2014-12-31.
- From registration on, no thread opens, under any earlier pre-registration, a holdout or history that contains a day of
  block 10 or 12. Open holdout plans of earlier lanes are void. The live monthly check (tools/s085_now) is the only process
  outside the evaluator that reads those rows; its outputs stay forbidden for design and evaluator work.
- Channels. Design work (also by helper agents) sees rows after 2014 only through evaluator outputs for DESIGN blocks. It
  does not call a market-data connector, a web source or a file reader for any series on dates in blocks 10 or 12, and it
  does not use figures for those dates from chat history, memory notes or reports. Shared memory, pages and reports written
  under XV1 hold only hashes, ledger line numbers, evaluator outputs for DESIGN and WEAK sets and G3 verdict words. Known and
  accepted: earlier lanes printed v1 figures for spans after 2014; whoever has seen one can subtract the section-3 figures
  and obtain v1's growth in blocks 10 + 12. That one number is treated as known; it says nothing about a candidate's paired
  difference there.
- Meaning of a pass. CONFIRMED = better than v1 on two blocks inside 2016-24 that lie between blocks used for design. It is
  cross-validation inside one era, not out-of-time evidence; only the forward record is. A CONFIRMED candidate replaces v1
  in live use only by a separate owner decision.
- What the sealed blocks cannot test. Which way the index, and each sector, went in 2016-18 and 2022-24 is public. A
  candidate that simply holds more, or holds something else all the time, is a bet on that public knowledge; the sealed
  blocks cannot confirm it. The gates therefore separate d (candidate minus v1) from d* (the part of d that comes from the
  timing of the holdings, section 2), and CONFIRMED needs both. The same holds for a rule on a periodic calendar field
  (month, weekday, year modulo 4): which calendar slots did well in the sealed years is public, so such a configuration can
  reach CONSISTENT at best.
- Power, stated in advance. Scored rows: design 4,513 (17.9 years), weak 3,468 (13.8 years), sealed 1,381 (5.5 years). On the
  sealed blocks CONFIRMED needs an observed paired difference of about 1.1 x TE per year (TE = annualised tracking error
  against v1). A true edge of 1.0 x TE per year is confirmed in about 42% of the cases, one of 1.1 x TE in about 49%. This
  structure can confirm only large edges; small improvements (a few pp/yr at TE 20%) cannot be confirmed here and are not
  claimed.
- Kept by code, and kept by procedure. Code enforces: the block table, the removal of sealed rows from every design
  figure, the refusal of the main account outside a logged opening, the G3 budget, the hash checks, the ledger chain, the
  batch numbering, the family rules, the voiding rules and the source gate of candidate files. Procedure, not code, keeps:
  who reads rows after 2014 outside the evaluator; the reading of candidate source for rules on the calendar position that
  no mechanical test sees (a row counter, a count on a calendar field, an own cumulative level compared with a fixed
  number); the per-batch statement on rules scored by earlier lanes; the registration data of new inputs (publication time,
  lag, carry, revisions); the "superseded" marks after a defect; and that nobody writes ledger lines by hand (a hand-written
  G1 line is refused because no results file stands behind it; other lines are protected only by the hash chain and by the
  copy of the ledger that is committed to the repository after every step). The evaluator guards against mistakes of its
  own operator, not against an operator who edits it.

## 1. Blocks (mechanical)

- Calendar: the Ken French trading dates from 1984-01-03 to 2026-08-31 as returned by jp.calendar. The evaluator checks that
  the last row is 2026-08-31 and that its block table equals the table below, and stops otherwise. Rows after 2026-08-31 that
  exist in the panels are never used.
- Block b = (calendar year - 1986) // 3, b = 0..13. A row belongs to the block of its calendar year.
- Length and origin. Blocks are 3 calendar years from 1986, the first account year. Three years is the shortest length
  that is at least twice the longest fixed signal memory (378 rows) and still leaves two sealed blocks after 2014. Both were
  fixed before the phase. No other length, origin or phase has been or will be scored on any data; a different blocking is
  a new registration with no access to rows of blocks 10 and 12.
- Phase: sha256 of the UTF-8 bytes of the string "FRESH2-XV1 block phase coin, 3-year calendar blocks from 1986", without a
  trailing newline, = 2bb460d197de90a9a688740d62c88c1c1f7bc3f921ee893cfa8cb18bf5fdcb61. The last hex digit is odd, so odd b
  = DESIGN and even b = VALIDATION. The digest was computed once on 2026-11-11 before the owner's message of 12:49Z, so the
  phase was known when the switch was proposed. It is a tie-break fixed by the registrant, not a proof of randomness, and
  it is not re-thrown.
- Embargo: the first 63 rows of every block are neither scored nor reported (no return, position, trade or count). "Per
  block" always means the scored rows, row 64 to the last row of the block. Every join of the design account (section 2) is
  the first row of a block, so the embargo covers it.

| b | kind | years | first row | first scored row | last row | rows | scored |
|---|---|---|---|---|---|---|---|
| 0 | WEAK | 1986-88 | 1986-01-02 | 1986-04-03 | 1988-12-30 | 759 | 696 |
| 1 | DESIGN | 1989-91 | 1989-01-03 | 1989-04-04 | 1991-12-31 | 758 | 695 |
| 2 | WEAK | 1992-94 | 1992-01-02 | 1992-04-01 | 1994-12-30 | 759 | 696 |
| 3 | DESIGN | 1995-97 | 1995-01-03 | 1995-04-03 | 1997-12-31 | 759 | 696 |
| 4 | WEAK | 1998-00 | 1998-01-02 | 1998-04-03 | 2000-12-29 | 756 | 693 |
| 5 | DESIGN | 2001-03 | 2001-01-02 | 2001-04-03 | 2003-12-31 | 752 | 689 |
| 6 | WEAK | 2004-06 | 2004-01-02 | 2004-04-02 | 2006-12-29 | 755 | 692 |
| 7 | DESIGN | 2007-09 | 2007-01-03 | 2007-04-04 | 2009-12-31 | 756 | 693 |
| 8 | WEAK | 2010-12 | 2010-01-04 | 2010-04-06 | 2012-12-31 | 754 | 691 |
| 9 | DESIGN | 2013-15 | 2013-01-02 | 2013-04-04 | 2015-12-31 | 756 | 693 |
| 10 | SEALED | 2016-18 | 2016-01-04 | 2016-04-05 | 2018-12-31 | 754 | 691 |
| 11 | DESIGN | 2019-21 | 2019-01-02 | 2019-04-03 | 2021-12-31 | 757 | 694 |
| 12 | SEALED | 2022-24 | 2022-01-03 | 2022-04-04 | 2024-12-31 | 753 | 690 |
| 13 | DESIGN | 2025-26 | 2025-01-02 | 2025-04-04 | 2026-08-31 | 416 | 353 |

- Sets are a closed list: D7 = {1,3,5,7,9,11,13}; W5 = {0,2,4,6,8}; POST3 = {block 9 from its first row of 2015, 11, 13}
  (252 + 694 + 353 scored rows); S2 = {10,12}, available only inside a G3 opening. The scoring functions take no other
  set, start date or end date. The calendar end is one of two registered ends: 2026-08-31, and 2015-12-31 for the account
  identity P4 and for the fixed-level check of G3. T0 is part of a registered configuration. The seven even blocks together
  are never scored.
- 63-row sub-blocks (test T, section 4): design 70 (11, 11, 10, 11, 11, 11 and 5 in blocks 1 .. 13), weak 53, sealed 20.
- Block 13 is closed at 2026-08-31 for XV1. The calendar is extended only by an amendment (section 7) with new file hashes,
  after the parity tests show that every earlier row is bit-identical. Rows added by an extension belong to no block and
  serve only forward records (section 4). A day that was available to the evaluator before a candidate's registration never
  counts as forward evidence for it.
- WEAK blocks were used to build v1 and every earlier lane. A result on them is a no-harm check, never validation.

## 2. Evaluator

### Chain and engine
- Inputs: exactly the MS1 real-path chain, only the end date moves: R, M = jp.calendar('1984-01-03', end);
  X = jp.mkX(R, M, 'NDX'); F = ov.flags_hist(X); the view starts ov.WARM = 300 rows before 1986-01-02.
- Engine: xeng.runx, a line-by-line extension of the locked beng.run1 by extra instruments. With no extra instrument it is
  bit-identical to beng.run1 / std.engine (test in section 2, "Tests"). Every account, also the reference, runs through it.
- Engine terms are set by the evaluator alone and are the same for candidate and reference: beng.F1 (delay 2, cost 0.003
  per side on traded notional, tax 0.22 on the yearly net realised gain above the deduction, deduction 0.25 of the opening
  equity as a fixed amount, harvest 3 with threshold 1.0, er3 0.0245, step 0.5) with idle-cash interest ZERO (cspr = 10.0).
  "delay 2" = the level decided with information up to the close of row t is traded at the close of row t+2 and earns from
  row t+3. A candidate supplies only: base level B (0 .. 3), the brake (v1's brake rx.av23s with v1's parameters and order
  step 0.1, or no brake, std.ident, with its own order step), and optionally extra instruments (daily returns G net of fund
  costs, target weights Wt, mode, inc, rebalance flags RB, bands up and dn). Extra instruments pay the same cost per side
  and are taxed in the same yearly pool. A candidate cannot set or override any engine term, and cannot supply another brake
  function or other brake parameters.
- Extra instruments, fixed rules. mode 0: v1 has priority; extras use only the cash v1 leaves idle and are cut pro rata when
  v1 needs it back. mode 1: extras have priority; the 3x NDX fund gets (v1 level / 3) of what is left, and every re-set of
  an extra re-sets the fund too, so money skimmed from an extra goes to v1 and a refill comes out of v1; a change of v1's
  level leaves the extras untouched. inc 0: a target weight means "hold this share of the account"; the position drifts
  between re-sets; a re-set happens when the target changes, when a rebalance flag decided at close t comes into force
  after the delay, when at a close the actual weight is above target x (1 + up) (profit skim) or below target x (1 - dn)
  (refill), again after the delay, and, in mode 0, at every change of v1's level (inside the idle cash). inc 1: tranche
  rule (a higher target adds fresh money, sized on the equity at the fill; a lower target sells pro rata; flags and bands
  are ignored); in mode 0 a tranche is never re-set: it is cut pro rata when idle cash is short and not bought back, and a
  tranche that does not fit lapses.
- Where this text is silent, the docstring and code of xeng.py (hash registered) govern. In particular: the yearly loss
  harvest and the step-up of the cost basis by the deduction exist for the 3x NDX fund only, not for extra instruments (so
  the 1x-hold context row has no harvest); the yearly tax is paid by a proportional sale of every holding including cash,
  at no cost, and the gains of that sale fall into the new tax year; trading cost is taken pro rata from all holdings; in
  mode 0 the target of an extra is Wt x total equity, capped at the equity outside the fund, and if the re-set of one
  extra does not fit all extras are scaled; a band compares the close weight after trades with the target in force and
  re-sets to the target of that row, and a breach gives `delay` consecutive re-sets; the fund is bought on the first
  account row, an extra not before the third; V carries no liquidation cost.
- Output rules, checked on what candidate code returns (a breach voids the configuration): B finite and inside 0 .. 3;
  mode and inc 0 or 1; the brake as above; weights finite, inside 0 .. 1, at most 1 in total per row; instrument returns
  finite and above -100% or missing (NaN); rebalance flags 0 or 1; bands >= 0 and finite; no weight on an instrument on
  a row on which it is missing or on one of the four rows before such a row; the account value finite and positive on
  every row.
- Instrument check. Every instrument a candidate holds must be one that could be held: a registered return input; the
  modelled daily-reset fund on the index, on the chain's 10-year bond return, on a registered 1x return input or on the
  splice of two of them; or the splice of a registered fund return with such a model (the actual fund where it exists, the
  model before). Fund model on a 1x return r with cash rate rf: L = 3, 2: L r - (L - 1) rf - (0.0095 + 0.0075 (L - 1)) / 252
  (3x: 0.0245 per year, the same drag as the 3x NDX fund); L = -1: -r + rf - 0.0095 / 252; L = 1: r - 0.002 / 252. The
  evaluator rebuilds each of these from its own arrays and compares (tolerance 1e-12); a return column that matches none
  voids the configuration.
- Reference REF = v1 = std.s085 = (bk.C3sig, rx.av23s, rx.P_av23s(0.85), fstep 0.1). REF is v1 in every gate for the whole
  life of XV1, also after a candidate is CONFIRMED. A CONFIRMED candidate may replace v1 in live use; it does not become
  REF. Changing REF needs a new pre-registration with its own ledger and no access to blocks 10 and 12.
- Context rows (information only, in the same design account): 3x hold (B = 3, no brake); 1x hold = one extra instrument
  (index return - 0.2%/yr) at constant weight 1, bought once, taxed like everything else, without the harvest.

### Accounts
- Design account: ONE continuous account on the design calendar = the evaluator calendar with every row of blocks 10 and 12
  removed and the remaining rows joined in order (rows to 2015-12-31, then 2019-01-02 .. 2021-12-31, then 2025-01-02 ..
  2026-08-31). Signal, weights, features and instrument returns are computed once, causally, on the full calendar and then
  indexed by the design rows; the index return, the cash rate and the instrument returns of a removed row never reach the
  engine. It scores every DESIGN and WEAK block, for candidate, REF and the context rows alike. Up to 2015-12-31 it is the
  account of the full calendar, bit for bit (checked). The 300 rows before 1986-01-02 are engine warm-up. Orders pending at
  a join (decided on the last two rows before it) are executed on the first rows after it.
- Main account: the full calendar in one account. It scores blocks 10 and 12 only and is run for scoring only inside a G3
  opening: the function refuses unless the last line of the ledger is the G3-OPEN line of an opening in progress, which
  only the G3 function writes, under its lock. Outside an opening three things run a full-calendar account inside the
  evaluator and return nothing computed from a sealed row: the prefix test (PASS / FAIL), the v1 shadow levels (a level
  path that only candidate code reads) and the parity checks P1 and P3 (booleans and counts on rows up to 2014-12-31).
- Why the design account is spliced and not restarted. v1's brake works on the drawdown from the all-time account peak and
  has one active rule on account age and peak (cush2.ck: after 756 account rows, if ln(peak) / years < 0.12 the cushion is
  multiplied by 0.8). A fresh account at the start of block 11 or 13 starts at its peak with age 0, so it would not measure
  v1 as it runs with a history. In synthetic worlds a brake candidate's paired difference had the same sign as in the
  continuous account in 45-59% of paths with fresh block accounts and in 77-80% with the spliced account. Figures of blocks
  11 and 13 are spliced-account figures: account state carried from 2015-12-31 (2021-12-31), market of the block. REF is
  v1 on an account opened 1986-01-02 with equity 1; XV1 does not claim that it equals an account opened on another date.
- Why not the full-calendar account for the design blocks: its state at the start of block 11 depends on the returns of
  block 10, so every block-11 figure would carry the account's profit and loss on sealed rows. In the spliced account the
  returns of removed rows never reach the engine (self-test: with the removed rows of return, cash rate, features, signal
  and weights replaced by noise the design account is bit-identical).
- What still crosses a sealed block: signals with memory (SMA200, 252-row high, 126-row yield change, 378-row inversion
  latch, the trend-gate state, index drawdown from its all-time high, any registered candidate signal, and the v1 shadow
  levels, which on removed rows are v1's levels in the full-calendar account). All of these are functions of market inputs
  on those rows, which a trader knew at the time and which candidate code can read anyway; that is accepted. A join is a
  three-year jump in the feature rows seen by the brake.
- Tax years are 252-row counts from the account's first row, not calendar years.

### Score
- Score equity V = liquidation value at the close of the row = equity minus 22% tax on every realised and unrealised gain
  not yet taxed (above the deduction where there is one). This is the after-tax wealth MS1 reports: on the <= 2014 calendar
  V equals, row by row, the final wealth of a locked-engine run cut at that row.
- x_k = ln(V_k / V_{k-1}) on scored rows. Block score g_b = sum of x over the scored rows of block b; annualised
  252 * g_b / n_b. Set score = 252 * sum(g_b) / sum(n_b). Paired difference d = candidate minus REF on the same rows.
- Timing difference d*. For a set, the static-equivalent benchmark holds, constantly, on the scored rows of the set on or
  after T0: kappa times the REF account, delta0 of the 3x fund and w_j of each extra instrument; the rest is cash that
  earns nothing. kappa and delta0 are the least-squares line of the candidate's actual 3x-fund weight on REF's
  (a_cand = kappa x a_ref + delta0; kappa = 1 if REF's weight does not vary), so that a candidate that scales v1, adds a
  constant amount of the fund or dilutes v1 with a sleeve is matched without v1's own timing being counted as the
  candidate's; w_j = mean actual weight of extra j over the rows on which the instrument exists. Its daily log return is
  m_t = ln(1 + kappa x (exp(x_REF,t) - 1) + delta0 x R3_t + sum_j w_j x G_j,t), with R3 the modelled daily return of the 3x
  fund and G_j the daily return of instrument j (no cost and no tax on the constant holdings). d*_t = x_candidate,t - m_t.
  A candidate that only holds more, less or something else on average has d* near 0 whatever the market did; a candidate
  whose gain comes from when it holds keeps it in d*. In synthetic worlds a pure exposure candidate tied to v1's level was
  typed "timing" in 0 to 0.9% of cases with this benchmark. For the sealed set kappa, delta0, w_j and d* are computed
  inside the evaluator and never reported.
- Known noise, fixed by this text so that nobody can pick it: the tax-year phase (the account starts on 1986-01-02). In
  synthetic worlds a shift of the start by a few rows moved a set-level paired score by about 1 to 2 pp/yr (standard
  deviation), without bias. One account per side is scored; no average over start dates is taken.

### Outputs (sealing)
- The evaluator returns scalars only, and only these: (a) per non-sealed block and per listed set: annualised growth, paired
  difference, row counts, tracking error, harm limits, test statistics, active-row counts; (b) for accounts: shares of
  scored rows at each held level, number of level changes, mean level, mean extra weight, mean difference of the 3x-fund
  weight against REF, and the drawdown of the curve re-based to 1 on the first scored row of the block; (c) for the design
  set of a configuration: kappa, delta0 and w_j of its benchmark, and the skewness and lag-1 autocorrelation of its 63-row
  sub-block means; (d) the model check and the data checks; (e) PASS / FAIL of the tests, a void reason, and counts of cuts
  only where they do not depend on sealed rows. One exception: the 63-row sub-block means of design-block paired
  differences are kept for the family-wise test; they are design material.
- It never returns, prints, stores or plots: an equity level or wealth multiple; a running peak; a drawdown measured from a
  peak set before the block's first scored row; cumulative tax, cost, trade count or cost basis; a growth figure over any
  span that contains a sealed row; any quantity that uses equity on two rows with a sealed row between them; any array of
  daily values after 2015-12-31.
- For sealed rows it returns nothing, except the one-word verdict of a logged G3 opening and, once G3 is closed for good,
  the G3-RELEASE report (section 4). No error text raised while sealed rows are scored leaves the G3 function.
- Data checks are the only figures allowed to cover sealed years, as whole-number counts and dates.

### Candidate code
- A candidate is a function make(view) -> dict(B, bfn, bp, fstep[, G, Wt, mode, inc, RB, up, dn]). Its only data inputs:
  view.c (the ov.Ctx of the calendar rows), view.m (the macro levels y10, y3m, cs of the REF chain), view.feat (the brake
  features), view.x (the registered extra inputs aligned to the same rows), view.T (the number of rows) and
  view.ref_target / view.ref_held (the level v1 wants after its brake at the close of row t, and the level v1 holds on row
  t, from v1 alone in a shadow account under the base engine terms). In the design view the rows of the design account
  carry v1's levels in the design account (the account the candidate is scored in) and the removed rows carry its levels
  in the full-calendar account; in the main view (G3 only) every row carries the full-calendar account.
- Two sides. The object handed to candidate code holds copies made for it, all write-protected; the kind of account, the
  list of design rows, the calendar position (view.c.ii) and the dates are not on it. The engine never reads from that
  object: it uses the evaluator's own arrays (returns, cash rate, features, design rows, shadow levels), which candidate
  code never receives. After every call the evaluator checks that no input on the candidate's object was changed or
  replaced.
- Source gate, applied to a candidate file and to every helper file it imports from its own folder before a batch is
  registered and before every load. Allowed: module-level imports of numpy, of xv1 and of files of the candidate's own
  folder; of xv1 only xv1.ref (v1 itself) and xv1.std.ident (no brake), and what candidate code imports under that name is
  a stand-in that holds nothing else. Not allowed: any other import, a from-import, an import inside a function, a name or
  attribute that begins with an underscore other than the file's own module-level names, the file and reflection built-ins
  (open, exec, eval, compile, getattr, setattr, delattr, hasattr, globals, locals, vars, dir, input, breakpoint,
  memoryview, id, type, object, super, print, help, exit, quit, classmethod, staticmethod, property), attributes that reach
  the interpreter, files, random numbers or an array's memory (sys, os, modules, setflags, flags, ctypes, tofile, dump,
  dumps, save, savez, savez_compressed, savetxt, load, loadtxt, fromfile, genfromtxt, memmap, random, base, data, ii, keep,
  account, lib, testing, f2py), `global` and `nonlocal`, and assigning to an attribute of an imported module.
- Reading the calendar position, a date, a file, a cache or a module-level data array is forbidden. Candidate source holds
  no date literal. Periodic calendar fields (month, day of month, weekday, calendar year modulo 4) may be registered as
  inputs; no absolute date, year or row position may be used. The gate and the tests below do not see every way to read
  the calendar position (a row counter, a count on a calendar field, an own cumulative level compared with a fixed number):
  these are excluded by reading the candidate source before registration. A period counted in rows from the first row on
  which an input exists (for example a yearly rebalance every 252 rows) is a periodic rule and is allowed.
- Level-scale test, before the first scored call of a candidate: the index level handed to candidate code (view.c.lvl) is
  multiplied by 2 and by 0.5 (exact in binary arithmetic); every output of the candidate and the features must stay
  bit-identical, else the configuration is void. A rule may use ratios of a price level, never its absolute height: a
  threshold on the height picks out an era without naming a date. The test covers the index level only. Registered level
  inputs are limited to an allow-list of series that carry no price height (lvl:_VIX3M, lvl:_VIX9D, lvl:_TYX, lvl:_FVX);
  every other price series enters only as a daily return. A threshold on a yield, a spread or a volatility index is
  allowed. REF passes this test (self-test: a planted height threshold must be reported as void).
- Candidate code runs inside the evaluator with its output streams closed. While it runs, the data readers (mkt._panel,
  mkt.fred, mkt.pser, md.load, md.kf, jp.calendar, jp.build, xdata.get, xdata.read_chips, numpy load, save, fromfile,
  loadtxt and genfromtxt, pandas read_csv) are replaced by functions that raise. A configuration whose code raises in any
  test or scoring call, or breaks an output rule, is void.
- One call. The full-calendar call of a configuration is made once, on a newly executed copy of its module and helper
  files: the same result is tested (prefix test, level-scale test, instrument check, T0 rule) and scored. In the stress
  runs of G1(d) that same output is used: the candidate's signals are held fixed while the engine terms move.
- Prefix test, before a configuration is scored (design view), once more on the main view before a G3 opening, and once on
  REF as a control (REF must pass or the evaluator is not used). The cut runs use another newly executed copy of the
  candidate module and go from the earliest cut to the latest, so nothing kept from a call that saw more rows can reach a
  call that should see fewer. For each cut row c: (a) deletion: the calendar and every registered input are cut after c
  and the candidate is called again; (b) noise: the rows after c are replaced by random values and everything is rebuilt.
  B, G, Wt, RB, the bands, the brake and its parameters, fstep, mode, inc, the feature rows and every column of the account
  record (equity, level in force, brake target, base level, liquidation value, weights) on the rows up to c must be
  bit-identical to the full run. Cuts: the last row of every block, the account rows 0, 62, 63 and 259 and 60 rows drawn
  from the whole account (both variants; 200 drawn rows for REF), and, deletion only, the event rows: every row on which
  the candidate's signal, a target weight or a rebalance flag changes, every row on which v1's own signal changes, and the
  first and last row of every run in which the candidate's level differs from v1's (the row itself and the row before).
  All event rows are cut up to 1,000; above that the 500 largest changes and 500 drawn ones. For REF every event row and
  every 21st row are cut. Event rows are cut because a look-ahead hidden behind a threshold shows only where it acts. The
  generator is seeded from the sha256 of the batch hash and the batch's ledger line (which carries its UTC time), for REF
  from the registration hash. A candidate that raises on a cut fails that cut. Output: PASS or FAIL. FAIL = the
  configuration is void, still counts in its batch, and no score is produced. Self-test: a planted 3-row look-ahead, a
  planted full-sample quantile, a planted centred 5-row window, a look-ahead through the v1 shadow level and a candidate
  that keeps the longest array it has seen between calls must all be reported as FAIL; a full-sample number hidden in the
  brake parameters is void by the output rules.
- Raw-level test of extra inputs, once per batch before any configuration of it is scored: the raw readers behind the
  registered inputs are wrapped in memory; for each cut (a) every raw row dated after it is deleted, (b) it is replaced by
  noise, (c) the input is rebuilt on the calendar cut at that row; the aligned input arrays up to the cut must be
  bit-identical. Cuts: the last row of every block, 12 drawn rows, and the 6 rows before and after every row on which an
  input starts, ends or has a gap and every calendar row inside a series' life that has no raw row, i.e. a carried-forward
  value (at most 600 of these, drawn). A failing input voids every configuration that uses it. Self-test: a planted 3-row
  backward fill must be reported as FAIL.
- Every input that REF does not use is registered with the candidate: source file and sha256, first and last raw date, the
  time at which the value for date t becomes public, the lag applied in rows, the maximum number of rows a value may be
  carried forward (daily series 5), and whether the series is revised (revised series only as first-release vintages).
  Price series enter only as daily ratios of adjusted closes. Before a fund's first date the candidate uses the modelled
  series of the instrument check or holds the REF level.

### Tests that must pass before any row after 2014-12-31 is scored
- P1 slice parity: X, F, bk.features, B, the held-level path, equity and liquidation value of REF from the full-calendar run
  are bit-identical to the <= 2014 calendar run on every row up to 2014-12-31.
- P2 MS1 identity: on the <= 2014 calendar the REF account is bit-identical to std.engine on
  std.contexts()['real_ndx_86_14'] with cspr = 10.0, and its CAGR after final liquidation tax is 30.53% (difference below
  0.005 pp). This figure is a constant of this text; the evaluator does not open a results file.
- P3 raw-level test of the REF chain: the raw readers (mkt.pser, mkt.fred, mkt.shiller_gs10, md.kf, mkt.spx) are wrapped in
  memory; no file is changed. For each cut (the last row of every block and 12 drawn
  rows) every raw row after the cut is (a) deleted and (b) replaced by noise; the chain is rebuilt; every cell of X, F,
  features, B, level path, equity and liquidation value up to the cut must be bit-identical. Control: y10 taken 5 rows
  early must be reported as FAIL.
- CAL: last row 2026-08-31; no weekend date; 248..254 rows per full year; after 2014 no NDX panel date missing from the
  calendar and no calendar row without an NDX observation.
- D1 coverage, per raw series (^NDX, ^IRX, ^TNX, ^VIX, DBAA, DAAA) and per calendar year: number of calendar rows with no
  raw observation and the longest run of such rows. The yearly maxima of the full years up to 2014 are the thresholds.
  Pass = last raw date >= 2026-08-31 (DBAA, DAAA: >= the calendar row before it) and no year after 2014 above a threshold.
- D2 fallbacks: rows from 1986-01-02 on where y10, y3m or cs come from a monthly fallback series. Must be 0 after 2014.
- D3 values, per calendar year. Stop counts (must be 0 after 2014): y10 <= 0; a zero ^IRX row between two rows >= 0.50;
  an NDX return above 20% in absolute value; duplicate raw dates. Threshold counts (no year after 2014 above the 1986-2014
  yearly maximum): day-to-day change above 0.60 pp in y10, above 1.00 pp in y3m. Report-only: rf < 0; NDX return exactly 0.
- D4 registered extra inputs of the first batch and the TQQQ return of the model check: per input the first and last valid
  date, the rows without a value between them, and the rows after the last valid one. Pass = no such row after 2014.
- P4 account identity: REF's design account from the full calendar equals, bit for bit on blocks 0-9, the account of the
  calendar cut at 2015-12-31 (a boolean).
- If any of these fails, nothing after 2014 is scored: the checks script writes a ledger line, and no batch is registered
  without a passed line under the hashes in force. An amendment may only add a mechanical repair rule that is registered
  before the repaired rows are scored.
- Hashes. The registry is research/xv1/HASHES.json together with the ledger. Registered with this text: the sha256 of
  every data file read by the chain and by the extra inputs (the two price panels, the calendar file, the DBAA, DAAA, BAA,
  AAA and TB3MS files, the Shiller file, the SPX and T-bill files, the brake parameter file fin_params.json, the Ken French
  Chips file), of the evaluator files (xv1.py, xeng.py, xdata.py) and of every project code file loaded by a full exercise
  of the evaluator on the <= 2014 calendar, the package versions (python, numpy, pandas, numba, llvmlite, scipy, xlrd) and
  the registered constants. Every function that scores (the reference table, the model check, batch registration, batch
  scoring, G0 line, G2, G3) recomputes all of them and stops on a mismatch, also when a project code file is loaded that
  the registry does not hold. In the real calendar the evaluator also stops if a registered constant (the sealed blocks,
  the embargo, the block length, the calendar ends, the engine and stress terms, the thresholds) no longer has its
  registered value. Candidate files and their helper files are covered by the configuration hashes (section 4). Changing
  an evaluator file after registration follows section 7.

## 3. First measurement after registration (no candidate, no pass / fail)

- REF, 1x hold and 3x hold on every DESIGN and WEAK block: annualised log growth of V per block and for D7, W5 and POST3;
  for REF also the level shares, level changes and in-block drawdown on scored rows.
- Model check, information only, scored rows of non-sealed blocks where TQQQ exists: modelled return 3r - 2rf - er3/252
  against the daily ratio of the fund's adjusted close; annualised gap (actual minus modelled). Counts first: rows without a
  fund observation and rows where the two differ by more than 5 pp (both must be 0, otherwise the gap of that block is
  void). The index has no dividends, so a positive gap is expected. No engine term is changed because of this check.
- Reading fixed in advance (descriptive; POST3 has about 5.2 scored years, the standard error of each difference is of the
  order of 10 to 20 pp/yr): D_A = REF - 3x hold (what de-risking did) and D_B = REF - 1x hold (the whole package against the
  index) on POST3, each with the two-sided 90% interval of test T, and each a second time with tax 0 on all three accounts
  (a hold account never sells, so with tax 0.22 both comparisons are tilted against REF; the 1x hold has no harvest, which
  the tax-0 repeat also removes). A sentence is printed only if the whole interval is on the same side of 0 in both
  versions. D_A: below 0 "v1's de-risking cost growth in the post-2014 design blocks", above 0 "v1's de-risking added growth
  in the post-2014 design blocks". D_B: below 0 "the v1 package grew less than the 1x index hold in the post-2014 design
  blocks", above 0 "the v1 package grew more than the 1x index hold in the post-2014 design blocks". Otherwise, for either:
  "not distinguishable from zero on 5.2 years". No statement is made from a sign alone. No rule is changed by this result.
- If D_A or D_B is below 0 with its whole interval in both versions, every later XV1 report carries the line: "v1 did not
  beat [3x hold / 1x hold] on the post-2014 design days; beating v1 is not by itself beating the index." v1's live status
  is the owner's decision outside XV1 and does not change REF.

## 4. Gates for candidates

### Definitions
- Configuration = candidate source file + function + parameter values + registered inputs + T0. Its hash is the sha256 of
  the bytes of the source file, of every helper file that the source file imports from its own folder (directly or through
  another helper), and of the canonical JSON of the rest. Two parameter points are two configurations.
- T0 = first date on which all candidate inputs exist plus the candidate's own warm-up. It is registered with the
  configuration and may lie at most 756 calendar rows after the first row on which every registered input and the chain's
  VIX exist (else the configuration is void), so the start of a record cannot be picked. Before T0 the candidate must
  equal REF exactly: the evaluator checks, on every account row before T0 (sealed rows included; in a G3 opening again on
  the main view), that the base level is v1's and that there is no weight and no rebalance flag, and that the paired
  difference is 0; else the configuration is void. All statistics use scored rows on or after T0.
- Active row = scored row on or after T0 on which the candidate holds a different v1 level than REF or holds an extra
  instrument. (A non-zero paired difference alone does not count: after the first divergence the two accounts differ a
  little on every row.) Active block = at least 20 active rows.
- TE_b = sqrt(252) x standard deviation of the daily paired difference on the scored rows of block b on or after T0.
  TE_D = the same on all scored design rows (reported, used in no gate).
- Test T (no resampling): the scored rows of each calendar block are cut into consecutive sub-blocks of L rows
  (leftover rows join the last sub-block); m_j = mean daily paired difference of sub-block j; t_L = mean(m) / (sd(m) /
  sqrt(k)); p_L = one-sided Student-t tail with k - 1 degrees of freedom. Sign-flip check for differences that live in a
  few episodes: the sums of the active 63-row sub-blocks (those that contain an active row; A of them) get random signs,
  the other sub-blocks are not flipped; p_sf = share of sign assignments whose total is at least the observed total (all
  2^A assignments up to A = 20, which covers the sealed set; otherwise 100,000 drawn ones, seed = first 8 hex digits of the
  configuration hash). p = the largest of p_63, p_126 and p_sf. Consequence, stated in advance: with fewer than 6 active
  sub-blocks in the sealed set a candidate cannot be CONFIRMED.
- Harm bound for a block: an active block with d_b < -2.0 x TE_b x sqrt(252 / n_b). It bounds harm; it is not a
  significance test (with zero true edge about 85% of candidates stay inside it on seven blocks).
- Batch = a list of configurations registered together (file with sha256, line in the ledger) before any of them is
  scored on any design row by any means. The batch number is the next one in the ledger and cannot be chosen; a
  configuration hash that stands in an earlier batch is refused, as is a source that fails the gate. The evaluator refuses
  a configuration that is not in a registered batch. Every configuration of a batch is scored and reported, losers
  included; each scoring is a ledger line. A void configuration (source gate, raw-level, prefix or level-scale test, output
  rules, instrument check, T0 rules, an error in its own code) is reported as void with its reason, is not scored, does
  not stop the batch and is not refunded. Batch k (k = 1, 2, ...) has the family-wise level alpha_k = 0.05 / 2^k, so all
  batches together spend less than 0.05. A batch is scored once; an interrupted run is resumed.
- Family-wise p of a configuration = single-step max-t over the scored (non-void) configurations of its batch: t_63 of
  every configuration on the 70 design sub-blocks; the null distribution of the maximum from 200,000 draws in which the
  sign of each sub-block is flipped for all configurations together (seed from the sha256 of the batch hash and the
  batch's ledger line; no daily difference exists before the batch is registered, so a seed cannot be shopped). A
  sub-block before a configuration's T0 enters as 0. The same test is run a second time on d* (seed + 1).
- Assumption behind the stated error rates: under the null the sub-block sums are symmetric around 0 and independent of
  each other. The design blocks contain 2001-03, 2007-09 and 2020. With every G1 line the evaluator prints the skewness
  and the lag-1 autocorrelation of the configuration's 70 design sub-block means; they are quoted in the report that asks
  for a G3 authorisation.
- Family = a pre-registered lane, defined by its new input or rule class. Mechanically: (1) one source function is one
  family in all batches (the same file and function may not carry two labels; a label may join several functions);
  (2) two configurations whose design sub-block means (the 70 values of the family-wise test) have an absolute correlation
  of 0.7 or more are one family, whatever their labels. A family goes on from G1 once in the whole of XV1: a configuration
  that is one family (by label or by correlation) with a configuration that went on in an earlier batch does not go on.
- Earlier scoring. A rule that an earlier lane scored on a day after 2014, as an exact rule (same logic and parameters), is
  not eligible for G3; the registrant states for every batch that it holds none (v1 itself, the AV23 brake at other
  strengths, the v104 / v107 formula sets and the v002 sleeves are such rules). Overlap with REF does not make a candidate
  ineligible, and REF is a member of no family.
- Ledger: research/xv1/LEDGER.jsonl, append-only, written only by the evaluator, each line with UTC time, call type,
  configuration hash, set, and the hash of the file before the line was added. Line 0 is the registration. The chain of
  hashes is verified on every read; a broken chain stops the evaluator. A number in a report is valid only if its ledger
  line exists. The G1 record of a configuration is read from the results file of its batch, whose sha256 stands in the
  ledger. A copy of the ledger is committed to the repository after every step.

### G0 simulation (a screen, not evidence; required where it exists)
- G0 exists for a configuration that registers no extra input, holds no extra instrument and read neither view.m nor the
  v1 shadow levels in its full-calendar call (a rule on the index chain alone); the evaluator records this with the G1
  line. For it: c = std.contexts()['dev250_path']; candidate and REF through std.engine with cspr = 10.0; d = difference of
  CAGR after yearly and final liquidation tax per path. Pass = median(d) > 0 and a share of paths with d > 1e-5 of at least
  0.60. Reported next to it, candidate and REF: the share of paths that reach an 80% and a 95% drawdown; a configuration
  with dd80 > max(0.01, REF dd80 + 0.003) or dd95 > REF dd95 carries the label "more tail risk than v1" in every report.
  std.measure is not used (it runs the reference without the candidate's engine terms). The paths are resampled from
  history the designers have seen.
- A configuration that fails G0 is closed: no G2, no G3. Where G0 exists, G2 and G3 refuse until the ledger holds its pass.
- For every other configuration MS1 cannot resample the inputs: G0 is "not available" and every verdict carries the label
  "no simulation standard". An exposure-type configuration without G0 has passed nothing but a screen on design data; it
  is reported as "design-block result only, not validated".
- G0 is run only for configurations that passed G1 and were selected. Its function reads no row after 2014-12-31; it lives
  in its own file, is written and independently reviewed before its first use, and its outcome is a ledger line that
  carries the sha256 of that file.

### G1 design (D7)
A configuration of batch k passes G1 if all hold:
- (a) set score d >= 1.0 pp/yr (log growth), with at least 3 active design blocks, at least 1,500 scored design rows on
  or after T0 and at least 1,500 scored design rows from its first active row on (a smaller d is inside the error of the
  fund model);
- (b) no active design block breaks the harm bound;
- (c) family-wise p <= alpha_k (on d);
- (d) with cost x2 (0.006 per side), with delay 3, with delay 1 and with tax 0, each applied to candidate and REF alike
  while the candidate's signals stay as they are: set score d > 0 in all four. (Tax 0 guards against a gain that is only
  tax timing.)
Type. A passing configuration is of type "timing" if its set score d* > 0 and its family-wise p on d* is <= alpha_k;
otherwise it is of type "exposure": its design gain is not separated from holding more (or holding something else) on
average. The type is printed with every figure of the configuration.
At most one configuration per family goes on. The passing configurations are taken in this order: timing type before
exposure type, then the smallest family-wise p (ties: the larger t_63); one is taken if it is not one family with a
configuration already taken in this batch or with one that went on in an earlier batch. G1 is a screen on data the
designers have seen. Passing it is never reported as significance.

### G2 old-data no-harm check (W5), not validation
- Given only to a configuration that passed G1 and was selected (and passed G0 where it exists), once (the evaluator
  refuses a second read). On scored WEAK rows on or after T0: set score d >= -1.0 x TE_W x sqrt(252 / n_W) (TE_W from the
  scored WEAK rows) and no active weak block breaks the harm bound.
- With fewer than 252 scored WEAK rows on or after T0, G2 is not available: nothing is read, the ledger says so, and the
  configuration is not eligible for G3 (it has no old-data check at all); it can only keep a forward record.
- Why not d > 0: REF was selected with data that contain every WEAK block, so a candidate of equal true quality is expected
  to show d < 0 there. G2 bounds harm on old data and nothing more; a pass is never cited as evidence. A fail closes that
  configuration and, by the family rule, its family.

### G3 sealed blocks (S2)
- At most 3 openings in the whole project, one per configuration hash. The G3 function opens for hash H only if: the
  results file of its batch (sha256 in the ledger) holds a G1 pass for H and H was selected; the ledger holds its G0 pass
  where G0 exists, its G2 pass and the owner's authorisation for H (the id of the owner's message and where the ledger
  stood); every registered hash, package version and constant is unchanged; fewer than 3 distinct hashes have a G3-OPEN
  line; and no other opening is in progress (a lock file). A configuration whose level does not depend on any input
  (cash, a fixed level, a constant extra weight with no v1 level) may not be opened. A configuration that is one family
  with an already opened configuration (label, or absolute correlation of the design sub-block means of 0.7 or more) may
  not be opened; the refusal does not consume an opening.
- Blocks 10 and 12 are scored from the main account (the full calendar in one account), for candidate and REF alike. Before
  the line G3-OPEN is written, the T0 rule and the prefix test are repeated on the main view (PASS / FAIL); a failure
  refuses the opening without using it up. The line G3-OPEN H is written and flushed before the main account is run for
  scoring and consumes one opening whatever follows; if the process ends before the verdict line, the same H with
  identical hashes may be re-run once and the retry is logged.
- Verdict (p = test T with the sign-flip check; all quantities computed inside the evaluator and never reported):
  - FAIL: set score d <= 0, or an active sealed block with d_b < -1.0 x TE_b x sqrt(252 / n_b) (TE_b from that block's own
    scored rows).
  - CONFIRMED: not FAIL, set score d >= 0.5 pp/yr, p <= 0.05 / 3 on d, and also set score d* > 0 with p <= 0.05 / 3 on d*,
    and the configuration was of type timing at G1 and registers no periodic calendar field as input.
  - CONSISTENT: not FAIL, set score d >= 0.5 pp/yr and p <= 0.05 / 3 on d, but not CONFIRMED. The candidate did better than
    v1 on the sealed blocks, and the evaluator cannot tell that from simply holding more (or something else, or a calendar
    slot) in years whose direction is public. It is not a confirmation; every report of it carries this sentence. The only
    tests of an exposure change are G0, where it exists, and the forward record.
  - INCONCLUSIVE: none of these. It is not a pass. Every report of it carries the sentence "with zero true edge this outcome
    occurs in about 47% of openings". The configuration does not replace v1 and is not described as validated.
  - REF was selected with data that contain, in resampled form and through a full-history gate, the sealed blocks. The FAIL
    rule is therefore tilted against a new candidate; the tilt is accepted, and a FAIL does not show that the candidate is
    worse than v1.
  - Size, stated in advance: with zero true edge one opening returns CONFIRMED in about 1.7% of cases or fewer (the d*
    condition and the sign-flip check only lower it). Three openings chosen without regard to earlier verdicts give at most
    about 5% in total; because a verdict word is visible before the next opening is chosen, the worst adaptive case found in
    simulation is about 6 to 7%. The family rule above removes the strongest of these cases (re-opening a near copy or the
    mirror image of an opened configuration).
  - Whether one of the three openings is spent on an exposure-type or calendar-reading configuration (which can reach
    CONSISTENT at best) is the owner's decision; the report that asks for the authorisation says so.
- The output of an opening is one word. d, d_b and p are not printed and not written to any file. After the third opening,
  or when the owner closes G3 for good, the evaluator re-runs each opened H (logged as G3-RELEASE, not an opening) and
  reports them together: for every opened H the set scores d and d*, the block scores d_b with TE_b, and p_63, p_126 and
  p_sf. The sealed d of a CONFIRMED configuration is then reported with the note "selected value, overstates the edge".
  The release function is written and independently reviewed before its first use.
- A configuration registered after any G3 opening may not contain, blend with or re-parameterise an opened configuration,
  and its registration says so. After the third opening the sealed blocks are spent: later candidates end at G2 and the
  forward record.

### Forward record
- May be kept for any configuration that passed G1, was selected and did not fail G0 or G2. Candidate minus REF on rows
  after the candidate's registration date R, read only at 12, 24, 36, 48 and 60 months after R; between these dates the
  live difference is not computed. The rows come from a calendar extension (section 7) and belong to no block; rows
  between 2026-09-01 and R are in no set. It counts as forward confirmation of a not-CONFIRMED candidate only if the 63-row
  p of test T is <= 0.0155 at one of these five readings (about 5% one-sided over the five readings with zero true edge;
  the sign-flip check is not used here, because with the 4 sub-blocks of the first reading it cannot fall below 1/16). The
  reader is written and independently reviewed before its first use.

## 5. Order of work

1. Self-tests on the <= 2014 calendar and on synthetic numbers: engine parity (bit-identical), P2, liquidation value
   against cut runs, prefix test (REF passes, planted leaks fail, also one that keeps state between calls and one through
   the shadow level), raw-level tests (pass, planted leak fails), level-scale test (planted height threshold fails),
   design-account mechanics with two old blocks playing the sealed ones (removed rows cannot change the account), batch,
   ledger and source-gate guards (planted violations are void or refused), and the whole chain G1 -> G2 -> G3 in a
   synthetic world with planted edges (every market value after 2014 replaced by old rows before anything is computed): a
   timing edge is CONFIRMED, a reversed edge FAILs, a pure exposure candidate is CONSISTENT.
2. Independent verification of the evaluator code and of the sealing, on synthetic worlds and on the <= 2014 calendar
   only; defects are fixed, the self-tests re-run and the changed parts verified again.
3. Registration: this text with its sha256, the hashes of the data files, of the code files, the package versions and the
   constants, and the forbidden list; ledger line 0 holds the sha256 and the id of the owner's message. No growth figure,
   level or position computed from a market value after 2014-12-31 is produced before this step.
4. CAL, P1, P3, P4, D1-D4 on the full calendar (counts, dates and booleans only); their ledger line.
5. Section 3 measurement on the design account.
6. Candidate batches: registered, scored on D7, G1; G0 and G2 for the selected passers; G3 only with the owner's
   authorisation.

## 6. Forbidden files (part of this text)

Never read, under /mnt/project-files/: research/onf1/holdout/, research/s085_contra/holdout/, research/theory_sim/holdout/,
research/v002/holdout/, research/v002/RESULT_V002_KO.md, research/np1/holdout/, tools/s085_now/out/, tools/s085_now/cache/,
reports/best_results_summary_*, research/deep/, research/audit/, any diag/ folder, research/mass_scan/,
research/us_mix_sb_oos/, research/user_port/, research/c3_relax/RESULT_RELAX_KO.md and results/holdout_once.csv,
research/user_v104/RESULT_V104_KO.md and results/, research/user_v107/RESULT_V107_KO.md, results/, unseen/, final/ and
SHARE_V107_vs_s085_KO.md, research/user_port4/RESULT_KO.md and results, research/c3_stock_combo/, research/c3_create/fwd/,
research/ov1/lanes/*/data/ raw files. Added by the code audit of this review: research/crash_overlay/results/,
research/c3_brake/results/ (their harnesses read the whole 1985-2026 history).
Added 2026-11-11: research/soxx_anatomy_20261111/FORWARD_OBS_KO.md (rows after 2026-08-31).
A lane's results folder, RESULT files, ledgers and caches are forbidden for XV1 design work unless the lane's own
pre-registration states that its data end on or before 2014-12-31. The outputs of the live monthly check
(tools/s085_now) and any message that quotes them stay forbidden for every design and evaluator thread.

## 7. Amendments, defects, end

- After registration this file is never edited. An amendment is a new file with its own sha256 and a ledger line; it lists
  every output that existed before it and is reported to the owner in the next report.
- Never amendable: the block table and the sets of section 1, the sealing rules, the account definitions, the G3 rules,
  its level and its budget, the definition of d and d*. Amendable only before the first batch is scored: the G1 and G2
  thresholds, i.e. the smallest d of G1 (1.0 pp), the 3 active blocks, the 1,500 rows, the 20 active rows of an active
  block, the harm multiples (2.0 per block, 1.0 for the weak set), the 252 rows of G2 and the list of stress runs.
  Amendable at any time: data repairs under the data checks, a calendar extension (new rows for forward records only),
  registration of new inputs, and the three functions that are written and reviewed before their first use (G0, the
  release function, the forward-record reader).
- Evaluator defects. The evaluator is frozen by hash at registration. A defect found later is first reproduced on synthetic
  data or on the <= 2014 calendar; the fix gets new hashes and repeats the self-tests; earlier DESIGN and WEAK outputs are
  issued again and the old ones marked superseded in the ledger. A re-issued G2 is logged and replaces the first; the
  corrected verdict governs. A G3 opening made with a defective evaluator stays used up. It is run again once, with the
  owner's authorisation, only if the reproduction shows that the defect can change a verdict; both verdicts are published
  and the corrected one governs.
- The G3 budget ends at the first of: the third G3 opening, the owner closing G3 for good, or 2031-01-01. Batches, G1, G2
  and forward records may continue after it. Rows of blocks 10 and 12 are released only as section 4 says or by a new
  registration.
