"""Link bias check (fix of final.py's EW-linked row, which passed K=1 and so held one name): EW of linked eligible
names vs EW of all eligible names, lab engine, 1986-2014 after tax (conservative rule). argv: code_dir out_json"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/lab'); sys.path.insert(0, sys.argv[1])
from lab import stocks
import m2lib as M, labbridge as LB
d = M.load(); P = stocks.load()
j86 = int(np.searchsorted(d.dd, pd.Timestamp('1986-01-01')))
pkl = np.full((d.nd, d.N), -1, np.int64)
for j in range(j86, d.nd):
    c_ = np.flatnonzero(d.elig[j] & d.linked[j]); pkl[j, :len(c_)] = c_
tgl = LB.targets_from_picks(P, d, pkl, d.N, rb='M')
tgl.wts = [np.full(len(p), 1.0 / max(len(p), 1)) for p in tgl.picks]
st = pd.Timestamp('1986-01-02')
o = dict(ew_linked_cons=stocks.run1(P, tgl, stocks.H_CONS, st, 0.003, 0.22, 2)['cagr_at'],
         ew_all_cons=stocks.ew_row(P, stocks.H_CONS, st, 0.003, 0.22, 2)['cagr_at'],
         linked_share_of_eligible_8614=float((d.elig[j86:] & d.linked[j86:]).sum() / d.elig[j86:].sum()))
json.dump(o, open(sys.argv[2], 'w'), indent=1); print(o)
