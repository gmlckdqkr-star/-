"""MX2 run order (PRECOMMIT_MX2 §2-4). Logs to results/run.log; placebo raw files deleted after summarising."""
import sys, os, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/mx2/code'); import lib
R = lib.R; LOG = open(R + 'results/run.log', 'a')
def log(*a):
    s = time.strftime('%FT%TZ ', time.gmtime()) + ' '.join(str(x) for x in a); print(s, flush=True); LOG.write(s + '\n'); LOG.flush()
T0 = lib.tables(lib.D0, lib.CB0)
step = sys.argv[1]
if step == 'R1':
    out, err = lib.run_kernel(T0, 0, 0, 0, 'R1'); log('R1', err)
elif step == 'R2':
    out, err = lib.run_kernel(T0, 1, 5_000_000_000, 20261112, 'R2'); log('R2', err)
elif step == 'SUB':
    out, err = lib.run_kernel(T0, 2, 100_000_000, 777, 'SUB_real'); log('SUB_real', err)
    S, C, ne = lib.read_out(out); sel = lib.select(S, C, 0, 20); oos = lib.wf_oos(sel, lib.D0, lib.CB0)
    json.dump(dict(oos=oos.tolist(), evals=int(ne)), open(R + 'results/sub_real.json', 'w'))
    log('SUB_real done (value sealed in sub_real.json until placebos finish)')
    rng = np.random.default_rng(20261112); res = []
    for i in range(1, 101):
        s1 = int(rng.integers(24, 349)); s2 = int(rng.integers(24, 325))
        D, CB = lib.shift_DC(lib.D0, lib.CB0, s1, s2); T = lib.tables(D, CB)
        out, err = lib.run_kernel(T, 2, 100_000_000, 777, 'SUB_p')
        S, C, ne = lib.read_out(out); sel = lib.select(S, C, 0, 20); oos = lib.wf_oos(sel, D, CB)
        res.append(dict(i=i, s1=s1, s2=s2, oos_sum=float(oos.sum()), oos_ndx=float(oos[20:].sum()), oos_spx=float(oos[:20].sum())))
        os.remove(out)
        json.dump(res, open(R + 'results/sub_placebo.json', 'w'))
        if i % 10 == 0: log('placebo', i, err)
    log('SUB placebos done')
