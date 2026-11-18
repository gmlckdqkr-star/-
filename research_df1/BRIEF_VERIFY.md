# DF1/DF2 verification brief (2026-11-18). Read this whole file first; it is your only shared context.

## Hard rules
- Data <= 2014-12-31 only. Never compute, print or write any number from 2015 or later.
- Never open these (forbidden): reports/best_results_summary_*, research/deep/, research/audit/, any diag/ folder, research/mass_scan/,
  research/us_mix_sb_oos/, research/user_port/, research/c3_relax/RESULT_RELAX_KO.md, research/c3_relax/results/holdout_once.csv,
  research/user_v104/ (RESULT + results), research/user_v107/, research/user_port4/, research/c3_stock_combo/, research/c3_create/fwd/,
  research/theory_sim/holdout/, research/s085_contra/holdout/, research/v002/holdout/, research/v002/RESULT_V002_KO.md, research/onf1/holdout/,
  research/np1/holdout/, research/soxx_anatomy_20261111/FORWARD_OBS_KO.md, tools/s085_now/out/, tools/s085_now/cache/, research_xv1/, research/xv1*,
  any file or folder named holdout*. (Code you import may load research/deep/lib indirectly; never open it yourself.)
- Do not use mcp__hearthbot__*, mcp__remote-devices__*, mcp__github__*, Financial_Datasets or any network data fetch. Do not write project memory.
  Do not git commit/push. Do not spawn sub-agents or workflows. Do not edit anything under /mnt/project-files/research/df1/code/ or results/.
- /mnt/project-files is a slow network mount: never search or list it recursively; use exact paths.
- Python: `cd /tmp/<your dir> && export NUMBA_CACHE_DIR=/home/claude/nbcache_std && ~/.cache/lab/ms1-venv/bin/python -B script.py`.
  NEVER run python with the current directory under /mnt/project-files/research (a folder there shadows a pandas dependency).
  At most 2 processes at a time; wrap long jobs in `timeout 1200`.
- Write only inside your own folder /mnt/project-files/research/df1/verify/<YOUR_ID>/ (code + one JSON + one short REPORT.md in English).

## What DF1/DF2 is
Thread goal (user): find the most defensive trading method, and among defensive ones the highest return. Pre-registrations:
/mnt/project-files/research/df1/PRECOMMIT_DF1.md (sha 5d08c7be) and PRECOMMIT_DF2.md (sha a99b868f) — read both, they are the spec.
Code: /mnt/project-files/research/df1/code/dfe.py (engine), dfctx.py (market inputs + target exposure), run_grid.py (DF1 grid),
select_tiers.py (DF1 selection), run_df2.py (DF2 grid + union selection + gates), robust.py / robust2.py (sensitivity rows),
t_parity.py / t_units.py (engine checks). Results: /mnt/project-files/research/df1/results/*.json (grid.json, grid_df2.json, select.json,
select_df2.json, robust.json, robust_df2.json, parity.json, units.json).
Adopted picks: tier -25% `v1|s0.1|L1.0|K1|RB`, tier -30% `v1|s0.2|L1.0|K1|RB`, tier -40% `DF2|M2|b1|v1|s0.3|L1.5|K2|RB`.
Config id format: `<trend k>|s<sigma*>|L<Lmax>|<knee>|<risk-off>`; DF2 ids add `DF2|<M0|M2>|<band b1|b2|b3>|` in front.
MS1 conventions the engine copies: /mnt/project-files/research/c3_brake/code/beng.py (function run1) and /mnt/project-files/research/measure_std/MEASURE_STD_KO.md.

## Return format
Your final answer is data for the orchestrator: a short list of findings, each with severity (critical / high / medium / low / none),
the evidence (file:line or numbers), and whether it changes any adopted pick or headline number. Also give the path of your REPORT.md.
