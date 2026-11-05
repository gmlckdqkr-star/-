"""OV1-C type-A kill test for ONE window ('early' or 'unseen'), as frozen in PRECOMMIT.md (sha256 40ca6129...).
Usage: python -B s2_killA.py early|unseen      Only the requested window's blocks are evaluated or printed."""
import sys, json, hashlib, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/lanes/OV1-C/code'); sys.path.insert(0, '/mnt/project-files/research/ov1/code')
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code')
import ov1lib as L, gate, sig_c, jp, ov  # noqa
LANE = '/mnt/project-files/research/ov1/lanes/OV1-C/'
SHA = hashlib.sha256(open(LANE + 'PRECOMMIT.md', 'rb').read()).hexdigest()
assert SHA.startswith('40ca6129c4f72f68'), SHA
WIN = sys.argv[1]; assert WIN in ('early', 'unseen')
if WIN == 'unseen':   # opened once, only after an early PASS on file
    e = json.load(open(LANE + 'results/killA_early.json')); assert e['early_pass'] is True, 'early did not pass'
XC = sig_c.change_index()

def era(stream, a, b, start):
    R, M = jp.calendar(a, b); X = jp.mkX(R, M, stream); cal = X.index; F = ov.flags_hist(X)
    i0 = cal.searchsorted(pd.Timestamp(start)) - ov.WARM
    c = ov.Ctx(X, F, np.arange(i0, len(X))[None, :]); B = pd.Series(L.v1_B(c)[0], index=cal[c.ii[0]])
    V = {k: x.reindex(cal.union(x.index)).ffill().reindex(cal).values[None, :].astype(float) for k, x in XC.items()}
    on, cnt, ok = sig_c.on_matrix(V)
    ON = pd.Series(on[0], index=cal); CNT = pd.Series(cnt[0], index=cal)
    lab = gate._frame(stream, a, b, start); pos = cal.get_indexer(lab.index); end = cal[np.minimum(pos + 23, len(cal) - 1)]
    return cal, B, ON, CNT, lab, end

def stats(lab, B, ON, CNT, m, name):
    blk = lab[m].astype(bool); Bt = B.reindex(blk.index); assert Bt.notna().all()
    uni = blk[Bt.values == 3]; o = ON.reindex(uni.index).astype(bool)
    y = uni[o.values]; n = int(len(y)); base = float(uni.mean()); hit = float(y.mean()) if n else float('nan')
    se = (hit * (1 - hit) / n) ** .5 if n else float('nan')
    # one-sided exact binomial P(X <= k | n, base) as information only
    from scipy.stats import binom
    p = float(binom.cdf(int(y.sum()), n, base)) if n else float('nan')
    return dict(era=name, n_blocks=int(len(blk)), always_in_hit=float(blk.mean()), n_universe=int(len(uni)), base=base,
                n_on=n, hit_on=hit, drop=(base - hit) if n else float('nan'), se_hit_on=se, p_binom_le=p,
                on_frac_universe=float(o.mean()) if len(o) else float('nan'),
                on_blocks=[dict(t=str(d.date()), cnt=int(CNT[d]), win=bool(uni[d])) for d in y.index])

res = []
if WIN == 'early':
    cal, B, ON, CNT, lab, end = era('SPX', '1928-01-03', '1985-12-31', '1955-01-03')
    m = (lab.index >= pd.Timestamp('1960-01-04')) & (end <= pd.Timestamp('1985-12-31'))
    res.append(stats(lab, B, ON, CNT, m, 'SPX_1960_1985'))
    cal, B, ON, CNT, lab, end = era('NDX', '1984-01-03', '2014-12-31', '1986-01-02')
    m = (lab.index >= pd.Timestamp('1986-01-02')) & (end <= pd.Timestamp('1999-12-31'))
    res.append(stats(lab, B, ON, CNT, m, 'NDX_1986_1999'))
else:
    cal, B, ON, CNT, lab, end = era('NDX', '1984-01-03', '2014-12-31', '1986-01-02')
    m = lab.index >= pd.Timestamp('2000-01-03')
    res.append(stats(lab, B, ON, CNT, m, 'NDX_2000_2014'))
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
with open(LANE + 'ledger.csv', 'a') as f:
    import os
    if os.path.getsize(LANE + 'ledger.csv') == 0: f.write('lane,variant,window,metric,value\n')
    for r in res:
        for k in ('n_universe', 'base', 'n_on', 'hit_on', 'drop'):
            f.write('OV1-C,fcb2of3_126d_25bp,%s:%s,%s,%s\n' % (WIN, r['era'], k, r[k]))
    f.write('OV1-C,fcb2of3_126d_25bp,%s:pooled,n_on,%s\n' % (WIN, n_on))
    f.write('OV1-C,fcb2of3_126d_25bp,%s:pooled,drop,%s\n' % (WIN, drop))
    f.write('OV1-C,fcb2of3_126d_25bp,%s:pooled,pass_A,%s\n' % (WIN, ok))
