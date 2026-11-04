"""SL1 one-time confirmation (PRECOMMIT_SL1 sec.3): both frozen top-20 lists -> 2000-2014 NDX vs 1x and vs s0.85,
condition (iii), G1 (signal = c1 decided or inactive, trials = n_total), MS1 stream representative (rule 1986-2014 daily
stream vs s0.85 stream, same dev250 paths, turnover 1) for discovery #1 and the best confirmation of each list."""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt1_mega as BM, bt1_path as BP, sl1_mega as SL, m1_confirm as CF, m1_ms1 as MM
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code'); import gate
SCR = BM.SCR
PER = {'spx_disc': ('spx', '1971-01-04', '1985-12-31'), 'ndx_disc': ('ndx', '1986-01-02', '1999-12-31'), 'ndx_conf': ('ndx', '2000-01-03', '2014-12-31')}


class Ctx:
    def __init__(self):
        self.E = SL.MS.era_inputs(); self.names, self.X = SL.products(self.E); self.CC = SL.costc(SL.NIDX + len(self.names))
        A = {e: np.load(SCR + 'cache/atoms_%s.npy' % e, mmap_mode='r') for e in ('spx', 'ndx')}
        s0 = int(self.E['spx']['dates'].searchsorted(pd.Timestamp(SL.SPX_START)))   # ADDENDUM_SL1_B: same state start as the screen
        self.s0 = s0; self.dates = {'spx': self.E['spx']['dates'][s0:], 'ndx': self.E['ndx']['dates']}
        self.A = {'spx': np.ascontiguousarray(A['spx'][:, s0:]), 'ndx': np.ascontiguousarray(A['ndx'])}
        self.X = {'spx': np.ascontiguousarray(self.X['spx'][:, s0:]), 'ndx': self.X['ndx']}
        self.LX = {e: BM.logx(self.X[e]) for e in ('spx', 'ndx')}
        self.s85 = CF.s085_logret()


def rule_daily(c, row, e):
    dec, act, g = BP._one(c.A[e], c.LX[e], np.asarray(row, np.int32), c.A[e].shape[1], c.CC)
    lg = g + np.log1p(c.X[e][2])
    return pd.DataFrame(dict(dec=dec, act=act, g=g, lg=lg), index=c.dates[e])


def ms1_stream(c, row, label):
    srv = MM.ms1._Server(); x = rule_daily(c, row, 'ndx').loc['1986-01-02':'2014-12-31']
    s85 = c.s85['ndx'].loc['1986-01-02':'2014-12-31']
    P = MM.stream_paths(srv, x.index, np.expm1(x['lg'].values)); Q = MM.stream_paths(srv, s85.index, np.expm1(s85.values))
    conv = {}
    for bn in MM.ms1.BASES:
        if P[bn] is None or Q[bn] is None: conv[bn] = None; continue
        d = P[bn]['fc'] - Q[bn]['fc']
        conv[bn] = dict(rule_stream=float(np.median(P[bn]['fc'])), s085_stream=float(np.median(Q[bn]['fc'])), d_stream=float(np.median(d)),
                        win=float(np.mean(d > 1e-5)), dd80_rule=float(np.mean(P[bn]['mdd'] <= -0.8)), dd80_s085=float(np.mean(Q[bn]['mdd'] <= -0.8)))
    return dict(label=label, row=list(map(int, row)), stream=conv, representative=0.1616 + conv['dev250_path']['d_stream'])


def confirm(c, listfile, key, outname, N):
    top = json.load(open(SCR + listfile))[key]; rows = []
    for rk, t in enumerate(top):
        row = t['row']; df = {e: rule_daily(c, row, e) for e in ('spx', 'ndx')}
        r = dict(rank=rk + 1, id=t['id'], rule=t['rule'], row=row)
        for p, (e, a, b) in PER.items():
            x = df[e].loc[a:b]; s = c.s85[e].reindex(x.index); ok = s.notna()
            r[p + '_adv_all'] = float(x['g'].mean() * 252); r[p + '_d_vs_s085'] = float((x['lg'][ok] - s[ok]).mean() * 252)
            r[p + '_ann_logret'] = float(x['lg'].mean() * 252)
        disc_d = (r['spx_disc_d_vs_s085'] * 180 + r['ndx_disc_d_vs_s085'] * 168) / 348; r['disc_d_vs_s085'] = disc_d
        r['conf_beats_1x'] = bool(r['ndx_conf_adv_all'] > 0)
        r['conf_pass_iii'] = bool(r['ndx_conf_d_vs_s085'] > 0 and r['ndx_conf_d_vs_s085'] >= 0.5 * disc_d and disc_d > 0)
        on = int(row[11]); sg = {e: (df[e]['dec'] == on) | (df[e]['act'] == 0) for e in ('spx', 'ndx')}
        sig = pd.concat([sg['spx'][sg['spx'].index < '1986-01-01'], sg['ndx'][sg['ndx'].index >= '1986-01-01']])
        g = gate.test(sig.astype(bool), trials=N, name=str(t['id']), verbose=False)
        r['g1'] = {k: (dict(hit=v['hit'], always=v['always_up'], hit_defl=v['hit_deflated']) if isinstance(v, dict) else v)
                   for k, v in g.items() if k in ('ndx_86_14', 'spx_55_85', 'verdict')}
        rows.append(r)
        print(rk + 1, t['rule'][:120], '| ndx86-99 adv %.3f -> 00-14 adv %.3f | d85 disc %.3f conf %.3f | G1 %s' % (
            r['ndx_disc_adv_all'], r['ndx_conf_adv_all'], disc_d, r['ndx_conf_d_vs_s085'], r['g1']['verdict']), flush=True)
    json.dump(dict(rows=rows, note='SL1 one-time confirmation of ' + listfile), open(SCR + outname, 'w'), indent=1, default=float)
    return rows


def main(n_total):
    c = Ctx()
    P = confirm(c, 'out/sl1_top20_frozen.json', 'top20', 'out/sl1_confirm.json', n_total)
    Q = confirm(c, 'out/sl1_top20t_frozen.json', 'top20_t', 'out/sl1_confirm_t.json', n_total)
    res = dict(disc1=ms1_stream(c, P[0]['row'], 'SL1 discovery #1: ' + P[0]['rule']))
    bp = max(P, key=lambda r: r['ndx_conf_d_vs_s085']); res['best_conf_primary'] = ms1_stream(c, bp['row'], 'SL1 best confirmation (primary): ' + bp['rule'])
    bq = max(Q, key=lambda r: r['ndx_conf_d_vs_s085']); res['best_conf_t'] = ms1_stream(c, bq['row'], 'SL1 best confirmation (t list): ' + bq['rule'])
    json.dump(res, open(SCR + 'out/sl1_ms1_final.json', 'w'), indent=1, default=float)
    for k, v in res.items(): print(k, 'MS1 stream representative %.4f' % v['representative'], v['label'][:140])


if __name__ == '__main__':
    main(int(sys.argv[1]))
