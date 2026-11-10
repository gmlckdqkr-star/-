"""CAPIT independent verifier, part 3: DEPTH table re-computed with my own single-pass algorithm (not the lane's s3_depth.py).
Descriptive table registered for NDX 1985-2014 and S&P 500 1928-2014; <= 2014-12-31 only (panel cut by timestamp before use).
NDX level  = vendor close from the panel (my own cut), NOT the MS1 frame return the builder compounded.
SPX_TR     = MS1 SPX frame return (same input as the builder: there is no second source locally), own algorithm.
GSPC price = vendor close from the panel `_GSPC` (my own cut)."""
import io, sys, json, lzma, numpy as np, pandas as pd
LANE = '/mnt/project-files/research/final1/lanes/CAPIT/'
sys.path.insert(0, '/mnt/project-files/research/ov1/code')
import ov1lib as L, jp  # noqa
END = pd.Timestamp('2014-12-31'); THR = (30, 40, 50, 60, 70)

def my_depth(idx, lvl, rf):
    lvl = np.asarray(lvl, float); rf = np.asarray(rf, float); n = len(lvl)
    g3 = np.ones(n); g3[1:] = 1 + 3 * (lvl[1:] / lvl[:-1] - 1) - 2 * rf[1:] - 0.0245 / 252
    def fwd(e, h):
        if e + h > n - 1: return None, None
        return float(lvl[e + h] / lvl[e] - 1), float(np.prod(g3[e + 1:e + h + 1]) - 1)
    cycles = []; cur = dict(peak=0, tr=0, trdd=0.0, cross={}); top = lvl[0]
    for i in range(1, n):
        if lvl[i] > top:
            cur['end'] = i; cycles.append(cur); top = lvl[i]; cur = dict(peak=i, tr=i, trdd=0.0, cross={})
            continue
        dd = lvl[i] / top - 1
        if dd < cur['trdd']: cur['trdd'] = dd; cur['tr'] = i
        for x in THR:
            if x not in cur['cross'] and dd <= -x / 100: cur['cross'][x] = (i, dd)
    cur['end'] = None; cycles.append(cur)
    eps = []
    for c in cycles:
        if 30 not in c['cross']: continue
        e = dict(peak=str(idx[c['peak']].date()), peak_is_first_obs=bool(c['peak'] == 0), trough=str(idx[c['tr']].date()), trough_dd=float(c['trdd']),
                 recovered=(str(idx[c['end']].date()) if c['end'] is not None else None), cross={})
        for x, (i, dd) in c['cross'].items():
            r = dict(date=str(idx[i].date()), dd_at_cross=float(dd))
            for tag, dl in (('', 2), ('_d0', 0)):
                for hn, h in (('1y', 252), ('3y', 756)):
                    a, b = fwd(i + dl, h); r['r1x_%s%s' % (hn, tag)] = a; r['r3x_%s%s' % (hn, tag)] = b
            en = i + 2; hh = min(en + 756, n - 1)
            r['min3x_within_3y'] = float(np.min(np.cumprod(np.r_[1.0, g3[en + 1:hh + 1]])) - 1) if en < n else None
            e['cross'][str(x)] = r
        eps.append(e)
    cells = {}
    for x in THR:
        cs = [e['cross'][str(x)] for e in eps if str(x) in e['cross']]; cell = dict(n_cycles_crossed=len(cs))
        for f in ('r1x_1y', 'r3x_1y', 'r1x_3y', 'r3x_3y'):
            v = [c[f] for c in cs if c[f] is not None]
            cell[f] = dict(n=len(v), median=(float(np.median(v)) if v else None), min=(min(v) if v else None), max=(max(v) if v else None), n_positive=int(sum(q > 0 for q in v)))
        cells[str(x)] = cell
    return dict(first=str(idx[0].date()), last=str(idx[-1].date()), n_days=int(n), max_dd=float(min([c['trdd'] for c in cycles])), n_cycles_ge30=len(eps), episodes=eps, cells=cells)

# ---- inputs
PN = pd.read_pickle('/tmp/final1_CAPIT_verify/ndx_panel_le2014.pkl')
R, M = jp.calendar('1928-01-03', '2014-12-31'); assert M.index.max() <= END; rf = M['rf']
assert PN.index.isin(rf.index).all()
mine = {'NDX_1985_2014': my_depth(PN.index, PN.close.values, rf.reindex(PN.index).values)}
X2 = jp.mkX(R, M, 'SPX'); assert X2.index.max() <= END
r2 = X2['r'].values.copy(); r2[0] = 0.0
mine['SPX_TR_1928_2014'] = my_depth(X2.index, np.cumprod(1 + r2), X2['rf'].values)
z = np.load(io.BytesIO(lzma.decompress(open('/mnt/project-files/research/data/panel_f32.npz.xz', 'rb').read())), allow_pickle=True)
tg = pd.to_datetime(np.asarray(z['_GSPC|ts']), unit='s').normalize(); ng = int((tg <= END).sum())
G = pd.Series(np.asarray(z['_GSPC|v'][:ng, 3], dtype=np.float64), index=tg[:ng]); G = G[~G.index.duplicated()]
gi = X2.index[X2.index >= G.index[0]]; gp = G.reindex(gi).ffill()
mine['GSPC_PRICE_1970_2014'] = my_depth(gi, gp.values, X2['rf'].reindex(gi).values)
inputs = dict(ndx_rows=int(len(PN)), gspc_rows_le2014=int(ng), gspc_first=str(G.index[0].date()), gspc_last=str(G.index[-1].date()),
              gspc_calendar_days_without_vendor_bar=int(G.reindex(gi).isna().sum()), gspc_vendor_days_not_in_calendar=int((~G.index.isin(X2.index)).sum()),
              rf_min=float(rf.min()), rf_max=float(rf.max()), rf_mean_annualised_1986_2014=float(rf['1986':'2014'].mean() * 252),
              rf_mean_annualised_1929_1932=float(rf['1929':'1932'].mean() * 252), rf_nan=int(rf.isna().sum()))

