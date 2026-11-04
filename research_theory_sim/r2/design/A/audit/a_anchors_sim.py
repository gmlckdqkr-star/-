"""AUDIT (blind auditor, lane A): anchors (check 2) and simulator sanity (check 7). Synthetic data only."""
import sys, time, json
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/A')
import numpy as np
import exec_engine as ee
import sim

T = 300 + 30 * 252
P = 2000
SEED = 777          # a seed the designer did not report using (any seed works for prior medians)
out = {}
W = {}
for mech in (True, False):
    t0 = time.time(); w = sim.simulate(P, T, SEED, mechanism=mech); dt = time.time() - t0
    W[mech] = w
    r, rf, y10 = w['r'], w['rf'], w['y10']
    p = w['params']
    lr = np.log1p(r[:, 300:]); lf = np.log1p(rf[:, 300:])
    prem = (lr - lf).mean(1) * 252
    vol = lr.std(1) * np.sqrt(252)
    cp = np.cumsum(lr, 1); dd = np.expm1((cp - np.maximum.accumulate(np.maximum(cp, 0), 1)).min(1))
    h1 = ee.hold(r, rf, 1)['cagr']
    k = 'ON' if mech else 'OFF'
    q = lambda a: [float(np.percentile(a, 10)), float(np.median(a)), float(np.percentile(a, 90))]
    out[k] = dict(sim_seconds=round(dt, 1),
                  prior_mu_g_p10_med_p90=q(p['mu_g']), prior_mu_g_sd=float(np.std(p['mu_g'])),
                  prior_sigma_p10_med_p90=q(p['sigma']), prior_sigma_logsd=float(np.std(np.log(p['sigma']))),
                  realised_logprem_p10_med_p90=q(prem), realised_vol_p10_med_p90=q(vol),
                  worst_dd_p10_med_p90=q(dd), p_dd50=float(np.mean(dd <= -0.5)), p_dd75=float(np.mean(dd <= -0.75)),
                  hold1_cagr_p10_med_p90=q(h1),
                  rf_mean_ann_med=float(np.median(rf[:, 300:].mean(1) * 252)),
                  nonfinite_r=int((~np.isfinite(r)).sum()), nonfinite_rf=int((~np.isfinite(rf)).sum()),
                  nonfinite_y10=int((~np.isfinite(y10)).sum()), r0_zero=bool(np.all(r[:, 0] == 0)),
                  min_r=float(r.min()), max_r=float(r.max()), rf_min=float(rf.min()), rf_max_ann=float(rf.max() * 252),
                  y10_min=float(y10.min()), y10_max=float(y10.max()))
    # per-path variation (2c): realised premium spread vs pure sampling noise sd/sqrt(30)
    out[k]['realised_prem_sd'] = float(np.std(prem))
    out[k]['sampling_noise_sd_expected'] = float(np.median(vol) / np.sqrt(30))

on, off = W[True], W[False]
same = dict(mu_g=bool(np.array_equal(on['params']['mu_g'], off['params']['mu_g'])),
            sigma=bool(np.array_equal(on['params']['sigma'], off['params']['sigma'])),
            nu=bool(np.array_equal(on['params']['nu'], off['params']['nu'])),
            rf=bool(np.array_equal(on['rf'], off['rf'])), y10=bool(np.array_equal(on['y10'], off['y10'])))
out['same_level_ON_OFF'] = same
# paired realised premium / vol difference ON-OFF
lon = np.log1p(on['r'][:, 300:]); loff = np.log1p(off['r'][:, 300:]); lf = np.log1p(on['rf'][:, 300:])
pon = (lon - lf).mean(1) * 252; poff = (loff - lf).mean(1) * 252
out['paired_prem_diff_ON_minus_OFF_med_mean'] = [float(np.median(pon - poff)), float(np.mean(pon - poff))]
von = lon.std(1) * np.sqrt(252); voff = loff.std(1) * np.sqrt(252)
out['paired_vol_diff_ON_minus_OFF_med_maxabs'] = [float(np.median(von - voff)), float(np.max(np.abs(von - voff)))]

