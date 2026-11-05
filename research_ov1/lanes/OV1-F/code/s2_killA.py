"""OV1-F type-A kill test for ONE window ('early' or 'unseen'), as frozen in PRECOMMIT.md (sha256 fb5aafb7...).
Usage: python -B s2_killA.py early|unseen      Only the requested window's blocks are evaluated or printed."""
import sys, os, json, hashlib, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/lanes/OV1-F/code'); sys.path.insert(0, '/mnt/project-files/research/ov1/code')
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code')
import ov1lib as L, gate, sig_f, jp, ov  # noqa
LANE = sig_f.LANE
SHA = hashlib.sha256(open(LANE + 'PRECOMMIT.md', 'rb').read()).hexdigest()
assert SHA.startswith('fb5aafb799206934'), SHA
WIN = sys.argv[1]; assert WIN in ('early', 'unseen')
if WIN == 'unseen':   # opened once, only after an early PASS on file
    e = json.load(open(LANE + 'results/killA_early.json')); assert e['early_pass'] is True, 'early did not pass'
    assert not os.path.exists(LANE + 'results/killA_unseen.json'), 'unseen already opened'
SM = sig_f.master_signal()       # master-calendar signal (y21, thr, fire, on)

def era(stream, a, b, start):
    R, M = jp.calendar(a, b); X = jp.mkX(R, M, stream); cal = X.index; F = ov.flags_hist(X)
    i0 = cal.searchsorted(pd.Timestamp(start)) - ov.WARM
    c = ov.Ctx(X, F, np.arange(i0, len(X))[None, :]); B = pd.Series(L.v1_B(c)[0], index=cal[c.ii[0]])
    S = SM.reindex(cal); assert S['lx'].index.equals(cal)
    lab = gate._frame(stream, a, b, start); pos = cal.get_indexer(lab.index); end = cal[np.minimum(pos + 23, len(cal) - 1)]
    return cal, B, S, lab, end

def stats(lab, B, S, m, name):
    from scipy.stats import binom
    blk = lab[m].astype(bool); Bt = B.reindex(blk.index); assert Bt.notna().all()
    uni = blk[np.isclose(Bt.values, 3)]; o = S['on'].reindex(uni.index).astype(bool)
    assert S['valid'].reindex(uni.index).astype(bool).all(), 'signal undefined inside window'
    y = uni[o.values]; n = int(len(y)); base = float(uni.mean()); hit = float(y.mean()) if n else float('nan')
    se = (hit * (1 - hit) / n) ** .5 if n else float('nan')
    p = float(binom.cdf(int(y.sum()), n, base)) if n else float('nan')
    return dict(era=name, n_blocks=int(len(blk)), always_in_hit=float(blk.mean()), n_universe=int(len(uni)), base=base,
                n_on=n, hit_on=hit, drop=(base - hit) if n else float('nan'), se_hit_on=se, p_binom_le=p,
                on_frac_universe=float(o.mean()) if len(o) else float('nan'),
                on_blocks=[dict(t=str(d.date()), yen21=round(float(S['y21'][d]), 4), thr=round(float(S['thr'][d]), 4),
                                win=bool(uni[d])) for d in y.index])

res = []
if WIN == 'early':
    cal, B, S, lab, end = era('SPX', '1928-01-03', '1985-12-31', '1955-01-03')
    m = (lab.index >= pd.Timestamp('1974-02-01')) & (end <= pd.Timestamp('1985-12-31'))
    res.append(stats(lab, B, S, m, 'SPX_1974_1985'))
    cal, B, S, lab, end = era('NDX', '1984-01-03', '2014-12-31', '1986-01-02')
    m = (lab.index >= pd.Timestamp('1986-01-02')) & (end <= pd.Timestamp('1999-12-31'))
    res.append(stats(lab, B, S, m, 'NDX_1986_1999'))
else:
    cal, B, S, lab, end = era('NDX', '1984-01-03', '2014-12-31', '1986-01-02')
    m = lab.index >= pd.Timestamp('2000-01-03')
    res.append(stats(lab, B, S, m, 'NDX_2000_2014'))
n_on = sum(r['n_on'] for r in res)
drop = (sum(r['n_on'] * r['drop'] for r in res if r['n_on']) / n_on) if n_on else float('nan')
ok = bool(n_on >= 8 and drop >= 0.10)
for r in res:
    print(json.dumps({k: v for k, v in r.items() if k != 'on_blocks'}))
    for b in r['on_blocks']: print('   on-block', r['era'], b)
out = dict(window=WIN, precommit_sha256=SHA, eras=res, pooled=dict(n_on=n_on, drop=drop, rule='era-matched base, weights n_on'),
           pass_A=ok, deflation='N=1 -> factor sqrt(1+ln1)=1')
out['early_pass' if WIN == 'early' else 'unseen_pass'] = ok
print('POOLED', WIN, 'n_on', n_on, 'drop', drop, 'PASS_A', ok)
json.dump(out, open(LANE + 'results/killA_%s.json' % WIN, 'w'), indent=1)
lf = LANE + 'ledger.csv'
with open(lf, 'a') as f:
    if os.path.getsize(lf) == 0: f.write('lane,variant,window,metric,value\n')
    for r in res:
        for k in ('n_universe', 'base', 'n_on', 'hit_on', 'drop'):
            f.write('OV1-F,yen21_q95_756_hold21_cut1x,%s:%s,%s,%s\n' % (WIN, r['era'], k, r[k]))
    f.write('OV1-F,yen21_q95_756_hold21_cut1x,%s:pooled,n_on,%s\n' % (WIN, n_on))
    f.write('OV1-F,yen21_q95_756_hold21_cut1x,%s:pooled,drop,%s\n' % (WIN, drop))
    f.write('OV1-F,yen21_q95_756_hold21_cut1x,%s:pooled,pass_A,%s\n' % (WIN, ok))
