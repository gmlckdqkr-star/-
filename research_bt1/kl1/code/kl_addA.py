"""KL1 addendum A (PRECOMMIT_KL1_ADDENDUM_A.md): selection-only scale test of the S2 families.
Same S2 generator distribution (pairs / triples), new SeedSequence child, vectorized draws; same engine, selection window,
cost and SPA/RW code as the main run. Confirmation is NOT computed (the era was already used once).
Usage: python kl_addA.py KR 6000000 4000000 6     |   python kl_addA.py US 1200000 800000 7
Writes results/addA_S2<panel>.json; big D arrays go to the scratch cache as memmaps."""
import os, sys, json, time, hashlib, numpy as np
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/claude-0/-home-user--/e60ac389-f078-575c-af9f-bad532fab64a/scratchpad/kl/nb')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wsdata as WD, kl_engine as EN, kl_run_s2 as R2, kl_stats as ST, kl_gen as G
CACHE = WD.CACHE; RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results')
N_MAIN = 557468
MIN_ACT = {'KR': 750, 'US': 1260}


def atom_features(panel):
    meta = json.load(open(CACHE + '%s_atoms_meta.json' % panel.lower()))
    names = sorted(set(m['feat'] for m in meta)); fid = {n: i for i, n in enumerate(names)}
    return np.array([fid[m['feat']] for m in meta], np.int64)


def gen_add(panel, n_pairs, n_triples, child):
    rng = np.random.default_rng(np.random.SeedSequence(G.SEED).spawn(child + 1)[child])
    af = atom_features(panel); n = len(af)
    shapes = np.array(G.SH_KR if panel == 'KR' else G.SH_US); holds = np.array(G.HOLDS)

    def draw(k, m):
        out = np.empty((m, k), np.int64); todo = np.arange(m)
        while len(todo):
            aa = rng.integers(0, n, (len(todo), k)); f = af[aa]
            ok = (f[:, 0] != f[:, 1]) if k == 2 else ((f[:, 0] != f[:, 1]) & (f[:, 0] != f[:, 2]) & (f[:, 1] != f[:, 2]))
            out[todo[ok]] = aa[ok]; todo = todo[~ok]
        return out
    P = draw(2, n_pairs); stp = np.where(rng.random(n_pairs) < 0.5, 1, 2)
    sp = shapes[rng.integers(0, len(shapes), n_pairs)]; hp = holds[rng.integers(0, 3, n_pairs)]
    rp = np.column_stack([P[:, 0], P[:, 1], np.zeros(n_pairs, np.int64), stp, sp[:, 0], sp[:, 1], hp])
    Tr = draw(3, n_triples); stt = rng.integers(3, 7, n_triples)
    s3 = shapes[rng.integers(0, len(shapes), n_triples)]; h3 = holds[rng.integers(0, 3, n_triples)]
    rt = np.column_stack([Tr[:, 0], Tr[:, 1], Tr[:, 2], stt, s3[:, 0], s3[:, 1], h3])
    return np.ascontiguousarray(np.vstack([rp, rt]).astype(np.int64))


