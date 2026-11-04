"""Verifier step 2 (check C + B): independent recomputation of hit rate / gain for three rules on both real eras.
Own sleeve, own trailing windows, own position-by-return-day alignment (decision at close k, traded close k+2, earns k+3..k+23).
Also: look-ahead perturbation test of the three rules, and two variants (s0.85 sleeve with its own level-change costs; switch costs)."""
import json, numpy as np

D = '/tmp/claude-0/-home-user--/0e26f5bd-b937-55ae-81a7-0c4a9abb6560/scratchpad/verify/'
STORED = json.load(open('/mnt/project-files/research/hybrid/results/info_le2014.json'))
RULES = [('VALPROF4_L1', 'MOM12'), ('BOND10_L3', 'TSM12'), ('SPXH_L1', 'DD30')]
BLK, DELAY = 21, 2
NC = 29


def s085_sleeve(TQ, DEP, CU, cost=0.0):
    """simulate the s0.85 sleeve myself: TQQQ part v0 + cash part v3; level CU[t] traded at close t (with optional cost)."""
    T = len(TQ); v0 = 0.0; v3 = 1.0; cur = None; V = np.ones(T); r = np.zeros(T)
    for t in range(T):
        if t > 0:
            prev = v0 + v3
            v0 *= 1 + TQ[t]; v3 *= 1 + DEP[t]
            r[t] = (v0 + v3) / prev - 1
        L = CU[t]
        if cur is None or L != cur:
            tot = v0 + v3; tgt = L / 3 * tot; tc = cost * abs(tgt - v0); tot -= tc
            v0 = L / 3 * tot; v3 = tot - v0; cur = L
            if t > 0:   # cost hits the day's return (traded at close t)
                r[t] = (v0 + v3) / prev - 1
        V[t] = v0 + v3
    return r


def run(bn, s085_cost=0.0, perturb_at=None, seed=0):
    z = np.load(D + 'data_%s.npz' % bn)
    TQ, DEP, CU = z['TQ'].copy(), z['DEP'].copy(), z['CU'].copy()
    T = len(TQ)
    cols = {'S085': s085_sleeve(TQ, DEP, CU, s085_cost)}
    for X, _ in RULES: cols[X] = z['S_' + X].astype(np.float64).copy()
    if perturb_at is not None:   # scramble everything strictly after day perturb_at
        rng = np.random.default_rng(seed)
        for n in cols: cols[n][perturb_at + 1:] = rng.normal(0, 0.03, T - perturb_at - 1)
    ks = list(range(252, T - 3, BLK))
    # position by RETURN day: return on day t is earned by the pick traded at the latest close k+2 <= t-1, i.e. latest k <= t-3
    out = {}
    for X, rule in RULES:
        s, x = cols['S085'], cols[X]
        picks = {}
        for k in ks:
            if rule == 'MOM12':
                rs = np.prod(1 + s[k - 251:k + 1]); rx = np.prod(1 + x[k - 251:k + 1]); pk = 1 if rx > rs else 0
            elif rule == 'TSM12':
                rs = np.prod(1 + s[k - 251:k + 1]); pk = 0 if rs > 1 else 1
            elif rule == 'DD30':
                lv = np.cumprod(1 + s[:k + 1]); w = lv[max(k - 251, 0):k + 1]; pk = 1 if lv[k] / w.max() - 1 < -0.30 else 0
            picks[k] = pk
        # daily position array for return days, -1 = not scored
        pos = np.full(T, -1); blk = np.full(T, -1)
        for i, k in enumerate(ks):
            for t in range(k + 3, min(k + 3 + BLK, T)):    # k+3 .. k+23
                pos[t] = picks[k]; blk[t] = i
        nb = len(ks); Gs = np.zeros(nb); Gx = np.zeros(nb)
        for t in range(T):
            if blk[t] >= 0:
                Gs[blk[t]] += np.log1p(s[t]); Gx[blk[t]] += np.log1p(x[t])
        pk = np.array([picks[k] for k in ks]); truth = (Gx > Gs).astype(int)
        hit = np.mean(pk == truth); n = nb; se = np.sqrt(hit * (1 - hit) / n)
        gain = np.where(pk == 1, Gx - Gs, 0.0)
        # switch cost variant: 0.3% per side when the pick changes (2 sides = 0.6%)
        chg = np.r_[pk[0] != 0, pk[1:] != pk[:-1]]
        gain_c = gain - chg * 2 * 0.003
        out[(X, rule)] = dict(n=n, hit=hit, hit_defl=hit - 2 * se * np.sqrt(1 + np.log(NC)), base=np.mean(truth == 0), sw=np.mean(pk == 1),
                              gain=gain.mean(), t=gain.mean() / (gain.std(ddof=1) / np.sqrt(n)), gain_swcost=gain_c.mean(),
                              picks=pk)
    return out, ks


rows = []
for bn in ['real_ndx_86_14', 'real_spx_55_85']:
    base, ks = run(bn)
    cst, _ = run(bn, s085_cost=0.003)
    for (X, rule), v in base.items():
        st = STORED['%s|%s|%s' % (bn, X, rule)]
        print('%-15s %-12s %-6s mine: n %d hit %.4f defl %.4f base %.4f sw %.4f gain %+.5f t %+.3f | stored: n %d hit %.4f defl %.4f base %.4f sw %.4f gain %+.5f t %+.3f'
              % (bn, X, rule, v['n'], v['hit'], v['hit_defl'], v['base'], v['sw'], v['gain'], v['t'],
                 st['n'], st['hit'], st['hit_defl'], st['base_s085'], st['frac_switch'], st['gain_mean'], st['gain_t']))
        c = cst[(X, rule)]
        print('      variant s0.85 sleeve WITH its 0.3%% level-change cost: hit %.4f gain %+.5f t %+.3f ; with 0.6%% round-trip switch cost: gain %+.5f'
              % (c['hit'], c['gain'], c['t'], v['gain_swcost']))
    # look-ahead perturbation: scramble all returns after day j; picks at block starts <= j must not change
    for j in [ks[40], ks[150], ks[300]]:
        pert, _ = run(bn, perturb_at=j, seed=j)
        for key in base:
            a = base[key]['picks']; b = pert[key]['picks']; m = np.array(ks) <= j
            assert np.array_equal(a[m], b[m]), ('LOOK-AHEAD', bn, key, j)
    print('  perturbation test passed (picks at k <= j unchanged when data after j scrambled) for', bn)
