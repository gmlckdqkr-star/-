import pandas as pd, numpy as np
CUT = pd.Timestamp('2014-12-31')

def load(path):
    """Load a date,r csv and truncate at CUT immediately. Returns (series, n_rows_after_cut_in_file)."""
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    n_post = int((df.index > CUT).sum())
    df = df.loc[df.index <= CUT]
    return df, n_post

def check(path):
    df, n_post = load(path)
    out = {'n_post2014_in_file': n_post}
    out['cols'] = list(df.columns)
    out['index_is_datetime'] = isinstance(df.index, pd.DatetimeIndex)
    r = pd.to_numeric(df['r'], errors='coerce') if 'r' in df.columns else pd.Series(dtype=float)
    isn = r.isna().values
    run = mx = 0
    for v in isn:
        run = run + 1 if v else 0
        mx = max(mx, run)
    out['n_nan'] = int(isn.sum()); out['max_nan_run'] = int(mx)
    idx = df.index
    out['dup_dates'] = int(idx.duplicated().sum())
    out['monotonic'] = bool(idx.is_monotonic_increasing)
    out['n_le_minus1'] = int((r <= -1).sum())
    d = idx.values.astype('datetime64[D]')
    if len(d) > 1:
        miss = np.busday_count(d[:-1] + np.timedelta64(1, 'D'), d[1:])
        big = np.where(miss > 5)[0]
        out['max_missing_weekdays'] = int(miss.max())
        out['gaps_gt5_weekdays'] = [f"{str(d[i])}->{str(d[i+1])}({int(miss[i])})" for i in big]
    out['start'] = str(idx[0].date()); out['end'] = str(idx[-1].date()); out['n'] = int(len(r))
    out['ann_vol'] = round(float(r.std() * np.sqrt(252)), 4)
    return out
