# FRESH1 amendment A2 (written 2026-11-11 before the numbers below exist)

Extra audit diagnostic A6, not in the sealed design. It tests the yardstick, not a strategy.

Question: is the conservative yardstick (MS1 dev250_path, alarms recomputed on scrambled
paths) too pessimistic about v1, as the user suspects (16.2% vs personal view 25%+)?

Method: use the one era that was NOT used to design v1's alarms, S&P 500 1955-1985.
Build 500 thirty-year paths from S&P 1955-85 days (250-day blocks, same seed rule as MS1),
once with alarms recomputed on the path ("path") and once with alarms pasted from their
original dates ("glued"). Then locate the real 1955-85 outcome of v1 (11.94%, locked
reference) inside both distributions. Same for 1970-85 as information.

Reading rule (fixed now):
- real outcome inside the 25th-75th percentile of "path": the path yardstick matches an
  unseen era; 16.2% stays the fair central expectation.
- real outcome above the 75th percentile of "path" and inside 25th-75th of "glued":
  the path yardstick understates v1; the fair expectation lies between path and glued.
- real outcome below the 25th percentile of "path": even the path yardstick is optimistic.
One era is one draw, so this is weak evidence either way and is reported as such.
