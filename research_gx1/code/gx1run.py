"""GX1 runs (PRECOMMIT_GX1.md). Stages: c1 (engine reproduction), foreign (18 hosts x 26 rules, placebo-adjusted score,
qualification, top-1, selection-adjusted p, Part B), us <rule id> (one-shot on MS1 bases)."""
import sys, json, math, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/gx1/code'); import gx1lib as G
from gx1lib import std, ov
R = '/mnt/project-files/research/gx1/results/'
MIN_ROWS = 1500; DIV = 0.03; ERA_SPLIT = pd.Timestamp('2006-12-31')
EUROPE_HOSTS = ['UK', 'DE', 'FR', 'CH', 'NL', 'ES', 'IT', 'BE', 'AT', 'IE', 'GR']

def c1():
    ref = dict(real_ndx_86_14=0.3052619999200501, dev250_path=0.1518094564876158, dev250_glued=0.2643632983856852); out = {}
    for bn, (X, F, ii, kind) in G.us_frames().items():
        if bn not in ref: continue
        v, Ev = G.acct(G.us_ctx(X, F, ii, kind)); val = std.row(v, Ev)[0]['cagr']
        out[bn] = dict(value=val, ref=ref[bn], ok=bool(abs(val - ref[bn]) < 1e-6))
    print('C1', out, flush=True); json.dump(out, open(R + 'c1.json', 'w'), indent=1)

def _one(X, F, rows, g=None, mode=None):
    c = ov.Ctx(X, F, rows[None, :]); cg, E = G.acct(c, Ghist=g, mode=mode)
    return float(cg[0]), np.log(E[0])

def _era(Dlog, dates):
    """log-growth difference (rule - v1) accumulated in era 1 (<= 2006) and era 2 (>= 2007) on the scored rows."""
    k = dates.searchsorted(ERA_SPLIT, 'right') - 1
    if k < 0: return [float('nan'), float(Dlog[-1] - Dlog[0])]
    if k >= len(dates) - 1: return [float(Dlog[k] - Dlog[0]), float('nan')]
    return [float(Dlog[k] - Dlog[0]), float(Dlog[-1] - Dlog[k])]

def host_block(h, div, J):
    """all runs for one host: v1, 26 rules, 26 rules x J shifts. Returns d[r], e[r], era_e[r], d_shift[r][j]."""
    X, i0 = G.host(h, div); F = ov.flags_hist(X); n = len(X); rows = np.arange(i0, n)
    D = G.world_signals(X.index, h); dates = X.index[i0 + G.W:]
    v1, lv = _one(X, F, rows)
    res = dict(v1=v1, d=[], e=[], era_e=[], d_shift=[], era_shift=[])
    for rid, (k, th, md) in enumerate(G.RULES):
        g = D['G%02d' % G.SIGNALS.index((k, th))].values.astype(bool)
        a, la = _one(X, F, rows, g, md); d = a - v1; era = _era(la - lv, dates)
        ds, es = [], []
        for j in range(J):
            s = 504 + 63 * j; gs = g.copy(); gs[rows] = g[np.roll(rows, s)]
            b, lb = _one(X, F, rows, gs, md); ds.append(b - v1); es.append(_era(lb - lv, dates))
        ds = np.array(ds); es = np.array(es)
        res['d'].append(d); res['e'].append(d - float(np.median(ds)))
        res['era_e'].append([era[q] - float(np.nanmedian(es[:, q])) if not math.isnan(era[q]) else float('nan') for q in (0, 1)])
        res['d_shift'].append(ds.tolist())
    res['C2_off'] = _one(X, F, rows, np.zeros(n, bool), 'ALARM')[0] - v1
    res['scored_from'] = str(dates[0].date()); res['rows'] = int(len(dates)); res['N_shift_rows'] = int(len(rows))
    res['signal_valid_share'] = {k: float((D['n_' + k].iloc[i0 + G.W:] >= G.MIN_VALID).mean()) for k in ('B200', 'D20', 'N126', 'INV')}
    res['signal_on_share'] = [float(D['G%02d' % i].iloc[i0 + G.W:].mean()) for i in range(13)]
    return res, (X, F, i0, D)

