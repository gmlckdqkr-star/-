"""Descriptive only (not trials, not judgement): paired d vs AV23 for already-measured H1 configs. Output results/desc_vs_av23.json"""
import os, sys, json
os.environ['NUMBA_NUM_THREADS'] = '2'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m1
from m1 import np, ce, AV23, w1b, w1t
def P2(a, b, base=None): return np.concatenate([np.array([float(a), float(b)]), AV23 if base is None else base])
S = lambda bfn, bp: (lambda c, bn: (m1.sig('c3', c, bn), bfn, bp, 0.1, {}))
ref = m1.run(S(ce.alt, AV23)); s85 = m1.run(S(m1.rx.av23s, m1.B85))
C = {'H1e_crash_all': S(w1b, P2(2, 2)), 'H1f_crash_anti_all': S(w1b, P2(3, 3)), 'H1g_Nf1_Wcrash': S(w1b, P2(0, 2)),
     'H1h_Ncrashanti_Wav23': S(w1b, P2(3, 0)), 'H1i_av23_no_gcg': S(ce.alt, m1.av(gcg=1.0)), 'H5b_av23_taxadj': S(w1t, P2(1, 1.0))}
out = {}
for k, f in C.items():
    st = m1.stats(m1.run(f), {'av23': ref, 's085': s85}); out[k] = st
    print(m1.line(k, st, 'av23'), flush=True)
json.dump(out, open('/mnt/project-files/research/multi_cand/w1_c3fam/results/desc_vs_av23.json', 'w'), indent=1)
