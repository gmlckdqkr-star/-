"""RC1 2단계: s0.85 분해 (MS1 std.measure, <=2014). 출력 results/ablate.json"""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
import bk, rx, ce
CM, ov, S = bk._co()
ID = std.ident; Z = np.zeros(1); B85 = rx.P_av23s(.85)
def volsw(c): v = c.vol(20); return np.where(v > 0.40, 1.0, 3.0)
def gate(c, B): off = ov.trend_gate(c, 200, 0.02, ov.macro_cond(c, ('inv', 'shock6m'))); return np.where(off, 0.0, B)
def caut(c, B): return np.where(ov.macro_cond(c, ('shock6m',)), np.minimum(B, 1.0), B)
def tq(c): return np.full(c.r.shape, 3.0)
C = {
 'A1_c3raw_nobrake':        lambda c: (bk.C3sig(c), ID, Z, 0.1),
 'A2_c3_av23':              lambda c: (bk.C3sig(c), ce.alt, ce.AV23, 0.1),
 'A3_s085':                 lambda c: (bk.C3sig(c), rx.av23s, B85, 0.1),
 'A4_volsw_raw':            lambda c: (volsw(c), ID, Z, 0.1),
 'A5_volsw_gate_raw':       lambda c: (gate(c, volsw(c)), ID, Z, 0.1),
 'A6_volsw_caut_raw':       lambda c: (caut(c, volsw(c)), ID, Z, 0.1),
 'A7_gate_caut_raw':        lambda c: (gate(c, caut(c, tq(c))), ID, Z, 0.1),
 'A8_volsw_s085brake':      lambda c: (volsw(c), rx.av23s, B85, 0.1),
 'A9_tqqq_s085brake':       lambda c: (tq(c), rx.av23s, B85, 0.1),
 'A10_gate_s085brake':      lambda c: (gate(c, tq(c)), rx.av23s, B85, 0.1),
}
out = {}
for k, f in C.items():
    T = std.measure(k, f, verbose=False); out[k] = T
    p = T['dev250_path']; r = T['real_ndx_86_14']
    print('%-22s MS1 %.1f%% dd80 %.0f%% d_vs_s085 %+.1fpp pw %.0f%% | realNDX %.1f%% | SPX55 %.1f%% SPX70 %.1f%% | holds 1x %.1f 2x %.1f 3x %.1f' % (
        k, 100*p['cagr'], 100*p['dd80'], 100*p['d_vs_s085'], 100*p['pw_vs_s085'], 100*r['cagr'],
        100*T['real_spx_55_85']['cagr'], 100*T['real_spx_70_85']['cagr'], 100*p['hold1x'], 100*p['hold2x'], 100*p['hold3x']), flush=True)
json.dump(out, open('/mnt/project-files/research/raw_core/results/ablate.json', 'w'), indent=1)