def qualify(H, hs):
    n = len(hs); need = math.ceil(0.6 * n); tab = []
    for rid in range(len(G.RULES)):
        d = np.array([H[h]['d'][rid] for h in hs]); e = np.array([H[h]['e'][rid] for h in hs])
        eu = np.array([H[h]['e'][rid] for h in hs if h in EUROPE_HOSTS]); ne = np.array([H[h]['e'][rid] for h in hs if h not in EUROPE_HOSTS])
        er = np.array([H[h]['era_e'][rid] for h in hs])
        if not (np.isfinite(d).all() and np.isfinite(e).all()): raise SystemExit('NaN in d/e for rule %d' % rid)
        row = dict(id=rid, n=n, d_med=float(np.median(d)), d_pos=int((d > 1e-6).sum()), e_med=float(np.median(e)), e_pos=int((e > 0).sum()),
                   e_med_EU=float(np.median(eu)), e_med_nonEU=float(np.median(ne)),
                   era1_med=float(np.nanmedian(er[:, 0])), era2_med=float(np.nanmedian(er[:, 1])))
        row['qual'] = bool(row['d_pos'] >= need and row['d_med'] >= 0.005 and row['e_pos'] >= need and row['e_med'] >= 0.005
                           and row['e_med_EU'] > 0 and row['e_med_nonEU'] > 0 and row['era1_med'] > 0 and row['era2_med'] > 0)
        tab.append(row)
    return tab

def foreign():
    out = dict(rules=[dict(id=i, signal=k, th=th, mode=md) for i, (k, th, md) in enumerate(G.RULES)], hosts={}, hosts_div={})
    # J from the shortest included host (shift range = rows i0..end, AT2 convention)
    lens = {}
    for h in G.HOSTS:
        X, i0 = G.host(h); lens[h] = (len(X) - i0, len(X) - i0 - G.W)
    hs = [h for h in G.HOSTS if lens[h][1] >= MIN_ROWS]
    out['skipped'] = {h: lens[h][1] for h in G.HOSTS if h not in hs}
    Nmin = min(lens[h][0] for h in hs); J = (Nmin - 1008) // 63 + 1; out['J'] = int(J); out['N_min'] = int(Nmin)
    print('hosts', hs, 'J', J, flush=True)
    H, Hd, keep = {}, {}, {}
    for h in hs:
        H[h], keep[h] = host_block(h, 0.0, J); print(h, H[h]['scored_from'], 'v1 %.4f' % H[h]['v1'], 'C2 %.2e' % H[h]['C2_off'], flush=True)
        Hd[h], _ = host_block(h, DIV, J)
    out['hosts'] = H; out['hosts_div'] = Hd
    at2 = json.load(open('/mnt/project-files/research/at2/results/at2_le2014.json'))
    out['C6_vs_AT2'] = {h: dict(gx1=H[h]['v1'], at2=at2[h]['A']) for h in ('UK', 'CA', 'AU', 'DE', 'FR', 'CH') if h in H}
    print('C6', out['C6_vs_AT2'], flush=True)
    t0 = qualify(H, hs); t1 = qualify(Hd, hs)
    for a, b in zip(t0, t1): a['qual_div'] = b['qual']; a['e_med_div'] = b['e_med']; a['qual_all'] = a['qual'] and b['qual']
    out['table'] = t0; q = [t for t in t0 if t['qual_all']]
    out['qualified'] = [t['id'] for t in q]
    out['selected'] = (sorted(q, key=lambda t: (-round(t['e_med'], 9), t['id']))[0]['id'] if q else None)
    # selection-adjusted p (report only): top median e over 26 rules under each shift j
    top_actual = max(t['e_med'] for t in t0); tops = []
    for j in range(J):
        best = -1e9
        for rid in range(len(G.RULES)):
            ej = [H[h]['d_shift'][rid][j] - float(np.median(H[h]['d_shift'][rid])) for h in hs]; best = max(best, float(np.median(ej)))
        tops.append(best)
    out['selection_adjusted'] = dict(top_e_med_actual=top_actual, null_tops=tops, p=float((1 + sum(t >= top_actual for t in tops)) / (1 + J)))
    print('qualified', out['qualified'], 'selected', out['selected'], 'p_sel', out['selection_adjusted']['p'], flush=True)
    # Part B (report only): v1 alarm truth on 12 new hosts (AT2 method)
    pb = {}
    for h in ['KR', 'NL', 'ES', 'IT', 'BE', 'AT', 'IE', 'GR', 'MX', 'ZA', 'NZ', 'JP']:
        if h not in keep: continue
        X, F, i0, D = keep[h]; n = len(X); rows = np.arange(i0, n); N = len(rows); a = H[h]['v1']; pl = []; s = 504
        while s <= N - 504:
            Fs = F.copy(); Fs.iloc[rows] = F.iloc[np.roll(rows, s)].values; pl.append(_one(X, Fs, rows)[0]); s += 63
        pl = np.array(pl); S = a - float(np.median(pl)); p = (1 + int((pl >= a).sum())) / (1 + len(pl))
        verdict = 'TRANSFERS' if (S >= 0.03 and p <= 0.10) else ('DOES NOT TRANSFER' if (S <= 0 or p >= 0.5) else 'INCONCLUSIVE')
        Fa = F.copy(); Fa['inv'] = True
        pb[h] = dict(A=a, placebo_med=float(np.median(pl)), n_placebo=int(len(pl)), S=S, p=p, verdict=verdict,
                     ALWAYS=_one(X, Fa, rows)[0], HOLD1=float(std.hold(ov.Ctx(X, F, rows[None, :]), 1)[0][0]))
        print('PartB', h, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in pb[h].items()}, flush=True)
    out['partB'] = pb
    json.dump(out, open(R + 'foreign_le2014.json', 'w'), indent=1)

