"""TS2 (round 2) post-2014 rows: USER ONLY. Writes only under research/theory_sim/holdout/r2/ (never memory, never other
threads). Protocol r2/TEST_PROTOCOL_R2.md section 3C:
  US C1-C3 exactly as TS1 (research/theory_sim/test/post2014.py run()), with the TS1 fill-order defect fixed
  (r is zero-filled BEFORE the forward fill of the other columns; in TS1 no interior NaN occurred, so no number changes);
  the 8 confirmation funds from 2015-01-02 (300-day warm-up before) to the panel end, rule vs round-1 L1 vs s0.85 vs holds.
Run: /root/.cache/ts-venv/bin/python -B post2014_r2.py <rule.py> <name> <out.json under holdout/r2/>"""
import sys, os, json, time, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/test'); import harness_r2 as HR  # noqa
sys.path.insert(0, '/mnt/project-files/research/theory_sim/test'); import post2014 as P  # noqa
import harness as H, jp, mkt  # noqa
HO = '/mnt/project-files/research/theory_sim/holdout/r2/'


def ndx_now_fixed(check=True):
    """post2014.ndx_now with r zero-filled before the forward fill (TS1 verifier defect c)"""
    if P._X: return P._X['X'], P._X['A']
    R, M = jp.calendar('1984-01-03', '2026-08-31'); X = jp.mkX(R, M, 'NDX')[['r', 'rf', 'y10', 'y3m', 'cs', 'vix']]
    N = mkt.ndx(); N = N[N.index > X.index[-1]][['r', 'rf', 'y10', 'y3m', 'cs', 'vix']]
    X = pd.concat([X, N]); S = pd.read_csv(P.HO + 'splice_td_20261104.csv', parse_dates=['date']).set_index('date')
    y, b = P._tsy(); last = X.index[-1]
    new = S.index[S.index > last]
    if len(new):
        E = pd.DataFrame(index=new); E['r'] = S['QQQ'].pct_change().reindex(new).values
        d13 = b['13 WEEKS BANK DISCOUNT'].reindex(new).ffill(); E['rf'] = (d13 / 100 / 252).values; E['y3m'] = d13.values
        E['y10'] = y['10 Yr'].reindex(new).ffill().values; E['cs'] = X['cs'].iloc[-1]; E['vix'] = np.nan
        X = pd.concat([X, E])
    X['r'] = X['r'].fillna(0.0); X = X.ffill()
    X['rb'] = mkt.bond10(X); X['p'] = (1 + X['r']).cumprod()
    A = {}
    for k in ('QQQ', 'QLD', 'TQQQ'):
        s = mkt.pser(k, 4); s = s[s.index <= last]
        A[k] = pd.concat([s.pct_change(), S[k].pct_change()[S.index > last]]).reindex(X.index)
    P._X['X'], P._X['A'] = X, A
    return X, A


P.ndx_now = ndx_now_fixed          # post2014.run() looks ndx_now up at call time


def funds_now(rule, r1, **kw):
    X, _ = ndx_now_fixed(); end = str(mkt.END.date()); Xf = X[X.index <= mkt.END]
    rows = [HR.conf_one(rule, r1, k, end=end, start='2015-01-02', X=Xf, **kw) for k in HR.FUNDS]
    for x in rows:
        print('  now %-5s %s..%s rule %.4f r1 %.4f s085 %.4f 1x %.4f 2x %.4f 3x %.4f' % (
            x['fund'], x['start'], x['end'], x['rule']['cagr'], x['r1_L1']['cagr'], x['s085']['cagr'], x['hold1x'], x['hold2x'],
            x['hold3x']), flush=True)
    return dict(rows=rows, summary=HR.summarise(rows))


if __name__ == '__main__':
    path, name, outp = sys.argv[1], sys.argv[2], sys.argv[3]
    if not os.path.abspath(outp).startswith(HO): raise SystemExit('post-2014 results must be written under ' + HO)
    if not os.path.exists(HR.R2 + 'FREEZE_TS2.txt'): raise SystemExit('no post-2014 run before r2/FREEZE_TS2.txt exists')
    rule = H.load_rule(path); r1 = H.load_rule(HR.R1_PRIMARY)
    R = dict(rule=path, name=name, t0=time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime()))
    R['us_base'] = P.run(rule, name)
    for lab, kw in (('delay3', dict(delay=3)), ('delay5', dict(delay=5)), ('cost2x', dict(cost=0.006))):
        R['us_' + lab] = P.run(rule, name + '|' + lab, **kw)
    R['funds_base'] = funds_now(rule, r1)
    R['funds_delay3'] = funds_now(rule, r1, delay=3)
    R['funds_cost2x'] = funds_now(rule, r1, cost=0.006)
    R['t1'] = time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())
    json.dump(R, open(outp, 'w'), indent=1, default=float)