# OFF world has no clustering / no predictable drift: acf of squared returns and of returns
def acf1(x):
    x = x - x.mean(1, keepdims=True); return ((x[:, 1:] * x[:, :-1]).mean(1) / (x * x).mean(1))
for k, L in (('ON', lon), ('OFF', loff)):
    a2 = L - L.mean(1, keepdims=True)
    out[k]['acf1_sq_med'] = float(np.median(acf1(a2 ** 2)))
    out[k]['acf1_ret_med'] = float(np.median(acf1(L)))
    # 20-day return autocorrelation
    n = L.shape[1] // 20; m = L[:, :n * 20].reshape(L.shape[0], n, 20).sum(2)
    out[k]['acf1_20d_ret_med'] = float(np.median(acf1(m)))

# rates (2d): long trending regimes. For each path: longest window (years) over which the 1y-smoothed rate moves
# monotonically by >= 2 pp, and the share of paths with a 10-year window with |change| >= 3 pp
ann = on['rf'] * 252
yr = 252
sm = np.cumsum(ann, 1); sm = (sm[:, yr:] - sm[:, :-yr]) / yr        # 1y moving average
s_y = sm[:, ::yr]                                                      # yearly samples
d10 = s_y[:, 10:] - s_y[:, :-10]
out['rates'] = dict(share_paths_10y_change_ge_3pp=float(np.mean(np.abs(d10).max(1) >= 0.03)),
                    share_paths_10y_up_ge_3pp=float(np.mean(d10.max(1) >= 0.03)),
                    share_paths_10y_down_ge_3pp=float(np.mean(d10.min(1) <= -0.03)),
                    share_paths_monthly_steps=float(np.mean(on['params']['rf_monthly'])))
# longest monotone run of yearly samples (same sign of yearly change), in years
dy = np.sign(np.diff(s_y, axis=1)); runs = []
for i in range(dy.shape[0]):
    best = cur = 1; prev = dy[i, 0]
    for v in dy[i, 1:]:
        if v == prev and v != 0: cur += 1
        else: cur = 1
        prev = v; best = max(best, cur)
    runs.append(best)
runs = np.array(runs)
out['rates']['longest_monotone_yearly_run_years_p10_med_p90'] = [float(np.percentile(runs, 10)), float(np.median(runs)), float(np.percentile(runs, 90))]
out['rates']['share_paths_monotone_run_ge_8y'] = float(np.mean(runs >= 8))
out['rates']['share_paths_flat_5y_within_0.5pp'] = float(np.mean((np.abs(s_y[:, 5:] - s_y[:, :-5]) < 0.005).any(1)))

# robustness options at defaults are bit-identical with the frozen copy
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/A/work')
import sim_frozen_copy as sf
a = sim.simulate(200, 3000, 11, mechanism=True); b = sf.simulate(200, 3000, 11, mechanism=True)
c = sim.simulate(200, 3000, 11, mechanism=False); d = sf.simulate(200, 3000, 11, mechanism=False)
out['sim_equals_frozen_copy'] = bool(np.array_equal(a['r'], b['r']) and np.array_equal(a['rf'], b['rf']) and np.array_equal(c['r'], d['r']))
# robustness worlds finite
for kw in (dict(prior_width=0.5), dict(prior_width=1.5), dict(mech_scale=0.5), dict(mech_scale=1.5)):
    w = sim.simulate(300, T, 12, mechanism=True, **kw)
    out['finite_' + '_'.join('%s%s' % kv for kv in kw.items())] = bool(np.isfinite(w['r']).all() and np.isfinite(w['rf']).all() and np.isfinite(w['y10']).all())
print(json.dumps(out, indent=1))
json.dump(out, open('/mnt/project-files/research/theory_sim/r2/design/A/audit/a_anchors_sim.json', 'w'), indent=1)
