"""BT1 one-time confirmation + MS1 + G1 for the frozen top-20 (PRECOMMIT_BT1 sec.3-4, ADDENDUM_BT1_1 sec.3).
Same computations as m1_confirm / m1_ms1, generalized to the 5 rule forms (bt1_path.one_path).
G1 signal (fixed before confirmation): long = the decided product is the rule's top tier (c1) or the rule is inactive (1x)."""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt1_mega as BM, bt1_path as BP, m1_search as SE, m1_confirm as CF, m1_ms1 as MM
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code'); import gate
SCR = BM.SCR
PER = CF.PER


def rule_daily(E, A, row, e):
    X = E[e]['X']; dec, act, g = BP.one_path(A[e], X, row)
    lg = g + np.log1p(X[2])
    return pd.DataFrame(dict(dec=dec, act=act, g=g, lg=lg), index=E[e]['dates'])


def confirm(listfile, key, outname, N, E, A, s85):
    top = json.load(open(SCR + listfile))[key]; rows = []
    for rk, t in enumerate(top):
        row = t['row']; df = {e: rule_daily(E, A, row, e) for e in ('spx', 'ndx')}
        r = dict(rank=rk + 1, id=t['id'], rule=t['rule'], row=row)
        for p, (e, a, b) in PER.items():
            x = df[e].loc[a:b]; full = df[e]['act'].shift(3).fillna(0).loc[a:b]; na = float(full.sum())
            r[p + '_adv_all'] = float(x['g'].mean() * 252); r[p + '_adv_active'] = float(x['g'].sum() / max(na, 1) * 252)
            r[p + '_active_share'] = float(na / len(x))
            s = s85[e].reindex(x.index); ok = s.notna()
            r[p + '_d_vs_s085'] = float((x['lg'][ok] - s[ok]).mean() * 252)
            r[p + '_ann_logret'] = float(x['lg'].mean() * 252)
        disc_d = (r['spx_disc_d_vs_s085'] * 372 + r['ndx_disc_d_vs_s085'] * 168) / 540
        r['disc_d_vs_s085'] = disc_d
        r['conf_beats_1x'] = bool(r['ndx_conf_adv_all'] > 0)
        r['conf_pass_iii'] = bool(r['ndx_conf_d_vs_s085'] > 0 and r['ndx_conf_d_vs_s085'] >= 0.5 * disc_d and disc_d > 0)
        on = int(row[11])
        sg = {e: (df[e]['dec'] == on) | (df[e]['act'] == 0) for e in ('spx', 'ndx')}
        sig = pd.concat([sg['spx'][sg['spx'].index < '1986-01-01'], sg['ndx'][sg['ndx'].index >= '1986-01-01']])
        g = gate.test(sig.astype(bool), trials=N, name=str(t['id']), verbose=False)
        r['g1'] = {k: (dict(hit=v['hit'], always=v['always_up'], hit_defl=v['hit_deflated']) if isinstance(v, dict) else v)
                   for k, v in g.items() if k in ('ndx_86_14', 'spx_55_85', 'verdict')}
        rows.append(r)
        print(rk + 1, t['rule'][:110], '| ndx86-99 adv %.3f -> 00-14 adv %.3f | d85 disc %.3f conf %.3f | G1 %s %.3f' % (
            r['ndx_disc_adv_all'], r['ndx_conf_adv_all'], disc_d, r['ndx_conf_d_vs_s085'], r['g1']['verdict'], r['g1']['ndx_86_14']['hit_defl']), flush=True)
    json.dump(dict(rows=rows, note='one-time confirmation of ' + listfile), open(SCR + outname, 'w'), indent=1, default=float)
    return rows


def measure(row, label, E, A):
    srv = MM.ms1._Server()
    df = {e: rule_daily(E, A, row, e) for e in ('spx', 'ndx')}
    dec = pd.concat([df['spx']['dec'][df['spx'].index < '1985-01-02'], df['ndx']['dec']])
    codes = sorted(set(BP.codes(row) + [2]))
    out = dict(label=label, row=list(map(int, row)), real=MM.real_rows(srv, dec, codes))
    x = df['ndx'].loc['1986-01-02':'2014-12-31']; rule_ret = np.expm1(x['lg'].values)
    s85 = CF.s085_logret()['ndx'].loc['1986-01-02':'2014-12-31']; s85_ret = np.expm1(s85.values)
    P = MM.stream_paths(srv, x.index, rule_ret); Q = MM.stream_paths(srv, s85.index, s85_ret)
    conv = {}
    for bn in MM.ms1.BASES:
        if P[bn] is None or Q[bn] is None: conv[bn] = None; continue
        d = P[bn]['fc'] - Q[bn]['fc']
        conv[bn] = dict(rule_stream=float(np.median(P[bn]['fc'])), s085_stream=float(np.median(Q[bn]['fc'])), d_stream=float(np.median(d)),
                        win=float(np.mean(d > 1e-5)), dd80_rule=float(np.mean(P[bn]['mdd'] <= -0.8)), dd80_s085=float(np.mean(Q[bn]['mdd'] <= -0.8)))
    out['stream'] = conv
    out['representative'] = 0.1616 + conv['dev250_path']['d_stream']
    return out


