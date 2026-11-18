"""DF5 families (PRECOMMIT_DF5.md section 3): config lists and per-world builders.
Each config: dict(id, fam, track, eng, cat=tuple, num=dict(name -> (index, n_values)), ...params).
build(cfg, ctx) returns an engine job: ('dfe', m_like, Ltg, kw) or ('dfk', ids, W, EV, kw)."""
import itertools, numpy as np
from numba import njit
import df5data as DD, df5sig as SG
WARM = 300
SIGS = ['N', 'T200', 'T200H', 'M252', 'C0', 'D10', 'VOTE', 'TE3', 'ME3', 'Y0T']
FIXED = [1.0, 1.5, 2.0]
VSIG = [0.20, 0.30]; VW = [20, 60]; VLM = [1.5, 2.0]
SIZES = [('F', x) for x in FIXED] + [('V', s, w, lm) for s in VSIG for w in VW for lm in VLM]
ROFFS = ['TBILL', 'B10', 'GOLD', 'DEF3']
REB = 63

def szs(z): return 'F%.1f' % z[1] if z[0] == 'F' else 'V%.2fw%dL%.1f' % (z[1], z[2], z[3])
def size_num(z):
    if z[0] == 'F': return ('F',), {'L': (FIXED.index(z[1]), len(FIXED))}
    return ('V',), {'s': (VSIG.index(z[1]), 2), 'w': (VW.index(z[2]), 2), 'lm': (VLM.index(z[3]), 2)}

