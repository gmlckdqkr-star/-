"""Pure-Python replay (v_replay.simulate) on the first NPATH paths of the HEADLINE basis dev250_path:
(1) per-path agreement with the std kernel for S0, S4 and the NBR combinations (own tax books);
(2) NBR caveat on the headline basis: one shared tax book instead of own books."""
import os, sys, json, time, importlib.util
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
import numpy as np
spec = importlib.util.spec_from_file_location('v_replay_lib', '/mnt/project-files/research/final1/verify_main/code/v_replay_lib.py')
VR = importlib.util.module_from_spec(spec); spec.loader.exec_module(VR)
std, bk, rx, beng, ce, S_lib, L = VR.std, VR.bk, VR.rx, VR.beng, VR.ce, VR.S_lib, VR.L
OUT = '/mnt/project-files/research/final1/verify_main/results/'
NPATH = int(sys.argv[1]) if len(sys.argv) > 1 else 100
c = std.contexts()['dev250_path']; T = c.r.shape[1]; yrs = (T - 300) / 252.0
feat = np.ascontiguousarray(bk.features(c))
def kern(B, **kw):
    k = dict(beng.F1); k['fstep'] = 0.1; k.update(kw); pp, D = beng._args(k)
    o, EE = ce.runPE(np.ascontiguousarray(c.r), np.ascontiguousarray(c.rf), np.ascontiguousarray(B, dtype=np.float64), feat, int(pp['delay']), pp['cost'],
                     pp['tax'], D, int(pp['harvest']), pp['hthr'], pp['cspr'], pp['er3'], pp['step'], rx.av23s, VR.BP, float(pp['fstep']))
    return o[:, 0].copy()
PTS = VR.NBR9
SIG = {p: S_lib.fam4(c, 3.0, p[1], 1.0, caution=('shock6m',), Lc=1.0, sl=p[0], band=0.02) for p in PTS}
FIN = {p: kern(SIG[p]) for p in PTS}
cg = lambda fin: np.maximum(fin, 1e-9) ** (1 / yrs) - 1
k_v1 = cg(FIN[(200, .40)]); k_s4 = cg(kern(SIG[(200, .40)], cspr=0.005, cost=0.0012))
k_n = {nm: cg(np.mean([np.maximum(FIN[p], 1e-9) for p in pts], axis=0)) for nm, pts in (('NBR5', VR.NBR5), ('NBR9', VR.NBR9))}
rows = []; t0 = time.time()
for i in range(NPATH):
    r = c.r[i]; rf = c.rf[i]; ft = feat[i]
    s0, _ = VR.simulate(r, rf, [SIG[(200, .40)][i]], ft, VR.y_base, 0.003, 2)
    s4, _ = VR.simulate(r, rf, [SIG[(200, .40)][i]], ft, VR.y_rp, 0.0012, 2)
    row = dict(i=i, s0=s0, s4=s4, k_s0=float(k_v1[i]), k_s4=float(k_s4[i]))
    for nm, pts in (('NBR5', VR.NBR5), ('NBR9', VR.NBR9)):
        Bs = [SIG[p][i] for p in pts]
        own, _ = VR.simulate(r, rf, Bs, ft, VR.y_base, 0.003, 2, joint=False)
        jnt, _ = VR.simulate(r, rf, Bs, ft, VR.y_base, 0.003, 2, joint=True)
        row.update({nm + '_own': own, nm + '_joint': jnt, 'k_' + nm: float(k_n[nm][i])})
    rows.append(row)
    if (i + 1) % 20 == 0: print(i + 1, '%.0fs' % (time.time() - t0), flush=True)
A = {k: np.array([x[k] for x in rows]) for k in rows[0]}
res = dict(n_paths=NPATH,
           replay_vs_kernel_maxabs=dict(S0=float(np.max(np.abs(A['s0'] - A['k_s0']))), S4=float(np.max(np.abs(A['s4'] - A['k_s4']))),
                                        NBR5=float(np.max(np.abs(A['NBR5_own'] - A['k_NBR5']))), NBR9=float(np.max(np.abs(A['NBR9_own'] - A['k_NBR9'])))))
for nm in ('NBR5', 'NBR9'):
    dj = A[nm + '_joint'] - A[nm + '_own']; d_own = A[nm + '_own'] - A['s0']; d_j = A[nm + '_joint'] - A['s0']
    res[nm] = dict(joint_minus_own_median=float(np.median(dj)), joint_minus_own_mean=float(np.mean(dj)), joint_minus_own_min=float(dj.min()), joint_minus_own_max=float(dj.max()),
                   d_own_median=float(np.median(d_own)), pw_own=float(np.mean(d_own > 1e-5)), d_joint_median=float(np.median(d_j)), pw_joint=float(np.mean(d_j > 1e-5)),
                   cagr_own_median=float(np.median(A[nm + '_own'])), cagr_joint_median=float(np.median(A[nm + '_joint'])), v1_median=float(np.median(A['s0'])))
print(json.dumps(res, indent=1))
json.dump(res, open(OUT + 'v_replay_path.json', 'w'), indent=1)
print('done %.0fs' % (time.time() - t0))
