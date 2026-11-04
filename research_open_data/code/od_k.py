"""OD-K: KR DART disclosure events -> 20-day returns, doubling rates (PRECOMMIT_OD1.md). <=2014 only."""
import json, glob, re, sys, collections, numpy as np, pandas as pd
SP = '/tmp/claude-0/-home-user--/526214ad-9394-524c-812d-1e7bfe44581c/scratchpad/'
OUT = '/mnt/project-files/research/open_data/results/'
z = np.load(SP + 'kr_panel.npz', allow_pickle=True)
dates = pd.DatetimeIndex(z['dates']); codes = pd.Index(z['codes']); C = z['close']; CR = z['cr']; AMT = z['amt']
with np.errstate(all='ignore'):
    rc = np.vstack([np.full((1, C.shape[1]), np.nan), C[1:] / C[:-1] - 1])
R = np.where(np.abs(CR) <= 15.5, CR / 100, np.where(np.abs(rc) <= .155, rc, 0.0)); R[~np.isfinite(C)] = np.nan
R = np.nan_to_num(R, nan=0.0)   # halted/missing day -> 0
alive = np.isfinite(C); last = np.where(alive.any(0), C.shape[0] - 1 - np.argmax(alive[::-1], 0), -1)
LR = np.cumsum(np.log1p(R), axis=0)   # cumulative log price
amt = np.nan_to_num(AMT, nan=0.0); camt = np.vstack([np.zeros((1, amt.shape[1])), np.cumsum(amt, 0)])
H, COST = 20, 0.0133
def liquid(e, j): return e >= 21 and alive[e, j] and amt[e, j] > 0 and (camt[e, j] - camt[e - 20, j]) / 20 >= 3e8
def outcome(e, j):   # entry close e, exit close e+H; delisted inside window -> remaining value x0.5 (conservative)
    x = min(e + H, C.shape[0] - 1); dl = last[j] < x
    path = np.exp(LR[e + 1:x + 1, j] - LR[e, j]) if not dl else np.exp(LR[e + 1:last[j] + 1, j] - LR[e, j])
    fin = (path[-1] if len(path) else 1.0) * (0.5 if dl else 1.0)
    return fin - 1, (path.max() if len(path) else 1.0) >= 2, fin >= 2, dl
# base: every 5th trading day, all liquid stocks
base = {}; bt = []; bd = []
for e in range(21, len(dates) - H - 1, 5):
    js = [j for j in np.where(alive[e] & (amt[e] > 0))[0] if liquid(e, j)]
    o = [outcome(e, j) for j in js]
    base[e] = np.mean([a[0] for a in o]); bt += [a[1] for a in o]; bd += [a[2] for a in o]
bidx = np.array(sorted(base)); bval = np.array([base[k] for k in bidx])
def base_at(e): return bval[min(np.searchsorted(bidx, e), len(bidx) - 1)]
P_T, P_D = float(np.mean(bt)), float(np.mean(bd))
def norm(nm):
    nm = re.sub(r'^(\[[^\]]*\]\s*)+', '', nm).strip()
    m = re.match(r'^주요사항보고서\((.*)\)$', nm)
    nm = (m.group(1) if m else re.sub(r'\(.*\)$', '', nm)).strip()
    nm = re.sub(r'[ㆍ·\s]', '', nm)
    return '단일판매공급계약체결' if nm in ('단일판매계약체결', '공급계약체결') else nm
ev = []
for f in sorted(glob.glob('/mnt/project-files/research/data/kr_dart/dart_[BI]_*.jsonl')):
    for l in open(f):
        x = json.loads(l); sc = x.get('stock_code', '').strip()
        if not sc or x['report_nm'].startswith('['): continue
        if sc not in codes: continue
        ev.append((norm(x['report_nm']), sc, pd.Timestamp(x['rcept_dt'])))
ev = sorted(set(ev), key=lambda t: t[2])
rows = []
for nm, sc, d in ev:
    j = codes.get_loc(sc); e = dates.searchsorted(d, 'right') - 1 + 2
    if e >= len(dates) - 1 or not liquid(e, j): continue
    r, t2, d2, dl = outcome(e, j)
    rows.append(dict(type=nm, code=sc, d=d, e=e, era='sel' if d.year <= 2008 else 'conf', net=r - COST, ex=r - COST - (base_at(e) - COST), t2=t2, d2=d2, dl=dl))
E = pd.DataFrame(rows)
cnt_sel = E[E.era == 'sel'].type.value_counts(); types = cnt_sel[cnt_sel >= 200].index.tolist()
def st(g):
    n = len(g); m = g.ex.mean(); t = m / (g.ex.std() / n ** .5) if n > 2 else np.nan
    return dict(n=n, ex=round(m, 4), t=round(t, 2), net=round(g.net.mean(), 4), hit=round((g.net > 0).mean(), 3),
                touch2x=round(g.t2.mean(), 4), end2x=round(g.d2.mean(), 4), lift_touch=round(g.t2.mean() / P_T, 2), delist=int(g.dl.sum()))