def us(rid):
    k, th, md = G.RULES[rid]; col = 'G%02d' % G.SIGNALS.index((k, th)); out = dict(rule=dict(id=rid, signal=k, th=th, mode=md), bases={})
    for bn, (X, F, ii, kind) in G.us_frames().items():
        D = G.world_signals(X.index, 'US'); gh = D[col].values.astype(bool)
        gp = G.path_world(X.index, ii, 'US') if kind == 'path' else None
        res = {}
        for dl in (None, 3):
            v, Ev = G.acct(G.us_ctx(X, F, ii, kind), delay=dl)
            if kind == 'path': r, Er = G.acct(G.us_ctx(X, F, ii, kind), Gpath=gp[col], mode=md, delay=dl); on = gp[col][:, G.W:]
            else: r, Er = G.acct(G.us_ctx(X, F, ii, kind), Ghist=gh, mode=md, delay=dl); on = gh[ii][:, G.W:]
            fv, f0 = std.row(v, Ev); fr, f1 = std.row(r, Er); d = f1 - f0
            res['delay%s' % (dl or 2)] = dict(v1=fv, rule=fr, d_median=float(np.median(d)), d_win=float(np.mean(d > 1e-5)), signal_on_share=float(on.mean()))
        den = gp['_den'][k][:, G.W:] if kind == 'path' else D['n_' + k].values[ii][:, G.W:]
        res['signal_valid_share'] = float((den >= G.MIN_VALID).mean()); res['valid_markets_median'] = float(np.median(den))
        out['bases'][bn] = res; print(bn, json.dumps(res['delay2'])[:500], flush=True)
    b = out['bases']; p2 = b['dev250_path']['delay2']; r2 = b['real_ndx_86_14']['delay2']
    out['C7_spx_equal'] = {nm: b[nm]['delay2']['rule']['cagr'] == b[nm]['delay2']['v1']['cagr'] for nm in ('real_spx_55_85', 'real_spx_70_85')}
    out['PASS'] = bool(p2['d_median'] >= 0.001 and p2['rule']['cagr'] >= p2['v1']['cagr'] + 0.001 and r2['rule']['cagr'] > r2['v1']['cagr'])
    out['MS1_headline_rule'] = p2['rule']['cagr']; out['reaches_30pct'] = bool(p2['rule']['cagr'] >= 0.30)
    json.dump(out, open(R + 'us_oneshot_le2014.json', 'w'), indent=1); print('C7', out['C7_spx_equal'], 'PASS', out['PASS'], flush=True)

if __name__ == '__main__':
    {'c1': c1, 'foreign': foreign}.get(sys.argv[1], lambda: us(int(sys.argv[2])))()
