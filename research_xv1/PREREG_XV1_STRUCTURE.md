# PREREG XV1: interleaved design / validation block structure

Registered text, version 7 (2026-11-12). Version 1 was a candidate text that went through four independent reviews
(sealing, causality, statistics, engine), a refutation pass on every finding and a final critic (15 further findings);
versions 2 to 4 carry the fixes that survived. Version 4 and its evaluator then went through an independent verification
with five lenses (engine, sealing, statistics, causality, text against code) on synthetic worlds and on the <= 2014
calendar: 50 findings, 3 of them critical; version 5 carries those fixes. Version 5 and evaluator version 5 went through a
second independent verification with three lenses (sealing, causality, statistics and text) on the <= 2014 calendar and
on synthetic worlds: 32 findings (sealing 15, causality 10, statistics 7). Among them: an error inside a G3 run could leave
the main account open; candidate code could reach the real built-in module, a package folder or a stale compiled file
through the import system, open files, read uninitialised memory, keep numpy's error call-back between calls or stop a
batch with SystemExit; a modelled 3x fund could be built on a 3x fund; rebalance flags on columns that are never held
could thin out the event cuts of the prefix test; an always-held tiny sleeve made every row active; checks of the main
view ran before an opening was logged. Version 6 and evaluator version 6 carry the fixes (each marked "v6" below). The
changed parts were then checked by two further independent readers (code-level sealing and causality; hindsight in the
candidate source and text against code): 2 more critical routes (the compiled brake function handed to candidate code
reached module globals and the real built-ins; a candidate could thin out the prefix test's event cuts with sub-step
changes of its signal) and 9 minor points, all fixed in version 6; the candidate source was found free of hindsight
constants. Version 6 and evaluator version 6 then went through a last independent check with four lenses (sealing and
ledger; candidate separation and look-ahead detection; statistics and text against code; a rehearsal of the whole real
procedure in a stand-in world with every raw reader disabled). No route was found by which a number from a sealed row
leaves outside a logged opening. 51 findings on other points, among them: the row grid of the prefix test had a fixed
phase, so a look-ahead that only holds a level on a few rows could pass; a list or dict parameter was one object shared
by all calls of a configuration and could carry what a longer call had seen into a shorter one; the registry file was not
tied to the ledger and no amendment function existed; batches could be scored out of order, which let two members of one
family go on; several interruptions (a stopped G2 read, a failed marker write, a cut file, a machine out of memory) left
states that the code refused for ever; the static-equivalent benchmark of d* counted its constant holdings before tax; a
calendar end that was not ISO text passed the guards. Version 7 and evaluator version 7 carry the fixes (each marked "v7"
below); the changed parts were read once more by an independent reader before registration. Versions 1 to 6 were never
registered and scored nothing.

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
  sealed blocks the d condition of CONFIRMED needs an observed paired difference of about 1.1 x TE per year (TE =
  annualised tracking error against v1) when the difference is spread evenly over all rows: a true edge of 1.0 x TE per
  year then passes the d condition in about 42% of the cases, one of 1.1 x TE in about 49%. Added in v7 (a statement, no new rule):
  CONFIRMED also needs the d* condition and the timing type (section 4), and a candidate that is active on part of the
  rows has fewer effective sub-blocks. In
  the last check before registration a planted timing rule held on about 30% of the rows was CONFIRMED in about 23% of
  synthetic worlds at a true edge of 1.0 x TE, 27% at 1.1, 49% at 1.5 and 56% at 1.7; an observed d of about 1.4 to 1.5 x
  TE was needed. A configuration with fewer than 6 active 63-row sub-blocks in the sealed set can reach neither CONSISTENT
  nor CONFIRMED whatever its edge (section 4, test T). By a count on old blocks (target levels and weights up to 2014, two
  blocks at a time) 67 of the 96 configurations of the first batch had a median below 6: rules that act in rare episodes.
  The G1 record carries the number of active sub-blocks per design block, and the report that asks for an authorisation
  quotes it. This structure can confirm only large edges that act often; small improvements (a few pp/yr at TE 20%) and
  rare-episode rules cannot be confirmed here and are not claimed.
- Kept by code, and kept by procedure. Code enforces: the block table, the removal of sealed rows from every design
  figure, the refusal of the main account outside a logged opening, the G3 budget, the hash checks, the ledger chain, the
  batch numbering, (v7) the tie between the registry file and the ledger and the order of the batches, the family rules, the voiding rules and the source gate of candidate files. Procedure, not code, keeps:
  who reads rows after 2014 outside the evaluator; the reading of candidate source for rules on the calendar position that
  no mechanical test sees (a row counter, a count on a calendar field, an own cumulative level compared with a fixed
  number); the per-batch statement on rules scored by earlier lanes; the registration data of new inputs (publication time,
  lag, carry, revisions); the "superseded" marks after a defect; and that nobody writes ledger lines by hand (a hand-written
  G1 line is refused because no results file stands behind it; other lines are protected only by the hash chain and by the
  copy of the ledger that is committed to the repository after every step; v7: the evaluator writes that copy itself
  after every line and refuses a ledger that lost or changed lines against it). The evaluator guards against mistakes of its
  own operator, not against an operator who edits it.

