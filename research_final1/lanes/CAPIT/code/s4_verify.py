"""CAPIT independent re-check (different code path, pandas only, straight from the lane CSV cuts). <= 2014 only. No label of the unseen
window is touched: part A re-counts SIGNAL days only; part B re-computes DEPTH-table cells (descriptive table, registered for 1985-2014)."""
import sys, json, numpy as np, pandas as pd
LANE = '/mnt/project-files/research/final1/lanes/CAPIT/'
sys.path.insert(0, '/mnt/project-files/research/ov1/code'); sys.path.insert(0, LANE + 'code')
import ov1lib as L, jp  # noqa
out = {}
# ---------- A. trigger re-count from the vendor CSV (close + volume), textbook formulas written again from scratch
d = pd.read_csv(LANE + 'data/ndx_close_volume_le2014.csv', parse_dates=['date']).set_index('date'); assert d.index.max() <= pd.Timestamp('2014-12-31')
ch = d['close'].diff(); up = ch.clip(lower=0); dn = (-ch).clip(lower=0)
def wilder(x, n=14):
    v = x.values; o = np.full(len(v), np.nan); o[n] = v[1:n + 1].mean()
    for i in range(n + 1, len(v)): o[i] = (o[i - 1] * (n - 1) + v[i]) / n
    return pd.Series(o, index=x.index)
rsi = 100 - 100 / (1 + wilder(up) / wilder(dn))
vr = pd.Series([d['volume'].iloc[i] / np.median(d['volume'].iloc[i - 60:i].values) if i >= 60 else np.nan for i in range(len(d))], index=d.index)
lo = rsi <= 30
c1 = lo & (vr >= 2.0)
c2 = (lo.rolling(3, min_periods=1).max() > 0) & (vr.rolling(3, min_periods=1).max() >= 2.5)
for nm, a, b in (('early_1986_1999', '1986-01-02', '1999-12-31'), ('unseen_2000_2014_signal_only', '2000-01-03', '2014-12-31')):
    m = (d.index >= a) & (d.index <= b)
    out[nm] = dict(days=int(m.sum()), rsi_le30_days=int(lo[m].sum()), vr_ge2_days=int((vr[m] >= 2.0).sum()), vr_ge2p5_days=int((vr[m] >= 2.5).sum()),
                   vr_ge1p5_days=int((vr[m] >= 1.5).sum()), max_vr=round(float(vr[m].max()), 3), max_vr_on_rsi_le30=round(float(vr[m][lo[m]].max()), 3),
                   CAP1_trigger_days=int(c1[m].sum()), CAP2_trigger_days=int(c2[m].sum()),
                   CAP1_dates=[str(x.date()) for x in d.index[m][c1[m].values]], CAP2_dates=[str(x.date()) for x in d.index[m][c2[m].values]])
    print(nm, json.dumps(out[nm]))
# signal-side facts quoted in the report (early window only)
me = (d.index >= '1986-01-02') & (d.index <= '1999-12-31')
out['early_facts'] = dict(
    vr_ge2_dates=[dict(t=str(x.date()), vr=round(float(vr[x]), 2), rsi=round(float(rsi[x]), 1)) for x in d.index[me][(vr[me] >= 2.0).values]],
    max_vr_on_rsi_le30_date=str(vr[me][lo[me]].idxmax().date()),
    oct1987={str(x.date()): dict(rsi=round(float(rsi[x]), 2), vr=round(float(vr[x]), 2)) for x in d.loc['1987-10-16':'1987-10-22'].index})
import cap as _cap   # parity of the frozen RSI (on the MS1 price frame) with this from-scratch RSI on the vendor close, early window only
Re, Me = jp.calendar('1984-01-03', '1999-12-31'); Xe = jp.mkX(Re, Me, 'NDX')
r_frame = pd.Series(_cap.rsi14((1 + Xe['r']).cumprod().values[None, :])[0], index=Xe.index)
dd = (r_frame - rsi.reindex(Xe.index))[Xe.index >= '1986-06-01'].abs()
out['early_facts']['rsi_frame_vs_vendor_close'] = dict(max_abs_diff=float(dd.max()), n=int(dd.notna().sum()), window='1986-06-01..1999-12-31')
print('early facts', json.dumps(out['early_facts']))
# ---------- B. DEPTH cells re-computed from closes (1x) and a from-scratch 3x compounding
T = json.load(open(LANE + 'results/depth_table.json')); chk = []
R, M = jp.calendar('1928-01-03', '2014-12-31'); rf = M['rf']      # full calendar: the financing rate must exist for the 1970s episodes
def recheck(series, close):
    close = close.dropna(); r = close.pct_change().fillna(0.0); f = rf.reindex(close.index).ffill().fillna(0.0)
    e3 = (1 + 3 * r - 2 * f - 0.0245 / 252).cumprod()
    for ep in T['series'][series]['episodes']:
        for k, c in ep['cross'].items():
            # the crossing itself: first close after the cycle peak at or below -k% from the running high
            seg = close[pd.Timestamp(ep['peak']):]; pk = seg.iloc[0]; hit = seg[seg / pk - 1 <= -int(k) / 100].index[0]
            i = close.index.get_loc(hit) + 2
            for hn, h in (('1y', 252), ('3y', 756)):
                if i + h > len(close) - 1: a = b = None
                else: a = float(close.iloc[i + h] / close.iloc[i] - 1); b = float(e3.iloc[i + h] / e3.iloc[i] - 1)
                chk.append(dict(series=series, thr=k, cross_table=c['date'], cross_recheck=str(hit.date()), h=hn, r1x_table=c['r1x_' + hn], r1x_recheck=a,
                                r3x_table=c['r3x_' + hn], r3x_recheck=b))
nd = d['close']; recheck('NDX_1985_2014', nd)
g = pd.read_csv(LANE + 'data/gspc_close_le2014.csv', parse_dates=['date']).set_index('date')['close']; recheck('GSPC_PRICE_1970_2014', g)
worst = 0.0; same_date = True
for x in chk:
    same_date &= (x['cross_table'] == x['cross_recheck'])
    for a, b in ((x['r1x_table'], x['r1x_recheck']), (x['r3x_table'], x['r3x_recheck'])):
        if a is None or b is None: assert a is None and b is None; continue
        worst = max(worst, abs(a - b))
print('DEPTH recheck rows', len(chk), 'crossing dates identical', bool(same_date), 'max abs diff of returns', worst)
out['depth_recheck'] = dict(rows=len(chk), crossing_dates_identical=bool(same_date), max_abs_diff=worst, detail=chk)
json.dump(out, open(LANE + 'results/verify.json', 'w'), indent=1)
