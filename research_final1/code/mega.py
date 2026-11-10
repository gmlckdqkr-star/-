"""FINAL1 lane MEGA (PRECOMMIT_FINAL1 section 3): does concentrating in the largest stocks beat the market? Ken French
'Portfolios Formed on Size' value-weighted monthly, rows <= 2014-12 only (later rows are dropped while parsing, never printed)."""
import io, sys, json, zipfile, hashlib, numpy as np, pandas as pd
D = '/tmp/final1_main/kf/'
def section(zpath, start_marker=None):
    z = zipfile.ZipFile(zpath); txt = z.read(z.namelist()[0]).decode('latin1').splitlines()
    i0 = 0
    if start_marker:
        i0 = next(i for i, l in enumerate(txt) if start_marker in l) + 1
    else:
        i0 = next(i for i, l in enumerate(txt) if l.strip().startswith(',')) 
    hdr = [h.strip() for h in txt[i0].split(',')]; rows = []
    for l in txt[i0 + 1:]:
        p = [x.strip() for x in l.split(',')]
        if not p[0].isdigit() or len(p[0]) != 6: break
        if int(p[0]) > 201412: continue
        rows.append([int(p[0])] + [float(x) for x in p[1:]])
    df = pd.DataFrame(rows, columns=['ym'] + hdr[1:]).set_index('ym')
    return df
me = section(D + 'me.zip', 'Value Weight Returns -- Monthly'); ff = section(D + 'ff.zip')
assert me.index.max() == 201412 and ff.index.max() == 201412
mkt = (ff['Mkt-RF'] + ff['RF']).reindex(me.index)
def stat(col, a, b):
    x = (me[col] - mkt).loc[a:b] / 100.0; n = len(x)
    return dict(n_months=int(n), ann_diff_pp=float(x.mean() * 12 * 100), t=float(x.mean() / x.std(ddof=1) * np.sqrt(n)),
                cagr_port=float(((1 + me[col].loc[a:b] / 100).prod()) ** (12 / n) - 1), cagr_mkt=float(((1 + mkt.loc[a:b] / 100).prod()) ** (12 / n) - 1))
W = {'1963_2014': (196307, 201412), 'half1_1963_1988': (196307, 198812), 'half2_1989_2014': (198901, 201412), '1986_2014': (198601, 201412),
     '1926_2014': (192607, 201412), '1986_1999': (198601, 199912), '2000_2014': (200001, 201412)}
res = {c: {w: stat(c, a, b) for w, (a, b) in W.items()} for c in ('Hi 10', 'Hi 20', 'Lo 10')}
for c in ('Hi 10', 'Hi 20'):
    r = res[c]; res[c]['PASS'] = bool(r['1963_2014']['ann_diff_pp'] >= 1.0 and r['1963_2014']['t'] >= 2 and r['half1_1963_1988']['ann_diff_pp'] > 0 and r['half2_1989_2014']['ann_diff_pp'] > 0)
    print(c, 'PASS', res[c]['PASS'])
    for w in W: print('  %-16s diff %+.2fpp/yr t %+.2f  port %.2f%% mkt %.2f%%  n %d' % (w, r[w]['ann_diff_pp'], r[w]['t'], 100 * r[w]['cagr_port'], 100 * r[w]['cagr_mkt'], r[w]['n_months']))
res['source'] = dict(url_me='https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Portfolios_Formed_on_ME_CSV.zip',
                     url_ff='https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip',
                     sha_me=hashlib.sha256(open(D + 'me.zip', 'rb').read()).hexdigest(), sha_ff=hashlib.sha256(open(D + 'ff.zip', 'rb').read()).hexdigest(),
                     note='current vintage downloaded 2026-11-10; rows after 2014-12 dropped at parse; value-weighted monthly table; Mkt = Mkt-RF + RF')
json.dump(res, open('/mnt/project-files/research/final1/results/mega.json', 'w'), indent=1)
