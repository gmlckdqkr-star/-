"""OV1-D type-A kill test for ONE window ('early' or 'unseen'), as frozen in PRECOMMIT.md.
Usage: ~/.cache/lab/ms1-venv/bin/python -B s2_killA.py early|unseen   Only the requested window's blocks are evaluated/printed.
Blocks/labels = gate._frame grids. Universe = blocks whose v1 target (L.v1_B on the real context) is 3 at block-start close t.
drop = sum_era n_on,era*(base_era - hit_on,era) / sum_era n_on,era. PASS A iff drop >= 0.10 and n_on >= 8."""
import sys, json, hashlib, numpy as np, pandas as pd
CODE = '/mnt/project-files/research/ov1/lanes/OV1-D/code'; LANE = '/mnt/project-files/research/ov1/lanes/OV1-D/'
for p in (CODE, '/mnt/project-files/research/ov1/code', '/mnt/project-files/research/breakthrough/code'): sys.path.insert(0, p)
import tankan_sig as TS, ov1lib as L, gate, jp, ov  # noqa
PC = open(LANE + 'PRECOMMIT.sha256').read().split()[0]
assert hashlib.sha256(open(LANE + 'PRECOMMIT.md', 'rb').read()).hexdigest() == PC, 'PRECOMMIT.md changed'
WIN = sys.argv[1]; assert WIN in ('early', 'unseen')
if WIN == 'unseen':   # opened once, only after an early PASS on file
    e = json.load(open(LANE + 'results/killA_early.json')); assert e['early_pass'] is True, 'early did not pass'
    import os; assert not os.path.exists(LANE + 'results/killA_unseen.json'), 'unseen already opened once'

def v1_target(stream, a, b, start):
    R, M = jp.calendar(a, b); X = jp.mkX(R, M, stream); F = ov.flags_hist(X)
    i0 = X.index.searchsorted(pd.Timestamp(start)) - ov.WARM          # identical to std.contexts() real contexts
    c = ov.Ctx(X, F, np.arange(i0, len(X))[None, :]); return pd.Series(L.v1_B(c)[0], index=X.index[c.ii[0]]), X.index

cal = TS.calendar(); rel = TS.releases(cal); ON = TS.on_daily(cal, rel)
eras = []
if WIN == 'early':
    Bs, cs = v1_target('SPX', '1928-01-03', '1985-12-31', '1955-01-03')
    ls = gate._frame('SPX', '1928-01-03', '1985-12-31', '1955-01-03')
    m = (ls.index >= pd.Timestamp('1979-08-01')) & (ls.index <= pd.Timestamp('1985-12-31'))
    eras.append(('SPX_1979_1985', ls[m], Bs))
    Bn, cn = v1_target('NDX', '1984-01-03', '2014-12-31', '1986-01-02')
    ln = gate._frame('NDX', '1984-01-03', '2014-12-31', '1986-01-02')
    pos = cn.get_indexer(ln.index); end = cn[np.minimum(pos + 23, len(cn) - 1)]
    m = (ln.index >= pd.Timestamp('1986-01-02')) & (end <= pd.Timestamp('1999-12-31'))
    eras.append(('NDX_1986_1999', ln[m], Bn))
else:
    Bn, cn = v1_target('NDX', '1984-01-03', '2014-12-31', '1986-01-02')
    ln = gate._frame('NDX', '1984-01-03', '2014-12-31', '1986-01-02')
    m = ln.index >= pd.Timestamp('2000-01-03')
    eras.append(('NDX_2000_2014', ln[m], Bn))

rows = []; on_blocks = []
for name, lab, B in eras:
    lab = lab.astype(bool); Bt = B.reindex(lab.index); assert Bt.notna().all()
    on_t = ON.reindex(lab.index); assert on_t.notna().all(); on_t = on_t.astype(bool)
    uni = lab[Bt.values == 3]; o = on_t[uni.index]
    y = uni[o.values]; n_on = int(len(y)); base = float(uni.mean()); hit = float(y.mean()) if n_on else float('nan')
    se = (hit * (1 - hit) / n_on) ** .5 if n_on else float('nan')
    rows.append(dict(era=name, n_blocks=int(len(lab)), always_in_hit=float(lab.mean()), n_universe=int(len(uni)), base=base,
                     n_on=n_on, hit_on=hit, drop=(base - hit) if n_on else float('nan'), se_hit_on=se,
                     n_on_any_v1_state=int(on_t.sum()), first_block=str(lab.index[0].date()), last_block=str(lab.index[-1].date())))
    on_blocks += [dict(era=name, t=str(d.date()), win=bool(uni[d])) for d in y.index]
n_on = sum(r['n_on'] for r in rows)
drop = sum(r['n_on'] * r['drop'] for r in rows if r['n_on']) / n_on if n_on else float('nan')
ok = bool(n_on >= 8 and drop >= 0.10 - 1e-12)
out = dict(window=WIN, precommit_sha256=PC, eras=rows, n_on=n_on, drop_era_matched=drop, pass_A=ok, on_blocks=on_blocks,
           deflation='N = 1 -> sqrt(1 + ln N) = 1, no deflation', releases_in_window_with_threshold=int(
               ((rel['u'] >= eras[0][1].index[0]) & (rel['u'] <= eras[-1][1].index[-1]) & rel['thr'].notna()).sum()))
if WIN == 'early':
    r2 = [r for r in rows if r['era'].startswith('NDX')][0]
    out['ndx_only_info'] = dict(n_on=r2['n_on'], drop=r2['drop'], note='reported, does not gate')
    out['early_pass'] = ok
else:
    out['unseen_pass'] = ok
for r in rows: print(json.dumps(r))
for b in on_blocks: print('  on-block', b)
print('VERDICT', WIN, dict(n_on=n_on, drop=drop, pass_A=ok))
json.dump(out, open(LANE + 'results/killA_%s.json' % WIN, 'w'), indent=1)
with open(LANE + 'ledger.csv', 'a') as f:
    for r in rows:
        for k in ('n_universe', 'base', 'n_on', 'hit_on', 'drop'):
            f.write('OV1-D,tankan_surprise_t33,%s:%s,%s,%s\n' % (WIN, r['era'], k, r[k]))
    f.write('OV1-D,tankan_surprise_t33,%s,n_on,%s\n' % (WIN, n_on))
    f.write('OV1-D,tankan_surprise_t33,%s,drop_era_matched,%s\n' % (WIN, drop))
    f.write('OV1-D,tankan_surprise_t33,%s,pass_A,%s\n' % (WIN, ok))
