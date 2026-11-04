"""Parity: s0.85 on the five MS1 bases + 1986-99 / 2000-14 pools must match ETX1 (16.16 / 27.03 / 31.08 / 11.94 / 12.63)."""
import sys, time, json, numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m3/code')
import m3env; G = m3env.G
out = {}
for bn in G.BASES + ['pool_e8699']:
    t0 = time.time(); b = G.Basis(bn); L = G.s085_levels(bn)
    ref = G.run(b, ['TQQQ', 'CASH'], [G.sl_s085(L)], [1.0]); out[bn] = G.row(ref)
    tmf = G.run(b, ['TQQQ', 'CASH', 'TMF'], [G.sl_s085(L, {'TMF': 1.0})], [1.0]); r2 = G.row(tmf, ref)
    print(bn, 'P', b.P, 's085 %.4f' % out[bn]['cagr'], 'TMFfill %.4f d %+.4f' % (r2['cagr'], r2['d_ref']), '%.0fs' % (time.time() - t0), flush=True)
json.dump(out, open(m3env.SCR + 'results/t0_parity.json', 'w'), indent=1)
