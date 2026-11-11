"""NP1-KF run (PRECOMMIT_KF.md). <= 2014 only. Direct MS1 engine runs vs v1 under the same terms, signal stats, G1-style diagnostic."""
import os, sys, json, time, hashlib
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
import numpy as np, pandas as pd
LANE = '/mnt/project-files/research/np1/'
sys.path.insert(0, LANE + 'code'); sys.path.insert(0, '/mnt/project-files/research/ov1/code')
import ov1lib as L, std, kf  # noqa
ov = L.ov
SHA = hashlib.sha256(open(LANE + 'PRECOMMIT_KF.md', 'rb').read()).hexdigest()
assert SHA == open(LANE + 'PRECOMMIT_KF.sha256').read().split()[0], 'PRECOMMIT changed'
FRZ = dict(l.split()[::-1] for l in open(LANE + 'code/CODE_FREEZE.sha256').read().strip().splitlines())
for f in ('kf.py', 'kfrun.py'):
    assert hashlib.sha256(open(LANE + 'code/' + f, 'rb').read()).hexdigest() == FRZ[f], f + ' changed after freeze'
VARS = tuple(kf.VARIANTS)
TERMS = (('base', {}), ('delay3', dict(delay=3)), ('cost2x', dict(cost=0.006)))
BASES = ('real_ndx_86_14', 'dev250_path', 'dev250_glued')
t0 = time.time(); C = std.contexts(); D = L.dates(); Cs = kf.level_series()
res = dict(precommit_sha256=SHA, N=4, rows={}, signal={}, diag={})

def stats(f, E, fr):
    row, _ = std.row(f, E); d = f - fr; ch = np.abs(d) > 1e-5
    row.update(d_med=float(np.median(d)), d_mean=float(np.mean(d)), v1=float(np.median(fr)), n_changed=int(ch.sum()),
               win_changed=float(np.mean(d[ch] > 0)) if ch.any() else float('nan'))
    return row

for bn in BASES:
    c = C[bn]; B = L.v1_B(c); bfn, bp, fs = L.v1_parts(c)
    Cl = L.path_series(Cs, bn) if bn == 'dev250_path' else L.gather(Cs, bn)
    ons = {}
    for v in VARS:
        on, trig = kf.on_window(Cl, v); ons[v] = on
        act = (on & (B >= 1.5)) if kf.VARIANTS[v]['side'] == 'cut' else (on & (B == 1.0))
        s = dict(signal_days_share=float(np.isfinite(kf.zscore(kf.diff_n(Cl, kf.VARIANTS[v]['n'])))[:, ov.WARM:].mean()),
                 trig_share=float(trig[:, ov.WARM:].mean()), on_share=float(on[:, ov.WARM:].mean()), active_share=float(act[:, ov.WARM:].mean()))
        if bn == 'real_ndx_86_14':
            idx = D[bn][c.ii[0]]; o = act[0].astype(int); st = np.flatnonzero((o[1:] == 1) & (o[:-1] == 0)) + 1
            s['active_episodes'] = [dict(start=str(idx[k].date()), days=int(o[k:].argmin() if (o[k:] == 0).any() else len(o) - k)) for k in st]
        res['signal']['%s|%s' % (v, bn)] = s
        print('signal', v, bn, {k: (round(x, 4) if isinstance(x, float) else x) for k, x in s.items() if k != 'active_episodes'}, flush=True)
        for e in s.get('active_episodes', []): print('   episode', e)
    for tag, kw in TERMS:
        fr, Er = std.engine(c, B, bfn, bp, fs, **kw)
        if tag == 'base':
            f0, _ = std.engine(c, *std.s085(c)); assert np.max(np.abs(f0 - fr)) < 1e-12
            res['rows']['v1|base|' + bn] = stats(fr, Er, fr)
        for v in VARS:
            f, E = std.engine(c, kf.overlay(B, ons[v], v), bfn, bp, fs, **kw); row = stats(f, E, fr)
            res['rows']['%s|%s|%s' % (v, tag, bn)] = row
            print('%-6s %-7s %-15s cagr %.4f v1 %.4f dmed %+.4f dmean %+.4f changed %d win %.3f mdd %.3f%s (%.0fs)' % (
                v, tag, bn, row['cagr'], row['v1'], row['d_med'], row['d_mean'], row['n_changed'], row['win_changed'], row['mdd'],
                (' dd80 %.3f' % row['dd80']) if 'dd80' in row else '', time.time() - t0), flush=True)
    if bn == 'real_ndx_86_14':   # G1-style diagnostic, 2004-2014, 21-day blocks: label = 3x NDX beats deposit over t+3..t+23
        idx = D[bn][c.ii[0]]; r = c.r[0]; rf = c.rf[0]; T = len(idx)
        x3 = 3 * r - 2 * rf - (0.0095 + 0.015) / 252
        t_ok = [t for t in range(0, T - 24, 21) if idx[t] >= pd.Timestamp('2004-01-01')]
        lab = np.array([np.prod(1 + x3[t + 3:t + 24]) > np.prod(1 + rf[t + 3:t + 24]) for t in t_ok])
        res['diag']['base_rate'] = dict(n=len(t_ok), p=float(lab.mean()))
        for v in VARS:
            on = ons[v][0][t_ok]
            res['diag'][v] = dict(n_on=int(on.sum()), p_on=float(lab[on].mean()) if on.any() else None,
                                  n_off=int((~on).sum()), p_off=float(lab[~on].mean()) if (~on).any() else None)
        print('diag', json.dumps(res['diag']), flush=True)

def passed(v):
    g = lambda tag, bn: res['rows']['%s|%s|%s' % (v, tag, bn)]
    p, r = g('base', 'dev250_path'), g('base', 'real_ndx_86_14')
    conds = dict(path_headline_gt_v1=p['cagr'] > p['v1'], path_mean_d_gt0=p['d_mean'] > 0,
                 path_win_changed_ge55=bool(p['n_changed'] > 0 and p['win_changed'] >= 0.55), real_gt_v1=r['cagr'] > r['v1'],
                 delay3_holds=g('delay3', 'dev250_path')['cagr'] > g('delay3', 'dev250_path')['v1'] and g('delay3', 'real_ndx_86_14')['cagr'] > g('delay3', 'real_ndx_86_14')['v1'],
                 cost2x_holds=g('cost2x', 'dev250_path')['cagr'] > g('cost2x', 'dev250_path')['v1'] and g('cost2x', 'real_ndx_86_14')['cagr'] > g('cost2x', 'real_ndx_86_14')['v1'])
    return dict(PASS=bool(all(conds.values())), **{k: bool(x) for k, x in conds.items()})
res['verdict'] = {v: passed(v) for v in VARS}
print('VERDICT', json.dumps(res['verdict']), '%.0fs' % (time.time() - t0))
os.makedirs(LANE + 'results', exist_ok=True)
json.dump(res, open(LANE + 'results/kf_measure.json', 'w'), indent=1, default=float)
