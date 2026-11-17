"""Reviewer diagnostics of the agree package inputs: NaN structure and validity only. No performance figure."""
import sys, json
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import numpy as np, xv1
import t_world; t_world.old()
import agree, cbase as cm
X = xv1.frame(xv1.OLD_END); v = xv1.View(X, xv1.extras(agree.NAMES_LADDER, X.index)); i0 = len(X) - v.T
def d(t): return str(X.index[i0 + int(t)].date())
print('T', v.T, 'WARM', xv1.WARM, 'first view row', d(0), 'first account row', d(xv1.WARM), 'last', d(v.T - 1))
for k in agree.NAMES_LADDER:
    a = v.x[k]; ok = ~np.isnan(a)
    f = int(np.argmax(ok)) if ok.any() else -1
    gaps = int(np.isnan(a[f:]).sum()) if f >= 0 else -1
    print('%-10s first valid row %5d %s  NaN after first valid %d' % (k, f, d(f) if f >= 0 else '-', gaps))
for nm, a in (('r', v.c.r[0]), ('rf', v.c.rf[0]), ('lvl', v.c.lvl[0])):
    print(nm, 'NaN', int(np.isnan(a).sum()))
for w in 'XQ':
    S = agree._core(v, w); val = S['valid']; f = int(np.argmax(val))
    print(w, 'first valid row', f, d(f), 'invalid rows after first valid', int((~val[f:]).sum()))
    for k in ('U', 'sma_rho', 'hi', 'l126', 'l21', 'v20', 'v120'):
        a = S[k]; ok = ~np.isnan(a); print('   ', k, 'first non-NaN', int(np.argmax(ok)), 'NaN after', int(np.isnan(a[int(np.argmax(ok)):]).sum()))
br = cm.breadth(v); ok = ~np.isnan(br); print('breadth first non-NaN', int(np.argmax(ok)), 'NaN after', int(np.isnan(br[int(np.argmax(ok)):]).sum()))
print('ref_target NaN', int(np.isnan(v.ref_target).sum()), 'ref_target distinct on account rows (count of values)', len(np.unique(v.ref_target[xv1.WARM:])))
B = xv1.ref(v)['B']; print('B values', np.unique(B), 'rows B==0', int((B == 0).sum()), 'B==1', int((B == 1).sum()), 'B==3', int((B == 3).sum()))
print('rows ref_target==0 (account rows)', int((v.ref_target[xv1.WARM:] == 0).sum()), 'rows B==0 (account rows)', int((B[xv1.WARM:] == 0).sum()),
      'rows B==0 & ref_target>0', int(((B == 0) & (v.ref_target > 0))[xv1.WARM:].sum()), 'rows B>0 & ref_target==0', int(((B > 0) & (v.ref_target == 0))[xv1.WARM:].sum()))
co = agree._caution_only(v, B); print('caution_only rows', int(co.sum()), 'episodes', int((co[1:] & ~co[:-1]).sum()),
      'caution_only & ref_target<1 rows', int((co & (v.ref_target < 1))[xv1.WARM:].sum()), 'caution_only & ref_target!=1', int((co & (v.ref_target != 1))[xv1.WARM:].sum()))
S6 = np.asarray(v.c.F['shock6m'][0], dtype=bool); print('shock6m rows', int(S6.sum()), 'shock6m & B==1', int((S6 & (B == 1)).sum()), 'shock6m & B==0', int((S6 & (B == 0)).sum()), 'shock6m & B==3', int((S6 & (B == 3)).sum()))

# ---- sensitivity of the breadth flag to the other reading of "French industries before the SPDRs have 200 days":
#      each SPDR against the SMA200 of its OWN closes once it has 200 closes, the French industry against its own SMA200 before
#      (cm.breadth, the shared helper, splices the RETURNS after 200 SPDR rows and takes one SMA200 of the spliced level)
up = np.zeros(v.T); cnt = np.zeros(v.T)
for a, b in cm.SECTORS:
    e = v.x['ret:' + a]; k = v.x['kf:' + b]
    lk = cm.level(k); sk = cm.sma(lk, 200); fk = lk > sk
    ok = ~np.isnan(e); f = int(np.argmax(ok)); le = np.full(v.T, np.nan); le[f - 1] = 1.0; le[f:] = np.cumprod(1 + np.where(ok[f:], e[f:], 0.0))
    se = cm.sma(le, 200); use = ~np.isnan(se)
    flag = np.where(use, le > np.where(use, se, 0.0), fk); okf = use | ~np.isnan(sk)
    up += flag & okf; cnt += okf