def screen(panel, rows):
    t0 = time.time()
    I = R2.inputs(panel); dates = I['dates']
    mon, w0, w1 = R2.month_slots(dates, *R2.SEL[panel]); nmon = int(mon.max()) + 1; t1 = w1
    A = np.ascontiguousarray(I['A'][:, :t1]); X = np.ascontiguousarray(I['X'][:, :t1])
    N = len(rows)
    D = np.lib.format.open_memmap(CACHE + 'D_addA_%s.npy' % panel, mode='w+', dtype=np.float32, shape=(N, nmon))
    S = np.zeros((N, 4))
    ch = 50000
    for i in range(0, N, ch):
        rr = np.ascontiguousarray(rows[i:i + ch])
        om = np.zeros((len(rr), nmon), np.float32); os_ = np.zeros((len(rr), 4))
        EN.screen(A, X, rr, t1, mon, nmon, w0, w1, om, os_, I['cost'])
        D[i:i + ch] = om; S[i:i + ch] = os_
        if (i // ch) % 20 == 0:
            print('  screen', panel, i + len(rr), '%.0fs' % (time.time() - t0), flush=True)
    D.flush()
    return D, S, time.time() - t0


def dedup_keep(D):
    N = len(D); h = np.empty(N, np.uint64); nz = np.zeros(N, bool)
    for i in range(0, N, 100000):
        blk = np.ascontiguousarray(D[i:i + 100000])
        nz[i:i + len(blk)] = blk.any(1)
        for j in range(len(blk)):
            h[i + j] = int.from_bytes(hashlib.blake2b(blk[j].tobytes(), digest_size=8).digest(), 'little')
    _, first = np.unique(h, return_index=True)
    uniq = np.sort(first)
    return uniq[nz[uniq]], len(uniq)


def stats(label, parts, S, rows, n_total):
    """parts: list of memmap/arrays to stack (rows in order); S/rows aligned with the stacked order."""
    t0 = time.time()
    N = sum(len(p) for p in parts); T = parts[0].shape[1]
    path = CACHE + 'D_addA_stack_%s.npy' % label
    if len(parts) == 1:
        Dall = parts[0]
    else:
        Dall = np.lib.format.open_memmap(path, mode='w+', dtype=np.float32, shape=(N, T)); o = 0
        for p in parts:
            for i in range(0, len(p), 200000):
                b = np.asarray(p[i:i + 200000]); Dall[o:o + len(b)] = b; o += len(b)
        Dall.flush()
    keep, nuniq = dedup_keep(Dall)
    kp = CACHE + 'D_addA_keep_%s.npy' % label
    Dk = np.lib.format.open_memmap(kp, mode='w+', dtype=np.float32, shape=(len(keep), T))
    for i in range(0, len(keep), 200000):
        Dk[i:i + 200000] = Dall[keep[i:i + 200000]]
    Dk.flush()
    print(label, 'N', N, 'unique', nuniq, 'kept', len(keep), '%.0fs' % (time.time() - t0), flush=True)
    res, aux = ST.spa_rw(Dk, verbose=False)
    print(label, 'SPA', {k: v for k, v in res.items() if k != 'rw_crit'}, '%.0fs' % (time.time() - t0), flush=True)
    adv = aux['dbar'] * 12
    okr = S[keep, 1] >= MIN_ACT[label[-2:]]
    cand = np.flatnonzero(okr & aux['good'])
    j = cand[np.argmax(adv[cand])]
    jt = int(np.argmax(np.where(aux['good'], aux['tstat'], -np.inf)))
    # cross-sectional variance of monthly Sharpe ratios (for DSR), on a 200k random subsample (memory)
    rs = np.random.default_rng(5).choice(len(keep), min(200000, len(keep)), replace=False); rs.sort()
    sub = np.asarray(Dk[rs]).astype(np.float64)
    srs = np.full(len(sub), np.nan)
    for q in range(len(sub)):                      # same as kl_select: from the first non-zero month on
        nzq = np.flatnonzero(sub[q] != 0)
        if len(nzq):
            xq = sub[q, nzq[0]:]
            if len(xq) > 24 and xq.std() > 0:
                srs[q] = xq.mean() / xq.std(ddof=1)
    sr_var = float(np.nanvar(srs))
    x = np.asarray(Dk[j], float); nzj = np.flatnonzero(x != 0); x = x[nzj[0]:] if len(nzj) else x
    d_tot = ST.dsr(x, sr_var, n_total)
    out = dict(label=label, N_stacked=int(N), N_unique=int(nuniq), N_kept=int(len(keep)), months=int(T),
               spa={k: v for k, v in res.items() if k != 'rw_crit'},
               top_by_mean=dict(row=[int(v) for v in rows[keep[j]]], raw_adv_ann=float(adv[j]), tstat=float(aux['tstat'][j]), rw_reject=bool(aux['rw_rej'][j]),
                                defl_adv_q50=float((aux['dbar'][j] - res['maxnull_q50'] * aux['om'][j] / np.sqrt(T)) * 12),
                                dsr_Ntotal=d_tot[0], sr_m=d_tot[1], sr0=d_tot[2]),
               best_t=dict(row=[int(v) for v in rows[keep[jt]]], tstat=float(aux['tstat'][jt]), raw_adv_ann=float(adv[jt])),
               sr_var_subsample=sr_var, N_total_for_dsr=int(n_total), secs=time.time() - t0)
    for p in (path, kp):
        if os.path.exists(p) and p != getattr(parts[0], 'filename', None):
            os.remove(p)
    return out


if __name__ == '__main__':
    panel = sys.argv[1]; npair = int(sys.argv[2]); ntri = int(sys.argv[3]); child = int(sys.argv[4])
    n_prev = int(sys.argv[5]) if len(sys.argv) > 5 else 0          # addendum variants already counted (KR run before US)
    t0 = time.time()
    rows = gen_add(panel, npair, ntri, child)
    print('gen', panel, rows.shape, '%.0fs' % (time.time() - t0), flush=True)
    D, S, ts = screen(panel, rows)
    n_total = N_MAIN + n_prev + len(rows)
    outA = stats('add_' + panel, [D], S, rows, n_total)
    D0 = np.load(CACHE + 'D_S2%s.npy' % panel, mmap_mode='r'); S0 = np.load(CACHE + 'stat_S2%s.npy' % panel)
    r0 = np.load(CACHE + 'gen_S2%s.npy' % panel)
    outB = stats('comb_' + panel, [D0, D], np.vstack([S0, S]), np.vstack([r0, rows]), n_total)
    out = dict(panel=panel, child=child, n_pairs=npair, n_triples=ntri, N_add=int(len(rows)), N_total=int(n_total),
               screen_secs=ts, addendum_only=outA, combined_with_main=outB,
               gen_sha256=hashlib.sha256(rows.tobytes()).hexdigest(),
               note='selection period only; no confirmation computed (confirmation era already used once); cannot pass by design')
    json.dump(out, open(os.path.join(RES, 'addA_S2%s.json' % panel), 'w'), indent=1, default=float)
    os.remove(CACHE + 'D_addA_%s.npy' % panel)
    print('done', panel, '%.0fs' % (time.time() - t0), flush=True)
