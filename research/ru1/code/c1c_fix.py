"""C1c: which 3-month series reproduces the research levels? Candidates the app could fetch for free."""
import sys, json, glob, csv, io, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ru1/code')
from c1lib import *
def bill_csv():
    d = {}
    for f in sorted(glob.glob('/mnt/project-files/research/ru1/data/bill*.csv')):
        for row in csv.DictReader(io.StringIO(open(f).read())):
            try:
                k = pd.Timestamp(row['Date']).strftime('%Y-%m-%d'); d[k] = float(row['13 WEEKS BANK DISCOUNT'])
            except (ValueError, TypeError): pass
    return {k: v for k, v in d.items() if k <= '2014-12-31'}
dtb3 = pd.read_csv('/mnt/project-files/research/data/deep_history/raw/DTB3.csv', na_values='.', parse_dates=['observation_date']).set_index('observation_date')['DTB3'].dropna()
dtb3 = dtb3[dtb3.index <= END]; dtb3 = {k.strftime('%Y-%m-%d'): float(v) for k, v in dtb3.items()}
bill = bill_csv()
def combo(y10src, y3src):
    keys = sorted(set(y10src) & set(y3src)); return {k: (y10src[k], y3src[k]) for k in keys}
y10_res = {k: v[0] for k, v in res_rates.items()}; y3_res = {k: v[1] for k, v in res_rates.items()}
y10_cmt = {k: v[0] for k, v in cmt.items()}; y3_cmt = {k: v[1] for k, v in cmt.items()}
bey = {k: 100 * 365 * (v / 100) / (360 - 91 * (v / 100)) for k, v in y3_res.items()}   # IRX discount -> bond-equivalent
out = {}
def sp_check(name, rates, lo):
    ks = [k for k in sorted(rates) if k >= lo and k in res_rates]
    a = np.array([res_rates[k][0] - res_rates[k][1] for k in ks]); b = np.array([rates[k][0] - rates[k][1] for k in ks])
    y3d = np.median([rates[k][1] - res_rates[k][1] for k in ks])
    return dict(days=len(ks), sign_differs=int(((a < 0) != (b < 0)).sum()), y3m_med_diff=float(y3d))
VAR = {
 'research_IRX_TNX': res_rates,
 'IRX_CMT10': combo(y10_cmt, y3_res),
 'CMT3m_TNX': combo(y10_res, y3_cmt),
 'app_CMT_CMT': cmt,
 'DTB3_CMT10': combo(y10_cmt, dtb3),
 'BEY(IRX)_TNX': combo(y10_res, bey),
}
out['C1c_1991'] = {}
for nm, rt in VAR.items():
    out['C1c_1991'][nm] = sp_check(nm, rt, '1990-01-02')
print('spread checks 1990-2014', json.dumps(out['C1c_1991']), flush=True)
out['C1c_levels_1991'] = compare('C1c', VAR, '1990-01-02', '1991-09-03')
VAR2 = {'research_IRX_TNX': res_rates, 'app_CMT_CMT': cmt, 'billCSV13w_CMT10': combo(y10_cmt, bill), 'DTB3_CMT10': combo(y10_cmt, dtb3)}
out['C1c_2002_spread'] = {nm: sp_check(nm, rt, '2002-01-02') for nm, rt in VAR2.items()}
print('spread checks 2002-2014', json.dumps(out['C1c_2002_spread']), flush=True)
out['C1c_levels_2003'] = compare('C1c2003', VAR2, '2002-01-02', '2003-08-06')
# the app as fixed: QQQ index unchanged, bill CSV 3m + CMT 10y
out['C1c_app_fixed_QQQ_2003'] = compare('C1cQQQ', {'research_NDX_IRX_TNX': (lvl, res_rates), 'app_QQQclose_CMT': (qc, cmt),
    'fixed_QQQclose_bill': (qc, combo(y10_cmt, bill)), 'fixed_NDX_bill': (lvl, combo(y10_cmt, bill))}, '2002-01-02', '2003-08-06')
json.dump(out, open('/mnt/project-files/research/ru1/results/c1c_fix.json', 'w'), indent=1)
