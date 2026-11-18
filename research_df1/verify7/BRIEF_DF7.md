# DF7 verification brief (2026-11-18). Read this whole file first; it is your only shared context.

## Hard rules
- Data <= 2014-12-31 only. Never compute, print or write any number from 2015 or later. The sealed periods 2016-18 and 2022-24 must never be touched.
- The AQR raw file /mnt/project-files/research/data/trend_aqr/raw/*.xlsx contains post-2014 rows: do NOT open it. Use only tsmom_monthly_le2014.csv.
- Never open these (forbidden; paths relative to /mnt/project-files/): reports/best_results_summary_*, research/deep/, research/audit/, any diag/ folder,
  research/mass_scan/, research/us_mix_sb_oos/, research/user_port/, research/c3_relax/RESULT_RELAX_KO.md, research/c3_relax/results/holdout_once.csv,
  research/user_v104/, research/user_v107/, research/user_port4/, research/c3_stock_combo/, research/c3_create/fwd/, research/theory_sim/holdout/,
  research/s085_contra/holdout/, research/v002/holdout/, research/v002/RESULT_V002_KO.md, research/onf1/holdout/, research/np1/holdout/,
  research/soxx_anatomy_20261111/FORWARD_OBS_KO.md, tools/s085_now/out/, tools/s085_now/cache/, research_xv1/, research/xv1*, research/ov1/lanes/*/data/raw_*,
  any file or folder named holdout*. (Code you import may load research/deep/lib indirectly; never open it yourself.)
- Do not use mcp__hearthbot__*, mcp__remote-devices__*, mcp__github__*, Financial_Datasets or any network fetch. Do not write project memory.
  Do not git commit/push. Do not spawn sub-agents or workflows. Do not edit anything under /mnt/project-files/research/df1/code/ or results/.
- /mnt/project-files is a slow network mount: never search or list it recursively; use exact paths.
- Python: `mkdir -p /tmp/df7v_<ID> && cd /tmp/df7v_<ID> && export NUMBA_CACHE_DIR=/tmp/df7v_<ID>/nb && timeout 1500 python3 -B script.py`.
  NEVER run python with the current directory under /mnt/project-files/research. Import the project code with
  `sys.path.insert(0, '/mnt/project-files/research/df1/code'); import df7 as D` (it pulls df5run/df5lib/df5data/dfk). At most 2 python processes at a time.
  World 'P' and 'X' are 500 paths x 7860 days; each run takes a few seconds; a whole world load ~30 s and ~2-4 GB RAM. Free a world with D.drop(name).
- Write only inside /mnt/project-files/research/df1/verify7/<ID>/ (your code + one JSON + one short REPORT.md in English).

## What DF7 is
User question: earlier rules all look tied to QQQ; are the user's own QLD + GDE + RSST + DBMF portfolios any good; is there a method (no TQQQ, leverage <= QLD,
gold / Treasuries / managed-futures trend as equal axes, or a new trading method) that beats QQQ hold on return AND has shallower drawdowns on all three bases
(REAL = actual NDX 1986-2014 single path; P = full bootstrap 500 paths; X = crash-free bootstrap 500 paths).
Spec: /mnt/project-files/research/df1/PRECOMMIT_DF7.md (sha256 ea733ce4..., locked in commit 2c4ad98 with code/df7.py sha 76dee7a4...; the lock file is
PRECOMMIT_DF7.sha256). Code: /mnt/project-files/research/df1/code/df7.py (trend proxy, panel7, configs, job7, run_set, gates, main, final, fstar).
Engine/gates reused from DF5: dfk.py (engine), df5run.py (run_job, qqq, summ), df5gate.py (gate_row), df5stress.py (gate_conds), df5data.py (panel), df5lib.py (worlds).
Results: results/df7_user.json (step A), results/df7_trend_stats.json, results/df7_main.json (198 rules, PRIM), results/df7_final.json (H1/H3/H4/H5, tiers,
selection, f*, report rows under PRIM/RAW/ZERO incl. P5/10/20/30, X5/10/20/30, REAL, P125). Draft result: RESULT_DF7_KO.md (Korean) when present.
Conventions: PRIM = DF5 neutral panel (gold & long Treasuries zero excess over T-bill) + trend excess shifted to 50% of the world's proxy mean;
Q = same with 25%; RAW = raw panel + 100%; ZERO = neutral + 0%. Gate summary per key: cagr = median per-path CAGR, p10, mdd_med, mdd_p10, pair = median of
per-path (rule CAGR - QQQ CAGR). Never use arithmetic means across paths for judgement.

## Return format
Your final answer is data for the orchestrator: a short list of findings, each with severity (critical / high / medium / low / none), the evidence
(file:line or numbers), and whether it changes any pass count, tier, selection, f* or headline number. Also give the path of your REPORT.md.
