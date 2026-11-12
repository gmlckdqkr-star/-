"""JS1 L2 (PRECOMMIT s.6): US v1 overlay with JST-rule state. usage: js1_overlay.py DATA.npz OUTDIR   (reads confirm.json)"""
import sys, os, json, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/claude-0/nbc')
sys.path.insert(0, '/mnt/project-files/research/measure_std'); sys.path.insert(0, '/mnt/project-files/research/gx1/code'); sys.path.insert(0, '/home/user/repo/research_js1/code')
import std, gx1lib, ce, js1_ref as R
data, out = sys.argv[1:3]; P = dict(np.load(data, allow_pickle=True)); A = P['A']; yrs = P['years']; ctry = list(P['ctry']); US = ctry.index('USA')
res = json.load(open(out + '/confirm.json')); cs = res['cands']
passed = [c for c in cs if c['L1']]; diag = False
if not passed: passed = sorted(cs, key=lambda c: -c['z_confirm'])[:3]; diag = True
FR = gx1lib.us_frames(); keys = ['real_ndx_86_14', 'dev250_path', 'real_spx_55_85', 'real_spx_70_85']
def off_series(code, idx):
    on_year = R.cond(A, code)[US]; f = np.where(idx.month >= 4, idx.year, idx.year - 1) - 1          # 3-month publication lag
    ok = (f >= yrs[0]) & (f <= 2013); st = np.where(ok, on_year[np.clip(f - yrs[0], 0, len(yrs) - 1)], True)
    return ~st                                                                                       # True = OFF (alarm)
def v1(cc):
    B, bfn, bp, fs = std.s085(cc); return np.array(B, dtype=np.float64), bfn, bp, fs
CTX = {k: gx1lib.us_ctx(*FR[k]) for k in keys}; base = {}; bdd = {}
for k in keys:
    cc = CTX[k]; B, bfn, bp, fs = v1(cc); fin, E = std.engine(cc, B, bfn, bp, fs, cspr=10.0); base[k] = fin; bdd[k] = float(np.mean(ce.mdd(E) <= -0.8))
    print('v1', k, 'median %.4f' % np.median(fin), 'dd80 %.2f' % bdd[k], flush=True)
rows = []
for c in passed:
    r = dict(name=c['name'], map=c['map'], code=c['code'], z_confirm=c['z_confirm'], diag=diag)
    for k in keys:
        cc = CTX[k]; X = FR[k][0]; off = off_series(c['code'], X.index)[cc.ii]
        B, bfn, bp, fs = v1(cc); B2 = np.where(off, np.minimum(B, 1.0) if c['map'] == 0 else 0.0, B)
        fin, E = std.engine(cc, np.ascontiguousarray(B2), bfn, bp, fs, cspr=10.0); d = fin - base[k]
        r[k] = dict(cagr=float(np.median(fin)), v1=float(np.median(base[k])), d=float(np.median(d)), win=float(np.mean(d > 1e-5)), off_share=float(off.mean()), dd80=float(np.mean(ce.mdd(E) <= -0.8)), dd80_v1=bdd[k])
    pas = r['real_ndx_86_14']['d'] > 0 and r['dev250_path']['d'] > 0 and r['dev250_path']['win'] >= 0.55 and r['dev250_path']['dd80'] - r['dev250_path']['dd80_v1'] <= 0.05
    r['L2'] = bool(pas); rows.append(r); print(c['name'][:90], {k: (round(r[k]['cagr'], 4), round(r[k]['d'], 4)) for k in keys}, 'L2', pas, flush=True)
json.dump(rows, open(out + '/overlay.json', 'w'), indent=1)
