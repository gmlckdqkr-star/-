"""LMX1 A1 diagnostic map (PRECOMMIT_LMX1_A1.md). Each library stream at w=0.20 on top of v1 100%, rows U and R. No selection."""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/lmx1/code'); sys.path.insert(0, '/mnt/project-files/research/c3_create/lanes/I_INTEGRATE/code')
import lmx, ii, el
t0 = time.time(); out = {}
REF = {bn: lmx.run(bn, [0, 0], 'R') for bn in lmx.BASES}
def run1(bn, j, mode):
    TQ, DEP, CU, IDL = ii.ref_in(bn); S, SO = ii.arrays(bn)
    s = S[:, :, j].astype(np.float64)
    if ii.SID[j].startswith('VALPROF'): s = s - 0.006 / 252
    Sa = np.ascontiguousarray(s[:, :, None]); SOa = np.ascontiguousarray(SO[:, :, j:j + 1].astype(np.float64))
    FIN = np.ascontiguousarray(lmx.fin_rate(bn, mode))
    return lmx._combf(np.ascontiguousarray(TQ), np.ascontiguousarray(DEP), FIN, np.ascontiguousarray(CU), np.ascontiguousarray(IDL), Sa, SOa,
                      1.0, np.array([0.2]), 0, 0.003, ii._PP['tax'], ii._D, int(ii._PP['harvest']), ii._PP['hthr'], 21, 0.05, 0.25)
for j, sid in enumerate(ii.SID):
    for mode in ('U', 'R'):
        rec = {}
        for bn in lmx.BASES:
            fin, E = run1(bn, j, mode); r = ii.stats(bn, fin, E)
            rec[bn] = {k: float(r[k]) for k in ('cagr', 'dd80', 'dd95', 'd', 'pw') if k in r}
            if bn == 'real_ndx_86_14': rec['halves'] = lmx.halves(E, REF[bn][1])
        p = rec['dev250_path']; n = rec['real_ndx_86_14']; h = rec['halves']
        c1 = p['d'] >= 0.003 and p['pw'] >= 0.6; c2 = n['d'] > 0 and h['d_86_99'] >= 0 and h['d_00_14'] >= 0
        c3 = rec['real_spx_55_85']['d'] >= 0 and rec['real_spx_70_85']['d'] >= 0
        rec['c123'] = [bool(c1), bool(c2), bool(c3)]; out[sid + '|' + mode] = rec
        print('%-14s %s path d %+.4f pw %.2f dd80 %.2f | NDX d %+.4f (%+.4f, %+.4f) | spx %+.4f %+.4f | c123 %s' % (
            sid, mode, p['d'], p['pw'], p['dd80'], n['d'], h['d_86_99'], h['d_00_14'], rec['real_spx_55_85']['d'], rec['real_spx_70_85']['d'],
            ''.join('Y' if x else 'n' for x in rec['c123'])), flush=True)
json.dump(out, open(lmx.OUT + 'lmx1_map.json', 'w'), indent=1)
print('done %.0fs' % (time.time() - t0))
