# PRECOMMIT lane CAPIT (FINAL1) - written before any CAPIT computation

Parent: /mnt/project-files/research/final1/PRECOMMIT_FINAL1.md sha256 e8b6610f28f20ca20a01e1bb7261ab44ca90552cbf53f47e8f6075378488e0a2.
The block between the two rules below is section 4 of that file, copied verbatim (byte-identical). Nothing in it is changed.

---
## 4. Lane CAPIT (agent; user idea: RSI bottom + abnormal volume), type B ADD overlay, N = 2, plus a descriptive DEPTH table
Trigger at close t (NDX, volume = the Nasdaq volume series used by RNG1, <=2014 cut):
- CAP1: RSI(14) <= 30 AND volume_t >= 2.0 x median(volume of the previous 60 trading days). Effect: for the next 42 trading days the v1 base
  target is raised to 3x wherever v1's base target is below 3x (the v1 brake still applies).
- CAP2: within the last 3 trading days RSI(14) <= 30 at least once AND max volume ratio >= 2.5; effect window 63 trading days.
Kill test B exactly as BRIEF section 4 (early <= 1999-12-31, unseen 2000-2014 once). Only a variant that passes both windows goes to measure2
(RSI computed on the path price; volume ratio glued from the source date and labelled as such). DEPTH table (descriptive only, not a test,
n of independent episodes stated): first crossing of -30/-40/-50/-60/-70% index drawdown from all-time high -> forward 1y and 3y return of
the 1x index and of the synthetic 3x product (MS1 formula), for NDX 1985-2014 and S&P 500 1928-2014 (and SOX if a <=2014 cut exists locally).
---

## Added by the lane builder (only the exact data file used for volume)
- Volume file: /mnt/project-files/research/data/panel_f32.npz.xz (sha256 fa2c35b295642ddf27924e1125a50c823ea464a0f6b47e54c0b3b254fd35242c,
  7,620,160 bytes), key `_NDX|ts` (unix s) and `_NDX|v` column 5 (volume) - the same file, key and column lane RNG1 used
  (research/rng1/PRECOMMIT_RNG1.md, research/rng1/code/rng.py `panel('_NDX')`). Rows are cut to date <= 2014-12-31 at load by the timestamp
  key before any value is looked at; rows after 2014 are never printed, saved or used.
