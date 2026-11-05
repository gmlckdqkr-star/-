"""OV1-A type-B kill test for ONE window ('early' or 'unseen'), as frozen in PRECOMMIT.md (sha256 70d8285c...).
Usage: python -B s2_killB.py early|unseen      Only the requested window's blocks are evaluated or printed."""
import sys, json, hashlib, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/lanes/OV1-A/code'); sys.path.insert(0, '/mnt/project-files/research/ov1/code')
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code')
import sig_a, ov1lib as L, gate, ov  # noqa
LANE = '/mnt/project-files/research/ov1/lanes/OV1-A/'
assert hashlib.sha256(open(LANE + 'PRECOMMIT.md', 'rb').read()).hexdigest().startswith('70d8285c181f8e07')
WIN = sys.argv[1]; assert WIN in ('early', 'unseen')
if WIN == 'unseen':   # opened once, only after an early PASS on file
    e = json.load(open(LANE + 'results/killB_early.json')); assert e['early_pass'] is True, 'early did not pass'

X = sig_a.ndx_X(); cal = X.index
# v1 target on the real_ndx_86_14 context (identical construction to std.contexts()['real_ndx_86_14'])
F = ov.flags_hist(X); i0 = cal.searchsorted(pd.Timestamp('1986-01-02')) - ov.WARM
c = ov.Ctx(X, F, np.arange(i0, len(X))[None, :]); B = pd.Series(L.v1_B(c)[0], index=cal[c.ii[0]])
lab = gate._frame('NDX', '1984-01-03', '2014-12-31', '1986-01-02')
pos = cal.get_indexer(lab.index); end = cal[np.minimum(pos + 23, len(cal) - 1)]
if WIN == 'early': m = (lab.index >= pd.Timestamp('1988-01-04')) & (end <= pd.Timestamp('1999-12-31'))
else: m = lab.index >= pd.Timestamp('2000-01-03')
blk = lab[m].astype(bool); Bt = B.reindex(blk.index); assert Bt.notna().all()
uni = blk[Bt.values < 3]

def stats(on_s, name):
    o = on_s.reindex(uni.index).fillna(False).astype(bool)
    y = uni[o.values]; n = int(len(y)); cond = float(y.mean()) if n else float('nan'); base = float(uni.mean())
    se = (cond * (1 - cond) / n) ** .5 if n else float('nan')
    ok = bool(n >= 8 and cond >= base + 0.10 and cond >= 0.60)
    r = dict(rule=name, window=WIN, n_blocks=int(len(blk)), always_in_hit=float(blk.mean()), n_universe=int(len(uni)), base=base,
             n_on=n, cond=cond, cond_minus_base=cond - base if n else float('nan'), se_cond=se, pass_B=ok,
             on_blocks=[dict(t=str(d.date()), v1B=float(Bt[d]), win=bool(uni[d])) for d in y.index])
    return r

Ns = sig_a.noise_star(cal); Vs = sig_a.vix_star(X)
on_n = sig_a.on_series(Ns); on_v = sig_a.on_series(Vs)
rv = stats(on_v, 'vix_control'); rn = stats(on_n, 'noise_relief')
print('CONTROL first:', json.dumps({k: v for k, v in rv.items() if k != 'on_blocks'}))
print('NOISE        :', json.dumps({k: v for k, v in rn.items() if k != 'on_blocks'}))
for b in rn['on_blocks']: print('  noise on-block', b)
for b in rv['on_blocks']: print('  vix   on-block', b)
out = dict(window=WIN, precommit_sha256='70d8285c181f8e0741c30875168883d2725efb5303c2e2cc9a91f003e04e9c9c', control=rv, noise=rn,
           universe_v1B_counts={str(k): int(v) for k, v in Bt[Bt < 3].value_counts().items()})
if WIN == 'early':
    vix_close = bool(rv['n_on'] >= 1 and rv['cond'] > rn['cond']) if rn['n_on'] else bool(rv['n_on'] >= 1)
    out['vix_control_closes'] = vix_close; out['early_pass'] = bool(rn['pass_B'] and not vix_close)
else:
    out['unseen_pass'] = bool(rn['pass_B'])
print('VERDICT', {k: v for k, v in out.items() if k in ('vix_control_closes', 'early_pass', 'unseen_pass')})
json.dump(out, open(LANE + 'results/killB_%s.json' % WIN, 'w'), indent=1)
with open(LANE + 'ledger.csv', 'a') as f:
    for r in (rn, rv):
        for k in ('n_universe', 'base', 'n_on', 'cond', 'cond_minus_base', 'pass_B'):
            f.write('OV1-A,%s,%s,%s,%s\n' % (r['rule'] if r['rule'] == 'noise_relief' else 'vix_control(not_in_N)', WIN, k, r[k]))