def configs(elig):
    C = []
    # A1
    for s, z, ro in itertools.product(SIGS, SIZES, ROFFS):
        if s == 'N' and z == ('F', 1.0): continue
        c0, n0 = size_num(z)
        C.append(dict(id='A1|%s|%s|%s' % (s, szs(z), ro), fam='A1', track='A', eng='dfe', sig=s, size=z, roff=ro, cat=('A1', s, ro) + c0, num=n0))
    # A2
    for s, sg, lm, kn, ro in itertools.product(['N', 'T200', 'VOTE'], VSIG, VLM, ['K1', 'K2'], ['TBILL', 'B10', 'DEF3']):
        z = ('V', sg, 20, lm)
        C.append(dict(id='A2|%s|%s|%s|%s' % (s, szs(z), kn, ro), fam='A2', track='A', eng='dfe', sig=s, size=z, roff=ro, knee=kn,
                      cat=('A2', s, ro), num={'s': (VSIG.index(sg), 2), 'lm': (VLM.index(lm), 2), 'kn': (['K1', 'K2'].index(kn), 2)}))
    # A3
    ES = [1.0, 1.25, 1.5, 2.0]; CS = [0.2, 0.35, 0.5]
    DMIX = {'LTT': ['LTT'], 'B10': ['B10'], 'GOLD': ['GOLD'], 'DEF3': ['DEF3'], 'SPX': ['SPX'], 'VALUE': ['VALUE'],
            'GOLD+LTT': ['GOLD', 'LTT'], 'GOLD+LTT+DEF3': ['GOLD', 'LTT', 'DEF3']}
    for e, c, dm, g in itertools.product(ES, CS, DMIX, ['none', 'T200']):
        a = (e - 1 + c) / 2; b = 1 - c - a
        if b < -1e-12: continue
        C.append(dict(id='A3|e%.2f|c%.2f|%s|%s' % (e, c, dm, g), fam='A3', track='A', eng='dfk', e=e, c=c, dmix=DMIX[dm], gate=g,
                      cat=('A3', dm, g), num={'e': (ES.index(e), 4), 'c': (CS.index(c), 3)}))
    # A4
    for Lx in [1.0, 1.5, 2.0]:
        C.append(dict(id='A4|GEM|L%.1f' % Lx, fam='A4', track='A', eng='dfk', kind='GEM', L=Lx, cat=('A4', 'GEM'), num={'L': ([1.0, 1.5, 2.0].index(Lx), 3)}))
    ucore = ['NDX', 'LTT', 'GOLD', 'DEF3']
    uwide = ['NDX', 'SPX', 'VALUE', 'SMALL', 'MOM', 'SOX', 'DEF3', 'GOLD', 'LTT'] + [x for x in ('DEVX', 'EM', 'CMDTY', 'USD') if elig.get(x)]
    for un, U in (('core', ucore), ('wide', uwide)):
        for k, lb, lv in itertools.product([1, 2, 3], [126, 252], [1.0, 1.5]):
            C.append(dict(id='A4|TOP|%s|k%d|lb%d|L%.1f' % (un, k, lb, lv), fam='A4', track='A', eng='dfk', kind='TOP', U=U, k=k, lb=lb, L=lv,
                          cat=('A4', 'TOP', un), num={'k': (k - 1, 3), 'lb': ([126, 252].index(lb), 2), 'L': ([1.0, 1.5].index(lv), 2)}))
    GS = {'S1': ['NDX', 'LTT', 'GOLD', 'DEF3'], 'S2': ['NDX', 'NDX', 'LTT', 'GOLD'], 'S3': ['NDX', 'SPX', 'LTT', 'GOLD', 'DEF3']}
    for sn, lv in itertools.product(GS, [1.0, 1.5, 2.0]):
        C.append(dict(id='A4|GTAA|%s|L%.1f' % (sn, lv), fam='A4', track='A', eng='dfk', kind='GTAA', U=GS[sn], L=lv,
                      cat=('A4', 'GTAA', sn), num={'L': ([1.0, 1.5, 2.0].index(lv), 3)}))
    # A5 ladder
    UPS = {'U1': (0.25, 0.10), 'U2': (0.50, 0.20), 'U3': (1.00, 0.30), 'U0': None}
    DNS = {'D1': (0.20, 0.30, 0.40), 'D2': (0.25, 0.40, 0.55), 'D0': None}
    for D, up, dn, d0 in itertools.product(['DEF3', 'VALUE', 'TBILL', 'B10', 'GOLD'], UPS, DNS, [0.0, 0.3]):
        if up == 'U0' and d0 == 0.0: continue
        for cf in (['now', 'T200'] if dn != 'D0' else ['-']):
            num = {'d0': ([0.0, 0.3].index(d0), 2)}
            if up != 'U0': num['up'] = (int(up[1]) - 1, 3)
            if dn != 'D0': num['dn'] = (int(dn[1]) - 1, 2)
            C.append(dict(id='A5|%s|%s|%s|%s|d%.1f' % (D, up, dn, cf, d0), fam='A5', track='A', eng='dfk', D=D, up=UPS[up], dn=DNS[dn], cf=cf, d0=d0,
                          cat=('A5', D, up == 'U0', dn == 'D0', cf), num=num))
    # A6
    A6 = {'H55': {'TQQQ': .55, 'TMF': .45}, 'H40': {'TQQQ': .40, 'TMF': .60}, 'N10': {'TQQQ': .30, 'QQQ': .10, 'TMF': .20, 'TBILL': .40},
          'N15': {'TQQQ': .50, 'TMF': .20, 'TBILL': .30}, 'RP': None}
    for nm, g in itertools.product(A6, ['none', 'T200']):
        grp = {'H55': ('H', 0), 'H40': ('H', 1), 'N10': ('N', 0), 'N15': ('N', 1), 'RP': ('R', 0)}[nm]
        C.append(dict(id='A6|%s|%s' % (nm, g), fam='A6', track='A', eng='dfk', mix=A6[nm], name=nm, gate=g,
                      cat=('A6', grp[0], g), num={'v': (grp[1], 2 if grp[0] != 'R' else 1)}))
    # A7 calendar (dfe)
    for nm, hi, lo, ro, tg in (('HAL21', 2.0, 1.0, 'TBILL', False), ('HAL151', 1.5, 1.0, 'TBILL', False), ('HAL20T', 2.0, 0.0, 'TBILL', False),
                               ('HAL20B', 2.0, 0.0, 'B10', False), ('HALT', 2.0, 1.0, 'TBILL', True)):
        num = {'hi': ({'HAL21': 1, 'HAL151': 0}[nm], 2)} if nm in ('HAL21', 'HAL151') else {}
        C.append(dict(id='A7|' + nm, fam='A7', track='A', eng='dfe', hi=hi, lo=lo, roff=ro, tgate=tg, cat=('A7', 'HAL2x' if nm in ('HAL21', 'HAL151') else nm), num=num))
    # A8 recovery leverage (dfe)
    for arm, win, lh, base in itertools.product([0.20, 0.30], [252, 504], [2.0, 3.0], ['T200', 'ONE']):
        C.append(dict(id='A8|a%.2f|w%d|L%.0f|%s' % (arm, win, lh, base), fam='A8', track='A', eng='dfe', arm=arm, win=win, lh=lh, base=base, roff='TBILL',
                      cat=('A8', base), num={'arm': ([0.2, 0.3].index(arm), 2), 'win': ([252, 504].index(win), 2), 'lh': ([2.0, 3.0].index(lh), 2)}))
    # A9 S&P core
    for core, s, Lx in itertools.product(['SPX', 'MIX'], ['N', 'T200', 'VOTE'], [1.5, 2.0, 3.0]):
        C.append(dict(id='A9|%s|%s|L%.1f' % (core, s, Lx), fam='A9', track='A', eng='dfk', core=core, sig=s, L=Lx,
                      cat=('A9', core, s), num={'L': ([1.5, 2.0, 3.0].index(Lx), 3)}))
    # A10 SOX
    for ws, Lx in itertools.product([0.3, 0.5], [1.0, 1.5]):
        C.append(dict(id='A10|sox%.1f|L%.1f' % (ws, Lx), fam='A10', track='A', eng='dfk', ws=ws, L=Lx,
                      cat=('A10',), num={'ws': ([0.3, 0.5].index(ws), 2), 'L': ([1.0, 1.5].index(Lx), 2)}))
    return C

