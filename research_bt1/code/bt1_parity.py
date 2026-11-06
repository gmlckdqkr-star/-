"""parity: bt1_mega.screen (form 0) == m1_engine.screen on random M1-format rules; timing benchmark per form."""
import sys, time, numpy as np
sys.path.insert(0, '.')
import bt1_mega as BM, m1_engine as EN
c = BM.setup()
rng = np.random.default_rng(1)
na = len(c.AM)
# M1-format random rules
n = 3000
rows = np.zeros((n, 7), np.int64)
for i in range(n):
    st = rng.integers(0, 7); ids = rng.choice(na, 3, replace=False)
    s = rng.integers(7)
    rows[i] = (ids[0], ids[1] if st > 0 else -1, ids[2] if st > 2 else -1, st, EN.SHAPE_CODES[s, 0], EN.SHAPE_CODES[s, 1], [1, 5, 21][rng.integers(3)])
R = np.full((n, BM.NC), -1, np.int32); R[:, 0] = 0; R[:, 1:4] = rows[:, :3]; R[:, 8] = rows[:, 3]; R[:, 11] = rows[:, 4]; R[:, 12] = rows[:, 5]; R[:, 14] = rows[:, 6]
D2, S2 = BM.screen_chunk(c, R)
mx = 0; mxs = 0
for era, (A, LX, t1, mon, w0, w1) in (('spx', c.spx), ('ndx', c.ndx)):
    import m1_search as MS
    E = MS.era_inputs()
X = {}
E = MS.era_inputs()
om = np.zeros((n, c.nmon), np.float32); os1 = np.zeros((n, 4)); os2 = np.zeros((n, 4))
A, LX, t1, mon, w0, w1 = c.spx; EN.screen(A, np.ascontiguousarray(E['spx']['X'][:, :t1]), rows, t1, mon, c.nmon, w0, w1, om, os1)
om2 = np.zeros((n, c.nmon), np.float32)
A, LX, t1, mon, w0, w1 = c.ndx; EN.screen(A, np.ascontiguousarray(E['ndx']['X'][:, :t1]), rows, t1, mon, c.nmon, w0, w1, om2, os2)
D1 = om + om2; S1 = np.hstack([os1, os2])
print('parity max |dD|', float(np.abs(D1 - D2).max()), 'max |dS|', float(np.abs(S1 - S2).max()), 'nonzero rules', int((D1 != 0).any(1).sum()))
for nn in (20000,):
    R = BM.gen_shard(c.AM, 999, nn, c.P)
    print('forms', np.bincount(R[:, 0], minlength=5))
    t = time.time(); BM.screen_chunk(c, R); dt = time.time() - t
    print('screen %d rules %.1fs -> %.0f rules/s' % (nn, dt, nn / dt))
t = time.time(); R = BM.gen_shard(c.AM, 998, 200000, c.P); print('gen 200k %.1fs' % (time.time() - t))
