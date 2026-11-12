"""JS1 builder (PRECOMMIT_JS1.md): JST R6 annual panel (<=2014) -> atoms, observations, outcomes. No association with returns is computed here."""
import numpy as np, pandas as pd, sys, hashlib
D0 = '/home/user/repo/research_js1/data/JSTdatasetR6.dta'
CTRY = ['Australia', 'Belgium', 'Denmark', 'Finland', 'France', 'Germany', 'Italy', 'Japan', 'Netherlands', 'Norway', 'Portugal',
        'Spain', 'Sweden', 'Switzerland', 'UK', 'USA']
Y0, Y1 = 1870, 2014; YRS = np.arange(Y0, Y1 + 1); NY = len(YRS); NC = len(CTRY)
QS = (.1, .2, .3, .5, .7, .8, .9); MINPCT = 20
DESIGN = (1871, 1985); CONFIRM = (1986, 2014)            # RETURN years; features use data through the year before

def load():
    d = pd.read_stata(D0); d = d[(d.year <= Y1) & (d.country.isin(CTRY))]
    S = {}
    for col in ('eq_tr', 'eq_capgain', 'bill_rate', 'stir', 'ltrate', 'cpi', 'narrowm', 'money', 'tloans', 'tmort', 'thh', 'tbus', 'hpnom',
                'gdp', 'wage', 'eq_dp', 'iy', 'debtgdp', 'unemp'):
        a = np.full((NC, NY), np.nan)
        for i, c in enumerate(CTRY):
            s = d[d.country == c].set_index('year')[col].astype(float); a[i, s.index.values - Y0] = s.values
        S[col] = a
    return S

def lag(x, k):
    o = np.full_like(x, np.nan); o[:, k:] = x[:, :-k]; return o

def logg(x, k):
    with np.errstate(divide='ignore', invalid='ignore'):
        l = np.where(x > 0, np.log(np.where(x > 0, x, 1)), np.nan)
    return l - lag(l, k)

def diff(x, k): return x - lag(x, k)

def exp_pct(x, minn=MINPCT):
    """expanding percentile of x[...,t] among x[...,s<=t] (valid only), NaN if fewer than minn valid so far or x_t invalid (causal)."""
    sh = x.shape; x2 = x.reshape(-1, sh[-1]); out = np.full_like(x2, np.nan)
    for r in range(x2.shape[0]):
        v = x2[r]
        for t in range(sh[-1]):
            if np.isnan(v[t]): continue
            h = v[:t + 1]; h = h[~np.isnan(h)]
            if len(h) < minn: continue
            out[r, t] = ((h < v[t]).sum() + 0.5 * (h == v[t]).sum()) / len(h)
    return out.reshape(sh)

def features(S):
    F = {}; lv = {k: S[k] for k in ('cpi', 'narrowm', 'money', 'tloans', 'tmort', 'thh', 'tbus', 'hpnom', 'gdp', 'wage')}
    EQ = np.full((NC, NY), np.nan)
    for i in range(NC):                                    # cumulative total-return index from first valid year (return in year t = eq_tr[t])
        r = S['eq_tr'][i]; idx = np.nan; 
        for t in range(NY):
            if np.isnan(r[t]): idx = np.nan if np.isnan(idx) else idx; EQ[i, t] = idx; continue
            idx = (1.0 if np.isnan(idx) else idx) * (1 + r[t]); EQ[i, t] = idx
    lv['EQ'] = EQ
    for s, x in lv.items():
        for k in (1, 3, 5): F['g%d_%s' % (k, s)] = logg(x, k)
    for s in ('tloans', 'tmort', 'thh', 'tbus'):
        with np.errstate(divide='ignore', invalid='ignore'): q = S[s] / S['gdp']
        F['q_' + s] = q
        for k in (1, 3, 5): F['dq%d_%s' % (k, s)] = diff(q, k)
    F['xc3_loans'] = F['g3_tloans'] - F['g3_gdp']; F['rhp3'] = F['g3_hpnom'] - F['g3_cpi']; F['rhp5'] = F['g5_hpnom'] - F['g5_cpi']
    F['rmo3'] = F['g3_money'] - F['g3_cpi']
    st, lt = S['stir'], S['ltrate']; F['stir'] = st; F['ltrate'] = lt; F['term'] = lt - st
    F['d1_stir'] = diff(st, 1); F['d1_lt'] = diff(lt, 1); F['d1_term'] = diff(F['term'], 1); F['d3_stir'] = diff(st, 3); F['d3_lt'] = diff(lt, 3)
    F['rstir'] = st - 100 * F['g1_cpi']; F['rlt'] = lt - 100 * F['g1_cpi']; F['d1_rstir'] = diff(F['rstir'], 1)
    F['eqdp'] = S['eq_dp']
    F['eqdd'] = EQ / np.fmax.accumulate(np.where(np.isnan(EQ), -np.inf, EQ), axis=1) - 1
    F['eqdd'] = np.where(np.isfinite(F['eqdd']), F['eqdd'], np.nan)
    F['iy'] = S['iy']; F['d3_iy'] = diff(S['iy'], 3); F['debtgdp'] = S['debtgdp']; F['d3_debt'] = diff(S['debtgdp'], 3)
    F['unemp'] = S['unemp']; F['d1_unemp'] = diff(S['unemp'], 1)
    return F