## 1. Blocks (mechanical)

- Calendar: the Ken French trading dates from 1984-01-03 to 2026-08-31 as returned by jp.calendar. The evaluator checks that
  the last row is 2026-08-31 and that its block table equals the table below, and stops otherwise. Rows after 2026-08-31 that
  exist in the panels are never used.
- Block b = (calendar year - 1986) // 3, b = 0..13. A row belongs to the block of its calendar year.
- Length and origin. Blocks are 3 calendar years from 1986, the first account year. Three years is the shortest length
  that is about twice the longest fixed signal memory (378 rows; a block has 752 to 759 rows) and still leaves two sealed
  blocks after 2014. Both were
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
- Output rules, checked on what candidate code returns (a breach voids the configuration): v6: a dict of plain values only
  (numbers, number arrays, lists or tuples of numbers, the brake function), a NaN weight or rebalance flag counts as 0;
  B finite and inside 0 .. 3;
  mode and inc 0 or 1; the brake as above; weights finite, inside 0 .. 1, at most 1 in total per row; instrument returns
  finite and above -100% or missing (NaN); rebalance flags 0 or 1; bands >= 0 and finite; no weight on an instrument on
  a row on which it is missing or on one of the four rows before such a row; the account value finite and positive on
  every row.
- Instrument check. Every instrument a candidate holds must be one that could be held: a registered return input; the
  modelled daily-reset fund on the index, on the chain's 10-year bond return, on a registered 1x return input or on the
  splice of two of them; or the splice of a registered fund return with such a model (the actual fund where it exists, the
  model before). v6: a model rests only on an unlevered series (the index, the chain's bond return, the Ken French
  series, chips / semis and the registered 1x funds and sector funds), and a real fund is spliced only with a model of its
  own leverage (SOXL, TQQQ, TMF, TNA, TECL, FAS, DRN 3; USD, QLD 2; ERX 3 or 2; PSQ -1; 1x funds 1). Fund model on a 1x
  return r with cash rate rf: L = 3, 2: L r - (L - 1) rf - (0.0095 + 0.0075 (L - 1)) / 252
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
  only the G3 function writes, under its lock. (v7: the G3-RELEASE report of section 4 is a later, separately reviewed
  function; it is added by an amendment of the evaluator code and runs only once G3 is closed or spent. Until then no
  code path scores the main account outside an opening.) Outside an opening these run a full-calendar account inside the evaluator
  and return nothing computed from a sealed row: the v1 shadow levels (a level path that only candidate code reads), the
  parity checks P1 and P3 (booleans, and counts on rows up to 2014-12-31 only), the base run of the design-view prefix
  test of a candidate and the prefix test of REF in section 3 (PASS / FAIL). The main-view checks of a candidate run only
  inside an opening (v6).
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
  m_t = ln(1 + kappa x (exp(x_REF,t) - 1) + f_t x (delta0 x R3_t + sum_j w_j x G_j,t)), with R3 the modelled daily return
  of the 3x fund and G_j the daily return of instrument j (no cost on the constant holdings). v7: f_t = 1 - 0.22 on a row
  before which the candidate's account owes liquidation tax (V below equity at the previous close: a gain or loss of the
  row then changes V by 78% of it), and 1 otherwise. x is growth after tax; versions up to 6 counted the constant holdings
  before tax (f = 1), which pushed d* down for a candidate that holds more and up for one that holds less of the fund than
  kappa x REF (found by the last check). d*_t = x_candidate,t - m_t.
  A candidate that only holds more, less or something else on average has d* near 0 whatever the market did; a candidate
  whose gain comes from when it holds keeps it in d*. In the last check (v7 benchmark; 20 planted candidates without timing skill;
  130 synthetic worlds with independent returns and 64 with a regime shift; one configuration tested at 0.025) such a
  candidate was typed "timing" in 1.2% of the cases (32 of 2,600; at most 5 of 130 for one candidate) and in 0.2% (3 of
  1,280). Their d* on the design set, averaged over the worlds, lay between -3.3 and +0.5 pp/yr (half of them below -0.5):
  the cost of a candidate's own trades stays in d*, which errs against the candidate. A planted timing rule was typed
  "timing" in every world. For the sealed set kappa, delta0, w_j and d* are computed
  inside the evaluator and never reported.
