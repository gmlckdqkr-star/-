"""Measurement correction after the phase-2 audit (made AFTER the pre-registration; candidates and pass rule unchanged).
  1. synthetic pre-1999 night residual: drift-free (mean removed) and 30 seeds instead of the single seed-11 draw,
  2. P presets: yearly tax deduction 0.25 of start equity (2.5M KRW on 10M, as for v1 and T/F),
  3. P presets also with the brake/cool-down multiplier through the same 2-day delay as v1 ('bd2').
Judging bases only (dev250_path, real_ndx_86_14).   python -B code/run_fix.py [P|T|F ...]  -> results/fix_<grp>_le2014.json"""
import sys, json
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
import numpy as np
from dataclasses import replace
import ntilt, ms1f, eng
which = sys.argv[1] if len(sys.argv) > 1 else 'PTF'
SEEDS = [11] + [s for s in range(1, 31) if s != 11]
BN = ('dev250_path', 'real_ndx_86_14'); OUT = paths.RES
T = {'T1': dict(impl=0, tau=1.0, gate=0, phi=0.15), 'T2': dict(impl=0, tau=0.5, gate=0, phi=0.075), 'T3': dict(impl=0, tau=2.0, gate=0, phi=0.30),
     'T4': dict(impl=0, tau=1.0, gate=1, phi=0.15), 'T5': dict(impl=0, tau=1.0, gate=2, phi=0.15), 'T6': dict(impl=0, tau=1.0, gate=0, vc=0.09, phi=0.15)}
F = {'F1': dict(impl=1, tau=1.0, gate=0), 'F2': dict(impl=1, tau=2.0, gate=0), 'F3': dict(impl=1, tau=1.0, gate=1)}
US = dict(use_kr=False, cash_spread=None)
P = {'P1 v9-US': replace(eng.V9, **US), 'P2 v10-US': replace(eng.V10, **US), 'P3 A-US': replace(eng.PRESET_A, **US)}
V1 = {bn: ms1f.ref_s085(bn) for bn in BN}


def one(kind, spec, bn, mode, fee2=False, bdel=0):
    if kind == 'P':
        cfg = replace(spec, c_us=0.000166) if fee2 else spec
        fin, mdd, _, _ = ms1f.measure_one(cfg, bn, mode, 2, 0.004, 0, 0.25, bdel)
    else:
        kw = dict(spec); kw.update(fee=0.000166) if fee2 else None
        fin, EE, o = ntilt.run(bn, mode, **kw); mdd = (EE / np.maximum.accumulate(EE, axis=1) - 1).min(axis=1)
    d = fin - V1[bn]
    return float(np.median(fin)), float(np.median(d)), float(np.mean(d > 1e-5)), float(np.median(mdd)), float(np.mean(mdd <= -0.8))


def agg(rows):
    a = np.array(rows); c, d = a[:, 0], a[:, 1]
    return dict(cagr=float(c.mean()), cagr_sd=float(c.std(ddof=1)), cagr_min=float(c.min()), cagr_max=float(c.max()),
                d=float(d.mean()), d_min=float(d.min()), d_max=float(d.max()), seeds_d_pos=int((d > 0).sum()), pw=float(a[:, 2].mean()),
                mdd=float(a[:, 3].mean()), dd80=float(a[:, 4].mean()), per_seed_cagr=[float(x) for x in c], per_seed_d=[float(x) for x in d])


def go(kind, group, tag, variants=((0, ''),)):
    res = {'seeds': SEEDS, 'v1': {bn: float(np.median(V1[bn])) for bn in BN}}
    for nm, spec in group.items():
        for bdel, suf in variants:
            for mode, fee2 in (('C', False), ('M', False), ('H', False), ('Z', False), ('C', True), ('M', True)):
                rows = {bn: [] for bn in BN}
                for sd in SEEDS:
                    ms1f.SPLIT.update(seed=sd, demean=True)
                    for bn in BN: rows[bn].append(one(kind, spec, bn, mode, fee2, bdel))
                key = '%s%s|%s|%s' % (nm, suf, mode, 'fee2' if fee2 else 'base'); res[key] = {bn: agg(rows[bn]) for bn in BN}
                a, b = res[key]['dev250_path'], res[key]['real_ndx_86_14']
                # rule 1 per seed: CAGR > v1 and paired d > 0 on both bases
                r1 = [(x > res['v1']['dev250_path']) and (y > 0) and (u > res['v1']['real_ndx_86_14']) and (v > 0)
                      for x, y, u, v in zip(a['per_seed_cagr'], a['per_seed_d'], b['per_seed_cagr'], b['per_seed_d'])]
                res[key]['seeds_pass_both'] = int(sum(r1)); res[key]['pass_flags'] = [bool(x) for x in r1]
                # rule 2 wording (fee x2): paired d > 0 on both bases (no CAGR condition)
                res[key]['dpos_flags'] = [bool((y > 0) and (v > 0)) for y, v in zip(a['per_seed_d'], b['per_seed_d'])]
                print('%-22s dev %.2f%% (d %+.2f, %d/30 pos, dd80 %.2f) | real %.2f%% (d %+.2f, %d/30 pos) | both>v1 %d/30' % (
                    key, a['cagr'] * 100, a['d'] * 100, a['seeds_d_pos'], a['dd80'], b['cagr'] * 100, b['d'] * 100, b['seeds_d_pos'], sum(r1)), flush=True)
            # rule 1 (base fee: CAGR > v1 and d > 0 on both bases) AND rule 2 (fee x2: d > 0 on both bases), per seed
            k1 = '%s%s|C|base' % (nm, suf); k2 = '%s%s|C|fee2' % (nm, suf)
            both = [x and y for x, y in zip(res[k1]['pass_flags'], res[k2]['dpos_flags'])]
            res['%s%s|rule1and2_C' % (nm, suf)] = int(sum(both))
            k1 = '%s%s|M|base' % (nm, suf); k2 = '%s%s|M|fee2' % (nm, suf)
            res['%s%s|rule1and2_M' % (nm, suf)] = int(sum(x and y for x, y in zip(res[k1]['pass_flags'], res[k2]['dpos_flags'])))
            print('   %s%s: seeds passing rule 1+2 under C: %d/30, under M: %d/30' % (nm, suf, res['%s%s|rule1and2_C' % (nm, suf)], res['%s%s|rule1and2_M' % (nm, suf)]), flush=True)
    json.dump(res, open(OUT + 'fix_%s_le2014.json' % tag, 'w'), indent=1)


if 'P' in which: go('P', P, 'P', ((0, ''), (2, ' bd2')))
if 'T' in which: go('T', T, 'T')
if 'F' in which: go('T', F, 'F')