WORLD = ['dq3_tloans', 'dq3_thh', 'rhp3', 'term', 'rstir', 'g3_EQ', 'eqdp', 'd1_lt', 'd1_stir']

def world(F):
    W = {}
    for k in WORLD:
        x = F[k]; n = np.sum(~np.isnan(x), axis=0)
        with np.errstate(invalid='ignore'):
            sm = np.nansum(x, axis=0); m = np.where(n >= 8, sm / np.maximum(n, 1), np.nan)
        W['w_' + k] = m
    tm = F['term']; n = np.sum(~np.isnan(tm), axis=0); inv = np.nansum(np.where(np.isnan(tm), 0, (tm < 0).astype(float)), axis=0)
    W['w_invshare'] = np.where(n >= 8, inv / np.maximum(n, 1), np.nan)
    return W

def build_atoms(F, W):
    names, rows = [], []
    for k in sorted(F):
        p = exp_pct(F[k])
        for q in QS:
            for sg, nm in ((1, '>'), (-1, '<')):
                with np.errstate(invalid='ignore'): a = (p > q) if sg == 1 else (p < q)
                names.append('%s %s q%.1f' % (k, nm, q)); rows.append(np.where(np.isnan(p), False, a))
    for k in sorted(W):
        p = exp_pct(W[k][None, :])[0]
        for q in QS:
            for sg, nm in ((1, '>'), (-1, '<')):
                with np.errstate(invalid='ignore'): a = (p > q) if sg == 1 else (p < q)
                names.append('%s %s q%.1f' % (k, nm, q)); rows.append(np.broadcast_to(np.where(np.isnan(p), False, a), (NC, NY)).copy())
    tm = F['term']; l1 = lag(tm, 1)
    with np.errstate(invalid='ignore'):
        inv0 = tm < 0; inv1 = (tm < 0) | (l1 < 0); sh = F['d1_lt'] >= 1.0
    for nm, a in (('NAT inv0', inv0), ('NAT inv1', inv1), ('NAT shock1', sh)):
        names.append(nm); rows.append(np.where(np.isnan(tm) if nm != 'NAT shock1' else np.isnan(F['d1_lt']), False, a))
    return names, np.array(rows)                        # (A, NC, NY) bool; atom value at (c, t) uses data through year t

def outcomes(S):
    r = np.full((NC, NY), np.nan); b = np.full((NC, NY), np.nan); infl = np.full((NC, NY), np.nan)
    r[:, :-1] = S['eq_tr'][:, 1:]; b[:, :-1] = S['bill_rate'][:, 1:]
    infl[:, :-1] = S['cpi'][:, 1:] / S['cpi'][:, :-1] - 1             # indexed by FEATURE year t: values of return year t+1
    ok = ~(np.isnan(r) | np.isnan(b) | np.isnan(infl)) & (infl <= 0.5)
    x1 = np.log(np.maximum(1e-4, 1 + 3 * r - 2 * b - 0.0245)) - np.log(1 + r - 0.002)       # 3x vs 1x
    x2 = np.log(np.maximum(1e-4, 1 + 3 * r - 2 * b - 0.0245))                                 # 3x vs cash (0 interest)
    x3 = np.log(1 + r - 0.002)                                                                # 1x vs cash
    return ok, np.stack([x1, x2, x3]), r, b

