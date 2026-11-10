"""CAPIT independent verifier, part 1: volume data cut + CAP1/CAP2 trigger re-count (SIGNAL SIDE ONLY, no label, no return).
Written from scratch (does not import the lane's cap.py). <= 2014-12-31 only: the panel is cut by its timestamp key before any
value is read. For 2000-2014 only signal COUNTS are produced (no outcome of any kind)."""
import io, json, lzma, hashlib, sys, numpy as np, pandas as pd
LANE = '/mnt/project-files/research/final1/lanes/CAPIT/'
SRC = '/mnt/project-files/research/data/panel_f32.npz.xz'
END = pd.Timestamp('2014-12-31')
out = {}

# ---------- 1. data cut ------------------------------------------------------------------------------------------------------
raw = open(SRC, 'rb').read(); sha = hashlib.sha256(raw).hexdigest()
z = np.load(io.BytesIO(lzma.decompress(raw)), allow_pickle=True)
ts = np.asarray(z['_NDX|ts']); t_all = pd.to_datetime(ts, unit='s')
n = int((t_all.normalize() <= END).sum())                       # number of rows to keep, from the timestamp key only
assert (np.diff(ts[:n]) > 0).all() and (t_all[:n].normalize() <= END).all()
V = np.asarray(z['_NDX|v'][:n], dtype=np.float64)                # only the first n rows are ever materialised
t = t_all[:n].normalize()
P = pd.DataFrame({'close': V[:, 3], 'volume': V[:, 5]}, index=t)
hours = sorted(set(t_all[:n].hour.tolist()))
csv = pd.read_csv(LANE + 'data/ndx_close_volume_le2014.csv', parse_dates=['date']).set_index('date')
gcsv = pd.read_csv(LANE + 'data/gspc_close_le2014.csv', parse_dates=['date']).set_index('date')
man = json.load(open(LANE + 'data/MANIFEST.json'))
sha_csv = hashlib.sha256(open(LANE + 'data/ndx_close_volume_le2014.csv', 'rb').read()).hexdigest()
out['data'] = dict(
    panel_sha256=sha, panel_sha_matches_precommit=bool(sha == 'fa2c35b295642ddf27924e1125a50c823ea464a0f6b47e54c0b3b254fd35242c'),
    panel_rows_le2014=n, panel_first=str(t[0].date()), panel_last=str(t[-1].date()), ts_hours_utc=hours, dup_dates=int(t.duplicated().sum()),
    csv_rows=int(len(csv)), csv_first=str(csv.index.min().date()), csv_last=str(csv.index.max().date()),
    csv_rows_after_2014=int((csv.index > END).sum()), gspc_csv_rows_after_2014=int((gcsv.index > END).sum()),
    gspc_csv_last=str(gcsv.index.max().date()),
    csv_sha256=sha_csv, csv_sha_matches_manifest=bool(sha_csv == man['files'][0]['sha256']),
    csv_dates_equal_panel=bool(len(csv) == n and (csv.index == t).all()),
    csv_close_max_rel_diff=float((csv['close'].values / P['close'].values - 1).__abs__().max()),
    csv_volume_max_rel_diff=float((csv['volume'].values / P['volume'].values - 1).__abs__().max()),
    volume_nonpositive_or_nan=int((~(np.isfinite(P.volume) & (P.volume > 0))).sum()),
    volume_equal_prev_day=int((P.volume.diff() == 0).sum()),
    volume_median_by_year_1985_1999={int(k): float(v) for k, v in P.volume[:'1999-12-31'].groupby(P.index[P.index <= '1999-12-31'].year).median().items()})
print('DATA', json.dumps(out['data']))

# ---------- 2. indicators, written again from scratch ------------------------------------------------------------------------
def rsi_wilder(p, n=14):
    """Wilder RSI: seed = simple mean of the first n gains/losses, then recursive smoothing with 1/n."""
    p = np.asarray(p, float); ch = np.diff(p); o = np.full(len(p), np.nan)
    up = np.where(ch > 0, ch, 0.0); dn = np.where(ch < 0, -ch, 0.0)
    au = up[:n].sum() / n; ad = dn[:n].sum() / n
    for i in range(n, len(p)):
        if i > n:
            au += (up[i - 1] - au) / n; ad += (dn[i - 1] - ad) / n
        o[i] = 100.0 if ad == 0 else 100.0 * au / (au + ad)
    return o