- Known noise, fixed by this text so that nobody can pick it: the tax-year phase (the account starts on 1986-01-02). In
  synthetic worlds a shift of the start by a few rows moved a set-level paired score by about 1 to 2 pp/yr (standard
  deviation), without bias. One account per side is scored; no average over start dates is taken.

### Outputs (sealing)
- The evaluator returns scalars only, and only these: (a) per non-sealed block and per listed set: annualised growth, paired
  difference, row counts, tracking error, harm limits, test statistics, active-row counts; (b) for accounts: shares of
  scored rows at each held level, number of level changes, mean level, mean extra weight, mean difference of the 3x-fund
  weight against REF, and the drawdown of the curve re-based to 1 on the first scored row of the block; (c) for the design
  set of a configuration: kappa, delta0 and w_j of its benchmark, the skewness and lag-1 autocorrelation of its 63-row
  sub-block means (of d and of d*), and (v7) the number of active 63-row sub-blocks in each design block; (d) the model
  check and the data checks; (e) PASS / FAIL of the tests and a void reason. v6: in the real
  calendar the prefix test returns PASS / FAIL only, the raw-level test the names of failing inputs only, and a void
  reason only its category (the text before its first colon: source gate, output rule, instrument check, error in
  candidate code, prefix test, ...); counts of cuts, exception names and details exist only in test worlds. One exception:
  the 63-row sub-block means of design-block paired differences (of d and of d*) are kept for the family-wise test;
  they are design material.
- Kept by code (v6): the real calendar after 2014 is built only inside the scoring entry points (reference table, model
  check, batch scoring, G2, G3, and the checks and section-3 scripts, which enter the same scope) and refused elsewhere;
  the v1 shadow levels answer only while candidate code runs; a test world (section 2, tests) cannot write into the
  registered folder (v7: nor into a folder below it, nor into the repository copy of the ledger), and no real calendar
  after 2014 is built while the test-world module is loaded; v7: a calendar end must be text of the form YYYY-MM-DD (the
  guards compare text), and the registered calendar must end on its end date. These guards stop
  accidental reads, not deliberate ones: the scope is a public switch, and an operator can read the data files with other
  programs; this text forbids both. Residual channels, stated: a configuration's void category, the time a run takes and (v7) whether G0 exists for it
  can depend on how its code behaves on sealed rows (the design view is the full calendar, see Accounts; the G0 flag is
  set from the weights on the rows of the design account, but also from whether the code asked for view.m or the shadow
  levels, which a branch on a sealed row can change); these are at most a few bits per
  configuration, every configuration counts in its batch, and code written to act on such a channel is excluded by the
  source review.
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
  replaced. v6: v1's brake function and the no-brake function reach candidate code only as opaque tokens (xv1.ref(v)['bfn']
  and xv1.std.ident), which the evaluator maps back to the functions; the functions themselves are compiled objects whose
  attributes lead to module globals and the real built-ins. A crawl of everything reachable from the objects candidate code
  gets, through attribute names the gate allows and through item access, found no module, globals dict, code object,
  frame, file or evaluator internal.
- Source gate (v6: an allow-list), applied to the bytes of a candidate file and of every helper file it imports from its
  own folder, before a batch is registered and before code is first executed. Allowed: module-level `import numpy`,
  `import xv1` and `import <helper>` (a file of the candidate's own folder whose name is plain and is not the name of a
  standard-library or built-in module); of xv1 only xv1.ref (v1 itself) and xv1.std.ident (no brake), and what candidate
  code imports under that name is a stand-in that holds nothing else; of numpy only a listed set of array functions and
  constants (xv1._NP_OK; no np.empty or anything else that hands out uninitialised memory, no submodule, no file, random or
  error-state function), one level deep (np.X, never np.X.Y); of a helper only its own functions and names, one level deep;
  of the built-ins only a listed set (xv1._BI_OK: arithmetic, containers, iteration, a few exception names; no open, hash,
  id, print, exit or import machinery). Not allowed: any other import, a from-import, an import inside a function, a module
  name used as a value, a class definition, a name or attribute that begins with an underscore other than the file's own
  module-level names or that contains a double underscore, attributes that reach the interpreter, frames, files, string
  formatting, random numbers or an array's memory (xv1._BAN_ATTR), assigning to or deleting any attribute, np.errstate
  with an argument other than divide / invalid / over / under / all, `global` and `nonlocal`, a number literal above 999,
  a string literal (other than a docstring) longer than 64 characters or containing a double underscore, a bytes literal,
  a string literal (other than a docstring) that contains a year 19xx / 20xx, and a list / tuple / set / dict display with
  more than 64 elements. The same literal rules apply to a configuration's parameter values. v7, a stated limit: the one-level rules (np.X, the
  two xv1 names, a helper's own names) hold for the module name used directly; a function first bound to a local name
  (f = np.maximum; f.reduce(...)) passes the gate. No escape follows from it (the banned attributes and the underscore
  rules apply to every name, and the crawl above followed such chains); the reader of the source rejects the form.
  Arithmetic on small literals
  can still build any number: the literal rules are a tripwire, and the reader of the source (below) is the guard.
