"""CAPIT amendment A1 (PRECOMMIT_A1.md): CAPA1 / CAPA2 = the registered CAP rule with the volume threshold lowered to 1.5x. <= 2014 only.
Direct engine measurement against v1 under the same terms (base, delay 3, cost x2) + real-NDX attribution by half.
Definitions come from the frozen cap.py; only the VARIANTS table is extended at run time (cap.py itself is not edited)."""
import os, sys, json, time, hashlib
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
import numpy as np, pandas as pd
LANE = '/mnt/project-files/research/final1/lanes/CAPIT/'
sys.path.insert(0, LANE + 'code'); sys.path.insert(0, '/mnt/project-files/research/ov1/code')
import ov1lib as L, std, cap  # noqa
ov = L.ov
SHA = hashlib.sha256(open(LANE + 'PRECOMMIT_A1.md', 'rb').read()).hexdigest()
assert SHA == open(LANE + 'PRECOMMIT_A1.sha256').read().split()[0], 'PRECOMMIT_A1 changed'
FRZ = dict(l.split()[::-1] for l in open(LANE + 'code/CODE_FREEZE.sha256').read().strip().splitlines())
assert hashlib.sha256(open(LANE + 'code/cap.py', 'rb').read()).hexdigest() == FRZ['cap.py'], 'cap.py changed after freeze'
cap.VARIANTS.update(CAPA1=dict(rsi_max=30.0, vr_min=1.5, look=1, W=42), CAPA2=dict(rsi_max=30.0, vr_min=1.5, look=3, W=63))
VARS = ('CAPA1', 'CAPA2')
TERMS = (('base', {}), ('delay3', dict(delay=3)), ('cost2x', dict(cost=0.006)))
BASES = ('real_ndx_86_14', 'dev250_path', 'dev250_glued')
E1, U0 = pd.Timestamp('1999-12-31'), pd.Timestamp('2000-01-03')
t0 = time.time(); C = std.contexts(); D = L.dates(); res = dict(precommit_a1_sha256=SHA, N=2, lane_total_N=4, rows={}, signal={})

def parts(bn):
    c = C[bn]; B = L.v1_B(c); bfn, bp, fs = L.v1_parts(c)
    rsi = cap.rsi14(c.lvl); vr = L.gather(cap.vr_for_gather(D[bn]), bn); vr = np.where(vr < 0, np.nan, vr)
    return c, B, bfn, bp, fs, rsi, vr

def stats(f, E, fr):
    row, _ = std.row(f, E); d = f - fr
    row.update(d_vs_v1=float(np.median(d)), pw_vs_v1=float(np.mean(d > 1e-5)), v1=float(np.median(fr)))
    return row

for bn in BASES:
    c, B, bfn, bp, fs, rsi, vr = parts(bn)
    ons = {}
    for v in VARS:
        trig = cap.trigger(rsi, vr, v); on = cap.on_window(trig, v); ons[v] = on
        act = on & (B < 3.0)
        s = dict(trigger_days_per_path=float(trig[:, ov.WARM:].sum(1).mean()), on_share=float(on[:, ov.WARM:].mean()),
                 active_share=float(act[:, ov.WARM:].mean()), v1_below3_share=float((B[:, ov.WARM:] < 3.0).mean()))
        if bn == 'real_ndx_86_14':
            idx = D[bn][c.ii[0]]; lvl = c.lvl[0]; T = len(idx); ev = []
            for t in np.flatnonzero(trig[0]):
                if t < ov.WARM: continue
                a, b = min(t + 2, T - 1), min(t + 2 + 42, T - 1)
                ev.append(dict(t=str(idx[t].date()), rsi=round(float(rsi[0, t]), 1), vr=round(float(vr[0, t]), 2), v1B=float(B[0, t]),
                               ndx_fwd42=round(float(lvl[b] / lvl[a] - 1), 4)))
            s['triggers'] = ev
            o = on[0].astype(int); st = np.flatnonzero((o[1:] == 1) & (o[:-1] == 0)) + 1
            s['on_episodes'] = [dict(start=str(idx[k].date()), days=int(o[k:].argmin() if (o[k:] == 0).any() else len(o) - k),
                                     active_days=int(act[0, k:k + (o[k:].argmin() if (o[k:] == 0).any() else len(o) - k)].sum())) for k in st]
        res['signal']['%s|%s' % (v, bn)] = s
        print('signal', v, bn, {k: (round(x, 4) if isinstance(x, float) else x) for k, x in s.items() if k not in ('triggers', 'on_episodes')}, flush=True)
        for e in s.get('triggers', []): print('   trigger', e)
        for e in s.get('on_episodes', []): print('   episode', e)
    for tag, kw in TERMS:
        fr, Er = std.engine(c, B, bfn, bp, fs, **kw)
        if tag == 'base':
            f0, _ = std.engine(c, *std.s085(c)); assert np.max(np.abs(f0 - fr)) < 1e-12
        for v in VARS:
            f, E = std.engine(c, cap.overlay(B, ons[v]), bfn, bp, fs, **kw); row = stats(f, E, fr)
            res['rows']['%s|%s|%s' % (v, tag, bn)] = row
            print('%-5s %-7s %-15s cagr %.4f v1 %.4f d %+.4f pw %.3f mdd %.3f%s (%.0fs)' % (
                v, tag, bn, row['cagr'], row['v1'], row['d_vs_v1'], row['pw_vs_v1'], row['mdd'],
                (' dd80 %.3f' % row['dd80']) if 'dd80' in row else '', time.time() - t0), flush=True)
    if bn == 'real_ndx_86_14':
        idx = D[bn][c.ii[0]]; fr, Er = std.engine(c, B, bfn, bp, fs)
        for v in VARS:
            for nm, m in (('only_1986_1999', idx <= E1), ('only_2000_2014', idx >= U0)):
                f, E = std.engine(c, cap.overlay(B, ons[v] & m[None, :]), bfn, bp, fs); row = stats(f, E, fr)
                res['rows']['%s|attr_%s|%s' % (v, nm, bn)] = row
                print('%-5s attr %-15s real d %+.4f (cagr %.4f)' % (v, nm, row['d_vs_v1'], row['cagr']), flush=True)

def passed(v):
    g = lambda tag, bn: res['rows']['%s|%s|%s' % (v, tag, bn)]
    p, r = g('base', 'dev250_path'), g('base', 'real_ndx_86_14')
    conds = dict(path_d_ge_0p5pp=p['d_vs_v1'] >= 0.005, path_pw_ge_55=p['pw_vs_v1'] >= 0.55, real_d_gt_0=r['d_vs_v1'] > 0,
                 delay3_signs=g('delay3', 'dev250_path')['d_vs_v1'] > 0 and g('delay3', 'real_ndx_86_14')['d_vs_v1'] > 0,
                 cost2x_signs=g('cost2x', 'dev250_path')['d_vs_v1'] > 0 and g('cost2x', 'real_ndx_86_14')['d_vs_v1'] > 0,
                 attr_both_halves_ge_0=g('attr_only_1986_1999', 'real_ndx_86_14')['d_vs_v1'] >= 0 and g('attr_only_2000_2014', 'real_ndx_86_14')['d_vs_v1'] >= 0)
    return dict(PASS=bool(all(conds.values())), **{k: bool(x) for k, x in conds.items()})
res['verdict'] = {v: passed(v) for v in VARS}
print('VERDICT', json.dumps(res['verdict']), '%.0fs' % (time.time() - t0))
json.dump(res, open(LANE + 'results/capA_measure.json', 'w'), indent=1, default=float)
