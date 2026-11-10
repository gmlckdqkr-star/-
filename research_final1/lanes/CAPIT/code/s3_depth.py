"""CAPIT DEPTH table (descriptive only, NOT a test, no selection). PRECOMMIT.md section 4. <= 2014-12-31 only.
Definitions fixed here before the first run:
  level        = cumulative product of (1 + daily return) of the 1x index from the first day of the series.
  episode      = one all-time-high cycle: from a new all-time high (ATH) of the daily close until the next new ATH. A cycle whose
                 peak is the very first observation of the series is flagged (the true earlier high is unknown).
  crossing     = first close in the cycle with level/ATH - 1 <= -X, X in 30/40/50/60/70 %. One crossing per cycle and threshold,
                 so n = number of independent ATH cycles that reached that depth.
  forward      = entry at the close of crossing day + 2 trading days (MS1 execution delay), held 252 (1y) and 756 (3y) trading days.
                 1x = index itself; 3x = synthetic daily-reset product, MS1 formula 3r - 2rf - 2.45%/yr (NON-ACTUAL).
                 Gross of trading cost and tax. A horizon that would end after 2014-12-31 is 'not available' (never extended).
  also stored  = entry-at-crossing-close variant (delay 0), worst interim value of the 3x leg inside 3y, depth and date of the cycle trough.
Series: NDX  = MS1 frame jp.mkX(...,'NDX') (Nasdaq-100 PRICE index, vendor bars from 1985-10-01)                      1x ACTUAL (price only)
        SPX  = MS1 frame jp.mkX(...,'SPX') 1928-01-03..2014-12-31 (S&P 500 TOTAL-RETURN reconstruction, [RECON] in md.py) 1x NON-ACTUAL
        GSPC = S&P 500 PRICE index, panel `_GSPC` close 1970-01-02..2014-12-31 (vendor bars), caveat check only         1x ACTUAL (price only)
        SOX  = not produced: no <=2014 cut of the SOX index exists locally (panel has no `_SOX`; the SOXX ETF cut starts 2001-07-13,
               after the 2000 high, so a drawdown from the all-time high cannot be defined on it)."""
import sys, io, json, lzma, hashlib, numpy as np, pandas as pd
LANE = '/mnt/project-files/research/final1/lanes/CAPIT/'
sys.path.insert(0, '/mnt/project-files/research/ov1/code')
import ov1lib as L, jp  # noqa
END = pd.Timestamp('2014-12-31'); THR = (0.30, 0.40, 0.50, 0.60, 0.70); H = {'1y': 252, '3y': 756}; DELAY = 2

def gspc_cut():
    SRC = '/mnt/project-files/research/data/panel_f32.npz.xz'; raw = open(SRC, 'rb').read(); sha = hashlib.sha256(raw).hexdigest()
    assert sha == 'fa2c35b295642ddf27924e1125a50c823ea464a0f6b47e54c0b3b254fd35242c'
    z = np.load(io.BytesIO(lzma.decompress(raw)), allow_pickle=True)
    t = pd.to_datetime(z['_GSPC|ts'], unit='s').normalize(); n = int((t <= END).sum())
    s = pd.Series(z['_GSPC|v'][:n, 3].astype(float), index=t[:n], name='close'); s.index.name = 'date'; s = s[~s.index.duplicated()]
    out = LANE + 'data/gspc_close_le2014.csv'; s.to_csv(out, float_format='%.6g')
    man = json.load(open(LANE + 'data/MANIFEST.json')); man['files'] = [f for f in man['files'] if f['name'] != 'gspc_close_le2014.csv']
    man['files'].append(dict(name='gspc_close_le2014.csv', sha256=hashlib.sha256(open(out, 'rb').read()).hexdigest(), rows=int(len(s)),
                             first=str(s.index[0].date()), last=str(s.index[-1].date()), columns=['date', 'close'],
                             label='ACTUAL (vendor index bars, S&P 500 price index)', source_file=SRC, source_sha256=sha,
                             source_key='_GSPC|ts, _GSPC|v column 3 (close)',
                             source_origin='Yahoo chart v8 daily bars for ^GSPC (shared base panel); no network request was made by this lane',
                             cut='rows with date <= 2014-12-31 only; later rows dropped by timestamp before use'))
    json.dump(man, open(LANE + 'data/MANIFEST.json', 'w'), indent=1)
    return s

