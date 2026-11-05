# PRECOMMIT OV1-G: Fed target cut outside a scheduled FOMC meeting re-arms 3x for 42 trading days (type B ADD overlay on v1)

Written 2026-11-05 (round 2), before any label, base rate, v1 state, signal-vs-outcome pairing or strategy return was computed.
Step-0/1 work (code/s0_data.py, code/s1_inspect.py, results/s1_inspect.json) looked only at the data: DFEDTAR / DFEDTARU / DFEDTARL
rows and change dates, and the FOMC meeting / conference-call calendar parsed from federalreserve.gov. No return, label or v1 state
was read. The signal is the completeness critic's pre-specified axis (work/WORKFLOW_RESULT_OV1.json, critic.next_axes[2]); this file
only fixes its ambiguities (listed in section 4b) and says so.

## 1. Hypothesis and novelty
An intended fed funds target cut made between scheduled FOMC meetings (conference call, Chairman's intermeeting discretion, or a
discount-rate action passed through) is an urgent "policy backstop". v1 sits in 1x/cash while NDX is under SMA200+2% or a macro alarm
is on, and re-enters late. The overlay only RAISES v1's non-3x target to 3x for 42 trading days after such a cut becomes public; it
never cuts v1's 3x, never touches the alarms or the brake. Input = FOMC action timing (calendar of Fed decisions), not NDX price.
Novelty vs registry: idea_check auto-rejects on T20 (pre-FOMC drift on SCHEDULED meeting days) and T09 E1 (FOMC meeting-date events)
by keyword; T23 (WX1-M1) used monthly fedfunds atoms (levels/changes), not the off-meeting subtype or its timing. The critic expected
a "same information" challenge; this lane is run as assigned and counts N = 1. If it fails it closes the off-meeting subtype too.

## 2. Data (frozen; sha256 of the files read by lane code; full manifest in data/MANIFEST.json)
- data/cut_DFEDTAR.csv  6b35fbcf494060267b09fc03141c83f104ab7081dd381cf3b4d11d7c9373aa12  (9,577 daily rows 1982-09-27..2008-12-15,
  no calendar-day gaps; raw raw_DFEDTAR.csv 323b6d9f..., https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFEDTAR)