alt = np.where(cnt == 9, up / 9, np.nan)
with np.errstate(invalid='ignore'):
    d3 = (br >= 2 / 3 - 1e-12) != (alt >= 2 / 3 - 1e-12)
rows = np.flatnonzero(d3 & ~np.isnan(br) & ~np.isnan(alt))
print('breadth flag (>= 2/3): rows that differ between cm.breadth and the own-SMA reading', len(rows), 'first/last', (d(rows[0]), d(rows[-1])) if len(rows) else None)

# ---- sensitivity counts of reading choices (decision rows only, account rows) --------------------------------------------
W0 = xv1.WARM
def add_B(variant):
    """QQQ-AGREE ADD under another reading. 'pkg' = the package; 'reset' = the lift ends when caution_only ends (a new one needs
    K_Q = 6 on three closes again); 'co3' = caution_only must hold on all three closes of the K_Q = 6 run."""
    S = agree._core(v, 'Q'); c = S['c']; valid = S['valid']; K = sum(c[k].astype(int) for k in c)
    r6 = cm.consec(valid & (K == 6) & (co if variant == 'co3' else True)); l4 = cm.consec(valid & (K <= 4)); st = False; out = B.copy()
    for t in range(v.T):
        if (not valid[t]) or (not c['trend'][t]) or l4[t] >= 3 or (variant == 'reset' and not co[t]): st = False
        elif co[t] and r6[t] >= 3: st = True
        if st and co[t]: out[t] = 2.0
    return out
pk = agree.qqq_agree(v, l_add=2.0)['B']; assert (add_B('pkg') == pk).all()
for nm in ('reset', 'co3'):
    alt = add_B(nm); print('ADD reading', nm, ': account rows whose base level differs from the package', int((alt != pk)[W0:].sum()), 'of', int((pk != B)[W0:].sum()), 'lifted rows')
# AGREE-4 vehicle: class tracked on every valid row (package) against the plain class of the row (no 0.03 margin)
S = agree._core(v, 'X'); cls = agree._vclass(S['v20'], S['valid']); raw = (S['v20'] >= 0.30).astype(int) + (S['v20'] >= 0.45)
o1 = agree.agree4(v); on = (o1['Wt'] != 0).any(axis=1)
print('AGREE-4 B1: ON account rows', int(on[W0:].sum()), 'of them tracked class != plain class', int((on & (cls != raw))[W0:].sum()),
      '| vehicle changes while ON: with margin', int((on[1:] & on[:-1] & (cls[1:] != cls[:-1]))[W0:].sum()), 'without', int((on[1:] & on[:-1] & (raw[1:] != raw[:-1]))[W0:].sum()))
print('AGREE-4 B1: ON account rows by class SOXL/USD/SOXX', [int((on & (cls == k))[W0:].sum()) for k in range(3)])
# how often the overlay can actually hold something: ON rows on which v1 alone wants less than level 3
L = v.ref_target
for nm, kw in (('B1', {}), ('B4', dict(k_on=3)), ('B5', dict(caution_only=True))):
    w = (agree.agree4(v, **kw)['Wt'] != 0).any(axis=1)
    print('AGREE-4', nm, 'weight rows (account)', int(w[W0:].sum()), 'of them v1 level < 3', int((w & (L < 3))[W0:].sum()), 'v1 level <= 1', int((w & (L <= 1))[W0:].sum()), 'v1 level 0', int((w & (L == 0))[W0:].sum()))
# QQQ-AGREE ADD: rows on which the state is ON but the lift is not applied (v1's base is not "1 solely for the caution flag")
Sq = agree._core(v, 'Q'); cq = Sq['c']; vq = Sq['valid']; Kq = sum(cq[k].astype(int) for k in cq)
r6 = cm.consec(vq & (Kq == 6)); l4 = cm.consec(vq & (Kq <= 4)); st = False; state = np.zeros(v.T, dtype=bool)
for t in range(v.T):
    if (not vq[t]) or (not cq['trend'][t]) or l4[t] >= 3: st = False
    elif co[t] and r6[t] >= 3: st = True
    state[t] = st
a = state & ~co
print('ADD: state ON account rows', int(state[W0:].sum()), 'lifted', int((state & co)[W0:].sum()), 'not lifted', int(a[W0:].sum()),
      'of them v1 base 3 / 1 / 0:', int((a & (B == 3))[W0:].sum()), int((a & (B == 1))[W0:].sum()), int((a & (B == 0))[W0:].sum()),
      '| state ON in warm-up rows', int(state[:W0].sum()))
