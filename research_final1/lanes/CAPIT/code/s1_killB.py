"""CAPIT type-B kill test (BRIEF_FINAL1 section 4) for ONE window, real calendar. PRECOMMIT.md sha256 ec06110c92bf....
Usage: python -B s1_killB.py early            -> evaluates ONLY blocks ending <= 1999-12-31
       python -B s1_killB.py unseen           -> 2000-01-03..2014-12-31, allowed once, only for variants with early_pass on file
       python -B s1_killB.py counts_unseen    -> SIGNAL COUNTS ONLY for 2000-2014 (trigger days, on-blocks); no label, no return, no hit rate
Block grid and label = research/breakthrough/code/gate.py _frame('NDX','1984-01-03','2014-12-31','1986-01-02'): a block every 21 trading days
from 1986-01-02, label = synthetic 3x NDX beats the deposit over t+3..t+23. Universe = blocks whose v1 base target at close t is < 3.
'on' block = overlay window ON at close t.  pass_B = n_on >= 8 AND cond >= base + 0.10 AND cond >= 0.60 (thresholds fixed by the brief).
Same convention as research/ov1/lanes/OV1-G/code/s2_killB.py. S&P 1955-85: no Nasdaq volume -> not covered."""
import sys, os, json, hashlib, numpy as np, pandas as pd
LANE = '/mnt/project-files/research/final1/lanes/CAPIT/'
sys.path.insert(0, LANE + 'code'); sys.path.insert(0, '/mnt/project-files/research/ov1/code')
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code')
import ov1lib as L, gate, jp, ov, cap  # noqa
from scipy.stats import binom
SHA = hashlib.sha256(open(LANE + 'PRECOMMIT.md', 'rb').read()).hexdigest(); assert SHA.startswith('ec06110c92bf9bc4'), SHA
FRZ = dict(l.split()[::-1] for l in open(LANE + 'code/CODE_FREEZE.sha256').read().strip().splitlines())
for f in ('cap.py', 's1_killB.py'):
    assert hashlib.sha256(open(LANE + 'code/' + f, 'rb').read()).hexdigest() == FRZ[f], f + ' changed after freeze'
WIN = sys.argv[1]; assert WIN in ('early', 'unseen', 'counts_unseen')
E0, E1, U0, U1 = pd.Timestamp('1986-01-02'), pd.Timestamp('1999-12-31'), pd.Timestamp('2000-01-03'), pd.Timestamp('2014-12-31')
if WIN != 'early':
    e = json.load(open(LANE + 'results/killB_early.json'))
    passed = [v for v in cap.VARIANTS if e['variants'][v]['early_pass']]
    if WIN == 'unseen':
        assert passed, 'no variant passed early: the unseen window stays closed'
        assert not os.path.exists(LANE + 'results/killB_unseen.json'), 'unseen already opened once'
    else:
        assert not passed, 'counts_unseen is only for the case where the unseen window is NOT opened'

R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX'); cal = X.index; F = ov.flags_hist(X)
i0 = cal.searchsorted(E0) - ov.WARM
c = ov.Ctx(X, F, np.arange(i0, len(X))[None, :]); cidx = cal[c.ii[0]]                       # = std.contexts()['real_ndx_86_14']
B = pd.Series(L.v1_B(c)[0], index=cidx)
rsi = cap.rsi14(c.lvl)                                                                       # (1,T) on the context price
vr = cap.vr_for_gather(cal).reindex(cidx).values[None, :]; vr = np.where(vr < 0, np.nan, vr)   # glued by source date (real: identity)
lab = gate._frame('NDX', '1984-01-03', '2014-12-31', '1986-01-02')
pos = cal.get_indexer(lab.index); end = cal[np.minimum(pos + 23, len(cal) - 1)]

def window_mask(idx, endv=None):
    if WIN == 'early': return (idx >= E0) & ((endv if endv is not None else idx) <= E1)
    return (idx >= U0) & (idx <= U1)

