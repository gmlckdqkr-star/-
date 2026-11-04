"""BT1 atoms = M1 atoms (old) + atoms of the 53 new primitives (flag new=True), same transforms/thresholds."""
import os, sys, json, time, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m1_atoms as MA, m1_data as D
SCR = D.SCR
if __name__ == '__main__':
    t = time.time()
    AM, out = MA.build()
    for m in AM: m['new'] = False
    R, M = D.cal(); idx = R.index
    rows = {e: (idx.searchsorted(pd.Timestamp(a)), idx.searchsorted(pd.Timestamp(b), side='right')) for e, (a, b) in (('spx', MA.SPX_ROWS), ('ndx', MA.NDX_ROWS))}
    z = np.load(SCR + 'cache/prim_bt1.npz'); meta = json.load(open(SCR + 'cache/prim_bt1_meta.json'))
    NEW = {'spx': [], 'ndx': []}
    for name, m in meta.items():
        for am, a in MA.atoms_of(name, z[name], m['kind'], m['freq'], False):
            am['era'] = 'both'; am['new'] = True; AM.append(am)
            for e in ('spx', 'ndx'):
                i0, i1 = rows[e]; NEW[e].append(a[i0:i1])
    for e in ('spx', 'ndx'):
        A = np.ascontiguousarray(np.vstack([out[e], np.vstack(NEW[e]).astype(np.int8)]))
        np.save(SCR + 'cache/atoms_%s.npy' % e, A); print(e, A.shape)
    json.dump(AM, open(SCR + 'cache/atoms_meta.json', 'w'))
    n_new = sum(m['new'] for m in AM); n_c3 = sum(m['c3'] for m in AM)
    print('atoms', len(AM), 'new', n_new, 'c3', n_c3, 'old non-c3', len(AM) - n_new - n_c3, '%.0fs' % (time.time() - t))