- data/cut_DFEDTARU.csv c4aa2ed627e7d6d7dc0a202bf73383a8f2b857bf37a6d2c03371ae907b54bc63 (2008-12-16..2014-12-31; 0 changes, 0.25)
- data/cut_DFEDTARL.csv aae89b29aa95e439d409a2474f0c59fc9ccde7520b144669393455019ed01efa (2008-12-16..2014-12-31; 0 changes, 0.00)
- data/fomc_events_1982_2014.csv 31917500f2b8f7916ffcdd27c4e9e5faf71ef729d5fbf31f0f30a1db14e7c8b6 (477 event days: 378 scheduled-meeting
  days, 97 conference-call days, 2 unscheduled; parsed from the h5 headings of
  https://www.federalreserve.gov/monetarypolicy/fomchistorical<YYYY>.htm, 1982..2014, raw pages in data/raw_fomc/ with sha256 in MANIFEST)
- Signal code: code/sig_g.py sha256 06c9b5cb74db3fad4c24808a0fb08d3174245c63564c5a97b66527b9a3f8371a (frozen with this file).
- ov1lib.py 8104ad4a...; gate.py 8bf85314... (labels gate._frame). Rows after 2014-12-31 are never read.
- v1 target: L.v1_B on real contexts built exactly as std.contexts() builds 'real_ndx_86_14' and 'real_spx_55_85'.

## 3. Point-in-time rule (fixed)
- Change dates before 1994-02-04 (targets not announced): usable from the close of the first trading day strictly AFTER the DFEDTAR
  change date (+1 trading day; Fed watchers inferred the change from that day's open-market operations). Conservative vs the desk action.
- Change dates on/after 1994-02-04 (announced): usable at the close of the change date itself (all post-1994 off-meeting cuts were
  announced before the 16:00 close: 1998-10-15 ~15:15, 2001-01-03 ~13:15, 2001-04-18 ~11:00, 2001-09-17 and 2008-01-22 pre-open,
  2008-10-08 07:00). v1's 2-day execution delay is applied by the engine / the label (t+3..t+23) as usual.
- Caveat stated, not fixable: DFEDTAR before 1994 is a later staff reconstruction of the "intended" rate (in 1982-87 it reflects the
  borrowed-reserves assumption); market participants may have seen some small moves late or not at all. Information-only sensitivity
  (section 5) lags pre-1994 events by +5 trading days instead of +1.

## 4. Signal (exact; N = 1)
### 4a. Rule (code/sig_g.py)
- Cut day d: DFEDTAR(d) < DFEDTAR(previous row). After 2008-12-16: a downward move of DFEDTARU or DFEDTARL (none occur <= 2014).
- S = every day of every scheduled 'Meeting' heading; DA = first weekday after the LAST day of each scheduled meeting;
  C = conference-call and unscheduled-meeting days.
- Off-meeting event iff d not in S AND (d not in DA OR d in C).
- Usable date u on the trading calendar of the basis (section 3). ON(t) = some event has u in trading positions [t-41, t] of the row
  (ON at the close of u and the next 41 trading days; overlapping events extend by union).
- Overlay: B_new(t) = 3 if ON(t) and v1_B(t) < 3, else v1_B(t). av23s(.85) brake, fstep .1, 2-day delay unchanged.
### 4b. Ambiguities fixed here (before any test), and nothing else changed
1. "The day after" a meeting = first weekday (Mon-Fri) after the meeting's last day. For every cut in the data this equals the next
   calendar day. Cuts 2-3 days after a meeting (1982-10-07, 1982-11-19, 1986-07-11, 1986-08-21, 1991-12-20) are off-meeting by the
   literal rule and are kept (caveat: some may be the meeting's decision implemented late).
2. Conflict "day after" vs "conference calls count as off-meeting": only 1992-07-02 (day after the June 30-July 1 meeting AND a
   conference-call day). The conference call is the decision venue, so it counts as off-meeting.
3. Announcement boundary = 1994-02-04 (first announced change). No off-meeting cut falls between 1992-09-04 and 1998-10-15, so the
   exact boundary does not matter.
4. "On for 42 trading days after the usable date" = 42 closes starting AT u (u..u+41), since the information is known at close u.
5. Path / glued bases: the event count series (cumulative number of usable events) is rebuilt along each path row with L.path_series
   (dev250_path) or taken by original date with L.gather (dev250_glued); ON(t) = count(t) - count(t-42) > 0 along the row (an event at
   row position 0 is not counted; NaN = not covered = off -> v1). Real bases: the same rule on the full calendar, indexed by c.ii.
6. SPX real bases: covered from 1982-09-27 only (DFEDTAR start); before that ON = False (= v1, "not covered").
### 4c. Resulting event list (data, frozen)
- SPX era 1982-09-27..1985-12-31 (15): 1982-10-01, 10-07, 11-19, 12-14; 1983-08-17, 09-15; 1984-09-20, 09-27, 10-11, 10-18, 11-23,
  12-06, 12-24; 1985-04-25, 05-20.
- NDX early 1986-1999 (26): 1986-03-07, 04-21, 07-11, 08-21; 1987-07-02; 1988-01-28; 1989-06-06, 07-27, 10-19, 11-06; 1990-07-13,
  10-29, 12-07; 1991-01-09, 02-01, 03-08, 04-30, 08-06, 09-13, 10-31, 12-06, 12-20; 1992-04-09, 07-02, 09-04; 1998-10-15.
- Unseen 2000-2014 (5): 2001-01-03, 2001-04-18, 2001-09-17, 2008-01-22, 2008-10-08.
- All 79 cuts 1982-09-27..2014: 46 off-meeting (above), 33 on a meeting day or the day after (not events): 4 in 1982-85,
  12 in 1986-99, 17 in 2000-08.

## 5. Kill test: type B (brief section 4, thresholds copied, not relaxed)
Brief text: "B ADD overlay (raise v1 1x/cash -> 3x when the signal fires): in v1 non-3x blocks, P(3x beats deposit | on)
>= base + 10pp AND >= 60%, >= 8 'on' blocks, both windows."
- Blocks / labels: gate._frame grid (non-overlapping 21-trading-day blocks); label of block at close t = 3x product (3r - 2rf - 2.45%/yr)
  beats deposit ((rf - 2pp)+ x 0.846) over t+3..t+23. NDX grid gate._frame('NDX','1984-01-03','2014-12-31','1986-01-02');
  SPX grid gate._frame('SPX','1928-01-03','1985-12-31','1955-01-03').
- Universe: blocks with v1_B(t) < 3 at block-start close t (era's real context). Signal: ON(t) at block-start close t.
- Early window (block membership):
  * era SPX: block start t in [1982-09-27, 1985-12-31] (labels end <= 1985-12-31 by construction).
  * era NDX: block start t >= 1986-01-02 AND label end (t+23) <= 1999-12-31 (a block straddling into 2000 is dropped from both windows).
  * Pooled statistic (era-matched base, as OV1-C): n_on = sum_e n_on,e; cond = sum of on-block wins / n_on;
    base = sum_e n_on,e x base_e / n_on, base_e = hit rate of ALL universe blocks of era e in the window.
  * PASS_early iff n_on >= 8 AND cond >= base + 0.10 AND cond >= 0.60. NDX-only and SPX-only numbers are reported, do not gate.
- Unseen window: NDX block start t >= 2000-01-03 (labels end <= 2014-12-31). base = hit rate of all unseen universe blocks;
  PASS_unseen iff n_on >= 8 AND cond >= base + 0.10 AND cond >= 0.60. Opened ONCE, only if early passes. n_on < 8 = FAIL
  (expected risk: at most 5 events x 2 block starts = 10 possible on-blocks).
- Information only (not variants, not in N, cannot rescue a fail; reported in the early window):
  (i) PIT sensitivity: pre-1994 events usable +5 trading days instead of +1; (ii) control: ALL target cuts (meeting days included),
  same 42-day rule; (iii) on-blocks in any v1 state; (iv) binomial SE of cond and one-sided exact binomial P(X >= wins | n_on, base).
- Deflation: N = 1 -> sqrt(1 + ln N) = 1.

## 6. Pass / fail actions
- Early FAIL -> stop, unseen never opened, kill_verdict FAIL, CLOSE + registry row proposal.
- Early pass -> unseen once with the identical rule. Unseen FAIL -> FAIL, CLOSE + registry row.
  An unseen pass is discounted: the 2001 and 2008 intermeeting cuts are famous and the idea generator knew them.
- Both pass -> L.measure2('OV1-G', make2) with B_new on all 5 bases (ON per section 4b.5). FINAL PASS iff HEADLINE_MS1 (dev250_path)
  > 0.1616 AND REAL_NDX > 0.3108 AND dev250_path pw_vs_s085 >= 0.55 AND real_spx_55_85 cagr >= v1's real_spx_55_85 cagr - 0.01
  (covered 1982-09..1985 only). Glued reported as an upper bound only; dd80 reported. Information-only PIT sensitivity (+5 days pre-1994)
  re-run in measure2 if reached; if it flips a pass, that is reported as a caveat.
- Every counted result -> ledger.csv (lane,variant,window,metric,value) and results/*.json; RESULT_OV1-G_KO.md in Korean.
- lab 사용: 아니오 (Fed target and FOMC calendar are not in the lab panel; v1 overlay needs ov1lib/measure2).
