# DF1/DF2 "other checks" brief (2026-11-18). Read fully; it is your only shared context.

User ask (thread "최대 방어 매매법 중 최고 수익 찾기"): find the most defensive trading method, and among defensive ones the highest return.
Follow-up (12:39 KST): "when done, check that running OTHER checks would not reveal problems or change the numbers". Your job is one such
check family. The goal is to find out, BEFORE we report, whether any reasonable alternative check would lower a headline number, push a pick
out of its defense tier, or flip which config is picked. Be adversarial: try to break the result, not to confirm it.

## Hard rules (same as /mnt/project-files/research/df1/verify/BRIEF_VERIFY.md — read its "Hard rules" section and obey it)
- Data <= 2014-12-31 only; forbidden files list in that brief; no mcp__hearthbot / remote-devices / github / Financial_Datasets; no network fetch
  except none (all data needed is local); no memory writes; no git; no sub-agents.
- Python: `mkdir -p /tmp/chk_<ID> && cd /tmp/chk_<ID> && export NUMBA_CACHE_DIR=/home/claude/nbcache_std && timeout 1500 ~/.cache/lab/ms1-venv/bin/python -B script.py`.
  NEVER run python with cwd under /mnt/project-files/research. Max 2 processes. The numba engine uses all cores; avoid running more than one
  heavy job at a time. Do not edit /mnt/project-files/research/df1/code/ or results/. Write only in /mnt/project-files/research/df1/checks/<ID>/.

## What exists (read PRECOMMIT_DF1.md and PRECOMMIT_DF2.md in /mnt/project-files/research/df1/ first — they are the spec)
- Engine: `sys.path.insert(0,'/mnt/project-files/research/df1/code'); import dfctx as DC, dfe, run_grid as RG, run_df2 as R2`
  - `m = DC.market(name)` -> dict of (P,T) arrays r rf rb cpn idxup bondup st_v1 st_al vol20 + 'ctx' (ov.Ctx) + 'X_index'.
    names: dev250_path (500 bootstrap paths, HEADLINE), dev250_glued, real_ndx_86_14, real_spx_29_54 (fill A), real_spx_29_54_B,
    real_spx_55_85, real_spx_70_85, UK, CA, AU, DE, FR, JP. WARM = 300 warm-up rows; CAGR years = (T-300)/252.
  - `RG.configs()` (483 DF1 configs), `R2.configs()` (640 DF2), `R2.run_cfg(cfg, m, **engine_overrides)` -> out array (P,9);
    `dfe.stats(out, T)` -> (cagr per path, mdd per path); `RG.summ(out, T, path_bool)` -> dict of the standard metrics.
  - `DC.target(m, k, sig, Lmax)` pre-brake exposure; `dfe.run(m, L, recon=False, **kw)` engine (kw: delay cost tax D harvest cspr er3 erq erb
    ertb step_hi step_lo roff vmode kon d0 d1 kfl reb_every). Contexts are built in dfctx._finish (read it to rebuild a market from a new
    index matrix / new X: e.g. other bootstrap seeds: `ov.boot_idx(len(X), P=500, years=30, block=..., seed=..., lo=1)`, then
    `c = ov.Ctx(X, ov.flags_hist(X), ii); c.F = std.path_flags(X, ii); m = DC._finish(c, X)` where X comes from
    `jp.calendar('1986-01-02','2014-12-31')` + `jp.mkX(R, M, 'NDX')` exactly like dfctx.market does for dev250).
- Results: /mnt/project-files/research/df1/results/grid.json, grid_df2.json (all configs x all markets), select_df2.json (final tier picks),
  robust.json / robust_df2.json (delay 3, cost 2x, MS1 cash, bond-excess-0, risk-off swaps), eras.json.
- Defense metric WD = min(dev250_path MDD 10th percentile, real_ndx_86_14 MDD, real_spx_29_54 MDD). Tiers: -20% (empty), -25% (primary
  "maximum defense"), -30%, -40%. Selection inside a tier = max dev250_path median after-tax CAGR (tie <0.05pp -> higher real NDX).
- ADOPTED PICKS: T25 `v1|s0.1|L1.0|K1|RB` (path 8.97%, WD -24.06%), T30 `v1|s0.2|L1.0|K1|RB` (path 10.18%, WD -29.97%),
  T40 `DF2|M2|b1|v1|s0.3|L1.5|K2|RB` (path 13.24%, WD -39.26%). References: QQQ 1x hold path 11.72% (WD -85%), v1 15.18% (WD -88%).

## Output
Write code + `result.json` + a 10-20 line `REPORT.md` (English) into /mnt/project-files/research/df1/checks/<ID>/.
Your final answer must be the structured object requested (verdict per pick + the numbers behind it). State plainly when a check DOES change
a number or a pick — that is the most valuable outcome. Label synthetic/reconstructed data NON-ACTUAL.
