"""TW1 runner (PRECOMMIT_TW1.md sha 6227e922). <=2014 only. v1 trades unchanged; only tax rate, cost per side, and a holding carry on the TQQQ leg change.
Engine = research/lmx1/code/lmx.py _combf (el._comb1 copy) with no sleeves and a0 = 1."""
import os, sys, json, time
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
import numpy as np
sys.path.insert(0, '/mnt/project-files/research/c3_create/lanes/I_INTEGRATE/code')
sys.path.insert(0, '/mnt/project-files/research/lmx1/code')
import ii, el, lmx
OUT = '/mnt/project-files/research/tw1/results/'
BASES = lmx.BASES

def run(bn, tax, cost, carry):
    TQ, DEP, CU, IDL = ii.ref_in(bn)
    TQ2 = np.ascontiguousarray(np.asarray(TQ, dtype=np.float64) - carry / 252.0)
    Z = np.zeros(TQ2.shape + (1,))
    return lmx._combf(TQ2, np.ascontiguousarray(DEP), np.zeros_like(TQ2), np.ascontiguousarray(CU), np.ascontiguousarray(IDL), Z, Z.copy(),
                      1.0, np.zeros(1), 0, float(cost), float(tax), ii._D, int(ii._PP['harvest']), ii._PP['hthr'], 21, 0.05, 0.25)

ROWS = {'C0': (0.11, 0.003, 0.00), 'C1': (0.11, 0.003, 0.01), 'C2': (0.11, 0.003, 0.02), 'C3': (0.11, 0.003, 0.03),
        'D0': (0.11, 0.006, 0.00), 'D1': (0.11, 0.006, 0.01), 'D2': (0.11, 0.006, 0.02), 'D3': (0.11, 0.006, 0.03),
        'K0': (0.11, 0.002, 0.00)}

def passes(rec):
    p = rec['dev250_path']; n = rec['real_ndx_86_14']; h = rec['halves']
    c1 = p['d'] >= 0.0030 and p['pw'] >= 0.60
    c2 = n['d'] > 0 and h['d_86_99'] >= 0 and h['d_00_14'] >= 0
    c3 = rec['real_spx_55_85']['d'] >= 0 and rec['real_spx_70_85']['d'] >= 0
    c4 = p['dd95'] <= rec['_v1dd95']
    return dict(c1=bool(c1), c2=bool(c2), c3=bool(c3), c4=bool(c4), all=bool(c1 and c2 and c3 and c4))

if __name__ == '__main__':
    t0 = time.time(); out = {'parity': {}, 'rows': {}, 'tax_base': float(ii._PP['tax'])}
    REF = {}
    for bn in BASES:
        fin, E = run(bn, ii._PP['tax'], 0.003, 0.0); r = ii.stats(bn, fin, E); REF[bn] = (fin, E, r)
        out['parity'][bn] = {k: float(r[k]) for k in ('cagr', 'mdd', 'dd80', 'dd95', 'd') if k in r}
        print('PARITY', bn, {k: round(v, 5) for k, v in out['parity'][bn].items()}, flush=True)
    for rn, (tax, cost, carry) in ROWS.items():
        rec = {}
        for bn in BASES:
            fin, E = run(bn, tax, cost, carry); r = ii.stats(bn, fin, E)
            rec[bn] = {k: float(r[k]) for k in ('cagr', 'mdd', 'p10', 'dd80', 'dd95', 'd', 'pw') if k in r}
            if bn == 'real_ndx_86_14': rec['halves'] = lmx.halves(E, REF[bn][1])
        rec['_v1dd95'] = out['parity']['dev250_path']['dd95']; rec['pass'] = passes(rec)
        out['rows'][rn] = dict(tax=tax, cost=cost, carry=carry, **rec)
        p = rec['dev250_path']; n = rec['real_ndx_86_14']; h = rec['halves']
        print('%-3s tax %.2f cost %.4f carry %.2f | path %.4f (d %+.4f pw %.2f dd80 %.2f dd95 %.3f) realNDX %.4f (d %+.4f; 86-99 %+.4f, 00-14 %+.4f) spx55 %+.4f spx70 %+.4f | %s' % (
            rn, tax, cost, carry, p['cagr'], p['d'], p['pw'], p['dd80'], p['dd95'], n['cagr'], n['d'], h['d_86_99'], h['d_00_14'],
            rec['real_spx_55_85']['d'], rec['real_spx_70_85']['d'], 'PASS' if rec['pass']['all'] else 'fail ' + ''.join(k for k in ('c1', 'c2', 'c3', 'c4') if not rec['pass'][k])), flush=True)
    json.dump(out, open(OUT + 'tw1.json', 'w'), indent=1)
    print('done %.0fs' % (time.time() - t0))
