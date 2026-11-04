"""M3 (a) stage 2 (PRECOMMIT_M3 sec 3): s0.85 idle share -> TMF while the bond gate is on (in force 2 trading days after the signal),
else CASH. Engine = etxeng / upeng.run_port (verified MS1 parity). Every d is the same-path paired median vs s0.85 under the SAME stress.
usage: t2_fill.py <basis>[,<basis>..] <kind>[,<kind>..]      kinds: base drift0 drift15 cost2x levx1 ext (SPX bases use ext)"""
import sys, json, time, gc, numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m3/code')
import m3env, m3sig as SG
G = m3env.G
import run_stage2 as S2           # ETX1 stress switches (dedrift etc.); its writer functions are never called here
WARM = G.WARM
CANDS = ['UNGATED'] + SG.ALL


def gate_matrix(b, sig):
    """(P, K) in-force gate: value at row t = WARM + k - 2 of the by-date gate gathered with the basis row index; off where no bond data"""
    if sig == 'UNGATED': return np.ones((b.P, b.K))
    arr = SG.on_basis(b.D.index, sig)
    g = arr[b.c.ii]
    tt = np.arange(WARM, b.T) - 2
    fin = np.isfinite(b.g('TLT'))
    return g[:, tt] * fin[:, tt]


def sl_gate(L, GT):
    def f(p, J):
        lv = L[p]; K = lv.shape[0]; gt = GT[p]; W = np.zeros((K, len(J)))
        W[:, J['TQQQ']] = lv / 3; idle = 1 - lv / 3
        W[:, J['TMF']] = idle * gt; W[:, J['CASH']] = idle * (1 - gt)
        fl = np.r_[True, (np.diff(lv) != 0) | (np.diff(gt) != 0)]
        return W, fl
    return f


def run_one(b, L, sig, kw):
    GT = gate_matrix(b, sig)
    r = G.run(b, ['TQQQ', 'CASH', 'TMF'], [sl_gate(L, GT)], [1.0], **kw)
    return r, float(np.mean(GT))


def run_set(bn, kind):
    t0 = time.time(); kw, delay = S2.stressed(kind)
    b = G.Basis(bn); L = G.s085_levels(bn, delay=delay)
    ref = G.run(b, ['TQQQ', 'CASH'], [G.sl_s085(L)], [1.0], **kw)
    res = {'_meta': dict(basis=bn, kind=kind, P=b.P, years=b.K / 252), 's085': G.row(ref)}
    paths = {'s085': ref['cagr']}
    for sig in CANDS:
        r, onsh = run_one(b, L, sig, kw); rw = G.row(r, ref); rw['gate_on_share'] = onsh
        idle = 1 - L / 3; rw['idle_share'] = float(np.mean(idle))
        res[sig] = rw; paths[sig] = r['cagr']
        print(bn, kind, '%-8s cagr %.4f d %+.4f pw %.2f dd80 %.3f on %.2f' % (sig, rw['cagr'], rw['d_ref'], rw['pw_ref'], rw['dd80'], onsh),
              '%.0fs' % (time.time() - t0), flush=True)
        del r; gc.collect()
    fn = m3env.SCR + 'results/t2_%s_%s.json' % (bn, kind)
    json.dump(res, open(fn, 'w'), indent=1)
    if b.P > 1: np.savez_compressed(fn.replace('.json', '_paths.npz'), **paths)
    S2.stressed('base')
    return res


if __name__ == '__main__':
    for bn in sys.argv[1].split(','):
        for kind in sys.argv[2].split(','): run_set(bn, kind)
