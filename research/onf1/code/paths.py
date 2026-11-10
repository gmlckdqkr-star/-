"""Folder layout shared by the ONF1 scripts.  ROOT = the folder that contains code/ (override with ONF1_ROOT).
Full data (through 2026) lives in ROOT/data when working locally and in ROOT/holdout/data in the project folder.
Outside project files needed on EVERY run (read by the v1 standard engine; not in this folder), all under PROJ/research/:
  modules  measure_std/std.py; c3_brake/code (beng, bk, brakes, agents/alt/alt.py, agents/cushion/cush2.py, agents/escape/esc.py);
           c3_combo/code (bvar, ce, jp); c3_integrated/code/ig.py; c3_invent/code/iv.py; c3_multi/code/md.py; c3_relax/code/rx.py;
           crash_overlay/code (common, mkt, ov, strat); mf1/code (mfeng, parity check only)
  data     data/panel_f32.npz.xz, data/panel_ext_f32.npz.xz, data/deep_history/clean/{SPX_TR,TBILL}_daily_1927_2014.csv,
           data/deep_history/raw/TB3MS.csv, data/macro_n/raw/{AAA,BAA,DAAA,DBAA}.csv, data/macro_regime/raw/SHILLER_ie_data_current.xls,
           c3_brake/code/agents/alt/fin_params.json, c3_multi/data/kf_sel.bin.xz
Python packages: pandas, numpy, numba, xlrd."""
import os, tempfile
ROOT = os.environ.get('ONF1_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, 'code') + '/'
RES = os.path.join(ROOT, 'results') + '/'
HOLD = os.path.join(ROOT, 'holdout') + '/'
DATA = (os.path.join(ROOT, 'data') if os.path.isdir(os.path.join(ROOT, 'data')) else os.path.join(ROOT, 'holdout', 'data')) + '/'
CUT = os.path.join(ROOT, 'data_cut') + '/'
PROJ = os.environ.get('ONF1_PROJECT_ROOT', '/mnt/project-files').rstrip('/')   # project files root (measure_std, c3_brake, mf1, data panel)
os.environ.setdefault('NUMBA_CACHE_DIR', os.path.join(tempfile.gettempdir(), 'onf1_nbcache'))
