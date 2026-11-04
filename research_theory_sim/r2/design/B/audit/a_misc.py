import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); import exec_engine as ee
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/B'); import sim, rule
T = 7860
# N1 OFF check
s = sim.simulate(500, T, 11, False); close = np.exp(np.cumsum(np.log1p(s['r']), axis=1)) * 100.0
x = np.diff(np.log(close), axis=1, prepend=np.log(close[:, :1]))
lam = 1 - 0.5 ** (1 / 250); sv = np.empty_like(x); v = np.full(500, 0.17)
for t in range(x.shape[1]): v = v + lam * (1.25 * np.sqrt(252) * np.abs(x[:, t]) - v); sv[:, t] = v
print('N1 seed 11 OFF: %.17f (logged 0.03884147676848637)' % ee.summary(ee.run(s['r'], s['rf'], np.clip(0.5 * 0.03 / sv ** 2, 0, 3)))['cagr_med'])
# scale invariance at engine level on fresh seed 10001 ON, P=2000
s = sim.simulate(2000, T, 10001, True); r, rf = s['r'], s['rf']
close = 100.0 * np.exp(np.cumsum(np.log1p(r), axis=1))
B1 = rule.target_levels(close, rf); B2 = rule.target_levels(close * 1000.0, rf)
a = ee.run(r, rf, B1); b = ee.run(r, rf, B2)
print('P=2000: max |level diff| %.3g; engine cagr identical on all paths: %s; n differing paths %d; median %.6f vs %.6f' % (
    np.nanmax(np.abs(B1 - B2)), np.array_equal(a['cagr'], b['cagr']), int((a['cagr'] != b['cagr']).sum()), np.median(a['cagr']), np.median(b['cagr'])))
# mechanism OFF really off: OFF returns equal fundamental returns d + c*u; check ON/OFF differ and OFF independent of A,B,h_m,h_s,rho
p_off = sim.simulate(300, T, 555, False); p_on = sim.simulate(300, T, 555, True)
print('ON vs OFF returns differ:', not np.allclose(p_on['r'], p_off['r']), ' same rf:', np.array_equal(p_on['rf'], p_off['rf']), ' same y10:', np.array_equal(p_on['y10'], p_off['y10']))
for k in ('mu', 'sigma', 'nu', 'h_v', 's_v'):
    assert np.array_equal(p_on['params'][k], p_off['params'][k])
print('same per-path mu, sigma, nu, h_v, s_v ON/OFF: True')
# monkeypatch: force A=B=0 inside ON solver -> should equal OFF up to the shock-scale choice
import types
orig = sim._draw_params
def dp0(g, P):
    p = orig(g, P); p['A'] = p['A'] * 0; p['B'] = p['B'] * 0; return p
sim._draw_params = dp0
z = sim.simulate(300, T, 555, True)
sim._draw_params = orig
lx_z = np.log1p(z['r']); lx_off = np.log1p(p_off['r'])
print('ON solver with A=B=0 vs OFF: max |log-return diff| %.3g (OFF branch == fundamental returns)' % np.max(np.abs(lx_z - lx_off)))
# skew / asymmetry ON vs OFF, autocorr of |r|
for lab, ss in (('ON', p_on), ('OFF', p_off)):
    lx = np.log1p(ss['r'][:, 300:])
    sk = ((lx - lx.mean(1, keepdims=True)) ** 3).mean(1) / lx.std(1) ** 3
    print(lab, 'median daily skew %.3f' % np.median(sk))
