"""Run all GT strategies x overlays on eras + 1986-2014 block bootstrap (MS1 analog). Writes results/gt_main_lag{k}.json."""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/giant_trend/code')
LAGK = int(sys.argv[1]) if len(sys.argv) > 1 else 0
NB = int(sys.argv[2]) if len(sys.argv) > 2 else 500
from gtsetup import *
EXTRA_STRATS = sys.argv[3] if len(sys.argv) > 3 else ''
if EXTRA_STRATS:
    import gtmeta; STRATS = gtmeta.strats(EXTRA_STRATS)
ERAS = {'long': [('TRAIN', '1927-01', '1969-12'), ('CONFIRM', '1970-01', '2014-12')],
        'op': [('TRAIN', '1964-01', '1985-12'), ('CONFIRM', '1986-01', '2014-12')],
        'base': [('TRAIN', '1927-01', '1969-12'), ('CONFIRM', '1970-01', '2014-12')]}
EXTRA_ERAS = [('R5585', '1955-01', '1985-12'), ('R8614', '1986-01', '2014-12')]
mup = c.mup.astype(int)
OVL = {'L1': np.ones(c.T, int), 'L2': np.full(c.T, 2), 'L3': np.full(c.T, 3),
       'LG': np.where(mup == 1, 3, 1), 'LG0': np.where(mup == 1, 3, 0)}
if LAGK: OVL = {k: np.r_[np.full(LAGK, v[0]), v[:-LAGK]] for k, v in OVL.items()}

def era_months(a, b):
    i0 = c.t_of(a); i1 = c.t_of(b); return list(range(i0 - 1, i1 + 1))

rng = np.random.default_rng(20261104)
b0 = c.t_of('1986-01'); b1 = c.t_of('2014-12')
PATHS = []
for _ in range(NB):
    st = rng.integers(b0, b1 - 11 + 1, size=30)
    m = [int(st[0]) - 1]
    for s in st: m += list(range(int(s), int(s) + 12))
    PATHS.append(m)

def boot(dec, lev):
    cg, dd80 = [], 0; W = []
    for m in PATHS:
        w, _ = E.run(dec, lev, P, m); g = w[-1] ** (1 / 30) - 1 if w[-1] > 0 else -1
        cg.append(g); pk = np.maximum.accumulate(w); dd80 += (w / pk - 1).min() <= -0.8; W.append(np.log(max(w[-1], 1e-12)))
    return np.array(cg), dd80 / len(PATHS), np.array(W)

out = {}; t_start = time.time()
base_boot = None
for name, (mk, fam) in STRATS.items():
    dec = mk()
    if LAGK: dec = S.lag(dec, LAGK)
    res = {}
    for ov, lev in OVL.items():
        if name == 'MKT_H' and ov not in ('L1', 'L2', 'L3'): continue
        row = {}
        for tag, a, b in ERAS[fam] + EXTRA_ERAS:
            mm = era_months(a, b); w, pre = E.run(dec, lev, P, mm)
            st_ = E.stats(w, pre, c.rf[mm[1:]]); row[tag] = {k: round(v, 4) for k, v in st_.items()}
        res[ov] = row
    # bootstrap only for L1 and the TRAIN-best overlay
    best = max(res, key=lambda k: res[k]['TRAIN']['cagr'])
    for ov in sorted({'L1', best}):
        cg, p80, lw = boot(dec, OVL[ov])
        res[ov]['BOOT'] = dict(med=round(float(np.median(cg)), 4), p10=round(float(np.percentile(cg, 10)), 4), dd80=round(p80, 3))
        if name == 'MKT_H' and ov == 'L1': base_boot = lw
        res[ov]['_lw'] = lw
    res['_best'] = best
    out[name] = res
    print(name, 'best', best, {ov: (res[ov]['TRAIN']['cagr'], res[ov]['CONFIRM']['cagr'], res[ov]['TRAIN']['sharpe'], res[ov]['CONFIRM']['sharpe']) for ov in res if not ov.startswith('_')}, round(time.time() - t_start), flush=True)
# paired d vs market 1x hold on same paths
for name, res in out.items():
    for ov in list(res):
        if ov.startswith('_'): continue
        if '_lw' in res[ov]:
            d = (res[ov]['_lw'] - base_boot) / 30
            res[ov]['BOOT']['d_vs_mkt'] = round(float(np.median(d)), 4); res[ov]['BOOT']['win'] = round(float((d > 0).mean()), 3)
            del res[ov]['_lw']
json.dump(out, open(f'/mnt/project-files/research/giant_trend/results/gt_{EXTRA_STRATS or "main"}_lag{LAGK}.json', 'w'), indent=1)
print('done', round(time.time() - t_start))
