"""Checks that must pass before any post-2014 day is scored. Output: PASS / FAIL, dates and whole-number counts only.

 CAL  calendar: last row 2026-08-31, no weekend, 248..254 rows per full year, NDX dates and calendar agree after 2014; block table.
 P1   slice parity: X, flags, features, v1 signal, level path, equity and liquidation value from the full-calendar run are
      bit-identical to the <= 2014 calendar run on every row up to 2014-12-31.
 P3   raw-level test: every raw reader is wrapped in memory; rows after a cut are deleted or replaced by noise; the whole chain is
      rebuilt; every cell up to the cut must be bit-identical. Control: y10 taken 5 rows early must be reported as FAIL.
 D1   coverage of each raw series, per year: calendar rows with no raw observation and the longest run of them.
 D2   rows whose value comes from a monthly fallback series.
 D3   value checks (zeros, jumps, duplicates).
 P4   the design account from the full calendar equals the account of the calendar cut at 2015-12-31 on blocks 0-9 (boolean).
 TAX  dates of the yearly tax payments of the design account.
(P2, the identity with the locked MS1 run and the recorded 30.53%, is t_old_end.py.)"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/-/research_xv1/code')
import xv1, std, xdata
from std import jp, ov, bk
import md, mkt

DRY = '--dry2014' in sys.argv            # mechanics test on the <= 2014 calendar only (CAL table and P3)
END = xv1.OLD_END if DRY else xv1.CAL_END
OK = True
def verdict(name, ok, **kw):
    global OK; OK &= bool(ok)
    print('%-4s %s %s' % (name, 'PASS' if ok else 'FAIL', json.dumps(kw, ensure_ascii=False, default=str)), flush=True)

def chain(end):
    """X, flags, features, v1 signal and account on the calendar up to `end` (fresh build, no module cache)"""
    R, M = jp.calendar(xv1.CAL_START, end); X = jp.mkX(R, M, 'NDX'); v = xv1.View(X); m = xv1._call(xv1.ref, v)
    return X, ov.flags_hist(X), v, m, xv1._run(v, m)

def diff(a, b): return xv1._same(np.asarray(a, dtype=float), np.asarray(b, dtype=float))

def compare(full, cut, n):
    """differing cells on the first n calendar rows"""
    X, F, v, m, rec = full; Xc, Fc, vc, mc, recc = cut; i0 = len(X) - v.T; T = n - i0; q = T - xv1.WARM
    return diff(X.values[:n], Xc.values[:n]) + diff(F.values[:n], Fc.values[:n]) + diff(v.feat[:T], vc.feat[:T]) + \
        diff(m['B'][:T], mc['B'][:T]) + diff(rec[:q], recc[:q])

# ---------------------------------------------------------------- CAL
X = xv1.frame(END); idx = X.index; cal = xv1.Cal(xv1.acc_dates(X))
per_year = pd.Series(1, index=idx).groupby(idx.year).sum()
full_years = per_year[(per_year.index >= 1985) & (per_year.index <= 2025)]
nd = mkt.pser('_NDX', 4); nd = nd[nd.index <= pd.Timestamp(END)]
miss_cal = nd.index.difference(idx); no_ndx = idx[idx >= nd.index[0]].difference(nd.index)
verdict('CAL', str(idx[-1].date()) == END and int((idx.dayofweek >= 5).sum()) == 0 and full_years.between(248, 254).all()
        and int((miss_cal.year > 2014).sum()) == 0 and int((no_ndx.year > 2014).sum()) == 0,
        last_row=idx[-1].date(), weekend_rows=int((idx.dayofweek >= 5).sum()), rows_per_year_min=int(full_years.min()), rows_per_year_max=int(full_years.max()),
        ndx_dates_missing_from_calendar=dict(upto2014=int((miss_cal.year <= 2014).sum()), after2014=int((miss_cal.year > 2014).sum())),
        calendar_rows_without_ndx=dict(upto2014=int((no_ndx.year <= 2014).sum()), after2014=int((no_ndx.year > 2014).sum())))
print('block table (dates and counts only):')
for r in cal.table(): print('  ', r)

# ---------------------------------------------------------------- P1
if not DRY:
    full = chain(END); n14 = int(idx.searchsorted(pd.Timestamp(xv1.OLD_END), side='right'))
    d = compare(full, chain(xv1.OLD_END), n14)
    verdict('P1', d == 0, rows_compared=n14, differing_cells=d)

# ---------------------------------------------------------------- P3
orig = dict(pser=mkt.pser, fred=mkt.fred, gs10=mkt.shiller_gs10, kf=md.kf, spx=mkt.spx)
state = dict(cut=None, mode='del', g=None, early=False)
def perturb(s):
    """delete or randomise every raw row dated after the cut (Series or DataFrame indexed by date)"""
    c = state['cut']
    if c is None: return s
    if state['mode'] == 'del': return s[s.index <= c]
    s = s.copy(); k = s.index > c; n = int(k.sum())
    if n == 0: return s
    if isinstance(s, pd.DataFrame): s.loc[k, :] = state['g'].normal(0, 0.02, (n, s.shape[1]))
    else: s[k] = np.abs(s[s.index <= c].iloc[-1] if (~k).any() else 1.0) * np.exp(np.cumsum(state['g'].normal(0, 0.02, n)))
    return s
mkt.pser = lambda k, col, f='panel_f32.npz.xz': perturb(orig['pser'](k, col, f))
mkt.fred = lambda path, col: perturb(orig['fred'](path, col))
mkt.shiller_gs10 = lambda: perturb(orig['gs10']())
md.kf = lambda: (orig['kf']() if state['mode'] != 'del' or state['cut'] is None else perturb(orig['kf']()))   # calendar dates: deletion only
mkt.spx = lambda: perturb(orig['spx']())
_macro = mkt.macro
def macro_early(i):
    M = _macro(i)
    if state['early']: M['y10'] = M['y10'].shift(-5)
    return M
mkt.macro = macro_early

def rebuilt(end):
    md._cache.clear(); xv1._FR.clear(); return chain(end)
g = np.random.default_rng(20261111)
cuts = sorted(set([int(cal.rows(b)[-1]) for b in range(xv1.NB) if len(cal.rows(b))][:-1]) | set(int(q) for q in g.integers(260, cal.n - 1, 12)))
i0 = len(idx) - cal.n - xv1.WARM
res = {}
for label, early in (('P3', False), ('P3-control', True)):
    cells = 0; bad = 0; runs = 0
    state.update(cut=None, early=early); base = rebuilt(END)
    for q in (cuts if not early else cuts[:6]):
        c = cal.dates[q]; n = i0 + xv1.WARM + q + 1
        for mode in ('del', 'noise'):
            state.update(cut=c, mode=mode, g=np.random.default_rng(q))
            k = compare(base, rebuilt(END if mode == 'noise' else str(c.date())), n); cells += k; bad += int(k > 0); runs += 1
    res[label] = (bad, cells, runs)
state.update(cut=None, early=False); mkt.macro = _macro
mkt.pser, mkt.fred, mkt.shiller_gs10, md.kf, mkt.spx = orig['pser'], orig['fred'], orig['gs10'], orig['kf'], orig['spx']
md._cache.clear(); xv1._FR.clear()
verdict('P3', res['P3'][0] == 0 and res['P3-control'][0] > 0, rebuilds=res['P3'][2], failed=res['P3'][0], differing_cells=res['P3'][1],
        control_y10_5_rows_early=dict(rebuilds=res['P3-control'][2], failed=res['P3-control'][0]))
if DRY:
    print('DRY RUN (<= 2014 calendar)', 'PASS' if OK else 'FAIL'); sys.exit(0 if OK else 1)

# ---------------------------------------------------------------- D1 coverage
X = xv1.frame(xv1.CAL_END); idx = X.index
raw = {'NDX': mkt.pser('_NDX', 4), 'IRX': mkt.pser('_IRX', 3), 'TNX': mkt.pser('_TNX', 3, 'panel_ext_f32.npz.xz'),
       'VIX': mkt.pser('_VIX', 3, 'panel_ext_f32.npz.xz'), 'DBAA': mkt.fred('macro_n/raw/DBAA.csv', 'DBAA'), 'DAAA': mkt.fred('macro_n/raw/DAAA.csv', 'DAAA')}
def runs(mask):
    best = cur = 0
    for x in mask:
        cur = cur + 1 if x else 0; best = max(best, cur)
    return best
ok1 = True; rep = {}
for k, s in raw.items():
    cidx = idx[idx >= s.index[0]]; missing = ~cidx.isin(s.index); yr = cidx.year
    tab = {int(y): (int(missing[yr == y].sum()), runs(missing[yr == y])) for y in sorted(set(yr))}
    y0 = int(s.index[0].year) + 1
    old = [tab[y] for y in tab if y0 <= y <= 2014]; new = {y: tab[y] for y in tab if y > 2014}
    th = (max(a for a, _ in old), max(b for _, b in old))
    last_ok = s.index[-1] >= (idx[-1] if k not in ('DBAA', 'DAAA') else idx[-2])
    over = {y: v for y, v in new.items() if v[0] > th[0] or v[1] > th[1]}
    ok1 &= last_ok and not over
    rep[k] = dict(first=s.index[0].date(), last=s.index[-1].date(), threshold_missing_rows_and_longest_run=th, years_after_2014_over_threshold=over,
                  worst_after_2014=(max(v[0] for v in new.values()), max(v[1] for v in new.values())))
verdict('D1', ok1, **rep)

# ---------------------------------------------------------------- D2 fallbacks
tnx = raw['TNX'].reindex(idx).ffill(); irx = raw['IRX'].reindex(idx).ffill(); csd = (raw['DBAA'] - raw['DAAA']).reindex(idx).ffill().shift(1)
fb = {k: s.isna() & (idx >= pd.Timestamp(xv1.ACC_START)) for k, s in (('y10_monthly', tnx), ('y3m_monthly', irx), ('cs_monthly', csd))}
verdict('D2', all(int(m[idx.year > 2014].sum()) == 0 for m in fb.values()),
        **{k: dict(upto2014=int(m[idx.year <= 2014].sum()), after2014=int(m[idx.year > 2014].sum())) for k, m in fb.items()})

# ---------------------------------------------------------------- D3 values
A = idx >= pd.Timestamp(xv1.ACC_START); y10 = X['y10']; y3m = X['y3m']; r = X['r']; yr = idx.year
def by(mask):
    m = np.asarray(mask) & A; o = pd.Series(m.astype(int), index=yr).groupby(level=0).sum()
    return dict(max_year_upto2014=int(o[o.index <= 2014].max()), max_year_after2014=int(o[o.index > 2014].max()), total_after2014=int(o[o.index > 2014].sum()))
irx_raw = raw['IRX']; z = irx_raw == 0
stop = dict(y10_le_0=by(y10 <= 0), ndx_abs_return_over_20pct=by(r.abs() > 0.20),
            y3m_zero_between_values_ge_050=dict(total_after2014=int((z & (irx_raw.shift(1) >= 0.5) & (irx_raw.shift(-1) >= 0.5))[irx_raw.index.year > 2014].sum())),
            duplicate_dates=dict(total_after2014=int(sum(int(s.index[s.index.year > 2014].duplicated().sum()) for s in raw.values()))))
thr = dict(y10_change_over_060pp=by(y10.diff().abs() > 0.60), y3m_change_over_100pp=by(y3m.diff().abs() > 1.00))
info = dict(rf_negative=by(X['rf'] < 0), ndx_return_exactly_0=by(r == 0))
ok3 = all(v['total_after2014'] == 0 for v in stop.values()) and all(v['max_year_after2014'] <= v['max_year_upto2014'] for v in thr.values())
verdict('D3', ok3, stop_counts=stop, threshold_counts=thr, report_only=info)

# ---------------------------------------------------------------- P4 (design account = cut-calendar account on blocks 0-9)
if not DRY:
    full = xv1._design_account(xv1.ref); keep = xv1.CAL_END; xv1.CAL_END = xv1.A_END
    try: cutacc = xv1._design_account(xv1.ref)
    finally: xv1.CAL_END = keep
    same = all(np.array_equal(full[b][f], cutacc[b][f]) for b in range(10) for f in ('x', 'lev', 'w', 'a0'))
    verdict('P4', same and sorted(full) == [b for b in range(xv1.NB) if b not in xv1.SEALED], blocks_scored=sorted(full), blocks_0_9_bit_identical=same)

# ---------------------------------------------------------------- TAX (design account: 252-row tax years from 1986-01-02 on the design calendar)
ca = xv1.Cal(xv1.acc_dates(xv1.frame(END))); days = np.flatnonzero(~np.isin(ca.blk, xv1.SEALED))
pay = [(str(ca.dates[days[k]].date()), int(ca.blk[days[k]]), bool(ca.rank[days[k]] < xv1.EMB)) for k in range(252, len(days), 252)]
print('TAX  design-account payment rows (date, block, inside the 63-row embargo): %d payments, %d inside an embargo' % (len(pay), sum(p[2] for p in pay)))
print('     ', ' '.join('%s%s' % (p[0], '*' if p[2] else '') for p in pay))
print('ALL CHECKS', 'PASS' if OK else 'FAIL')
sys.exit(0 if OK else 1)
