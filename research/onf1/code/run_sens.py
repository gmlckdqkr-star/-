"""Sensitivities OUTSIDE the pre-registration (information only: candidates, pass rule and verdict are NOT changed by these).
<=2014 data only, corrected measurement (de-meaned synthetic residual, 30 seeds), d = paired median difference vs v1.
  python -B code/run_sens.py A|B|C|D|E|F|G|V -> results/sens_<section>_le2014.json (+ print; V = v1 path statistics)
  A fee   : fee per side 0.30bp and 0.60bp (registered 0.83bp and stress 1.66bp are in fix_*), modes C and M
  B m96   : mode M with the premium starting 1996-01-01 instead of 1993-01-29 (the SPY 1993-95 night premium is not robust
            to a tick-size adjustment of the opening print), base fee and fee x2
  C carry : 'carry-neutral' mode C: the synthetic night also earns rf*(W_ON - beta) (registered C sets the intercept of
            the RAW night return to 0 while the engines charge the night 81% of the financing cost), base fee and fee x2
  D cash  : futures-account cash earns max(rf-2%p, 0) after 15.4% tax (the upload's assumption; project rule is 0):
            P presets and F1, alone and together with carry, base fee and fee x2
  E spx   : S&P-era bases real_spx_55_85 / real_spx_70_85 (no night data at all: fully synthetic, alpha 0), mode C, all 12
  F unit  : T1/T5 with whole MNQ contracts at 80M KRW start (1 MNQ = 83.55M KRW notional), modes C and M
  G final : added after the fourth review round: PRESET_A US-only with the brake ONE day late (bd1); the stacked favourable
            case (mode M + account cash interest + fee 0.30bp) with the brake on the same close / 1 day / 2 days late;
            T1/T5 with whole contracts when 1 MNQ = 74.9M KRW (index of 2026-11-09 instead of 2026-10-07)"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
import numpy as np
from dataclasses import replace
import ntilt, ms1f, eng
sec = sys.argv[1]
SEEDS = [11] + [s for s in range(1, 31) if s != 11]
BN = ('dev250_path', 'real_ndx_86_14'); SPX = ('real_spx_55_85', 'real_spx_70_85')
T = {'T1': dict(impl=0, tau=1.0, gate=0, phi=0.15), 'T2': dict(impl=0, tau=0.5, gate=0, phi=0.075), 'T3': dict(impl=0, tau=2.0, gate=0, phi=0.30),
     'T4': dict(impl=0, tau=1.0, gate=1, phi=0.15), 'T5': dict(impl=0, tau=1.0, gate=2, phi=0.15), 'T6': dict(impl=0, tau=1.0, gate=0, vc=0.09, phi=0.15),
     'F1': dict(impl=1, tau=1.0, gate=0), 'F2': dict(impl=1, tau=2.0, gate=0), 'F3': dict(impl=1, tau=1.0, gate=1)}
US = dict(use_kr=False, cash_spread=None)
P = {'P1 v9-US': replace(eng.V9, **US), 'P2 v10-US': replace(eng.V10, **US), 'P3 A-US': replace(eng.PRESET_A, **US)}
_V1 = {}
def v1(bn, W0=1e7):
    if (bn, W0) not in _V1: _V1[(bn, W0)] = ntilt.ref(bn, W0)[0]
    return _V1[(bn, W0)]


def one(nm, bn, mode, fee=0.000083, bdel=0, cint=0, W0=1e7, notional=0.0):
    if nm in P:
        fin, mdd, _, _ = ms1f.measure_one(replace(P[nm], c_us=fee), bn, mode, 2, 0.004, cint, 0.25, bdel)
    else:
        kw = dict(T[nm]); kw.update(fee=fee, W0=W0, notional=notional)
        if cint: kw.update(cmode=1)
        fin, EE, o = ntilt.run(bn, mode, **kw)
    d = fin - v1(bn, W0)
    return float(np.median(fin)), float(np.median(d))


def cell(nm, mode, bases=BN, split=None, **kw):
    """30-seed mean of (median CAGR, paired median d) per basis."""
    out = {}
    for bn in bases:
        rows = []
        for sd in SEEDS:
            ms1f.SPLIT.update(seed=sd, demean=True, cut_m=None, carry=False); ms1f.SPLIT.update(split or {})
            rows.append(one(nm, bn, mode, **kw))
        a = np.array(rows)
        out[bn] = dict(cagr=float(a[:, 0].mean()), d=float(a[:, 1].mean()), d_min=float(a[:, 1].min()), d_max=float(a[:, 1].max()),
                       seeds_d_pos=int((a[:, 1] > 0).sum()), per_seed_cagr=[float(x) for x in a[:, 0]], per_seed_d=[float(x) for x in a[:, 1]])
    ms1f.SPLIT.update(seed=11, demean=False, cut_m=None, carry=False)
    return out


res = {'seeds': SEEDS, 'note': 'outside the pre-registration; information only'}
def put(key, c, bases=BN):
    res[key] = c; a, b = c[bases[0]], c[bases[1]]
    print('%-34s %s %.2f%% (d %+.2f, %d/30 pos) | %s %.2f%% (d %+.2f, %d/30 pos)' % (
        key, bases[0], a['cagr'] * 100, a['d'] * 100, a['seeds_d_pos'], bases[1], b['cagr'] * 100, b['d'] * 100, b['seeds_d_pos']), flush=True)


FEE = {'fee030': 0.00003, 'fee060': 0.00006, 'base': 0.000083, 'fee2': 0.000166}
MAIN = ('P1 v9-US', 'P2 v10-US', 'P3 A-US', 'T5', 'F1')
if sec == 'A':
    for nm in MAIN:
        for mode in ('C', 'M'):
            for f in ('fee030', 'fee060'): put('%s|%s|%s' % (nm, mode, f), cell(nm, mode, fee=FEE[f]))
    put('P3 A-US bd2|C|fee030', cell('P3 A-US', 'C', fee=FEE['fee030'], bdel=2))
    put('P3 A-US bd2|M|fee030', cell('P3 A-US', 'M', fee=FEE['fee030'], bdel=2))
elif sec == 'B':
    for nm in MAIN + ('T6',):
        for f in ('base', 'fee2'): put('%s|M96|%s' % (nm, f), cell(nm, 'M', split=dict(cut_m='1996-01-01'), fee=FEE[f]))
elif sec == 'C':
    for nm in MAIN + ('T6',):
        for f in ('base', 'fee2'): put('%s|Ccarry|%s' % (nm, f), cell(nm, 'C', split=dict(carry=True), fee=FEE[f]))
elif sec == 'D':
    for nm in ('P1 v9-US', 'P2 v10-US', 'P3 A-US', 'F1'):
        for f in ('base', 'fee2'):
            put('%s|Ccash|%s' % (nm, f), cell(nm, 'C', fee=FEE[f], cint=1))
            put('%s|Ccarry+cash|%s' % (nm, f), cell(nm, 'C', split=dict(carry=True), fee=FEE[f], cint=1))
    put('P3 A-US bd2|Ccarry+cash|base', cell('P3 A-US', 'C', split=dict(carry=True), cint=1, bdel=2))
elif sec == 'E':
    res['v1'] = {bn: float(np.median(v1(bn))) for bn in SPX}; print('v1', res['v1'])
    for nm in list(P) + list(T):
        put('%s|C|base' % nm, cell(nm, 'C', bases=SPX), SPX)
    for nm in P: put('%s bd2|C|base' % nm, cell(nm, 'C', bases=SPX, bdel=2), SPX)
elif sec == 'F':
    W0, N = 8e7, 83.55e6
    res['v1_W0_8e7'] = {bn: float(np.median(v1(bn, W0))) for bn in BN}; print('v1 at W0 80M', res['v1_W0_8e7'])
    for nm in ('T5', 'T1'):
        for mode in ('C', 'M'):
            put('%s|%s|unit80M' % (nm, mode), cell(nm, mode, W0=W0, notional=N))
            put('%s|%s|frac80M' % (nm, mode), cell(nm, mode, W0=W0))
elif sec == 'G':
    put('P3 A-US bd1|C|base', cell('P3 A-US', 'C', bdel=1))
    put('P3 A-US bd1|M|base', cell('P3 A-US', 'M', bdel=1))
    put('P3 A-US bd1|C|fee030', cell('P3 A-US', 'C', fee=FEE['fee030'], bdel=1))
    for bd, tag in ((0, 'P3 A-US'), (1, 'P3 A-US bd1'), (2, 'P3 A-US bd2')):
        put('%s|M+cash|fee030' % tag, cell('P3 A-US', 'M', fee=FEE['fee030'], cint=1, bdel=bd))
    put('F1|M+cash|fee030', cell('F1', 'M', fee=FEE['fee030'], cint=1))
    W0, N = 8e7, 74.9e6
    for nm in ('T5', 'T1'):
        for mode in ('C', 'M'): put('%s|%s|unit80M_n749' % (nm, mode), cell(nm, mode, W0=W0, notional=N))
elif sec == 'V':
    res = {'note': 'v1 path statistics for the MDD comparison line', 'v1': {}}
    for bn in BN:
        fin, EE, o = ntilt.ref(bn); mdd = (EE / np.maximum.accumulate(EE, axis=1) - 1).min(axis=1)
        res['v1'][bn] = dict(cagr=float(np.median(fin)), mdd=float(np.median(mdd)), dd80=float(np.mean(mdd <= -0.8)))
        print('v1', bn, res['v1'][bn])
else:
    sys.exit('usage: run_sens.py A|B|C|D|E|F|G|V')
json.dump(res, open(paths.RES + 'sens_%s_le2014.json' % sec, 'w'), indent=1)