EXPO = np.array([3, 2, 1, 0, -1]); FROMEXPO = {3: 0, 2: 1, 1: 2, 0: 3, -1: 4}


def bag(rows, label, N, E, A):
    """ADDENDUM_BT1_3: daily median exposure of the given rules, rounded down -> product code; one-time confirmation."""
    import bt1_evaldec as EV
    ev = EV.Evaluator(); dec = {}
    for e in ('spx', 'ndx'):
        M = np.vstack([EXPO[BP.one_path(A[e], E[e]['X'], r)[0]] for r in rows])
        med = np.floor(np.median(M, 0)).astype(int)
        dec[e] = np.array([FROMEXPO[int(v)] for v in med], np.int64)
    d, s = ev.discovery(dec['spx'], dec['ndx'])
    from fc1 import ev_disc_d
    out = dict(label=label, n_rules=len(rows), disc_in_sample=s, disc_d_vs_s085_in_sample=ev_disc_d(ev, dec), conf=ev.confirm(dec['ndx']))
    sg = {e: pd.Series(dec[e] == 0, index=ev.era_dates(e)) for e in ('spx', 'ndx')}
    sig = pd.concat([sg['spx'][sg['spx'].index < '1986-01-01'], sg['ndx'][sg['ndx'].index >= '1986-01-01']])
    g = gate.test(sig.astype(bool), trials=N, name=label, verbose=False)
    out['g1'] = {k: (dict(hit=v['hit'], always=v['always_up'], hit_defl=v['hit_deflated']) if isinstance(v, dict) else v)
                 for k, v in g.items() if k in ('ndx_86_14', 'spx_55_85', 'verdict')}
    out['ms1'] = ev.ms1(dec['spx'], dec['ndx'], label=label)
    print(label, 'conf adv_vs_1x %.4f d_vs_s085 %.4f | G1 %s | MS1 %.4f' % (out['conf']['adv_vs_1x'], out['conf']['d_vs_s085'], out['g1']['verdict'], out['ms1']['representative']), flush=True)
    return out


def main(n_total=None):
    S = json.load(open(SCR + 'out/search.json')); N = int(n_total) if n_total else S['N_generated']   # G1 trials = all lanes
    E = SE.era_inputs(); A = {e: np.ascontiguousarray(np.load(BM.SCR + 'cache/atoms_%s.npy' % e)) for e in ('spx', 'ndx')}
    s85 = CF.s085_logret()
    print('== PRIMARY top-20 (pre-registered ranking) ==', flush=True)
    P = confirm('out/top20_frozen.json', 'top20', 'out/confirm.json', N, E, A, s85)
    print('== SECONDARY top-20 by t ==', flush=True)
    Q = confirm('out/top20t_frozen.json', 'top20_t', 'out/confirm_t.json', N, E, A, s85)
    # MS1: discovery #1 (failure reference) + the best confirmed rule of each list by confirmation d vs s0.85
    res = {}
    res['disc1'] = measure(P[0]['row'], 'discovery #1: ' + P[0]['rule'], E, A)
    bp = max(P, key=lambda r: r['ndx_conf_d_vs_s085']); res['best_conf_primary'] = measure(bp['row'], 'best confirmation (primary): ' + bp['rule'], E, A)
    bq = max(Q, key=lambda r: r['ndx_conf_d_vs_s085']); res['best_conf_t'] = measure(bq['row'], 'best confirmation (t list): ' + bq['rule'], E, A)
    json.dump(res, open(SCR + 'out/ms1_final.json', 'w'), indent=1, default=float)
    # ADDENDUM_BT1_3 ensembles (N counts +2 bag trials)
    bg = dict(BAG50=bag([t['row'] for t in S['top50'][:50]], 'BAG50', N + 2, E, A),
              BAGT20=bag([t['row'] for t in S['top20_by_t'][:20]], 'BAGT20', N + 2, E, A))
    json.dump(bg, open(SCR + 'out/bag_final.json', 'w'), indent=1, default=float)
    for k, v in res.items():
        print(k, 'MS1 representative %.4f' % v['representative'], {bn: round(x['cagr'], 4) for bn, x in v['real'].items()}, v['label'][:120])


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
