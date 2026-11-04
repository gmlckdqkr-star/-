"""N2 S&P 500 deletion rebound (DEL60, DEL120) and addition control (ADD60). Calendar-time EW sleeve, 1x long-only.
Entry: decision at close of first non-member (or first member) day, executed 2 days later (close). Exit at entry+H close.
Costs 0.3%/side on traded weight; dividend tax 15.4% of divy on held weight; yearly 22% tax on positive sleeve gain (no deduction).
Delisting in hold: lab rule (250d ret to last price < -30% -> -50%, else 0). Stress S: exits with no price after deletion and r250<-30% are bought at -50%."""
import numpy as np, pandas as pd, json, sys
from common import *
z = np.load('/tmp/claude-0/fx/panel.npz', allow_pickle=True)
dates = pd.to_datetime(z['dates'], unit='D'); T = len(dates)
mem = np.unpackbits(z['member'], axis=0)[:T].astype(bool); adj = z['adj'].astype(np.float64); divy = np.nan_to_num(z['divy'].astype(np.float64))
r = np.full_like(adj, np.nan); r[1:] = adj[1:] / adj[:-1] - 1
# rf by date (NDX calendar 1984+, SPX calendar before)
R, M = jp.calendar('1984-01-03', '2014-12-31'); rfa = jp.mkX(R, M, 'NDX')['rf']
R, M = jp.calendar('1928-01-03', '1985-12-31'); rfb = jp.mkX(R, M, 'SPX')['rf']
rf = pd.concat([rfb[rfb.index < rfa.index[0]], rfa]).reindex(dates).ffill().fillna(0).values
EW = np.nanmean(np.where(mem[:-1], r[1:], np.nan), axis=1); EW = np.r_[0, np.nan_to_num(EW)]   # PIT EW member index return (t-1 member)

def last_valid(j):
    f = np.nonzero(np.isfinite(adj[:, j]))[0]; return f[-1] if len(f) else -1

def events(kind):
    if kind == 'DEL': t, j = np.nonzero(mem[:-1] & ~mem[1:])
    else: t, j = np.nonzero(~mem[:-1] & mem[1:])
    return [(tt + 1, jj) for tt, jj in zip(t, j) if dates[tt + 1].year >= 1970]

def sleeve(kind, H, stress=False, clip=None, drop=()):
    W = np.zeros((T,)); ret = np.zeros(T); n_act = np.zeros(T); cost = np.zeros(T); dtax = np.zeros(T)
    pos = []   # (entry_idx, exit_idx, j, forced_ret_on_last)
    nev = 0; car = []
    for t0, j in events(kind):
        if (t0, j) in drop: continue
        e = t0 + 2
        if e >= T: continue
        lv = last_valid(j)
        if not np.isfinite(adj[e, j]):
            if stress and kind == 'DEL' and lv >= 0 and lv <= t0 + 1:
                a = adj[max(lv - 250, 0), j]
                if np.isfinite(a) and adj[lv, j] / a - 1 < -0.3: pos.append((min(e, T - 1), min(e + 1, T - 1), j, -0.5)); nev += 1
            continue
        x = min(e + H, T - 1); forced = None
        if lv < x:   # delisted inside hold
            a = adj[max(lv - 250, 0), j]; forced = -0.5 if (np.isfinite(a) and adj[lv, j] / a - 1 < -0.3) else 0.0; x = lv + 1 if lv + 1 < T else lv
        pos.append((e, x, j, forced)); nev += 1
        rr = np.nan_to_num(r[e + 1:x + 1, j]); car.append(np.prod(1 + rr) * (1 + (forced or 0)) - np.prod(1 + EW[e + 1:x + 1]))
    # calendar-time EW of active positions: active on day d if e < d <= x
    act = [[] for _ in range(T)]; ent = np.zeros(T); exi = np.zeros(T)
    for (e, x, j, f) in pos:
        for d in range(e + 1, x + 1): act[d].append((j, f if d == x else None, x))
        ent[e] += 1; exi[x] += 1
    for d in range(T):
        A = act[d]
        if not A: ret[d] = rf[d]; continue
        vals = []
        for (j, f, x) in A:
            v = r[d, j] if np.isfinite(r[d, j]) else 0.0
            if clip is not None and abs(v) > clip: v = 0.0   # suspect print (data error) -> 0
            if f is not None and not np.isfinite(adj[d, j]): v = f   # day after last price: forced delisting return
            elif f is not None: v = (1 + v) * (1 + f) - 1 if not np.isfinite(adj[min(d + 1, T - 1), j]) and d == x else v
            vals.append(v); dtax[d] += 0.154 * divy[d, j] / len(A)
        ret[d] = np.mean(vals); n_act[d] = len(A)
    nprev = np.r_[0, n_act[:-1]]
    for d in range(T):   # traded weight: entries at close d weigh 1/n(d+1), exits at close d weigh 1/n(d)
        we = ent[d] / max(n_act[min(d + 1, T - 1)], 1); wx = exi[d] / max(n_act[d], 1); cost[d] = 0.003 * (we + wx)
    net = ret - cost - dtax
    return dict(net=net, gross=ret, n_act=n_act, nev=nev, car=np.array(car))

