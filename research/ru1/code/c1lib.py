"""C1: the app's v1 inputs (QQQ adjusted closes + Treasury CMT 3m/10y) vs the research inputs (NDX price + ^IRX/^TNX).
Uses the app's own v1_signal.py (PC copy, sha in results). <=2014 only."""
import sys, json, glob, hashlib, numpy as np, pandas as pd
sys.path.insert(0, '/tmp/claude-0/ru1_app'); sys.path.insert(0, '/mnt/project-files/research/acct3/code'); sys.path.insert(0, '/mnt/project-files/research/ru1/code')
from ait_accounts import v1_signal as V
import ac3, ru, std
from std import jp, ov
sys.path.insert(0, '/mnt/project-files/research/crash_overlay/code'); import mkt
END = pd.Timestamp('2014-12-31')
R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX'); assert X.index.max() <= END
idx = X.index; lvl = X['p']
# Treasury CMT (the app's own source and parser)
cmt = {}
for f in sorted(glob.glob('/mnt/project-files/research/ru1/data/tr*.csv')):
    cmt.update(V.parse_treasury_csv(open(f).read()))
cmt = {d: v for d, v in cmt.items() if d <= '2014-12-31'}
# QQQ (Yahoo panel): col 3 close (split-adjusted), col 4 adj close (split + dividends)
qc = mkt.pser('QQQ', 3); qa = mkt.pser('QQQ', 4); qc = qc[qc.index <= END]; qa = qa[qa.index <= END]
def rows_for(price, rates, first):
    """price: Series on dates; rates: dict date->(y10,y3m); rows from `first`."""
    p = price[price.index >= pd.Timestamp(first)]
    pr = [(d.strftime('%Y-%m-%d'), float(v)) for d, v in p.items()]
    return V.align_rows(pr, rates)
res_rates = {d.strftime('%Y-%m-%d'): (float(a), float(b)) for d, a, b in zip(idx, X['y10'].values, X['y3m'].values)}
ref = ac3.prep()['real_ndx_86_14']
OUT = {'v1_signal_sha256': hashlib.sha256(open('/tmp/claude-0/ru1_app/ait_accounts/v1_signal.py', 'rb').read()).hexdigest()}
# ---- parity: app code on research inputs from 1984 vs research executed levels from 1986-01-02
rows = rows_for(lvl, res_rates, '1984-01-03'); dates = [r[0] for r in rows]
st = dates.index('1986-01-02'); res = V.compute_rows(rows, st)
inf = np.array(res['inforce'][st:], float); Lr = ref['L'][0]
OUT['parity_mismatch_days'] = int(np.sum(np.abs(inf - Lr[:len(inf)]) > 1e-9)); OUT['parity_days'] = int(len(inf))
print('parity', OUT['parity_mismatch_days'], 'of', len(inf), flush=True)
# ---- account helper: user account from start date to 2014-12-31 on research NDX returns, given in-force levels by date
r_all = X['r'].values; rf_all = X['rf'].values
def account(levels_by_date, start):
    j = idx.get_loc(pd.Timestamp(start)); L = levels_by_date.reindex(idx[j:]).ffill().values
    T = ru.WARM + len(L); r = np.zeros(T); rf = np.zeros(T); r[ru.WARM:] = r_all[j:]; rf[ru.WARM:] = rf_all[j:]
    o = np.zeros(9); eu = np.zeros(len(L)); ek = np.zeros(len(L))
    ru.acct(r, rf, np.ascontiguousarray(L), np.ones(T), np.zeros(len(L)), 0, 0, 0.0, .003, .22, .25, .0245, 1.0, o, eu, ek)
    y = len(L) / 252
    return dict(cagr=float(ru.cagr(o[0], y)), mdd=float(o[2]), trades=int(o[4]), years=y)
def run_variant(price, rates, first, start):
    rows = rows_for(price, rates, first); d = [r[0] for r in rows]
    s = next(i for i, x in enumerate(d) if x >= start); assert s >= V.MIN_ROWS_BEFORE_START, (s, start)
    rr = V.compute_rows(rows, s)
    inf = pd.Series(rr['inforce'][s:], index=pd.to_datetime(d[s:]), dtype=float)
    held = pd.Series(rr['held'], index=pd.to_datetime(d), dtype=float)
    return inf, held, d[s]
def compare(name, variants, first, start):
    variants = {k: (v if isinstance(v, tuple) else (lvl, v)) for k, v in variants.items()}
    o = {}; base = None
    for vn, (price, rates) in variants.items():
        inf, held, s0 = run_variant(price, rates, first, start)
        a = account(inf, s0)
        if base is None: base = (inf, held, a)
        bi = base[0].reindex(inf.index).ffill(); mis = int(np.sum(np.abs(inf.values - bi.values) > 1e-9))
        a.update(start=s0, mismatch_days=mis, days=int(len(inf)), mismatch_share=mis / len(inf), d_cagr_vs_first=a['cagr'] - base[2]['cagr'])
        o[vn] = a; print(name, vn, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in a.items()}, flush=True)
    return o
