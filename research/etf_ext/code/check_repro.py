"""Reproduce s0.85 (MS1 locked 16.16 / 27.03 / 31.08 / 11.94 / 12.63) and R1 / B2 (user_port_up, r1_lever) on this engine."""
import sys, os, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import etxeng as G
for bn in G.BASES:
    t0 = time.time(); b = G.Basis(bn); L = G.s085_levels(bn)
    ref = G.run(b, ['TQQQ', 'CASH'], [G.sl_s085(L)], [1.0])
    r1 = G.run(b, ['TQQQ', 'CASH', 'DBMF', 'GDE'], G.bind(b, [G.sl_s085(L, {'DBMF': 1.0}), G.sl_static({'GDE': 1.0}), G.sl_static({'DBMF': 1.0})]), [0.7, 0.15, 0.15])
    b2 = G.run(b, ['TQQQ', 'CASH', 'DBMF', 'RSST'], G.bind(b, [G.sl_s085(L, {'DBMF': 1.0}), G.sl_static({'RSST': 1.0})]), [0.7, 0.3])
    print(bn, 's085 %.4f' % G.row(ref)['cagr'], 'R1 %.4f' % G.row(r1)['cagr'], 'B2 %.4f' % G.row(b2)['cagr'],
          'cov TB %.3f GOLD %.3f IEF %.3f' % (b.cover('U_TB'), b.cover('U_GOLD'), b.cover('IEF')), '%.0fs' % (time.time() - t0), flush=True)