T = {}
for ty in types:
    T[ty] = {era: st(E[(E.type == ty) & (E.era == era)]) if ((E.type == ty) & (E.era == era)).sum() > 0 else None for era in ('sel', 'conf')}
picked = [ty for ty in types if T[ty]['sel']['ex'] > 0 and T[ty]['sel']['t'] > 2]
confirmed = [ty for ty in picked if T[ty]['conf'] and T[ty]['conf']['ex'] > 0 and T[ty]['conf']['t'] > 2]
# strategy: picked types, max 20 slots, weight 1/20, cash 0
def strat(era_years, tys):
    S = E[E.type.isin(tys)].sort_values(['e', 'type', 'code'], kind='mergesort'); y0, y1 = era_years
    i0, i1 = dates.searchsorted(pd.Timestamp(f'{y0}-01-01')), dates.searchsorted(pd.Timestamp(f'{y1}-12-31'), 'right') - 1
    port = np.zeros(i1 + H + 2); openpos = []
    for _, r in S.iterrows():
        if not (i0 <= r.e <= i1): continue
        openpos = [p for p in openpos if p > r.e]
        if len(openpos) >= 20: continue
        j = codes.get_loc(r.code); x = min(r.e + H, last[j], len(dates) - 1); openpos.append(r.e + H)
        dr = np.expm1(np.diff(LR[r.e:x + 1, j])); port[r.e + 1:x + 1] += dr / 20; port[r.e + 1] -= COST / 2 / 20; port[x] -= COST / 2 / 20
        if last[j] < min(r.e + H, len(dates) - 1): port[x] -= 0.5 * np.exp(LR[x, j] - LR[r.e, j]) / 20
    p = port[i0:i1 + 1]; cagr = np.exp(np.log1p(p).sum() / (len(p) / 250)) - 1
    return dict(sharpe=round(float(p.mean() / p.std() * 250 ** .5), 2) if p.std() > 0 else None, cagr=round(float(cagr), 4), days=len(p))
res = dict(base=dict(touch2x=round(P_T, 4), end2x=round(P_D, 4)), n_events=len(E), types=T, trials=len(types), picked=picked, confirmed=confirmed,
           strat_sel_picked=strat((2001, 2008), picked) if picked else None, strat_conf_picked=strat((2009, 2014), picked) if picked else None,
           double_candidates=[ty for ty in types for era in ('sel',) if T[ty][era]['lift_touch'] >= 3 and T[ty][era]['n'] >= 30])
json.dump(res, open(OUT + 'od_k.json', 'w'), ensure_ascii=False, indent=1, default=str)
print('events', len(E), 'types', len(types), 'base touch2x', P_T, 'end2x', P_D)
for ty in types:
    s, c = T[ty]['sel'], T[ty]['conf']
    print(f"{ty[:28]:28s} sel n{s['n']:5d} ex{s['ex']:+.4f} t{s['t']:+.1f} 2x{s['lift_touch']:.1f} | conf " + (f"n{c['n']:5d} ex{c['ex']:+.4f} t{c['t']:+.1f} 2x{c['lift_touch']:.1f}" if c else '-'))
print('picked', picked); print('confirmed', confirmed); print('strat sel', res['strat_sel_picked'], 'conf', res['strat_conf_picked']); print('2x cand', res['double_candidates'])

# --- diagnostics (added after main run; hindsight rows labelled) ---
print('base EW 20d mean net (sel/conf):', round(float(np.mean([base_at(e) for e in E[E.era=='sel'].e]) - COST), 4), round(float(np.mean([base_at(e) for e in E[E.era=='conf'].e]) - COST), 4))
for ty in confirmed: print(ty, T[ty])
diag = dict(strat_conf_confirmedonly_HINDSIGHT=strat((2009, 2014), confirmed), strat_sel_confirmedonly_HINDSIGHT=strat((2001, 2008), confirmed),
            picked_events_conf=int(E[(E.type.isin(picked)) & (E.era == 'conf')].shape[0]), picked_net_mean_conf=round(float(E[(E.type.isin(picked)) & (E.era == 'conf')].net.mean()), 4),
            picked_ex_mean_conf=round(float(E[(E.type.isin(picked)) & (E.era == 'conf')].ex.mean()), 4))
print(diag); res['diag'] = diag; json.dump(res, open(OUT + 'od_k.json', 'w'), ensure_ascii=False, indent=1, default=str)