def obs_index(ok, lo, hi):
    """feature years t with return year t+1 in [lo,hi]; list of (c, ti) ordered by country then year."""
    out = []
    for c in range(NC):
        for t in range(NY - 1):
            if lo <= YRS[t] + 1 <= hi and ok[c, t]: out.append((c, t))
    return out

def pack(A, X, obs):
    """pack atoms over obs into uint64 words; each country segment padded to a multiple of 64 bits. Returns bits (A,Wn), x (3,Wn*64) demeaned per
    country, unit word ranges, flips masks (first-in-run bit mask), per-unit weights w_u (3,U)."""
    segs = {}
    for (c, t) in obs: segs.setdefault(c, []).append(t)
    cs = sorted(segs); pos = []; unit_rng = []; w = 0
    slot = []                                         # (c, t, global bit position)
    for c in cs:
        ts = segs[c]; nw = (len(ts) + 63) // 64; unit_rng.append((w, w + nw))
        for j, t in enumerate(ts): slot.append((c, t, w * 64 + j))
        w += nw
    Wn = w; nb = Wn * 64; Aa = A.shape[0]
    bitsarr = np.zeros((Aa, nb), bool); xs = np.zeros((X.shape[0], nb)); valid = np.zeros(nb, bool); first = np.zeros(nb, bool)
    prev = {}
    for (c, t, p) in slot:
        bitsarr[:, p] = A[:, c, t]; xs[:, p] = X[:, c, t]; valid[p] = True
        first[p] = not (c in prev and prev[c][0] == t - 1)   # run start: no flip counted against previous obs
        prev[c] = (t, p)
    bits = np.packbits(bitsarr.reshape(Aa, nb // 8, 8), axis=2, bitorder='little').reshape(Aa, nb // 8)
    xd = np.zeros_like(xs); wu = np.zeros((X.shape[0], len(cs))); n_u = np.zeros(len(cs), int)
    for ui, (a, b_) in enumerate(unit_rng):
        sl = slice(a * 64, b_ * 64); v = valid[sl]; n = int(v.sum()); n_u[ui] = n
        for m in range(X.shape[0]):
            xv = xs[m, sl][v]; mu = xv.mean(); d = np.where(v, xs[m, sl] - mu, 0.0); xd[m, sl] = d
            wu[m, ui] = n / (n - 1) * float((d ** 2).sum()) if n > 1 else 0.0
    return dict(bits=bits, xd=xd, valid=valid, first=first, unit_rng=np.array(unit_rng), wu=wu, n_u=n_u, units=np.array(cs), slot=np.array(slot))

def main(out):
    S = load(); F = features(S); Wd = world(F); names, A = build_atoms(F, Wd); ok, X, r, b = outcomes(S)
    des = obs_index(ok, *DESIGN); con = obs_index(ok, *CONFIRM)
    ond = np.array([A[:, c, t] for (c, t) in des]); keep = (ond.sum(0) >= 40) & (ond.sum(0) <= len(des) - 40)
    sig = {}; uniq = []
    for i in np.where(keep)[0]:
        h = hashlib.md5(np.packbits(ond[:, i]).tobytes()).hexdigest()
        if h in sig: continue
        sig[h] = i; uniq.append(i)
    uniq = np.array(uniq); A2 = A[uniq]; names2 = [names[i] for i in uniq]
    P = {}
    for nm, ob in (('des', des), ('con', con)):
        pk = pack(A2, X, ob)
        for k, v in pk.items(): P['%s_%s' % (nm, k)] = v
    np.savez_compressed(out, names=np.array(names2), A=A2, X=X, ok=ok, r=r, b=b, years=YRS, ctry=np.array(CTRY), **P)
    print('countries', NC, 'atoms before/after filter', len(names), len(names2), 'design obs', len(des), 'confirm obs', len(con))

if __name__ == '__main__': main(sys.argv[1])