def rsi_cutler(p, n=14):
    """SMA RSI (Cutler): plain n-day sums of gains and losses."""
    ch = pd.Series(np.asarray(p, float)).diff(); u = ch.clip(lower=0).rolling(n).sum(); d = (-ch).clip(lower=0).rolling(n).sum()
    return (100 * u / (u + d)).values
def rsi_ema(p, n=14):
    """EMA(span=n) RSI, another common vendor variant."""
    ch = pd.Series(np.asarray(p, float)).diff(); u = ch.clip(lower=0).ewm(span=n, adjust=False).mean(); d = (-ch).clip(lower=0).ewm(span=n, adjust=False).mean()
    return (100 * u / (u + d)).values
def vol_ratio(v, k=60, stat='median', include_today=False):
    v = np.asarray(v, float); o = np.full(len(v), np.nan)
    for i in range(k, len(v)):
        w = v[i - k + 1:i + 1] if include_today else v[i - k:i]
        o[i] = v[i] / (np.median(w) if stat == 'median' else np.mean(w))
    return o

rsi = pd.Series(rsi_wilder(P.close.values), index=P.index); vr = pd.Series(vol_ratio(P.volume.values), index=P.index)
lo = rsi <= 30.0
def last3_any(b): b = np.asarray(b, bool); return b | np.r_[False, b[:-1]] | np.r_[False, False, b[:-2]]
cap1 = pd.Series(lo.values & (vr.values >= 2.0), index=P.index)
cap2 = pd.Series(last3_any(lo.values) & last3_any(vr.values >= 2.5), index=P.index)
WIN = {'early_1986_1999': ('1986-01-02', '1999-12-31'), 'unseen_2000_2014_SIGNAL_COUNTS_ONLY': ('2000-01-03', '2014-12-31')}
for nm, (a, b) in WIN.items():
    m = (P.index >= a) & (P.index <= b)
    r = dict(days=int(m.sum()), rsi_le30_days=int(lo[m].sum()), vr_ge2_days=int((vr[m] >= 2.0).sum()), vr_ge2p5_days=int((vr[m] >= 2.5).sum()),
             CAP1_trigger_days=int(cap1[m].sum()), CAP2_trigger_days=int(cap2[m].sum()),
             CAP1_dates=[dict(t=str(d.date()), rsi=round(float(rsi[d]), 2), vr=round(float(vr[d]), 3)) for d in P.index[m][cap1[m].values]],
             CAP2_dates=[str(d.date()) for d in P.index[m][cap2[m].values]])
    if nm.startswith('early'):
        x = vr[m][lo[m]]
        r.update(max_vr=round(float(vr[m].max()), 3), max_vr_date=str(vr[m].idxmax().date()),
                 max_vr_on_rsi_le30=round(float(x.max()), 3), max_vr_on_rsi_le30_date=str(x.idxmax().date()),
                 vr_ge2_dates=[dict(t=str(d.date()), vr=round(float(vr[d]), 3), rsi=round(float(rsi[d]), 1)) for d in P.index[m][(vr[m] >= 2.0).values]],
                 vr_quantiles={q: round(float(vr[m].quantile(float(q))), 3) for q in ('0.5', '0.9', '0.99', '0.999')},
                 vr_on_rsi_le30_quantiles={q: round(float(x.quantile(float(q))), 3) for q in ('0.5', '0.9', '0.99')},
                 min_rsi=round(float(rsi[m].min()), 2), min_rsi_date=str(rsi[m].idxmin().date()),
                 oct1987={str(d.date()): dict(rsi=round(float(rsi[d]), 2), vr=round(float(vr[d]), 2)) for d in P.loc['1987-10-16':'1987-10-22'].index})
    out[nm] = r; print(nm, json.dumps(r))

# ---------- 3. false-negative probes on the EARLY window, signal side only (no label is ever touched) -------------------------
me = (P.index >= '1986-01-02') & (P.index <= '1999-12-31'); fn = {}
RS = {'wilder': rsi.values, 'cutler_sma': rsi_cutler(P.close.values), 'ema_span14': rsi_ema(P.close.values)}
VR = {'median_prev60': vr.values, 'mean_prev60': vol_ratio(P.volume.values, stat='mean'), 'median_incl_today60': vol_ratio(P.volume.values, include_today=True),
      'median_prev60_volume_shifted_+1d': np.r_[np.nan, vr.values[:-1]], 'median_prev60_volume_shifted_-1d': np.r_[vr.values[1:], np.nan]}