def depth(name, idx, r, rf, label_1x, note):
    r = np.asarray(r, float).copy(); r[0] = 0.0; rf = np.asarray(rf, float)
    lvl = np.cumprod(1 + r); x3 = 3 * r - 2 * rf - 0.0245 / 252; x3[0] = 0.0; l3 = np.cumprod(1 + x3)
    ath = np.maximum.accumulate(lvl); dd = lvl / ath - 1
    newhi = np.r_[True, lvl[1:] > ath[:-1]]; cyc = np.cumsum(newhi) - 1; n = len(lvl)
    peaks = np.where(newhi)[0]; eps = []
    for k, p in enumerate(peaks):
        q = peaks[k + 1] if k + 1 < len(peaks) else n          # cycle = [p, q)
        seg = dd[p:q]
        if seg.min() > -THR[0]: continue
        tr = p + int(seg.argmin())
        e = dict(peak=str(idx[p].date()), peak_is_first_obs=bool(p == 0), trough=str(idx[tr].date()), trough_dd=float(seg.min()),
                 recovered=(str(idx[q].date()) if q < n else None), cross={})
        for X in THR:
            hit = np.where(seg <= -X)[0]
            if not len(hit): continue
            t = p + int(hit[0]); c = dict(date=str(idx[t].date()), dd_at_cross=float(dd[t]), days_to_trough=int(tr - t))
            for dl, tag in ((DELAY, ''), (0, '_d0')):
                en = t + dl
                for hn, h in H.items():
                    if en + h <= n - 1:
                        c['r1x_%s%s' % (hn, tag)] = float(lvl[en + h] / lvl[en] - 1); c['r3x_%s%s' % (hn, tag)] = float(l3[en + h] / l3[en] - 1)
                    else:
                        c['r1x_%s%s' % (hn, tag)] = None; c['r3x_%s%s' % (hn, tag)] = None
            en = t + DELAY; hh = min(en + H['3y'], n - 1)
            c['min3x_within_3y'] = float(l3[en:hh + 1].min() / l3[en] - 1) if en < n else None
            c['min3x_window_complete'] = bool(en + H['3y'] <= n - 1)
            e['cross']['%d' % round(X * 100)] = c
        eps.append(e)
    cells = {}
    for X in THR:
        k = '%d' % round(X * 100); cs = [(e, e['cross'][k]) for e in eps if k in e['cross']]
        cell = dict(n_cycles_crossed=len(cs), n_cycles_peak_first_obs=sum(e['peak_is_first_obs'] for e, _ in cs))
        for f in ('r1x_1y', 'r3x_1y', 'r1x_3y', 'r3x_3y'):
            v = [c[f] for _, c in cs if c[f] is not None]
            cell[f] = dict(n=len(v), values=v, median=(float(np.median(v)) if v else None), min=(min(v) if v else None), max=(max(v) if v else None),
                           n_positive=int(sum(x > 0 for x in v)))
        cells[k] = cell
    return dict(series=name, first=str(idx[0].date()), last=str(idx[-1].date()), n_days=int(n), label_1x=label_1x, label_3x='NON-ACTUAL (synthetic 3r-2rf-2.45%/yr)',
                note=note, max_dd=float(dd.min()), n_cycles_ge30=len(eps), episodes=eps, cells=cells)

out = dict(lane='CAPIT', kind='DEPTH table: descriptive only, not a test, no selection', thresholds=[int(round(x * 100)) for x in THR],
           entry='close of crossing day + 2 trading days (delay-0 variant stored with suffix _d0)', horizons=H,
           costs='gross of trading cost and tax; 3x drag 2.45%/yr and financing 2rf included (MS1 formula)',
           sox='not produced: no <=2014 cut of the SOX index locally (panel has no _SOX; SOXX ETF cut starts 2001-07-13, after the 2000 high)',
           series={})
R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX'); assert X.index.max() <= END
first = R['NDX'].first_valid_index(); i0 = X.index.get_loc(first) - 1                     # level starts at the first index bar
out['series']['NDX_1985_2014'] = depth('NDX_1985_2014', X.index[i0:], X['r'].values[i0:], X['rf'].values[i0:], 'ACTUAL (price index, no dividends)',
                                       'Nasdaq-100 price index, vendor bars start 1985-10-01 (index launched 1985-01-31)')
R2, M2 = jp.calendar('1928-01-03', '2014-12-31'); X2 = jp.mkX(R2, M2, 'SPX'); assert X2.index.max() <= END
out['series']['SPX_TR_1928_2014'] = depth('SPX_TR_1928_2014', X2.index, X2['r'].values, X2['rf'].values, 'NON-ACTUAL (total-return reconstruction, MS1 SPX frame)',
                                          'S&P 500 total return [RECON] as used by MS1 real_spx bases; dividends included')
g = gspc_cut(); gi = X2.index[(X2.index >= g.index[0])]; gp = g.reindex(gi).ffill(); gr = gp.pct_change().fillna(0.0)
out['series']['GSPC_PRICE_1970_2014'] = depth('GSPC_PRICE_1970_2014', gi, gr.values, X2['rf'].reindex(gi).values, 'ACTUAL (price index, no dividends)',
                                              'caveat check for the S&P rows: price index only, series starts 1970-01-02 (no earlier high known)')
json.dump(out, open(LANE + 'results/depth_table.json', 'w'), indent=1)

def pc(x): return '   n/a' if x is None else '%+6.0f%%' % (100 * x)
for sn, s in out['series'].items():
    print('\n==', sn, s['first'], s['last'], 'maxDD %.1f%%' % (100 * s['max_dd']), '| cycles >=30%:', s['n_cycles_ge30'], '|', s['label_1x'])
    for e in s['episodes']:
        print('  cycle peak', e['peak'], 'trough', e['trough'], '%.1f%%' % (100 * e['trough_dd']), 'recovered', e['recovered'], '(peak = first obs)' if e['peak_is_first_obs'] else '')
        for k, c in e['cross'].items():
            print('     -%s%% on %s | 1x 1y %s 3y %s | 3x 1y %s 3y %s | 3x worst<=3y %s | d0: 1x %s %s 3x %s %s' % (
                k, c['date'], pc(c['r1x_1y']), pc(c['r1x_3y']), pc(c['r3x_1y']), pc(c['r3x_3y']), pc(c['min3x_within_3y']),
                pc(c['r1x_1y_d0']), pc(c['r1x_3y_d0']), pc(c['r3x_1y_d0']), pc(c['r3x_3y_d0'])))
    for k, cell in s['cells'].items():
        print('  cell -%s%%: cycles %d | ' % (k, cell['n_cycles_crossed']) + ' | '.join('%s n=%d med %s pos %d' % (f, cell[f]['n'], pc(cell[f]['median']), cell[f]['n_positive']) for f in ('r1x_1y', 'r3x_1y', 'r1x_3y', 'r3x_3y')))
print('\nsaved results/depth_table.json')
