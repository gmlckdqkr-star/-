"""OV1-D step 1: data-quality inspection of the scouted Tankan data. NO returns, NO labels, NO v1 states, NO on-flags.
Parses the raw BoJ CSV independently, rebuilds the surprise table, compares it with the scout's cut CSV, rolls the
usable dates onto the trading calendar and checks threshold availability. Writes results/s1_inspect.json.
Run: ~/.cache/lab/ms1-venv/bin/python -B s1_inspect.py"""
import sys, json, io, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std, jp  # noqa
LANE = '/mnt/project-files/research/ov1/lanes/OV1-D/'
RAW = LANE + 'data/boj_tankan_raw.csv'; CUT = LANE + 'data/boj_tankan_cut_le2014.csv'
CODES = dict(actual_mfg='TK99F1000601GCQ01000', forecast_mfg='TK99F1000601GCQ11000',
             actual_el='TK99F1150601GCQ01000', forecast_el='TK99F1150601GCQ11000')

def parse_raw():
    lines = open(RAW, encoding='utf-8').read().splitlines()
    k = [i for i, l in enumerate(lines) if l.startswith('SERIES_CODE,')][0]
    df = pd.read_csv(io.StringIO('\n'.join(lines[k:])), dtype=str)
    df['v'] = pd.to_numeric(df['VALUES'].replace('null', np.nan), errors='coerce')
    w = df.pivot(index='SURVEY_DATES', columns='SERIES_CODE', values='v')
    w = w.rename(columns={v: k for k, v in CODES.items()})[list(CODES)]
    w.index = w.index.astype(int); return w.sort_index(), df

def qend(code):
    y, q = divmod(int(code), 100); return pd.Timestamp(y, 3 * q, 1) + pd.offsets.MonthEnd(0)

def ucal(code):   # 1st calendar day of the 2nd month after the quarter-end month
    e = qend(code); return pd.Timestamp(e.year, e.month, 1) + pd.DateOffset(months=2)

w, df = parse_raw()
out = dict(raw_rows=int(len(df)), series_rows={k: int(df['SERIES_CODE'].eq(v).sum()) for k, v in CODES.items()},
           quarters=int(len(w)), first_q=int(w.index.min()), last_q=int(w.index.max()))
assert w.index.max() <= 201404
out['null_counts'] = {k: int(w[k].isna().sum()) for k in CODES}
out['null_quarters'] = {k: [int(q) for q in w.index[w[k].isna()]] for k in CODES}
out['non_integer_values'] = int(sum(((w[k].dropna() % 1) != 0).sum() for k in CODES))
quarters_expected = [y * 100 + q for y in range(1974, 2015) for q in range(1, 5)]
out['missing_quarter_codes'] = [q for q in quarters_expected if q not in w.index]

t = pd.DataFrame(index=w.index)
t['s_mfg'] = w['actual_mfg'] - w['forecast_mfg']; t['s_el'] = w['actual_el'] - w['forecast_el']
t['surprise'] = (t['s_mfg'] + t['s_el']) / 2
t.loc[200401, 'surprise'] = np.nan   # BoJ continuity break (Dec 2003 -> Mar 2004 survey)
t['quarter_end'] = [qend(q) for q in t.index]; t['u_cal'] = [ucal(q) for q in t.index]

c = pd.read_csv(CUT)
c = c.set_index('quarter_code')
out['cut_rows'] = int(len(c))
d = (c['surprise_q'] - t['surprise']).abs()
out['cut_vs_rebuild_max_abs_diff'] = float(d.max()) if d.notna().any() else None
out['cut_vs_rebuild_nan_mismatch'] = int((c['surprise_q'].isna() != t['surprise'].isna()).sum())
out['cut_ucal_mismatch'] = int((pd.to_datetime(c['usable_from_calendar']).values != t['u_cal'].values).sum())
for k in CODES: out['cut_col_diff_' + k] = float((c[k] - w[k]).abs().max())

v = t['surprise'].dropna()
out['n_valid_surprise'] = int(len(v)); out['nan_surprise_quarters'] = [int(q) for q in t.index[t['surprise'].isna()]]
out['surprise_descr'] = dict(mean=float(v.mean()), sd=float(v.std()), min=float(v.min()), max=float(v.max()),
                             share_negative=float((v < 0).mean()), share_multiple_of_half=float(((v * 2) % 1 == 0).mean()))
out['example_2008Q4'] = dict(actual_mfg=float(w.loc[200804, 'actual_mfg']), forecast_mfg=float(w.loc[200804, 'forecast_mfg']),
                             actual_el=float(w.loc[200804, 'actual_el']), forecast_el=float(w.loc[200804, 'forecast_el']))

# trading calendar (Ken French dates, shared by NDX and SPX frames)
R, M = jp.calendar('1928-01-03', '2014-12-31'); cal = R.index
pos = cal.searchsorted(t['u_cal'].values)            # first trading day on/after u_cal
t['u_trd'] = [cal[p] if p < len(cal) else pd.NaT for p in pos]
lagd = (t['u_trd'] - t['u_cal']).dt.days.dropna()
out['u_roll_calendar_days_max'] = int(lagd.max()); out['u_after_2014'] = [int(q) for q in t.index[t['u_trd'].isna()]]
vt = t.dropna(subset=['surprise', 'u_trd'])
gaps = np.diff(cal.get_indexer(vt['u_trd']))
out['release_gap_trading_days'] = dict(min=int(gaps.min()), max=int(gaps.max()), median=float(np.median(gaps)),
                                       note='max includes the 2004Q1 NaN skip')
# threshold availability: >= 20 valid surprises with U < U_q
cnt = np.arange(len(vt))                              # number of earlier valid releases (U strictly earlier)
first = vt.index[cnt >= 20][0]
out['first_release_with_threshold'] = dict(quarter=int(first), u_trading=str(vt.loc[first, 'u_trd'].date()),
                                           n_prior=int(cnt[list(vt.index).index(first)]))
out['twentieth_valid_surprise'] = dict(quarter=int(vt.index[19]), u_trading=str(vt.loc[vt.index[19], 'u_trd'].date()))
act = vt[cnt >= 20]
out['releases_with_threshold'] = dict(
    spx_era_before_1986=int((act['u_trd'] < pd.Timestamp('1986-01-02')).sum()),
    early_ndx_1986_1999=int(((act['u_trd'] >= pd.Timestamp('1986-01-02')) & (act['u_trd'] <= pd.Timestamp('1999-12-31'))).sum()),
    unseen_2000_2014=int((act['u_trd'] >= pd.Timestamp('2000-01-03')).sum()))
out['last_release_in_sample'] = dict(quarter=int(vt.index[-1]), u_trading=str(vt['u_trd'].iloc[-1].date()))
out['spec_note'] = ('U < U_q strictly with >= 20 prior: the 20th valid surprise is released at its own U, so the first '
                    'release that HAS a threshold is the 21st valid surprise.')
t.to_csv(LANE + 'results/s1_surprise_table.csv')
json.dump(out, open(LANE + 'results/s1_inspect.json', 'w'), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
