# Designer lens: idle-cash

Ideas only; written without running market data. Rules are quoted as the designer wrote them.

## 1. Gated long-Treasury fill of idle cash (yield-shock exclusion + stock-bond hedge-regime gate)

**family**: Idle-cash fill with duration (E06 family, reopened)

**exact_rule**: v1 runs unchanged. One extra instrument B in mode 0.
Signals at close t (traded t+2):
- r_s = daily log return of the Nasdaq-100 index; dy_s = daily change in pp of the 10-year constant-maturity yield, with the same publication lag v1 uses for its yield flag.
- kappa_t(W) = mean over the last W valid days s<=t of sign(r_s)*sign(dy_s); days with r_s=0, dy_s=0 or a missing yield are skipped.
- H_t (hedge regime, with hysteresis): H=1 if kappa_t >= +0.10; H=0 if kappa_t <= 0; otherwise H_{t-1}. H=0 until W valid days exist.
- S_t = v1's own shock6m flag (10-year yield up more than 1pp in 6 months), unchanged.
- idle_t = 1 - q_t/3, where q_t is the level v1 actually holds after the brake.
- E_t (one point only) = Nasdaq-100 close below its 50-day simple average.
Gate_t = (S_t = 0) AND (H_t = 1) [AND E_t in point P5; H dropped in points P4, P6].
Target weight of B = min(cap, floor(10*idle_t)/10) if Gate_t, else 0.
Trading: move B to target only when |target - held| >= 0.20 of the account, or when target = 0 and held > 0; the mode-0 cut applies whenever v1 needs the cash.
Reported alongside, with no selection on them: (a) the ungated fill on the same engine (E06 replica); (b) the same points with the bond's excess return over bills demeaned over 1986-2026 (zero-excess-return null).
Pre-set kill tests: K1 DESIGN mean paired block difference > 0 and at least 4 of 7 design blocks >= -0.5pp/yr; K2 DESIGN mean excluding 2001-03 >= 0; K3 WEAK mean > 0 with 1986-88 and 1992-94 each >= -1pp/yr; K4 difference >= 0 under the zero-excess-return null (if K4 fails the result is a bond-regime bet, per X47, not an edge); K5 share of resampled paths reaching -80% not above v1's.

**instruments**: TMF (3x 20-year Treasuries, 2009-04) or TLT (2002-07). Before inception: the project's synthetic series from the 30-year/10-year constant-maturity yields as used in E06 (3x daily, financed at 2x the 3-month bill, 1.0%/yr fee for the 3x version).

**engine_mode**: v1 unchanged + mode 0 (non-dilutive overlay)

**parameter_points**: P1 (primary): TMF, cap 1.0, gate notS AND H(252).
P2: TMF, cap 0.5, gate notS AND H(252).
P3: TLT, cap 1.0, gate notS AND H(252).
P4: TMF, cap 1.0, gate notS only (E06 plus v1's own flag; shows what H adds).
P5: TMF, cap 1.0, gate notS AND H(252) AND Nasdaq-100 below its 50-day average (bonds only while equities are still weak).
P6: TLT, cap 1.0, gate notS only.
Fixed, not tuned: kappa thresholds +0.10 / 0, 0.20 no-trade band, 0.1 weight grid.

**data_needed_and_start**: All in the project: Nasdaq-100 index (1985), 10-year and 30-year yields (1970/1977), 3-month bill, TLT (2002), TMF (2009), v1 flags and held level from the engine. H is valid from about 1986-10; before that the fill is off.

**nearest_closed_ids**: E06 (TMF fill, +5.2pp but bond-bull share), E10 (term-premium gates, 0/7), E09 (inflation gates), X47 and X39 (bond fill = policy bet), E03, E02

**main_failure_mode**: 1. Era risk, stated plainly: if long bonds earn no excess return, a 3x bond fund loses its decay and fee (about 6-7%/yr) on the idle half of the account, up to about -3pp/yr; P4 has no protection against a slow yield grind that never reaches +1pp in 6 months.
2. Post-panic giveback while v1 is still waiting to re-enter (Jan-Jun 2009 after the Dec 2008 spike; Oct-Nov 1998).
3. Joint selloff inside a hedge regime before either gate reacts (spring 2025 type).
4. Brake feedback: fill losses deepen the account drawdown and make the brake cut v1's level at re-entry.
5. Concentration: one block (2001-03) may carry most of the DESIGN gain, which is why K2 exists.

**own_probability_to_pass_pct**: 18

## 2. SOXL crash-rebound sleeve funded only from v1's idle cash (owner direction a, non-dilutive form)

**family**: Semiconductor crash buying (T13 / AG2 family, reopened through non-dilutive funding)

**exact_rule**: v1 runs unchanged. One extra instrument, SOXL.
Signals at close t (traded t+2):
- X_t = SOXX adjusted close (before 2001-07: the Ken French 48-industry Chips total-return index, as in AG2).
- DD_t = X_t / max(X over the last 756 trading days) - 1.
- idle_t = 1 - q_t/3 (q_t = level v1 holds after the brake).
State FLAT -> LONG when all hold: (a) DD_t <= -D; (b) confirm variant: X_t above its 50-day simple average; no-confirm variant: always true; (c) idle_t >= 0.5; (d) not blocked.
State LONG: target SOXL weight = min(w, idle_t).
LONG -> FLAT when any holds: (e) X_t <= 0.85 * X at entry (stop; sets the block); (f) DD_t > -0.10 (cycle back near its 3-year high); (g) mode 0 only: idle_t < 0.05 for 5 consecutive closes (v1 fully re-invested); (h) mode 1 only: X_t <= 0.75 * highest X since entry (trailing exit).
Block after a stop: confirm variant, until X has closed below its 50-day average at least once and then above it again; no-confirm variant, 20 trading days.
w = 0.15 in mode 0, 0.10 in mode 1.

**instruments**: SOXL (3x semiconductors, 2010-03). Before inception: 3x daily SOXX / Chips proxy, financed at 2x the 3-month bill, 0.95%/yr fee (AG2 construction). Signal series SOXX (2001) / Chips proxy.

**engine_mode**: v1 unchanged + mode 0 for S1-S4; mode 1 (sleeve has priority while held, capped at 10%) for S5-S6

**parameter_points**: S1: D=0.35, confirm, mode 0, w=0.15.
S2: D=0.50, confirm, mode 0, w=0.15.
S3: D=0.35, no confirm, mode 0, w=0.15 (closest to the owner's wording: buy in the crash).
S4: D=0.50, no confirm, mode 0, w=0.15 (deeper entry).
S5: D=0.35, confirm, mode 1, w=0.10 (longer hold, trailing exit).
S6: D=0.50, confirm, mode 1, w=0.10.

**data_needed_and_start**: All in the project: SOXX (2001), SOXL (2010), Ken French Chips daily series (1926), 3-month bill, v1 held level. Scored from 1986.

**nearest_closed_ids**: T13 (bottom buying; chip index 1 win in 3), AG2 result file (8 rules, -3.1 to +2.7%/yr alone 1950-2014, all worse when carved out of v1), T40 (capitulation add), E07 (SOXL as on-state fund), X41, L03

**main_failure_mode**: A long semiconductor bear market with repeated 20-50% rallies (2000-02): each entry loses about 45% of the sleeve at the stop, five or six times in a row (about -35% of the account in the worst case before the winners). Second: a gap through the stop on a 3x fund with a two-day execution delay makes the realised loss larger than planned. Third: the owner's actual wish (hold to the cycle top) is not what mode 0 delivers.

**own_probability_to_pass_pct**: 3
