"""OV1-E type-A kill test for ONE window ('early' or 'unseen'), as frozen in PRECOMMIT.md.
Usage: python -B s2_killA.py early|unseen      Only the requested window's blocks are evaluated or printed."""
import sys, os, json, hashlib, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/lanes/OV1-E/code'); sys.path.insert(0, '/mnt/project-files/research/ov1/code')
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code')
import ov1lib as L, gate, sig_e, jp, ov  # noqa
from scipy.stats import binom
LANE = '/mnt/project-files/research/ov1/lanes/OV1-E/'
SHA = hashlib.sha256(open(LANE + 'PRECOMMIT.md', 'rb').read()).hexdigest()
assert SHA.startswith('e2a080f6ce9b1dd4'), SHA
assert hashlib.sha256(open(LANE + 'code/sig_e.py', 'rb').read()).hexdigest().startswith('39a9d9aa52d0eadf')
WIN = sys.argv[1]; assert WIN in ('early', 'unseen')
if WIN == 'unseen':   # opened once, only after an early PASS on file
    e = json.load(open(LANE + 'results/killA_early.json')); assert e['early_pass'] is True, 'early did not pass'
    assert not os.path.exists(LANE + 'results/killA_unseen.json'), 'unseen already opened once'
FAM = 2; DEFL = (1 + np.log(FAM)) ** .5                     # T33 funding-stress family: OV1-A (HPW ADD) + OV1-E (TED CUT)

MCAL = sig_e.master_cal(); TED = sig_e.ted_star(MCAL); ON_M, X_M, Q_M = sig_e.on_series(TED)

def era(stream, a, b, start):
    R, M = jp.calendar(a, b); X = jp.mkX(R, M, stream); cal = X.index; F = ov.flags_hist(X)
    i0 = cal.searchsorted(pd.Timestamp(start)) - ov.WARM
    c = ov.Ctx(X, F, np.arange(i0, len(X))[None, :]); B = pd.Series(L.v1_B(c)[0], index=cal[c.ii[0]])
    assert cal.isin(MCAL).all()
    ON = ON_M.reindex(cal); XX = X_M.reindex(cal); QQ = Q_M.reindex(cal)
    lab = gate._frame(stream, a, b, start); pos = cal.get_indexer(lab.index); end = cal[np.minimum(pos + 23, len(cal) - 1)]
    return cal, B, ON, XX, QQ, lab, end

def stats(lab, B, ON, XX, QQ, m, name):
    blk = lab[m].astype(bool); Bt = B.reindex(blk.index); assert Bt.notna().all()
    assert ON.reindex(blk.index).notna().all()
    uni = blk[Bt.values == 3]; o = ON.reindex(uni.index).astype(bool)
    y = uni[o.values]; n = int(len(y)); base = float(uni.mean()); hit = float(y.mean()) if n else float('nan')
    se = (hit * (1 - hit) / n) ** .5 if n else float('nan')
    p = float(binom.cdf(int(y.sum()), n, base)) if n else float('nan')      # one-sided exact binomial P(X <= k | n, base), info only
    defined = (~np.isnan(QQ.reindex(blk.index).values))
    on_all = ON.reindex(blk.index).astype(bool)
    return dict(era=name, n_blocks=int(len(blk)), first_block=str(blk.index[0].date()), last_block=str(blk.index[-1].date()),
                signal_defined_all_blocks=bool(defined.all()), always_in_hit=float(blk.mean()), n_universe=int(len(uni)), base=base,
                n_on=n, hit_on=hit, drop=(base - hit) if n else float('nan'), se_hit_on=se, p_binom_le=p,
                on_frac_universe=float(o.mean()) if len(o) else float('nan'),
                n_on_all_blocks=int(on_all.sum()), n_on_blocks_v1_not3x=int((on_all & (Bt != 3)).sum()),
                on_blocks=[dict(t=str(d.date()), x=round(float(XX[d]), 4), q90=round(float(QQ[d]), 4), win=bool(uni[d])) for d in y.index])

res = []
if WIN == 'early':
    cal, B, ON, XX, QQ, lab, end = era('SPX', '1928-01-03', '1985-12-31', '1955-01-03')
    m = (lab.index >= pd.Timestamp('1976-03-31')) & (end <= pd.Timestamp('1985-12-31'))
    res.append(stats(lab, B, ON, XX, QQ, m, 'SPX_1976_1985'))
    cal, B, ON, XX, QQ, lab, end = era('NDX', '1984-01-03', '2014-12-31', '1986-01-02')
    m = (lab.index >= pd.Timestamp('1986-01-02')) & (end <= pd.Timestamp('1999-12-31'))
    res.append(stats(lab, B, ON, XX, QQ, m, 'NDX_1986_1999'))
else:
    cal, B, ON, XX, QQ, lab, end = era('NDX', '1984-01-03', '2014-12-31', '1986-01-02')
    m = lab.index >= pd.Timestamp('2000-01-03')
    res.append(stats(lab, B, ON, XX, QQ, m, 'NDX_2000_2014'))
n_on = sum(r['n_on'] for r in res)
drop = (sum(r['n_on'] * r['drop'] for r in res if r['n_on']) / n_on) if n_on else float('nan')
hit_on = (sum(r['n_on'] * r['hit_on'] for r in res if r['n_on']) / n_on) if n_on else float('nan')
se = (hit_on * (1 - hit_on) / n_on) ** .5 if n_on else float('nan')
ok = bool(n_on >= 8 and drop >= 0.10)
for r in res:
    print(json.dumps({k: v for k, v in r.items() if k != 'on_blocks'}))
    for b in r['on_blocks']: print('   on-block', r['era'], b)
out = dict(window=WIN, precommit_sha256=SHA, eras=res,
           pooled=dict(n_on=n_on, drop=drop, hit_on=hit_on, se_hit_on=se, z=(drop / se) if se else float('nan'),
                       rule='era-matched base, weights n_on'),
           pass_A=ok, info_deflation=dict(family='T33 funding/arbitrage stress', family_N=FAM, lane_N=1, factor=DEFL,
                                          drop_lower_2se_deflated=(drop - 2 * se * DEFL) if se else float('nan'),
                                          note='information only; the gate is the brief threshold on the raw pooled drop'))
out['early_pass' if WIN == 'early' else 'unseen_pass'] = ok
print('POOLED', WIN, 'n_on', n_on, 'drop', drop, 'PASS_A', ok)
json.dump(out, open(LANE + 'results/killA_%s.json' % WIN, 'w'), indent=1)
with open(LANE + 'ledger.csv', 'a') as f:
    if os.path.getsize(LANE + 'ledger.csv') == 0: f.write('lane,variant,window,metric,value\n')
    for r in res:
        for k in ('n_universe', 'base', 'n_on', 'hit_on', 'drop'):
            f.write('OV1-E,ted63_p90_1260,%s:%s,%s,%s\n' % (WIN, r['era'], k, r[k]))
    f.write('OV1-E,ted63_p90_1260,%s:pooled,n_on,%s\n' % (WIN, n_on))
    f.write('OV1-E,ted63_p90_1260,%s:pooled,drop,%s\n' % (WIN, drop))
    f.write('OV1-E,ted63_p90_1260,%s:pooled,pass_A,%s\n' % (WIN, ok))
