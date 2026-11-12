"""self-tests for ru.acct: (1) KRW basis with X == 1 equals the USD basis; (2) zero deposits: wait rule irrelevant;
(3) a constant FX jump with no trades after it changes KRW value but not USD value; (4) parity with ac3.joint Z account."""
import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/acct3/code'); sys.path.insert(0, '/mnt/project-files/research/ru1/code')
import ac3, ru
b = ac3.prep()['dev250_path']; R, RF, L = b['R'][:50], b['RF'][:50], b['L'][:50]; P, T = R.shape; n = T - ru.WARM
one = np.ones((P, T)); Z = np.zeros((P, n))
o0, _, _ = ru.acctP(R, RF, L, one, Z, 0, 0, 0.0, .003, .22, .25, .0245, 1.0)
o1, _, _ = ru.acctP(R, RF, L, one, Z, 1, 0, 0.0, .003, .22, .25, .0245, 1.0)
o2, _, _ = ru.acctP(R, RF, L, one, Z, 0, 1, 0.0, .003, .22, .25, .0245, 1.0)
assert np.allclose(o0[:, 0], o1[:, 0], rtol=1e-12), 'krw basis with X=1 differs'
assert np.allclose(o0[:, 0], o2[:, 0], rtol=1e-12), 'wait rule without deposits differs'
# ac3.joint Z parity: cash 0 (cspr 1.0), no harvest
oj, _ = ac3.jointP(R, RF, L, L, 1e7, 1.0, 0.0, 0.0, 1, 1, 7.0, .003, .22, 0, ac3.PP['hthr'], 1.0, .0245, .003, .0245, .08, .073, .00021)
assert np.allclose(o0[:, 0], oj[:, 0], rtol=1e-9), (o0[:3, 0], oj[:3, 0])
# FX: X doubles on the last day only -> USD final unchanged (USD basis); KRW final x2 (no conversion cost)
X = one.copy(); X[:, -1] = 2.0
o3, _, _ = ru.acctP(R, RF, L, X, Z, 0, 0, 0.0, .003, .22, .25, .0245, 1.0)
assert np.allclose(o3[:, 0], o0[:, 0]) and np.allclose(o3[:, 1], 2 * o0[:, 0])
# hand example: buy all at X=1 (day 0), X=2 from day 1, sell all on day 2 (r=0, rf=0, no fees on the fund)
W = ru.WARM; T = W + 3; r = np.zeros(T); rf = np.zeros(T); Lh = np.array([3.0, 3.0, 0.0]); Xh = np.ones(T); Xh[W + 1:] = 2.0
o = np.zeros(9); eu = np.zeros(3); ek = np.zeros(3)
ru.acct(r, rf, Lh, Xh, np.zeros(3), 1, 0, 0.0, .003, .22, .25, 0.0, 1.0, o, eu, ek)
assert abs(o[1] - (0.994009 * 2 - 0.22 * (0.997 * 2 - 1 - 0.25))) < 1e-9, o[1]      # KRW gain taxed: 1.824338
ru.acct(r, rf, Lh, Xh, np.zeros(3), 0, 0, 0.0, .003, .22, .25, 0.0, 1.0, o, eu, ek)
assert abs(o[0] - 0.994009) < 1e-9 and abs(o[1] - 1.988018) < 1e-9, o[:2]           # USD basis: no gain, no tax
# deposits: one deposit 2 days after a trade waits (wait=1) and is bought at once (wait=0)
T = W + 10; r = np.full(T, 0.01); rf = np.zeros(T); Lh = np.r_[np.full(5, 3.0), np.full(5, 1.5)]; dep = np.zeros(10); dep[2] = 1.0
for wt in (0, 1):
    ru.acct(r, rf, Lh, np.ones(T), dep, 0, wt, 0.0, .003, .22, .25, 0.0, 1.0, o, eu, ek)
    if wt == 1: assert o[7] == 0 and o[8] == 0          # no app trade in the 4 days before day 2 (only the day-0 start) -> no wait
# a deposit 2 days after an app trade waits until the next level change (days 5..8 pending)
Lh = np.r_[np.full(3, 3.0), np.full(5, 1.5), np.full(2, 3.0)]; dep = np.zeros(10); dep[5] = 1.0; fins = []
for wt in (0, 1):
    ru.acct(r, rf, Lh, np.ones(T), dep, 0, wt, 0.0, .003, .22, .25, 0.0, 1.0, o, eu, ek); fins.append(o[0])
    if wt == 1: assert o[7] == 1 and o[8] == 4, o[7:9]
    else: assert o[7] == 0
assert fins[0] != fins[1]
print('t_ru: all checks pass; paths', P)
