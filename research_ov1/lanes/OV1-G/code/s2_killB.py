"""OV1-G type-B kill test for ONE window ('early' or 'unseen'), as frozen in PRECOMMIT.md (sha256 c45d74ea...).
Usage: python -B s2_killB.py early|unseen      Only the requested window's blocks are evaluated or printed."""
import sys, os, json, hashlib, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/lanes/OV1-G/code'); sys.path.insert(0, '/mnt/project-files/research/ov1/code')
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code')
import ov1lib as L, gate, sig_g, jp, ov  # noqa
from scipy.stats import binom
LANE = '/mnt/project-files/research/ov1/lanes/OV1-G/'
SHA = hashlib.sha256(open(LANE + 'PRECOMMIT.md', 'rb').read()).hexdigest(); assert SHA.startswith('c45d74eaedd18ba0'), SHA
assert hashlib.sha256(open(LANE + 'code/sig_g.py', 'rb').read()).hexdigest().startswith('06c9b5cb74db3fad'), 'sig_g.py changed'
WIN = sys.argv[1]; assert WIN in ('early', 'unseen')
if WIN == 'unseen':   # opened once, only after an early PASS on file
    e = json.load(open(LANE + 'results/killB_early.json')); assert e['early_pass'] is True, 'early did not pass'

def era(stream, a, b, start):
    R, M = jp.calendar(a, b); X = jp.mkX(R, M, stream); cal = X.index; F = ov.flags_hist(X)
    i0 = cal.searchsorted(pd.Timestamp(start)) - ov.WARM
    c = ov.Ctx(X, F, np.arange(i0, len(X))[None, :]); B = pd.Series(L.v1_B(c)[0], index=cal[c.ii[0]])
    lab = gate._frame(stream, a, b, start); pos = cal.get_indexer(lab.index); end = cal[np.minimum(pos + 23, len(cal) - 1)]
    return cal, B, lab, end

def stats(lab, B, ON, m, name, universe='non3x'):
    blk = lab[m].astype(bool); Bt = B.reindex(blk.index); assert Bt.notna().all()
    uni = blk[Bt.values < 3] if universe == 'non3x' else blk
    o = ON.reindex(uni.index).fillna(False).astype(bool)
    y = uni[o.values]; n = int(len(y)); w = int(y.sum()); base = float(uni.mean()) if len(uni) else float('nan')
    cond = float(y.mean()) if n else float('nan'); se = (cond * (1 - cond) / n) ** .5 if n else float('nan')
    p = float(binom.sf(w - 1, n, base)) if n else float('nan')        # P(X >= w | n, base), information only
    vc = {str(k): int(v) for k, v in Bt.reindex(uni.index).value_counts().sort_index().items()}
    return dict(era=name, universe=universe, universe_v1B_counts=vc, n_blocks=int(len(blk)), always_in_hit=float(blk.mean()), n_universe=int(len(uni)),
                base=base, n_on=n, wins=w, cond=cond, cond_minus_base=(cond - base) if n else float('nan'), se_cond=se, p_binom_ge=p,
                on_blocks=[dict(t=str(d.date()), v1B=float(Bt[d]), win=bool(uni[d])) for d in y.index])

def pooled(res):
    n = sum(r['n_on'] for r in res); w = sum(r['wins'] for r in res)
    if not n: return dict(n_on=0, wins=0, cond=float('nan'), base=float('nan'), cond_minus_base=float('nan'), pass_B=False)
    base = sum(r['n_on'] * r['base'] for r in res if r['n_on']) / n; cond = w / n
    return dict(n_on=n, wins=w, cond=cond, base=base, cond_minus_base=cond - base,
                pass_B=bool(n >= 8 and cond >= base + 0.10 and cond >= 0.60))

def run(kw, universe='non3x'):
    res = []
    if WIN == 'early':
        cal, B, lab, end = ES
        res.append(stats(lab, B, sig_g.on_series(cal, **kw), (lab.index >= pd.Timestamp('1982-09-27')) & (end <= pd.Timestamp('1985-12-31')),
                         'SPX_1982_1985', universe))
        cal, B, lab, end = EN
        res.append(stats(lab, B, sig_g.on_series(cal, **kw), (lab.index >= pd.Timestamp('1986-01-02')) & (end <= pd.Timestamp('1999-12-31')),
                         'NDX_1986_1999', universe))
    else:
        cal, B, lab, end = EN
        res.append(stats(lab, B, sig_g.on_series(cal, **kw), lab.index >= pd.Timestamp('2000-01-03'), 'NDX_2000_2014', universe))
    return res, pooled(res)

EN = era('NDX', '1984-01-03', '2014-12-31', '1986-01-02')
if WIN == 'early': ES = era('SPX', '1928-01-03', '1985-12-31', '1955-01-03')
res, P = run({})
for r in res:
    print(json.dumps({k: v for k, v in r.items() if k != 'on_blocks'}))
    for b in r['on_blocks']: print('   on-block', r['era'], b)
print('POOLED', WIN, json.dumps(P))
out = dict(window=WIN, precommit_sha256=SHA, eras=res, pooled=P, deflation='N=1 -> sqrt(1+ln1)=1')
out['early_pass' if WIN == 'early' else 'unseen_pass'] = P['pass_B']
info = {}
if WIN == 'early':   # information only: not variants, not in N, cannot rescue a fail
    r5, p5 = run(dict(pit_extra=4)); rc, pc = run(dict(include_meeting=True)); ra, pa = run({}, universe='any')
    info = dict(pit_plus5=dict(pooled=p5, eras=[{k: v for k, v in r.items() if k != 'on_blocks'} for r in r5]),
                control_all_cuts=dict(pooled=pc, eras=[{k: v for k, v in r.items() if k != 'on_blocks'} for r in rc]),
                any_v1_state=dict(eras=[{k: v for k, v in r.items()} for r in ra]))
    print('INFO pit+5 pooled', json.dumps(p5)); print('INFO all-cuts control pooled', json.dumps(pc))
    for r in ra: print('INFO any-state', r['era'], 'n_on', r['n_on'], 'cond', r['cond'], 'always_in', r['always_in_hit'])
out['information_only'] = info
print('VERDICT', WIN, 'PASS_B' if P['pass_B'] else 'FAIL')
json.dump(out, open(LANE + 'results/killB_%s.json' % WIN, 'w'), indent=1, default=str)
new = not os.path.exists(LANE + 'ledger.csv') or os.path.getsize(LANE + 'ledger.csv') == 0
with open(LANE + 'ledger.csv', 'a') as f:
    if new: f.write('lane,variant,window,metric,value\n')
    for r in res:
        for k in ('n_universe', 'base', 'n_on', 'wins', 'cond', 'cond_minus_base'):
            f.write('OV1-G,offmtg_cut_42d,%s:%s,%s,%s\n' % (WIN, r['era'], k, r[k]))
    for k in ('n_on', 'wins', 'base', 'cond', 'cond_minus_base', 'pass_B'):
        f.write('OV1-G,offmtg_cut_42d,%s:pooled,%s,%s\n' % (WIN, k, P[k]))