# ---- compare with the builder's depth_table.json
T = json.load(open(LANE + 'results/depth_table.json')); worst = 0.0; worst_where = None; n_val = 0; problems = []
def cmpv(a, b, where):
    global worst, worst_where, n_val
    if a is None or b is None:
        if not (a is None and b is None): problems.append(where + ': None mismatch %r vs %r' % (a, b))
        return
    n_val += 1; d = abs(a - b)
    if d > worst: worst, worst_where = d, where
for sn in mine:
    A, Bt = mine[sn], T['series'][sn]
    for k in ('first', 'last', 'n_days', 'n_cycles_ge30'):
        if A[k] != Bt[k]: problems.append('%s %s: mine %r builder %r' % (sn, k, A[k], Bt[k]))
    cmpv(A['max_dd'], Bt['max_dd'], sn + ' max_dd')
    if len(A['episodes']) != len(Bt['episodes']): problems.append(sn + ': episode count differs'); continue
    for ea, eb in zip(A['episodes'], Bt['episodes']):
        for k in ('peak', 'trough', 'recovered', 'peak_is_first_obs'):
            if ea[k] != eb[k]: problems.append('%s episode %s %s: mine %r builder %r' % (sn, ea['peak'], k, ea[k], eb[k]))
        cmpv(ea['trough_dd'], eb['trough_dd'], '%s %s trough_dd' % (sn, ea['peak']))
        if set(ea['cross']) != set(eb['cross']): problems.append('%s %s: crossed thresholds differ' % (sn, ea['peak'])); continue
        for x in ea['cross']:
            ca, cb = ea['cross'][x], eb['cross'][x]
            if ca['date'] != cb['date']: problems.append('%s %s -%s%%: crossing date mine %s builder %s' % (sn, ea['peak'], x, ca['date'], cb['date']))
            for f in ca:
                if f == 'date': continue
                cmpv(ca[f], cb[f], '%s %s -%s%% %s' % (sn, ea['peak'], x, f))
    for x in A['cells']:
        ca, cb = A['cells'][x], Bt['cells'][x]
        if ca['n_cycles_crossed'] != cb['n_cycles_crossed']: problems.append('%s cell -%s%% n_cycles mine %d builder %d' % (sn, x, ca['n_cycles_crossed'], cb['n_cycles_crossed']))
        for f in ('r1x_1y', 'r3x_1y', 'r1x_3y', 'r3x_3y'):
            for q in ('n', 'n_positive'):
                if ca[f][q] != cb[f][q]: problems.append('%s cell -%s%% %s %s mine %r builder %r' % (sn, x, f, q, ca[f][q], cb[f][q]))
            for q in ('median', 'min', 'max'): cmpv(ca[f][q], cb[f][q], '%s cell -%s%% %s %s' % (sn, x, f, q))
res = dict(inputs=inputs, n_values_compared=n_val, max_abs_diff=worst, max_abs_diff_where=worst_where, max_abs_diff_pp=worst * 100, problems=problems, mine=mine)
json.dump(res, open(LANE + 'verify/v3_depth.json', 'w'), indent=1)
print('INPUTS', json.dumps(inputs))
print('values compared', n_val, '| max abs diff %.3g (%s)' % (worst, worst_where), '| structural problems:', problems)
def pc(x): return '  n/a' if x is None else ('%+.1f%%' % (100 * x) if abs(x) > 0.995 or abs(x) < 0.01 else '%+.0f%%' % (100 * x))
for sn, s in mine.items():
    print('\n==', sn, s['first'], s['last'], 'n', s['n_days'], 'maxDD %.1f%%' % (100 * s['max_dd']), 'cycles>=30%:', s['n_cycles_ge30'])
    for e in s['episodes']:
        for x, c in e['cross'].items():
            print('  peak %s trough %s (%.1f%%) rec %s | -%s%% on %s | 1x 1y %s 3y %s | 3x 1y %s 3y %s | 3x min<=3y %s | d0 3x 1y %s' % (
                e['peak'], e['trough'], 100 * e['trough_dd'], e['recovered'], x, c['date'], pc(c['r1x_1y']), pc(c['r1x_3y']), pc(c['r3x_1y']), pc(c['r3x_3y']),
                pc(c['min3x_within_3y']), pc(c['r3x_1y_d0'])))
    for x, cell in s['cells'].items():
        print('  cell -%s%% n=%d | ' % (x, cell['n_cycles_crossed']) + ' | '.join('%s med %s (%s ~ %s) pos %d/%d' % (
            f, pc(cell[f]['median']), pc(cell[f]['min']), pc(cell[f]['max']), cell[f]['n_positive'], cell[f]['n']) for f in ('r1x_1y', 'r1x_3y', 'r3x_1y', 'r3x_3y')))
print('\nsaved verify/v3_depth.json')
