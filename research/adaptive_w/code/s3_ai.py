"""AW synthetic AI-sleeve test (PRECOMMIT_AW.md, illustrative only, dev250_path). <=2014 path data + synthetic alpha/noise."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/adaptive_w/code'); import data, s1_run, ii
OUT = '/mnt/project-files/research/adaptive_w/results/'
bn = 'dev250_path'
def build(scn):
    A, B = data.load(bn, ['VALPROF4_L1', 'IDX_L1']); A = A.copy(); B = B.copy(); P, T, _ = A.shape
    t = np.arange(T) / T
    al = {'up': -0.05 + 0.20 * t, 'luck': 0 * t, 'down': 0.10 - 0.20 * t, 'step': np.where(t < 1 / 3, 0.0, 0.15)}[scn]
    rng = np.random.default_rng(20261105); z = rng.standard_normal((P, T)) * 0.20 / np.sqrt(252); z[:, 0] = 0
    A[:, :, 1] = A[:, :, 1] + al[None, :] / 252 + z
    so = np.zeros((P, T)); so[:, 251::252] = 0.7; B[:, :, 1] = so
    return np.ascontiguousarray(A), np.ascontiguousarray(B)
if __name__ == '__main__':
    sel = json.load(open(OUT + 's1_select.json')); names = [sel['selected']] + sorted(set(sel['family_best'].values()) - {sel['selected']})
    rules = [r for r in s1_run.RULES if r[0] in names]; W0 = [.70, .20, .10]; R = {}
    for scn in ('up', 'luck', 'down', 'step'):
        A, B = build(scn); f0, E0, _ = data.run(bn, A, B, W0); c0 = data.cagr(f0, E0)
        R[scn] = {'FIXED': float(np.median(c0))}
        for (n, rid, prm, cap) in rules:
            f, E, WT = data.run(bn, A, B, W0, rid, prm, cap=cap); c = data.cagr(f, E); d = c - c0; wa = WT[:, :-2, 2]
            yr = [float(np.median(wa[:, min(12 * y, wa.shape[1] - 1)])) for y in (1, 5, 10, 15, 20, 25, 30)]
            R[scn][n] = dict(d=float(np.median(d)), win=float(np.mean(d > 0)), ai_w_by_year=yr, ai_w_p90_y30=float(np.percentile(wa[:, -1], 90)),
                             ai_w_p10_y30=float(np.percentile(wa[:, -1], 10)))
            print(scn, n, round(R[scn][n]['d'] * 100, 2), [round(x, 3) for x in yr], flush=True)
    json.dump(R, open(OUT + 's3_ai.json', 'w'), indent=1)