def taxed_curve(net, idx):
    """yearly 22% on positive calendar-year gain, final liquidation tax on remaining unrealized (approx: none left since yearly MTM)"""
    E = 1.0; yr = None; start = 1.0; out = []
    for d in idx:
        y = dates[d].year
        if yr is not None and y != yr:
            g = E - start; E -= 0.22 * max(g, 0); start = E
        yr = y; E *= 1 + net[d]; out.append(E)
    g = E - start; E -= 0.22 * max(g, 0); out[-1] = E
    return np.array(out)

def stats(S, a, b, lab):
    idx = np.nonzero((dates >= a) & (dates <= b))[0]; n = S['net'][idx]; ex = n - rf[idx]
    yrs = len(idx) / 252; Ec = taxed_curve(S['net'], idx)
    o = dict(lab=lab, nev=S['nev'], car_mean=float(np.mean(S['car'])), car_med=float(np.median(S['car'])),
             frac_invested=float(np.mean(S['n_act'][idx] > 0)), avg_names=float(np.mean(S['n_act'][idx][S['n_act'][idx] > 0])),
             sharpe_aftercost=float(ex.mean() / ex.std() * np.sqrt(252)), cagr_pretax=float(np.prod(1 + n) ** (1 / yrs) - 1),
             cagr_aftertax=float(Ec[-1] ** (1 / yrs) - 1), mdd=float((Ec / np.maximum.accumulate(Ec) - 1).min()))
    print(' '.join('%s=%s' % (k, ('%.4f' % v) if isinstance(v, float) else v) for k, v in o.items()), flush=True); return o

if __name__ == '__main__':
    res = {}; streams = {}
    for kind, H, st_ in (('DEL', 60, False), ('DEL', 120, False), ('ADD', 60, False), ('DEL', 60, True), ('DEL', 120, True)):
        nm = '%s%d%s' % (kind, H, 'S' if st_ else ''); S = sleeve(kind, H, st_); streams[nm] = S['net']
        res[nm] = [stats(S, '1986-01-02', '2014-12-31', nm + ' 86-14'), stats(S, '1971-01-04', '1985-12-31', nm + ' 71-85')]
    # robustness (conservative checks, not new trials): suspect daily prints |r|>50% set to 0; drop top-5 CAR events (winner removal)
    for H in (60, 120):
        base = sleeve('DEL', H); ev = [(t0, j) for t0, j in events('DEL') if t0 + 2 < T and np.isfinite(adj[t0 + 2, j])]
        top = set(ev[k] for k in np.argsort(-base['car'])[:5])
        for nm, S in (('DEL%d_clip50' % H, sleeve('DEL', H, clip=0.5)), ('DEL%d_drop5' % H, sleeve('DEL', H, drop=top)),
                      ('DEL%d_clip50_drop5' % H, sleeve('DEL', H, clip=0.5, drop=top))):
            streams[nm] = S['net']; res[nm] = [stats(S, '1986-01-02', '2014-12-31', nm + ' 86-14'), stats(S, '1971-01-04', '1985-12-31', nm + ' 71-85')]
    ewn = dict(net=EW - 0.0, n_act=np.ones(T), nev=0, car=np.zeros(1)); res['EW'] = [stats(ewn, '1986-01-02', '2014-12-31', 'EW gross 86-14')]
    np.savez(RES + '/n2_streams.npz', dates=z['dates'], rf=rf, **streams)
    json.dump(res, open(RES + '/n2_deletion.json', 'w'), indent=1)
