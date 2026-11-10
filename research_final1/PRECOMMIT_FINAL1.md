# PRECOMMIT_FINAL1 (written 2026-11-10 14:35Z, before any FINAL1 computation)

Thread: "Find final best trading method" (user order 11-10 13:47Z: one final all-out push). Data <= 2014-12-31. Engine: locked MS1
(research/measure_std/std.py via research/ov1/code/ov1lib.py). Parity run before this file: v1 dev250_path 0.16159, real NDX 86-14 0.31081.
Bar: beat v1 on BOTH MS1 dev250_path (16.16%) and real NDX 1986-2014 (31.08%) with the pre-registered variant. Holdout (2015+) is opened at
most once and only for a candidate that passes; otherwise never.

## 0. Records audit (no computation): planned-but-undone items vs closed registry (idea_check, 108 rows)
| plan item | status from records | evidence |
|---|---|---|
| 0 tax reserve kept until May / in SGOV | tested: "5월 납부, 현금에서 먼저 납부" -0.02..0.00 | research/tax_min/RESULT_TAX_MIN_KO.md row 36 |
| 1 confidence-scaled sizing | continuous sizing on raw chassis -0.8pp; QLD 2x middle states -0.18/-2.18 | X10 (raw_core), X41 (v1_states) |
| 1 long calls / asymmetric options | covered calls, put-writes, spreads, calls on 3x leg, LEAPS all negative | L02 (volprem), X01 (tax_min LEAPS -4pp) |
| 1(a) neighbour-parameter split | ensemble on raw chassis (lab) -1.9pp; NOT yet measured on v1 itself with std -> lane NBR below | X10 |
| 1(b) take-profit / trim / let-run | profit lock, pyramiding, RSI-overbought exits, infinite-buy all negative | L03, L04, T27 |
| 2 index add/delete | S&P deletions/additions fail conservative prices; ceiling SR .53 | S14, S15 |
| 2 leveraged-ETF close rebalancing flow | not in registry; needs intraday data + 0.6% round-trip at spot -> desk ceiling in final report | - |
| 2 vol premium, merger arb | closed | L02, S06 |
| 3 fundamentals intact + macro-shock drop | EDGAR events 25 tests 0 pass; regime stock picking closed | S06, S03, S01 |
| 3 KR investor flows | BLOCKED (KRX JSON needs login; ECOS key needs user identity) | T17 |
| 3 cross-ETF reference for the TQQQ decision | 499 free signals, sector lead, SMH/QQQ, XLY/XLP, breadth, correlation closed | T08, T16, T32, T14, T15 |
| 3 RSI bottom + abnormal volume | RSI2 / SOX bottoms / distribution days closed; RSI+volume joint trigger NOT yet measured -> lane CAPIT | T13, T39 |
| 4 point-in-time top 10-30 megacaps (+leverage) | "big + profitable survivors" 10.1%; megacap concentration itself NOT measured -> lane MEGA | S11 |
| overnight futures | parallel thread ONF1 (interim 0/12) | research/onf1/ |

## 1. Lane STACK (type F, account/execution terms, deterministic, NO selection, N = 9 rows all reported)
Same v1 rules; only engine terms change (ov1lib.measure2 engine_kw). Rows:
- S0 base (cspr .02, cost .003) = v1 reference.
- S1 CASH0: idle USD earns 0 (cspr = 10). Program reality noted 11-06.
- S2 CASHRP: idle USD in a no-commission USD RP / MMF-like vehicle, yield rf - 0.5pp, taxed 15.4% (cspr = .005).
- S3 FEE: cost .0012/side (0.07% promo commission + 0.05% spread).
- S4 CASHRP + FEE. - S5 CASH0 + FEE.
- S6 OPENFILL (OV1-B engine mode 1, unchanged code, base terms) - S7 OPENFILL + CASHRP + FEE (only if the OV1-B engine takes the same
  term overrides without code change; otherwise reported as "not run").
