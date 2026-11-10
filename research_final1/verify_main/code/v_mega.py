"""Independent verifier, lane MEGA (PRECOMMIT_FINAL1 section 3). Own parser; rows after 2014-12 are dropped immediately after
the text block is read and are never printed or used. Usage: python -I -B v_mega.py <me.zip> <ff.zip> <out.json>"""
import sys, io, json, zipfile, hashlib
import numpy as np, pandas as pd
ME, FF, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
CUT = 201412

def blocks(zp):
    """return {title: DataFrame} for every monthly (6-digit index) block of a Ken French CSV, cut at 2014-12."""
    z = zipfile.ZipFile(zp); lines = z.read(z.namelist()[0]).decode('latin1').split('\n')
    lines = [l.rstrip('\r') for l in lines]
    out = {}; i = 0; n = len(lines)
    while i < n:
        if lines[i].startswith(','):                       # header row of a block
            title = ''
            j = i - 1
            while j >= 0 and lines[j].strip() == '': j -= 1
            if j >= 0 and not lines[j].split(',')[0].strip().isdigit(): title = lines[j].strip()
            cols = [c.strip() for c in lines[i].split(',')][1:]
            k = i + 1; rows = []
            while k < n and lines[k].split(',')[0].strip().isdigit():
                rows.append(lines[k]); k += 1
            first = rows[0].split(',')[0].strip() if rows else ''
            if len(first) == 6:                             # monthly block
                df = pd.read_csv(io.StringIO('\n'.join(rows)), header=None, names=['ym'] + cols, skipinitialspace=True)
                df = df[df['ym'] <= CUT].set_index('ym').astype(float)      # CUT FIRST
                key = title if title not in out else title + '#2'
                out[key if key else 'block@%d' % i] = df
            i = k
        else:
            i += 1
    return out

me = blocks(ME); ff = blocks(FF)
print('ME monthly blocks:', [(k, v.shape, int(v.index.min()), int(v.index.max())) for k, v in me.items()])
print('FF monthly blocks:', [(k, v.shape, int(v.index.min()), int(v.index.max())) for k, v in ff.items()])
vw = [v for k, v in me.items() if 'Value Weight' in k and 'Monthly' in k]; assert len(vw) == 1; vw = vw[0]
ew = [v for k, v in me.items() if 'Equal Weight' in k and 'Monthly' in k][0]
nf = [v for k, v in me.items() if 'Number of Firms' in k][0]
sz = [v for k, v in me.items() if 'Average Firm Size' in k][0]
fac = list(ff.values())[0]
for d in (vw, ew, nf, sz, fac): assert d.index.max() == CUT and d.index.is_monotonic_increasing and d.index.is_unique
assert list(fac.columns) == ['Mkt-RF', 'SMB', 'HML', 'RF']
mkt = (fac['Mkt-RF'] + fac['RF']).reindex(vw.index)
assert mkt.notna().all()
miss = {c: int((vw[c] <= -99).sum()) for c in ('Hi 10', 'Hi 20', 'Lo 10')}
print('missing codes in VW cols (<=2014):', miss)

def nw_t(x, lag=6):
    x = np.asarray(x, float); n = len(x); m = x.mean(); e = x - m; lrv = e @ e / n
    for l in range(1, lag + 1): lrv += 2 * (1 - l / (lag + 1)) * (e[l:] @ e[:-l]) / n
    return float(m / np.sqrt(lrv / n))

def stat(port, bench, a, b):
    p = port.loc[a:b] / 100.0; q = bench.loc[a:b] / 100.0; x = p - q; n = len(x)
    return dict(n_months=int(n), ann_diff_pp=float(x.mean() * 12 * 100), t=float(x.mean() / x.std(ddof=1) * np.sqrt(n)), t_nw6=nw_t(x.values),
                cagr_port=float((1 + p).prod() ** (12 / n) - 1), cagr_mkt=float((1 + q).prod() ** (12 / n) - 1))
W = {'1963_2014': (196307, 201412), 'half1_1963_1988': (196307, 198812), 'half2_1989_2014': (198901, 201412), '1986_2014': (198601, 201412),
     '1926_2014': (192607, 201412), '1986_1999': (198601, 199912), '2000_2014': (200001, 201412)}
res = {}
for col in ('Hi 10', 'Hi 20', 'Lo 10'):
    res[col] = {w: stat(vw[col], mkt, a, b) for w, (a, b) in W.items()}
for col in ('Hi 10', 'Hi 20'):
    r = res[col]
    r['PASS'] = bool(r['1963_2014']['ann_diff_pp'] >= 1.0 and r['1963_2014']['t'] >= 2 and r['half1_1963_1988']['ann_diff_pp'] > 0 and r['half2_1989_2014']['ann_diff_pp'] > 0)
    print(col, 'PASS', r['PASS'])
    for w in W: print('   %-16s diff %+.4f pp/yr  t %+.3f (NW6 %+.3f)  port %.3f%% mkt %.3f%% n %d' % (
        w, r[w]['ann_diff_pp'], r[w]['t'], r[w]['t_nw6'], 100 * r[w]['cagr_port'], 100 * r[w]['cagr_mkt'], r[w]['n_months']))
# cross-check of the market definition: cap-weighted aggregate of the ten deciles (weights = firms x average firm size) vs Mkt-RF+RF
dec = ['Lo 10', '2-Dec', '3-Dec', '4-Dec', '5-Dec', '6-Dec', '7-Dec', '8-Dec', '9-Dec', 'Hi 10']
cap = (nf[dec] * sz[dec])
agg = (vw[dec] * cap).sum(axis=1) / cap.sum(axis=1)
dd = (agg - mkt).loc[196307:201412]
res['mkt_check'] = dict(corr=float(np.corrcoef(agg.loc[196307:201412], mkt.loc[196307:201412])[0, 1]), mean_abs_diff_pp_month=float(dd.abs().mean()),
                        ann_mean_diff_pp=float(dd.mean() * 12), hi10_minus_decile_aggregate_ann_pp=float((vw['Hi 10'] - agg).loc[196307:201412].mean() * 12),
                        hi20_minus_decile_aggregate_ann_pp=float((vw['Hi 20'] - agg).loc[196307:201412].mean() * 12))
print('mkt_check', res['mkt_check'])
# how many firms are in the top decile / quintile (proxy gap vs "top 10-30 stocks"), <=2014 only
res['n_firms'] = {str(ym): dict(hi10=int(nf.loc[ym, 'Hi 10']), hi20=int(nf.loc[ym, 'Hi 20']), all=int(nf.loc[ym, dec].sum())) for ym in (196307, 198601, 200001, 201412)}
res['hi10_cap_share'] = {str(ym): float(cap.loc[ym, 'Hi 10'] / cap.loc[ym].sum()) for ym in (196307, 198601, 200001, 201412)}
print('n_firms', res['n_firms']); print('hi10 cap share', res['hi10_cap_share'])
res['source'] = dict(sha_me=hashlib.sha256(open(ME, 'rb').read()).hexdigest(), sha_ff=hashlib.sha256(open(FF, 'rb').read()).hexdigest(),
                     max_row_used=int(vw.index.max()), table='Average Value Weight Returns -- Monthly', market='Mkt-RF + RF (F-F Research Data Factors, monthly)')
json.dump(res, open(OUT, 'w'), indent=1)