- Loading (v6). The candidate's bytes are read once per configuration; the gate, the configuration hash and the executed
  code all come from those bytes. They are compiled and executed directly, never through the import system (no sys.path,
  no sys.modules entry, no compiled cache file, no package folder), with only the allowed built-ins and an import function
  that serves numpy, the xv1 stand-in and the configuration's own helper files. Every call of a candidate executes a new
  copy of its module and helper modules, so no state survives from one call to the next. v7: the function name, the
  parameter values, the input names, T0 and the calendar mark of a configuration are fixed as canonical JSON when its
  object is made; every call receives a new copy of the parameter values (in the last check a list parameter used as a
  memory carried a longer call's returns into the cut calls and passed the prefix test), and a later change of an
  attribute cannot reach a call or a gate.
- Reading the calendar position, a date, a file, a cache or a module-level data array is forbidden. Candidate source holds
  no date literal. Periodic calendar fields (month, day of month, weekday, calendar year modulo 4) may be registered as
  inputs; no absolute date, year or row position may be used. The gate and the tests below do not see every way to read
  the calendar position (a row counter, a count on a calendar field, an own cumulative level compared with a fixed number):
  these are excluded by reading the candidate source before registration. A period counted in rows from the first row on
  which an input exists (for example a yearly rebalance every 252 rows) is a periodic rule and is allowed.
- Hindsight written into code. No test can tell a rule from a rule that carries knowledge of later days as constants (rows
  or dates of later events, fingerprints of later values): the causality verifier showed such a candidate passing the
  prefix and level-scale tests. Guards: the literal rules of the gate (v6), and before registration a reader who did not
  write the candidates reads every candidate and helper file and its parameter values for such constants; the batch is
  registered only after that reading finds none. What no guard removes: the designers know the broad history of 2016-2024
  (the 2018 fourth quarter, 2020, the 2022 bear market); a rule chosen because it would have helped in a known year is a
  selection the sealed blocks cannot detect. Every G3 report carries this sentence.
- Level-scale test, before the first scored call of a candidate: the index level handed to candidate code (view.c.lvl) is
  multiplied by 2 and by 0.5 (exact in binary arithmetic); every output of the candidate and the features must stay
  bit-identical, else the configuration is void. A rule may use ratios of a price level, never its absolute height: a
  threshold on the height picks out an era without naming a date. The test covers the index level only. Registered level
  inputs are limited to an allow-list of series that carry no price height (lvl:_VIX3M, lvl:_VIX9D, lvl:_TYX, lvl:_FVX);
  every other price series enters only as a daily return. A threshold on a yield, a spread or a volatility index is
  allowed. REF passes this test (self-test: a planted height threshold must be reported as void).
- Candidate code runs inside the evaluator with its output streams closed and warnings dropped (v6), with numpy's error
  state set to its defaults and no error call-back (v6), restored afterwards. While it runs, the data readers (mkt._panel,
  mkt.fred, mkt.pser, md.load, md.kf, jp.calendar, jp.build, xdata.get, xdata.read_chips, numpy load, save, fromfile,
  loadtxt and genfromtxt, pandas read_csv) are replaced by functions that raise. A configuration whose code raises in any
  test or scoring call (v6: any exception, also one outside Exception such as SystemExit), or breaks an output rule, is
  void; only an interrupt by the operator stops a run (the batch is then resumed). v7: a machine out of memory is not the
  candidate's rule break either: the batch run stops, the event is logged and the run is resumed; a configuration on
  which this happens a second time is void. Inside a G3 opening it gives G3-ABORT and the retry rule.
- One call. The full-calendar call of a configuration is made once (like every call, on a newly executed copy of its
  module and helper files): the same result is tested (prefix test, level-scale test, instrument check, T0 rule) and
  scored. In the stress
  runs of G1(d) that same output is used: the candidate's signals are held fixed while the engine terms move. v7,
  precisely: once per scoring step. G2 and each step of a G3 opening call the candidate again on a new copy of its
  module; the code is deterministic and keeps no state, so the output is the same.
- Prefix test, before a configuration is scored (design view), once more on the main view inside a G3 opening (v6: after
  its G3-OPEN line), and once on REF as a control (REF must pass or the evaluator is not used). Every cut run executes a
  new copy of the candidate module, so nothing kept from a call that saw more rows can reach a call that should see
  fewer. For each cut row c: (a) deletion: the calendar and every registered input are cut after c
  and the candidate is called again; (b) noise: the rows after c are replaced by random values and everything is rebuilt.
  B, G, Wt, RB, the bands, the brake and its parameters, fstep, mode, inc, the feature rows and every column of the account
  record (equity, level in force, brake target, base level, liquidation value, weights) on the rows up to c must be
  bit-identical to the full run. Cuts: the last row of every block, the account rows 0, 62, 63 and 259 and 60 rows drawn
  from the whole account (both variants; 200 drawn rows for REF), and, deletion only, every 5th account row (v6; v7: the
  phase of this grid is drawn from the seed, so candidate code cannot know which rows it holds) and the
  event rows (the row itself and the row before): every row on which the candidate's signal or v1's own signal changes,
  the first and last row of every run in which the candidate's level differs from v1's, and every row on which a target
  weight or a rebalance flag of a column that is ever held changes (v6: a column that is never held makes no event, since
  the engine never reads it). v6: every event row is cut, without a cap, so a candidate that adds changes only adds cuts
  (with a cap, sub-step changes of the signal that the engine ignores could push a look-ahead out of the cut rows). The
  noise of variant (b) keeps the decimal grid on which the real values of each series lie (v6: a level quoted in
  hundredths stays in hundredths, a return quoted in basis points stays in basis points), and calendar fields keep their
  real values (the calendar is known in advance). Event rows are cut because a look-ahead hidden behind a threshold
  shows only where it acts.
  v7, every-row test. The cuts above are a sample. A look-ahead that only HOLDS a level on a few rows makes no event row
  and is seen only by a cut on one of those rows (found by the last check before registration: with 20 such rows the
  sample caught it at every seed tried, with 2 rows it depends on the drawn rows). Therefore (1) a configuration whose
  design set score d reaches 1.0 pp/yr (the size G1 (a) asks for; a smaller d cannot pass G1) is tested once more before
  its score is kept, with a deletion cut after EVERY account row of the design view; (2) in a G3 opening the prefix test
  of the main view cuts after every account row; (3) for REF every account row is cut. With a cut after every row the
  test is exhaustive: the output on the rows up to c computed from the rows up to c equals the full run for every c,
  which is the definition of a rule that reads nothing ahead. FAIL = void, as below. The design figures of a
  configuration below that size rest on the sampled test only. Stated limit (v7): no cut lies inside the 300 warm-up
  rows, so a look-ahead from a warm-up row to another warm-up row or to the first account row (1986-01-02) is not seen;
  it can carry nothing later than that row (a later row read from a warm-up row is caught by the first cut) and is
  excluded by the reading of the source. The
  generator is seeded from the sha256 of the batch hash and the batch's ledger line (which carries its UTC time), for REF
  from the registration hash. A candidate that raises on a cut fails that cut. Output: PASS or FAIL. FAIL = the
  configuration is void, still counts in its batch, and no score is produced. Self-test: a planted 3-row look-ahead, a
  planted full-sample quantile, a planted centred 5-row window, a look-ahead through the v1 shadow level and a candidate
  that keeps the longest array it has seen between calls must all be reported as FAIL; a full-sample number hidden in the
  brake parameters is void by the output rules. v7: a planted one-row look-ahead that holds the level on two rows (no
  event row) must be reported as FAIL by the every-row test with exactly two failing cuts, and must be void in a batch
  run in which the sampled test is made to pass; a candidate that uses a list parameter as a memory between calls must
  be reported as FAIL. v6, re-run of the verifiers' probes: a look-ahead diluted by thousands
  of flag changes on never-held columns or by sub-step changes of the signal, and one that acts only when the future row
  lies on the 0.01 grid, are reported as FAIL; probes through a file named builtins.py or gc.py, a package folder, a
  stale compiled file, open(), np.empty, str hash, SystemExit, the attributes of the compiled brake function and a 3x
  model on a 3x fund are refused by the gate, voided, or have no effect.
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
- P2 MS1 identity: on the <= 2014 calendar the REF account's equity is bit-identical on every row to std.engine on
  std.contexts()['real_ndx_86_14'] with cspr = 10.0, and its CAGR after final liquidation tax is 30.53% (difference below
  0.005 pp). This figure is a constant of this text; the evaluator does not open a results file. v6: the checks script
  asserts both (0 differing equity cells, the CAGR equal to std.engine's within 1e-9 and within 0.005 pp of 30.53%).
- P3 raw-level test of the REF chain: the raw readers (mkt.pser, mkt.fred, mkt.shiller_gs10, md.kf, mkt.spx) are wrapped in
  memory; no file is changed. For each cut (the last row of every block and 12 drawn
  rows) every raw row after the cut is (a) deleted and (b) replaced by noise (md.kf, whose index is the calendar itself,
  deletion only); the chain is rebuilt; every cell of X, F,
  features, B, level path, equity and liquidation value up to the cut must be bit-identical. Control: y10 taken 5 rows
  early must be reported as FAIL. v6: counts are reported only for cuts up to 2014-12-31; for later cuts only a boolean.
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
- Hashes. The registry is research/xv1/HASHES.json together with the ledger. v7: ledger line 0 (later: the latest
  amendment line) carries the sha256 of HASHES.json, and every scoring function refuses a registry file that is not that
  file or that does not hold exactly the data files of the chain; its keys are paths below research_xv1 and below the
  project-files folder, so it holds wherever the two lie in a later session. Registered with this text: the sha256 of
  every data file read by the chain and by the extra inputs (the two price panels, the calendar file, the DBAA, DAAA, BAA,
  AAA and TB3MS files, the Shiller file, the SPX and T-bill files, the brake parameter file fin_params.json, the Ken French
  Chips file), of the evaluator files (xv1.py, xeng.py, xdata.py) and of every project code file loaded by a full exercise
  of the evaluator on the <= 2014 calendar, the package versions (python, numpy, pandas, numba, llvmlite, scipy, xlrd) and
  the registered constants. Every function that scores (the reference table, the model check, batch registration, batch
  scoring, G0 line, G2, G3) recomputes all of them and stops on a mismatch, also when a project code file is loaded that
  the registry does not hold; v7: in the real calendar each of them, and the authorisation line, also stops unless the
  latest checks line under the registry in force passed and carries the sha256 of the registered checks script. In the real calendar the evaluator also stops if a registered constant (the sealed blocks,
  the embargo, the block length, the calendar ends, the engine and stress terms including beng.F1 and the carry limit,
  the thresholds, the active-row weight, the G3 end date, the literal limits, and v6: the allow- and ban-lists of the gate
  and the leverage table of the instrument check) no longer has its registered value. Candidate files and their helper files are covered by the configuration hashes (section 4). Changing
  an evaluator file after registration follows section 7 (v7: xv1.amend, called by m_register.py --amend: an amendment
  file, a ledger line with its sha256 and the sha256 of the new registry, then the new registry; the checks must pass
  again under it and the partial results of an unfinished batch are computed again).

## 3. First measurement after registration (no candidate, no pass / fail)

- REF, 1x hold and 3x hold on every DESIGN and WEAK block: annualised log growth of V per block and for D7, W5 and POST3;
  for REF also the level shares, level changes and in-block drawdown on scored rows.
- Model check, information only, scored rows of non-sealed blocks where TQQQ exists: modelled return 3r - 2rf - er3/252
  against the daily ratio of the fund's adjusted close; annualised gap (actual minus modelled). Counts first: rows without a
  fund observation and rows where the two differ by more than 5 pp (both must be 0, otherwise the gap of that block is
  void). The index has no dividends, so a positive gap is expected. No engine term is changed because of this check.
- Reading fixed in advance (descriptive; POST3 has about 5.2 scored years, the standard error of each difference is of the
  order of 10 to 20 pp/yr): D_A = REF - 3x hold (what de-risking did) and D_B = REF - 1x hold (the whole package against the
  index) on POST3, each with the two-sided 90% interval of test T (the wider of the L = 63 and L = 126 intervals), and each
  a second time with tax 0 on all three accounts
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
  canonical JSON of: the module name, the name and sha256 of the bytes of the source file and of every helper file that
  the source file imports from its own folder (directly or through another helper), in name order, and the rest (v6: the
  very bytes that are gated and executed). Two parameter points are two configurations.
- T0 = first date on which all candidate inputs exist plus the candidate's own warm-up. It is registered with the
  configuration and may lie at most 756 calendar rows after the first row on which every registered input and the chain's
  VIX exist (else the configuration is void), so the start of a record cannot be picked. Before T0 the candidate must
  equal REF exactly: the evaluator checks, on every account row before T0 (sealed rows included; in a G3 opening again on
  the main view), that the base level is v1's and that there is no weight and no rebalance flag, and that the paired
  difference is 0; else the configuration is void. All statistics use scored rows on or after T0.
- Active row = scored row on or after T0 on which the candidate holds a different v1 level than REF, or on which its
  extra instruments (or REF's) make up at least 1% of the account in actual weight (v6: a tiny always-held sleeve does
  not make every row active). (A non-zero paired difference alone does not count: after the first divergence the two
  accounts differ a little on every row.) Active block = at least 20 active rows.
- TE_b = sqrt(252) x standard deviation of the daily paired difference on the scored rows of block b on or after T0.
  TE_D = the same on all scored design rows (reported, used in no gate).
- Test T (no resampling): the scored rows of each calendar block are cut into consecutive sub-blocks of L rows
  (leftover rows join the last sub-block); m_j = mean daily paired difference of sub-block j; t_L = mean(m) / (sd(m) /
  sqrt(k)); p_L = one-sided Student-t tail with k - 1 degrees of freedom. Sign-flip check for differences that live in a
  few episodes: the sums of the active 63-row sub-blocks (those that contain an active row; A of them) get random signs,
  the other sub-blocks are not flipped; p_sf = share of sign assignments whose total is at least the observed total (all
  2^A assignments up to A = 20, which covers the sealed set; otherwise 100,000 drawn ones, seed = first 8 hex digits of the
  configuration hash). v6: p_sf is at least 2^-A_eff with A_eff = (sum |s_j|)^2 / sum s_j^2 over the active sub-block sums
  s_j (the number of sub-blocks that carry the difference); a difference that lives in one or two large sub-blocks
  cannot reach a small p_sf because many small active sub-blocks surround it. p = the largest of p_63, p_126 and p_sf.
  Consequence, stated in advance: with A_eff below 5.91 in the sealed set (2^-A_eff above 0.05 / 3) a candidate can be
  neither CONFIRMED nor CONSISTENT. The stated power figures assume a difference spread over many sub-blocks: in the
  last check (v7) an edge of 1.5 x TE carried by 2, 4, 6 or 10 of the 20 sealed sub-blocks reached p <= 0.05 / 3 in about
  0.5%, 13%, 32% and 55% of cases when the other sub-blocks carried noise, and in about 0%, 0%, 0.1% and 58% when the
  candidate was active only in those sub-blocks; the floor changes nothing when the edge is spread.
- Harm bound for a block: an active block with d_b < -2.0 x TE_b x sqrt(252 / n_b). It bounds harm; it is not a
  significance test (with zero true edge about 85% of candidates stay inside it on seven blocks).
- Batch = a list of configurations registered together (file with sha256, line in the ledger) before any of them is
  scored on any design row by any means. The batch number is the next one in the ledger and cannot be chosen; a
  configuration hash that stands in an earlier batch is refused, as is a source that fails the gate. The evaluator refuses
  a configuration that is not in a registered batch. Every configuration of a batch is scored and reported, losers
  included; each scoring is a ledger line. A void configuration (source gate, raw-level, prefix or level-scale test, output
  rules, instrument check, T0 rules, an error in its own code) is reported as void with its reason, is not scored, does
  not stop the batch and is not refunded. v7: an input name that cannot be read and a T0 that is not a date are refused
  at registration, before the batch file is written, and so is an empty batch; a batch is registered and scored only when
  every earlier batch is scored (the family rule reads the earlier batches). Batch k (k = 1, 2, ...) has the family-wise
  level alpha_k = 0.05 / 2^k, so all batches together spend less than 0.05 (with 200,000 draws the smallest family-wise p
  is 1 / 200,001, so a batch after the 13th cannot pass G1). A batch is scored once; an interrupted run is resumed.
- Family-wise p of a configuration = single-step max-t over the scored (non-void) configurations of its batch: t_63 of
  every configuration on the 70 design sub-blocks; the null distribution of the maximum from 200,000 draws in which the
  sign of each sub-block is flipped for all configurations together (seed from the sha256 of the batch hash and the
  batch's ledger line; no daily difference exists before the batch is registered, so a seed cannot be shopped). A
  sub-block before a configuration's T0 enters as 0. The same test is run a second time on d* (seed + 1).
- Assumption behind the stated error rates: under the null the sub-block sums are symmetric around 0 and independent of
  each other. The design blocks contain 2001-03, 2007-09 and 2020. With every G1 line the evaluator prints the skewness
  and the lag-1 autocorrelation of the configuration's 70 design sub-block means; they are quoted in the report that asks
  for a G3 authorisation. v7, sizes from the last check (zero true edge, synthetic sub-block sums): with symmetric
  independent sums the family-wise level of 96 correlated configurations was 2.6% at nominal 2.5% and one opening passed
  the d test in about 1.1%. With left-skewed sums (skewness -0.6 / -1.3) the family-wise level was about 6% / 12%; with a
  lag-1 autocorrelation of +0.1 / +0.2 / +0.4 about 6% / 13% / 41%; one opening passed the d test in about 2% to 5% at a
  sample skewness of -0.5 to -1.2 or an autocorrelation of 0.4. Dummies that add exposure had skewness between -1 and
  -3.5 on old data. Therefore: the type "timing" is given only inside the range in which the rates were checked (G1,
  below), and a G1 pass or a CONSISTENT verdict of a configuration whose d sub-block means have skewness below -1 or
  autocorrelation above 0.2 is reported with the sentence "error rate not controlled (skewed or autocorrelated
  differences)".
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
  ledger. A copy of the ledger is committed to the repository after every step. v7: one writer at a time (a lock on the
  machine that runs the evaluator; the procedure is one container and one process); after every line the evaluator
  copies the ledger to research_xv1/registry/LEDGER.jsonl and from then on refuses a ledger that lost or changed lines
  against that copy (the hash chain alone cannot see a removed tail); a line about a configuration must name its hash; a
  last line that was cut while it was written is removed only by repair_ledger, which logs the repair.

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
Type. A passing configuration is of type "timing" if its set score d* > 0, its family-wise p on d* is <= alpha_k and
(v7) the 63-row design sub-block means of its d* have skewness >= -1.0 and lag-1 autocorrelation <= 0.2;
otherwise it is of type "exposure": its design gain is not separated from holding more (or holding something else) on
average. The type is printed with every figure of the configuration.
At most one configuration per family goes on. The passing configurations are taken in this order: timing type before
exposure type, then the smallest family-wise p (ties: the larger t_63); one is taken if it is not one family with a
configuration already taken in this batch or with one that went on in an earlier batch. G1 is a screen on data the
designers have seen. Passing it is never reported as significance.

### G2 old-data no-harm check (W5), not validation
- Given only to a configuration that passed G1 and was selected (and passed G0 where it exists), once (the evaluator
  refuses a second read; v7: a read that was interrupted before its result line, so that nothing was returned, is run
  again once and logged as a re-run). On scored WEAK rows on or after T0: set score d >= -1.0 x TE_W x sqrt(252 / n_W) (TE_W from the
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
  stood; v6: the message id must be a message id and the authorisation line must come after the G2 pass line; v7: a message id
  that already stands in the ledger is refused, so every opening has its own message of the owner); every
  registered hash, package version and constant is unchanged; fewer than 3 distinct hashes have a G3-OPEN line, and the
  ledger holds at least as many G3-OPEN lines as the separate marker file G3_OPENINGS.log (v6: a shortened ledger cannot
  hide an opening); G3 has not been closed (G3-CLOSED, written by close_g3 with the owner's message id); the date is before
  2031-01-01 (v6: enforced); and no other opening is in progress (a lock file). A configuration whose level does not depend
  on any input (cash, a fixed level, a constant extra weight with no v1 level; v6: also checked by replacing every input
  after T0 by noise on the calendar that ends 2015-12-31, twice, and finding B, Wt and RB unchanged) may not be opened. A configuration that is one family
  with an already opened configuration (label, or absolute correlation of the design sub-block means of 0.7 or more) may
  not be opened; the refusal does not consume an opening.
- Blocks 10 and 12 are scored from the main account (the full calendar in one account), for candidate and REF alike. v6:
  the line G3-OPEN H (and its marker) is written and flushed BEFORE the candidate is first called on the main view, and
  consumes one opening whatever follows. Then the T0 rule (v7: both parts, the signal and the paired difference) and the prefix test (v7: with a cut after
  every account row) are repeated on the main view; a failure
  gives the verdict FAIL (a refusal at that point would have been a bit about sealed rows without a used opening). The main
  account answers only while the G3 function holds the token of that opening. If the candidate breaks a rule on the main
  view (an output rule, the instrument check, an error in its own code: a void), the verdict is FAIL (v6; the code is
  deterministic, so a retry would void again). If the run raises anything else (v7: also a machine out of memory), the ledger gets G3-ABORT H and the
  function raises a fixed text (nothing of the error leaves); the same H with identical hashes may be re-run once and the
  retry is logged.
- Verdict (p = test T with the sign-flip check; all quantities computed inside the evaluator and never reported):
  - FAIL: set score d <= 0, or an active sealed block with d_b < -1.0 x TE_b x sqrt(252 / n_b) (TE_b from that block's own
    scored rows), or a failed check or a void on the main view (above).
  - CONFIRMED: not FAIL, set score d >= 0.5 pp/yr, p <= 0.05 / 3 on d, and also set score d* > 0 with p <= 0.05 / 3 on d*,
    and the configuration was of type timing at G1, registers no periodic calendar field as input and (v7) is not
    marked by its registrant as using a period counted in rows (a 252-row rebalance from a known first row is a calendar
    slot in all but name; the yearly-rebalance barbell configurations of the first batch carry the mark).
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
6. Candidate batches: read for hindsight constants by a reader who did not write them (section 2), registered, scored
   on D7, G1; G0 and G2 for the selected passers; G3 only with the owner's authorisation.

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
  every output that existed before it and is reported to the owner in the next report (v7: written by xv1.amend together
  with the new registry; the registered text and ledger line 0 stay as they are).
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