- S8 delay 1 day + S4 terms (report only).
Rule for the recommended configuration (fixed now): CASH and FEE rows are account terms; they are reported as conditional on the user
actually getting those terms (facts lane) and are NOT counted as a trading-rule improvement. OPENFILL is adopted only if at base terms path
d >= +0.3pp and real d > 0, AND both stay > 0 with +0.1%/side extra cost on postponed fills, AND the summed overnight return on v1 decrease
days is positive in both halves of the ACTUAL open-price window (1999-2007, 2008-2014). Otherwise "not adopted".

## 2. Lane NBR (user idea: split the account across neighbouring parameters), type F, N = 2
Each sub-account = fam4(c, 3.0, vcap, 1.0, caution=('shock6m',), Lc=1.0, sl=sl, band=.02) + av23s(.85) brake, own tax book, equal start,
never rebalanced across sub-accounts. Combined after-tax final wealth = mean of sub-account finals; MDD from the mean equity curve.
- NBR5: (sl, vcap) = (200,.40), (180,.40), (220,.40), (200,.35), (200,.45).
- NBR9: sl in {180, 200, 220} x vcap in {.35, .40, .45}.
PASS: path paired d > +0.3pp with pw >= .55 AND real NDX d > 0. Selection among 2 -> report both; a pass needs both variants path d > 0.

## 3. Lane MEGA (user idea: concentrate in the largest 10-30 stocks), type D/E, N = 2
Ken French "Portfolios Formed on Size" (value-weighted, monthly, <=2014-12): Hi 10 (largest decile) and Hi 20 minus the market (Mkt = Mkt-RF+RF).
- M1: mean annualised (Hi10 - Mkt) and t-stat, 1963-07..2014-12; halves 1963-1988 / 1989-2014; also 1986-2014.
- M2: same for Hi 20.
PASS (to continue to an MS1 build): difference >= +1.0pp/yr with t >= 2 in 1963-2014 AND positive in both halves. Otherwise closed.
Single-stock leveraged ETFs have no history before 2014 -> the "+leverage" part is NON-TESTABLE and is reported as such.

## 4. Lane CAPIT (agent; user idea: RSI bottom + abnormal volume), type B ADD overlay, N = 2, plus a descriptive DEPTH table
Trigger at close t (NDX, volume = the Nasdaq volume series used by RNG1, <=2014 cut):
- CAP1: RSI(14) <= 30 AND volume_t >= 2.0 x median(volume of the previous 60 trading days). Effect: for the next 42 trading days the v1 base
  target is raised to 3x wherever v1's base target is below 3x (the v1 brake still applies).
- CAP2: within the last 3 trading days RSI(14) <= 30 at least once AND max volume ratio >= 2.5; effect window 63 trading days.
Kill test B exactly as BRIEF section 4 (early <= 1999-12-31, unseen 2000-2014 once). Only a variant that passes both windows goes to measure2
(RSI computed on the path price; volume ratio glued from the source date and labelled as such). DEPTH table (descriptive only, not a test,
n of independent episodes stated): first crossing of -30/-40/-50/-60/-70% index drawdown from all-time high -> forward 1y and 3y return of
the 1x index and of the synthetic 3x product (MS1 formula), for NDX 1985-2014 and S&P 500 1928-2014 (and SOX if a <=2014 cut exists locally).

## 5. Wildcard round (agents): rules fixed now
- 4 scouts with different lenses + 1 false-negative auditor of closed lanes. Every idea must pass idea_check and carry a free <=2014 data proof,
  a kill-test type, an argument why it does not take capital from v1 at 3x, and a prior pass probability.
- Court (1 agent, adversarial): at most 3 new lanes + at most 1 re-check lane from the false-negative audit; only ideas whose judged prior of a
  both-bases pass is >= 5%. If none qualifies, nothing is built.
- Each built lane: <= 2 variants, own PRECOMMIT + sha before computing, early pick, unseen once, then measure2. Every PASS is re-implemented by an
  independent verifier before it counts.

## 6. Final acceptance
A candidate is "best" only if: pre-registered variant, FINAL PASS of BRIEF section 4, independent verifier reproduces within 0.1pp, delay 3 and
cost x2 rows keep the sign on both bases, and the gain is stated net of selection (N reported). If nothing passes, the conclusion is
"v1 stays", with the measured account-term table (STACK) as the only confirmed improvement path.
