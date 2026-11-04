"""s0.85 daily return streams on the MS1 bases (real_ndx_86_14, dev250_path), after cost, BEFORE the 22% tax.
Saves the source dates of every path row so a stock stream can be re-sampled on the same paths (as lab ms1.series).
Output: scratch npz (large) + results/s085_streams_meta.json (checks). <=2014 only (std contexts end 2014-12-31)."""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std, jp, iv, ov

OUT = sys.argv[1] if len(sys.argv) > 1 else '/tmp/s085_streams.npz'
C = std.contexts()
R, M = jp.calendar('1984-01-03', '2014-12-31'); Xr = jp.mkX(R, M, 'NDX')
a, b, Pn, blk, seed = iv.POOLS['dev250']; R2, M2 = jp.calendar(a, b); Xd = jp.mkX(R2, M2, 'NDX')
meta = dict(pool=[a, b, Pn, blk, seed])
save = {}
for bn, X in (('real_ndx_86_14', Xr), ('dev250_path', Xd)):
    c = C[bn]
    rB, rbf, rbp, rfs = std.s085(c)
    f_tax, E_tax = std.engine(c, rB, rbf, rbp, rfs)
    f0, E0 = std.engine(c, rB, rbf, rbp, rfs, tax=0.0)
    ii = c.ii[:, ov.WARM:]
    assert E0.shape == ii.shape, (E0.shape, ii.shape)
    r = np.empty_like(E0); r[:, 0] = E0[:, 0] - 1.0; r[:, 1:] = E0[:, 1:] / E0[:, :-1] - 1.0
    # cash return of the MS1 engine: max(rf - 2%/252, 0) x (1 - 15.4%)
    rf = c.rf[:, ov.WARM:]
    cashr = np.maximum(rf - 0.02 / 252, 0.0) * (1 - 0.154)
    incash = np.abs(r - cashr) < 1e-10
    save[bn + '_r'] = r.astype(np.float64)
    save[bn + '_ii'] = ii.astype(np.int32)
    save[bn + '_cash'] = incash
    save[bn + '_rf'] = rf
    save[bn + '_ndx'] = c.r[:, ov.WARM:]
    save[bn + '_srcdates'] = X.index.values.astype('datetime64[D]').astype(np.int64)
    meta[bn] = dict(shape=list(E0.shape), cagr_tax_med=float(np.median(f_tax)), cagr_notax_med=float(np.median(f0)),
                    cash_share=float(incash.mean()), first_date=str(X.index[ii[0, 0]].date()),
                    last_date=str(X.index[ii[0, -1]].date()))
    print(bn, meta[bn], flush=True)
np.savez(OUT, **save)
json.dump(meta, open('/mnt/project-files/research/multi_cand/w3_stock_new/results/s085_streams_meta.json', 'w'), indent=1)