def run(var):
    trig = pd.Series(cap.trigger(rsi, vr, var)[0], index=cidx); on = pd.Series(cap.on_window(trig.values[None, :], var)[0], index=cidx)
    dm = window_mask(cidx)                                                # day mask of the window (signal side)
    td = trig[dm]; od = on[dm]; Bd = B[dm]
    # trigger clusters = runs of ON days (independent episodes of the overlay)
    o = od.values.astype(int); n_epi = int(((o[1:] == 1) & (o[:-1] == 0)).sum() + (o[0] == 1)) if len(o) else 0
    sig = dict(n_days=int(dm.sum()), trigger_days=int(td.sum()), trigger_days_v1_below3=int((td & (Bd < 3)).sum()),
               on_days=int(od.sum()), on_days_v1_below3=int((od & (Bd < 3)).sum()), on_episodes=n_epi,
               v1_below3_days=int((Bd < 3).sum()),
               trigger_dates=[dict(t=str(d.date()), rsi=round(float(rsi[0][cidx.get_loc(d)]), 2), vr=round(float(vr[0][cidx.get_loc(d)]), 2),
                                   v1B=float(B[d])) for d in td.index[td.values]])
    bm = window_mask(lab.index, end)
    blk_idx = lab.index[bm]; Bt = B.reindex(blk_idx); assert Bt.notna().all()
    uni_idx = blk_idx[Bt.values < 3]; o_b = on.reindex(uni_idx).fillna(False).astype(bool)
    r = dict(variant=var, window=WIN, signal=sig, n_blocks=int(len(blk_idx)), n_universe=int(len(uni_idx)),
             universe_v1B_counts={str(k): int(v) for k, v in Bt.reindex(uni_idx).value_counts().sort_index().items()},
             n_on=int(o_b.sum()), n_on_any_v1_state=int(on.reindex(blk_idx).fillna(False).astype(bool).sum()))
    if WIN == 'counts_unseen':                                            # no label is touched
        r['on_block_dates'] = [dict(t=str(d.date()), v1B=float(Bt[d])) for d in uni_idx[o_b.values]]
        return r
    blk = lab[bm].astype(bool); uni = blk[Bt.values < 3]; y = uni[o_b.values]
    n = int(len(y)); w = int(y.sum()); base = float(uni.mean()) if len(uni) else float('nan')
    cond = float(y.mean()) if n else float('nan'); se = (cond * (1 - cond) / n) ** .5 if n else float('nan')
    ya = blk[on.reindex(blk.index).fillna(False).astype(bool).values]
    r.update(always_in_hit=float(blk.mean()), base=base, wins=w, cond=cond, cond_minus_base=(cond - base) if n else float('nan'), se_cond=se,
             p_binom_ge=float(binom.sf(w - 1, n, base)) if n else float('nan'),
             pass_B=bool(n >= 8 and cond >= base + 0.10 and cond >= 0.60),
             fail_reasons=[s for s, bad in (('n_on<8', n < 8), ('cond<base+10pp', not (n and cond >= base + 0.10)), ('cond<60%', not (n and cond >= 0.60))) if bad],
             on_blocks=[dict(t=str(d.date()), v1B=float(Bt[d]), win=bool(uni[d])) for d in y.index],
             info_any_v1_state=dict(n_on=int(len(ya)), cond=float(ya.mean()) if len(ya) else float('nan'), note='information only, not the test'))
    return r

out = dict(lane='CAPIT', window=WIN, precommit_sha256=SHA, N=2, variants={},
           early_window='1986-01-02..1999-12-31 (volume valid from 1985-10-01; ratio defined from the 61st row, 1985-12-26)',
           spx_1955_85='not covered (no Nasdaq volume)')
todo = list(cap.VARIANTS) if WIN != 'unseen' else passed
for var in todo:
    r = run(var); key = {'early': 'early_pass', 'unseen': 'unseen_pass'}.get(WIN)
    if key: r[key] = r['pass_B']
    out['variants'][var] = r
    print(WIN, var, json.dumps({k: v for k, v in r.items() if k not in ('on_blocks', 'signal', 'on_block_dates')}))
    print('   signal', json.dumps({k: v for k, v in r['signal'].items() if k != 'trigger_dates'}))
    for d in r['signal']['trigger_dates']: print('   trigger', d)
    for b in r.get('on_blocks', r.get('on_block_dates', [])): print('   on-block', b)
fn = dict(early='killB_early.json', unseen='killB_unseen.json', counts_unseen='signal_counts_unseen.json')[WIN]
json.dump(out, open(LANE + 'results/' + fn, 'w'), indent=1)
print('saved', fn)
