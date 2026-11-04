"""M1 one-time confirmation (PRECOMMIT_M1 sec.5/7/8): the frozen top-20 (out/top20_frozen.json) on real NDX
2000-01-03..2014-12-31; decay table vs discovery; d vs s0.85 (pre-tax after-cost log growth, s0.85 = std.engine tax 0 on
the real paths); G1 (gate.test, trials = N generated) computed only now. Run once."""
import os, sys, json, numpy as np, pandas as pd
SCR = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m1/'
os.environ['NUMBA_CACHE_DIR'] = SCR + 'nb'
sys.path.insert(0, SCR + 'code')
import m1_engine as EN, m1_search as SE
sys.path.insert(0, '/mnt/project-files/research/measure_std'); sys.path.insert(0, '/mnt/project-files/research/breakthrough/code')
import std, jp, gate

PER = {'spx_disc': ('spx', '1955-01-03', '1985-12-31'), 'ndx_disc': ('ndx', '1986-01-02', '1999-12-31'),
       'ndx_conf': ('ndx', '2000-01-03', '2014-12-31')}


def s085_logret():
    """daily pre-tax after-cost log growth of s0.85 on the real paths, indexed by date."""
    C = std.contexts(); out = {}
    for e, bn, cal in (('spx', 'real_spx_55_85', ('1928-01-03', '1985-12-31')), ('ndx', 'real_ndx_86_14', ('1984-01-03', '2014-12-31'))):
        c = C[bn]; B, bfn, bp, fs = std.s085(c)
        _, EE = std.engine(c, B, bfn, bp, fs, tax=0.0)
        R, M = jp.calendar(*cal); d = R.index[c.ii[0][std.ov.WARM:]]
        lg = np.r_[0.0, np.diff(np.log(EE[0]))]
        out[e] = pd.Series(lg, index=d)
    return out


def rule_daily(E, A, row, e):
    X = E[e]['X']; dec, act, g = EN.one_path(A[e], X, np.asarray(row, np.int64), A[e].shape[1])
    lg = g + np.log1p(X[2])
    return pd.DataFrame(dict(dec=dec, act=act, g=g, lg=lg), index=E[e]['dates'])


def main(listfile='out/top20_frozen.json', key='top20', outname='out/confirm.json'):
    top = json.load(open(SCR + listfile))[key]
    S = json.load(open(SCR + 'out/search.json'))
    E = SE.era_inputs()
    A = {e: np.ascontiguousarray(np.load(SCR + 'cache/atoms_%s.npy' % e)) for e in ('spx', 'ndx')}
    s85 = s085_logret()
    N = S['N_generated']
    rows = []
    for rk, t in enumerate(top):
        row = t['row']
        df = {e: rule_daily(E, A, row, e) for e in ('spx', 'ndx')}
        r = dict(rank=rk + 1, id=t['id'], rule=t['rule'])
        for p, (e, a, b) in PER.items():
            x = df[e].loc[a:b]
            # position earning day i = decision of close i-3: 'active' days = act shifted by 3
            actd = pd.Series(x['act'].values, index=x.index)
            full = df[e]['act'].shift(3).fillna(0).loc[a:b]
            na = float(full.sum())
            r[p + '_adv_all'] = float(x['g'].mean() * 252)
            r[p + '_adv_active'] = float(x['g'].sum() / max(na, 1) * 252)
            r[p + '_active_share'] = float(na / len(x))
            s = s85[e].reindex(x.index)
            ok = s.notna()
            r[p + '_d_vs_s085'] = float((x['lg'][ok] - s[ok]).mean() * 252)
            r[p + '_s085_vs_1x'] = float((s[ok] - np.log1p(E[e]['X'][2][df[e].index.get_indexer(x.index[ok])])).mean() * 252)
            r[p + '_ann_logret'] = float(x['lg'].mean() * 252)
        disc_d = (r['spx_disc_d_vs_s085'] * 372 + r['ndx_disc_d_vs_s085'] * 168) / 540
        r['disc_d_vs_s085'] = disc_d
        r['conf_pass_iii'] = bool(r['ndx_conf_d_vs_s085'] > 0 and r['ndx_conf_d_vs_s085'] >= 0.5 * disc_d and disc_d > 0)
        r['decay_adv_ratio'] = float(r['ndx_conf_adv_all'] / r['ndx_disc_adv_all']) if r['ndx_disc_adv_all'] != 0 else None
        # G1: bullish state = decided product is the rule's 'on' product (inactive 1x -> long = True)
        on = int(row[4])
        sig_spx = (df['spx']['dec'] == on) | (df['spx']['act'] == 0)
        sig_ndx = (df['ndx']['dec'] == on) | (df['ndx']['act'] == 0)
        sig = pd.concat([sig_spx[sig_spx.index < '1986-01-01'], sig_ndx[sig_ndx.index >= '1986-01-01']])
        g = gate.test(sig.astype(bool), trials=N, name=str(t['id']), verbose=False)
        r['g1'] = {k: (dict(hit=v['hit'], always=v['always_up'], hit_defl=v['hit_deflated']) if isinstance(v, dict) else v)
                   for k, v in g.items() if k in ('ndx_86_14', 'spx_55_85', 'verdict')}
        rows.append(r)
        print(rk + 1, t['rule'][:120], '| disc adv(active) %.3f ndx86-99 adv %.3f -> conf00-14 adv %.3f | d85 disc %.3f ndx86-99 %.3f conf %.3f | G1 %s %.3f/%.3f' % (
            t['adv_active'], r['ndx_disc_adv_all'], r['ndx_conf_adv_all'], disc_d, r['ndx_disc_d_vs_s085'], r['ndx_conf_d_vs_s085'], r['g1']['verdict'],
            r['g1']['ndx_86_14']['hit'], r['g1']['spx_55_85']['hit'] if r['g1']['spx_55_85'] else float('nan')), flush=True)
    json.dump(dict(rows=rows, note='one-time confirmation of ' + listfile), open(SCR + outname, 'w'), indent=1)


if __name__ == '__main__':
    print('== PRIMARY (pre-registered ranking) top-20 ==', flush=True)
    main()
    print('== SECONDARY (ADDENDUM_M1_1: top-20 by SPA t) ==', flush=True)
    main('out/top20t_frozen.json', 'top20_t', 'out/confirm_t.json')
