"""RC1: std(MS1) 재측정 + 지연·비용 스트레스. C3 원형, s0.85, S5(비대칭 재진입), S3(주간). 출력 results/stress.json"""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
import bk, rx
CM, ov, S = bk._co()
ID = std.ident; Z = np.zeros(1); B85 = rx.P_av23s(.85)
def s5(c):
    v = c.vol(20); B = np.where(v > 0.40, 1.0, 3.0)
    B = np.where(ov.macro_cond(c, ('shock6m',)), np.minimum(B, 1.0), B)
    cond = ov.macro_cond(c, ('inv', 'shock6m')); sm = c.sma(200)
    lo = c.lvl < sm * 0.98; hi = (c.lvl > sm * 1.02) & (c.lvl >= c.hi(63))
    off = ov.hyst(hi | ~cond, lo & cond); return np.where(off, 0.0, B)
def s3(c):
    B = bk.C3sig(c).copy(); idx = (np.arange(B.shape[1]) // 5) * 5; return B[:, idx]
C = {'C3raw': lambda c, kw: (bk.C3sig(c), ID, Z, 0.1, kw), 's085': lambda c, kw: (bk.C3sig(c), rx.av23s, B85, 0.1, kw),
     'S5_asym': lambda c, kw: (s5(c), ID, Z, 0.1, kw), 'S3_weekly': lambda c, kw: (s3(c), ID, Z, 0.1, kw)}
ST = {'base': {}, 'delay3': dict(delay=3), 'delay5': dict(delay=5), 'cost2x': dict(cost=0.006)}
out = {}
for sn, kw in ST.items():
    for k, f in C.items():
        T = std.measure(k, lambda c, f=f, kw=kw: f(c, kw), verbose=False); out[k + '|' + sn] = T
        p = T['dev250_path']; r = T['real_ndx_86_14']
        print('%-10s %-7s MS1 %.1f%% p10 %.1f%% dd80 %.0f%% | realNDX %.1f%% | SPX55 %.1f%% SPX70 %.1f%%' % (k, sn, 100*p['cagr'], 100*p['p10'], 100*p['dd80'], 100*r['cagr'], 100*T['real_spx_55_85']['cagr'], 100*T['real_spx_70_85']['cagr']), flush=True)
json.dump(out, open('/mnt/project-files/research/raw_core/results/stress.json', 'w'), indent=1)
