"""OV1-C signal construction (foreign central-bank synchronized tightening). <=2014 data only.
X_c = change index per country c in {JP, DE_EZ, UK}: start level + cumulative sum of the source's own period-to-period
changes, with the change at each splice (JP 1985-07 discount->call; DE->EZ 1999-01) set to 0.
Each value is indexed by its AVAILABILITY calendar date (point-in-time rule):
  monthly obs for month m (dated m-01)  -> available from (m+1)-01, i.e. first trading day on/after the 1st of m+1
  ECB daily obs dated d                 -> available from d+1 calendar day, i.e. the first trading day after d
Forward-filled onto any trading calendar (L._onto does union+ffill).  Rows dated after 2014-12-31 are never read."""
import numpy as np, pandas as pd
D = '/mnt/project-files/research/ov1/lanes/OV1-C/data/'
CUT = pd.Timestamp('2014-12-31')

def _rd(fn, col=1):
    s = pd.read_csv(D + fn); s.columns = ['date'] + list(s.columns[1:])
    s['date'] = pd.to_datetime(s['date']); s = s[s['date'] <= CUT]
    v = pd.to_numeric(s.iloc[:, col], errors='coerce'); return pd.Series(v.values, index=s['date'].values).sort_index()

def _avail_monthly(s):   # obs dated m-01 -> availability date (m+1)-01
    return pd.Series(s.values, index=s.index + pd.offsets.MonthBegin(1))

def _avail_daily(s):     # obs dated d -> availability date d+1 (first trading day after d after ffill)
    return pd.Series(s.values, index=s.index + pd.Timedelta(days=1))

def _splice(a, b):
    """a, b: level series on availability dates (a ends before b starts). Returns change-index:
    a's level path, then b's own changes only (change at the join := 0)."""
    a = a.dropna(); b = b.dropna(); b = b[b.index > a.index[-1]]
    xb = a.iloc[-1] + (b - b.iloc[0])          # join change set to 0
    return pd.concat([a, xb])

def raw_sources():
    jpd = _rd('cut_INTDSRJPM193N.csv'); jpd = jpd[jpd.index <= pd.Timestamp('1985-06-01')]
    jpc = _rd('cut_IRSTCI01JPM156N.csv'); jpc = jpc[jpc.index >= pd.Timestamp('1985-07-01')]
    de = _rd('cut_ALFRED_INTDSRDEM193N_v20141231.csv'); de = de[de.index <= pd.Timestamp('1998-12-01')]
    ez = _rd('derived_ecb_mro_filled.csv'); ez = ez[ez.index >= pd.Timestamp('1999-01-01')]
    uk = _rd('cut_INTDSRGBM193N.csv'); uk = uk[uk.index <= pd.Timestamp('2013-03-01')]
    return dict(jp_disc=jpd, jp_call=jpc, de=de, ez=ez, uk=uk)

def change_index():
    """dict c -> pd.Series of X_c on availability dates (calendar dates; ffill onto trading days)."""
    S = raw_sources()
    xjp = _splice(_avail_monthly(S['jp_disc']), _avail_monthly(S['jp_call']))
    xde = _splice(_avail_monthly(S['de']), _avail_daily(S['ez']))
    xuk = _avail_monthly(S['uk'])                  # 2013-04..2014-12 carried flat at 0.50 (BOERUKM-confirmed) by ffill
    out = {}
    for k, x in (('JP', xjp), ('DE_EZ', xde), ('UK', xuk)):
        x = x[~x.index.duplicated(keep='last')].sort_index(); out[k] = x[x.index <= CUT]
    return out

def on_matrix(V, H=126, thr=0.25, valid_from=None):
    """V: dict c -> (P,T) array of X_c along each row (calendar or path). Returns ON (P,T) bool and up counts.
    up_c(t) = X_c(t) - X_c(t-H) >= thr (H positions back along the row); undefined (NaN) -> not up AND row-day invalid.
    ON(t) = sum_c up_c(t) >= 2, and False wherever any of the three differences is undefined (fallback = v1)."""
    ups = []; ok = None
    for k in ('JP', 'DE_EZ', 'UK'):
        x = V[k]; d = np.full(x.shape, np.nan); d[:, H:] = x[:, H:] - x[:, :-H]
        good = ~np.isnan(d); ok = good if ok is None else (ok & good)
        ups.append(np.where(good, d >= thr - 1e-9, False))
    cnt = np.sum(ups, axis=0); on = (cnt >= 2) & ok
    return on, cnt, ok
