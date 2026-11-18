"""Item 5: synthetic 10y bond leg (mkt.bond10, NON-ACTUAL) vs ACTUAL Treasury funds (Yahoo adjclose, rows <= 2014-12-31 only).
IEF (iShares 7-10y Treasury, 2002-07+) and VFITX (Vanguard Intermediate-Term Treasury, 1991-10+). Synthetic net of the engine's 0.15%/yr ER."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, jp, mkt
END = pd.Timestamp('2014-12-31')
R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX'); assert X.index.max() <= END
syn = (mkt.bond10(X) - 0.0015 / 252).rename('syn'); ndx = X['r'].rename('ndx') if 'r' in X else None
def yh(path):
    d = json.load(open(path))['chart']['result'][0]; ts = pd.to_datetime(d['timestamp'], unit='s').normalize()
    s = pd.Series(d['indicators']['adjclose'][0]['adjclose'], index=ts).dropna(); s = s[s.index <= END]
    return s[~s.index.duplicated()]
out = {}
for t in ('IEF', 'VFITX'):
    a = yh('/tmp/chk_final/yh/%s.json' % t).pct_change().dropna().rename('act')
    d = pd.concat([a, syn], axis=1, join='inner').dropna(); d = d[d.index > d.index[0]]
    if ndx is not None: d = d.join(ndx, how='left')
    yrs = len(d) / 252
    cg = lambda x: float(np.prod(1 + x) ** (1 / yrs) - 1)
    yr = d.groupby(d.index.year)[['act', 'syn']].apply(lambda g: (1 + g).prod() - 1)
    win = {}
    for nm, a0, b0 in (('1994', '1994-01-01', '1994-12-31'), ('2000-02', '2000-01-01', '2002-12-31'), ('2008H2', '2008-07-01', '2008-12-31'),
                       ('2013 taper', '2013-05-01', '2013-09-30'), ('1987-10', '1987-10-01', '1987-10-31')):
        g = d.loc[a0:b0]
        if len(g) > 5: win[nm] = dict(act=float((1 + g['act']).prod() - 1), syn=float((1 + g['syn']).prod() - 1))
    def mdd(x): e = (1 + x).cumprod(); return float((e / e.cummax() - 1).min())
    r = dict(start=str(d.index[0].date()), end=str(d.index[-1].date()), days=len(d), cagr_act=cg(d['act']), cagr_syn=cg(d['syn']),
             gap_per_yr=cg(d['syn']) - cg(d['act']), corr_daily=float(d['act'].corr(d['syn'])), beta_act_on_syn=float(np.polyfit(d['syn'], d['act'], 1)[0]),
             vol_act=float(d['act'].std() * 252 ** .5), vol_syn=float(d['syn'].std() * 252 ** .5), mdd_act=mdd(d['act']), mdd_syn=mdd(d['syn']),
             yearly_gap_median=float((yr['syn'] - yr['act']).median()), yearly_gap_max=float((yr['syn'] - yr['act']).abs().max()), windows=win)
    if ndx is not None:
        r['corr_ndx_act'] = float(d['act'].corr(d['ndx'])); r['corr_ndx_syn'] = float(d['syn'].corr(d['ndx']))
    out[t] = r
    print(t, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k != 'windows'}))
    print('  windows', {k: {kk: round(vv, 4) for kk, vv in v.items()} for k, v in win.items()})
json.dump(out, open('/mnt/project-files/research/df1/checks/final/bond_vs_actual.json', 'w'), indent=1)