# ------------------------------------------------------------------ helpers
def ev_changes(W, extra=None):
    E = np.zeros(W.shape[:2], bool); E[:, 1:] = np.any(np.abs(W[:, 1:] - W[:, :-1]) > 1e-12, axis=2); E[:, WARM - 1] = True
    if extra is not None: E |= extra
    E[:, :WARM - 1] = False
    return E

def split_ndx(L):
    """vmode-0 split of NDX exposure L (array) into (TQQQ, QQQ, rest)"""
    lo = L <= 1.0
    t3 = np.where(lo, 0.0, (L - 1) / 2); q = np.where(lo, L, 1 - t3); rest = np.where(lo, 1 - L, 0.0)
    return t3, q, rest

def monthly(P, T):
    E = np.zeros((P, T), bool); E[:, WARM - 1::21] = True; return E

def level(a): return np.cumprod(1 + a, axis=1)

@njit(cache=True)
def _ladder(lv, t200, RQ, R2, R3, RD, g, f, upon, th1, th2, th3, dnon, conf, d0, W, EV):
    P, T = lv.shape
    for p in range(P):
        w = np.zeros(4); w[0] = 1.0 - d0; w[3] = d0
        Rup = lv[p, WARM - 1]; H = lv[p, WARM - 1]
        s = 0; armed = np.zeros(3, np.bool_); epi = False; Hep = 0.0; D0 = 0.0
        for i in range(4): W[p, WARM - 1, i] = w[i]
        EV[p, WARM - 1] = True
        th = np.array([th1, th2, th3])
        for t in range(WARM, T):
            # drift with day-t returns
            g0 = w[0] * (1 + RQ[p, t]); g1 = w[1] * (1 + R2[p, t]); g2 = w[2] * (1 + R3[p, t]); g3 = w[3] * (1 + RD[p, t])
            tot = g0 + g1 + g2 + g3
            if tot <= 0: tot = 1e-300
            w[0] = g0 / tot; w[1] = g1 / tot; w[2] = g2 / tot; w[3] = g3 / tot
            x = lv[p, t]; ev = False
            if x > H: H = x
            if upon and not epi and x >= Rup * (1 + g):
                mv = f * w[0]; w[0] -= mv; w[3] += mv; Rup = x; ev = mv > 0
            if dnon:
                dd = x / H - 1.0
                for j in range(s, 3):
                    if dd <= -th[j]: armed[j] = True
                if armed[0] and not epi:
                    epi = True; Hep = H; D0 = w[3]
                if epi and (conf == 0 or t200[p, t]):
                    while s < 3 and armed[s]:
                        mv = min(D0 / 3.0, w[3])
                        if mv > 0:
                            w[3] -= mv; w[s] += mv; ev = True
                        s += 1
                if epi and x >= Hep:
                    if w[1] > 0 or w[2] > 0: ev = True
                    w[0] += w[1] + w[2]; w[1] = 0.0; w[2] = 0.0
                    s = 0; armed[:] = False; epi = False; Rup = x
            if ev:
                EV[p, t] = True
            for i in range(4): W[p, t, i] = w[i]

@njit(cache=True)
def _vladder(held, RT, RD, g, f, d0, W, EV):
    """v1-core ladder: sleeve s in v1 (TQQQ held/3 + cash), 1-s in D. assets [TQQQ, D]; cash = rest."""
    P, T = held.shape
    for p in range(P):
        s = 1.0 - d0; Vref = 1.0; V = 1.0
        cur = held[p, WARM - 1]
        W[p, WARM - 1, 0] = s * cur / 3.0; W[p, WARM - 1, 1] = 1.0 - s; EV[p, WARM - 1] = True
        wt = s * cur / 3.0; wc = s * (1 - cur / 3.0); wd = 1.0 - s
        for t in range(WARM, T):
            a = wt * (1 + RT[p, t]); c = wc; d = wd * (1 + RD[p, t]); tot = a + c + d
            if tot <= 0: tot = 1e-300
            wt = a / tot; wc = c / tot; wd = d / tot
            sv = wt + wc                                 # v1 sleeve share
            r_sl = (cur / 3.0) * RT[p, t]                 # sleeve return with the held mix
            V *= (1 + r_sl)
            ev = False
            nh = held[p, t]
            if V >= Vref * (1 + g) and sv > 0:
                mv = f * sv; sv -= mv; wd += mv; Vref = V; ev = True
            if nh != cur or ev:
                cur = nh; wt = sv * cur / 3.0; wc = sv * (1 - cur / 3.0); ev = True
            if ev: EV[p, t] = True
            W[p, t, 0] = wt; W[p, t, 1] = wd