for rn, rv in RS.items():
    for vn, vv in VR.items():
        l = np.nan_to_num(rv, nan=999.0) <= 30.0; h2 = np.nan_to_num(vv, nan=-1.0) >= 2.0; h25 = np.nan_to_num(vv, nan=-1.0) >= 2.5
        fn['%s|%s' % (rn, vn)] = dict(rsi_le30=int(l[me].sum()), vr_ge2=int(h2[me].sum()), vr_ge2p5=int(h25[me].sum()),
                                      CAP1=int((l & h2)[me].sum()), CAP2=int((last3_any(l) & last3_any(h25))[me].sum()))
out['false_negative_probes_early_signal_only'] = fn
for k, v in fn.items(): print('FN', k, v)
# hard upper bound on 'on' blocks in the early window if EVERY vr>=2.0 day were a trigger regardless of RSI (21-day grid, W=42 / 63)
d2 = np.where((vr.values >= 2.0) & me)[0]; d25 = np.where((vr.values >= 2.5) & me)[0]
out['upper_bound'] = dict(vr_ge2_days_any_rsi=int(len(d2)), max_on_blocks_CAP1_if_rsi_ignored=int(len(d2) * 2), vr_ge2p5_days_any_rsi=int(len(d25)),
                          max_on_blocks_CAP2_if_rsi_ignored=int(len(d25) * 3), needed=8)
print('UPPER BOUND', json.dumps(out['upper_bound']))
# builder file comparison
kb = json.load(open(LANE + 'results/killB_early.json')); su = json.load(open(LANE + 'results/signal_counts_unseen.json')); bv = json.load(open(LANE + 'results/verify.json'))
cmp = dict(
    early_CAP1_trigger_days=(out['early_1986_1999']['CAP1_trigger_days'], kb['variants']['CAP1']['signal']['trigger_days']),
    early_CAP2_trigger_days=(out['early_1986_1999']['CAP2_trigger_days'], kb['variants']['CAP2']['signal']['trigger_days']),
    early_n_days=(out['early_1986_1999']['days'], kb['variants']['CAP1']['signal']['n_days']),
    unseen_CAP1_trigger_days=(out['unseen_2000_2014_SIGNAL_COUNTS_ONLY']['CAP1_trigger_days'], su['variants']['CAP1']['signal']['trigger_days']),
    unseen_CAP2_trigger_days=(out['unseen_2000_2014_SIGNAL_COUNTS_ONLY']['CAP2_trigger_days'], su['variants']['CAP2']['signal']['trigger_days']),
    unseen_n_days=(out['unseen_2000_2014_SIGNAL_COUNTS_ONLY']['days'], su['variants']['CAP1']['signal']['n_days']),
    early_rsi_le30_days=(out['early_1986_1999']['rsi_le30_days'], bv['early_1986_1999']['rsi_le30_days']),
    early_vr_ge2_days=(out['early_1986_1999']['vr_ge2_days'], bv['early_1986_1999']['vr_ge2_days']),
    early_vr_ge2p5_days=(out['early_1986_1999']['vr_ge2p5_days'], bv['early_1986_1999']['vr_ge2p5_days']),
    early_max_vr_on_rsi_le30=(out['early_1986_1999']['max_vr_on_rsi_le30'], bv['early_1986_1999']['max_vr_on_rsi_le30']))
out['compare_mine_vs_builder'] = {k: dict(mine=a, builder=b, equal=bool(a == b)) for k, (a, b) in cmp.items()}
for k, v in out['compare_mine_vs_builder'].items(): print('CMP', k, v)
# keys of the builder's unseen file: must hold no outcome field
bad = ('base', 'cond', 'wins', 'always_in_hit', 'on_blocks', 'p_binom_ge', 'pass_B', 'win', 'hit', 'ret', 'label')
keys = set()
def walk(o):
    if isinstance(o, dict):
        for k, v in o.items(): keys.add(k); walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(su)
out['unseen_file_keys'] = sorted(keys); out['unseen_file_outcome_keys'] = sorted(k for k in keys if k in bad)
print('UNSEEN FILE KEYS', out['unseen_file_keys'], 'outcome keys:', out['unseen_file_outcome_keys'])
json.dump(out, open(LANE + 'verify/v1_signals.json', 'w'), indent=1)
P.to_pickle('/tmp/final1_CAPIT_verify/ndx_panel_le2014.pkl')
pd.DataFrame({'rsi': rsi, 'vr': vr, 'cap1': cap1, 'cap2': cap2}).to_pickle('/tmp/final1_CAPIT_verify/sig.pkl')
print('saved verify/v1_signals.json')
