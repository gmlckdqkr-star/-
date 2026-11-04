"""M3 (a) time-shift nulls on a basis (PRECOMMIT_M3 sec 3), 200 draws each, seed 20261104, circular shift k in [252, n-252].
N3 (E06 literal): TLT excess return over rf shifted (finite rows only), gate and s0.85 fixed.
N2 (gate information): the by-date gate shifted on the basis calendar, bond returns and s0.85 fixed.
usage: t3_null.py <basis> <n> <sig>[,<sig>..]"""
import sys, json, time, gc, numpy as np, pandas as pd
sys.path.insert(0, '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m3/code')
import m3env, m3sig as SG, t2_fill as T2
G = m3env.G; S2 = T2.S2; WARM = G.WARM


def gate_from_arr(b, arr):
    g = arr[b.c.ii]; tt = np.arange(WARM, b.T) - 2; fin = np.isfinite(b.g('TLT'))
    return g[:, tt] * fin[:, tt]


def run(bn, n, sig):
    t0 = time.time(); S2.stressed('base')
    b = G.Basis(bn); L = G.s085_levels(bn)
    ref = G.run(b, ['TQQQ', 'CASH'], [G.sl_s085(L)], [1.0])
    arr0 = SG.on_basis(b.D.index, sig)
    act = G.run(b, ['TQQQ', 'CASH', 'TMF'], [T2.sl_gate(L, gate_from_arr(b, arr0))], [1.0])
    d_act = float(np.median(act['cagr'] - ref['cagr']))
    rfd = np.full(len(b.D), np.nan); rfd[b.c.ii.ravel()] = np.asarray(b.c.rf, float).ravel(); rfd = pd.Series(rfd).ffill().bfill().values
    tlt0 = b.D['TLT'].values.astype(float).copy(); fi = np.where(np.isfinite(tlt0))[0]; ex0 = tlt0[fi] - rfd[fi]
    rng = np.random.default_rng(20261104); res = {'basis': bn, 'sig': sig, 'n': n, 'd_actual': d_act}
    for kind in ('N3', 'N2'):
        ds = []
        for i in range(n):
            if kind == 'N3':
                k = int(rng.integers(252, len(fi) - 252)); x = tlt0.copy(); x[fi] = np.roll(ex0, k) + rfd[fi]
                b.D['TLT'] = x; b._g = {}; GT = gate_from_arr(b, arr0)
            else:
                k = int(rng.integers(252, len(arr0) - 252)); b.D['TLT'] = tlt0; b._g = {}; GT = gate_from_arr(b, np.roll(arr0, k))
            r = G.run(b, ['TQQQ', 'CASH', 'TMF'], [T2.sl_gate(L, GT)], [1.0]); ds.append(float(np.median(r['cagr'] - ref['cagr'])))
            del r; gc.collect()
            if (i + 1) % 50 == 0: print(bn, sig, kind, i + 1, '%.0fs' % (time.time() - t0), flush=True)
        b.D['TLT'] = tlt0; b._g = {}
        ds = np.array(ds)
        res[kind] = dict(mean=float(ds.mean()), p50=float(np.median(ds)), p95=float(np.percentile(ds, 95)), max=float(ds.max()),
                         p_value=float((np.sum(ds >= d_act) + 1) / (n + 1)), draws=ds.tolist())
        print(bn, sig, kind, 'd_act %+.4f null mean %+.4f p95 %+.4f p %.3f' % (d_act, ds.mean(), np.percentile(ds, 95), res[kind]['p_value']), flush=True)
    json.dump(res, open(m3env.SCR + 'results/t3_null_%s_%s.json' % (bn, sig), 'w'), indent=1)


if __name__ == '__main__':
    for s in sys.argv[3].split(','): run(sys.argv[1], int(sys.argv[2]), s)
