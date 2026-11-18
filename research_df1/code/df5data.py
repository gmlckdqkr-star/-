"""DF5 asset panel per world (PRECOMMIT_DF5.md section 2). <=2014 only.
Every asset series lives on the source calendar w['S'].index and is moved onto the paths with the world's own index ii
(same dates together -> crash-time correlations kept). Neutralization means are taken over the days the world actually samples
(all paths, t >= WARM). Returns are daily decimals; the panel holds NET returns (after neutralization and expense ratio) and the
income part INC that is taxed 15.4% when paid (dfk HV=1 rule) or HV=2 for the T-bill ETF."""
import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df5lib as L
WARM = 300
END = pd.Timestamp('2014-12-31')
DQ = 0.0055                                   # QQQ 1999-2014 measured dividend yield (proxy for all years)
ERQ = 0.002 - DQ * (1 - 0.154)                # QQQ leg: expense minus after-tax dividend (same value used in dfe erq)
DY = 0.02                                     # equity income part taxed 15.4% (S&P-like dividend proxy)
CLEAN = '/mnt/project-files/research/df5/data/clean/'
# id -> (kind, expense ratio). kind: 'eq' = equity-neutral (mean moved to SPX mean), 'zx' = zero excess over rf, 'bond' = zero excess + coupon
SLEEVES = {'DEF3': ('eq', 0.0015), 'VALUE': ('eq', 0.0020), 'SMALL': ('eq', 0.0020), 'MOM': ('eq', 0.0015), 'SOX': ('eq', 0.0047),
           'TECH': ('eq', 0.0015), 'ENER': ('eq', 0.0015), 'FIN': ('eq', 0.0015), 'MANU': ('eq', 0.0015), 'SHOP': ('eq', 0.0015),
           'TELE': ('eq', 0.0015), 'HLTH': ('eq', 0.0015), 'UTIL': ('eq', 0.0015), 'STAP': ('eq', 0.0015),
           'DEVX': ('eq', 0.0033), 'EM': ('eq', 0.0068), 'GOLD': ('zx', 0.0040), 'CMDTY': ('zx', 0.0085), 'USD': ('zx', 0.0078),
           'LTT': ('bond', 0.0015)}
FILES = {}                                    # id -> csv path (set by set_files from the locked manifest choice)
ELIG = {}                                     # id -> bool (coverage 1985-03-01..2014-12-31 without gaps)

def set_files(d):
    FILES.clear(); FILES.update(d)

def _csv(path):
    s = pd.read_csv(path, parse_dates=['date']).set_index('date')['r'].astype(float)
    return s[s.index <= END]

_SRC = {}
def src_series():
    """source-calendar daily returns of every asset (full history <=2014), plus y30 and the DEF3 basket"""
    if _SRC: return _SRC
    for k, p in FILES.items(): _SRC[k] = _csv(p)
    if all(x in _SRC for x in ('STAP', 'UTIL', 'HLTH')):
        idx = _SRC['STAP'].index.intersection(_SRC['UTIL'].index).intersection(_SRC['HLTH'].index)
        _SRC['DEF3'] = (_SRC['STAP'].reindex(idx) + _SRC['UTIL'].reindex(idx) + _SRC['HLTH'].reindex(idx)) / 3.0
    import lzma, io
    d = np.load(io.BytesIO(lzma.open('/mnt/project-files/research/data/panel_ext_f32.npz.xz').read()), allow_pickle=True)
    ts = pd.to_datetime(d['_TYX|ts'], unit='s').normalize(); v = d['_TYX|v'][:, 3].astype(float)
    y = pd.Series(v, index=ts); y = y[(y.index <= END) & (y > 0)]; y = y[~y.index.duplicated()]
    _SRC['y30'] = y
    return _SRC

def eligibility():
    S = src_series(); out = {}
    for k in SLEEVES:
        if k not in S: out[k] = False; continue
        s = S[k]; ok = s.first_valid_index() is not None and s.first_valid_index() <= pd.Timestamp('1985-03-01')
        out[k] = bool(ok)
    ELIG.clear(); ELIG.update(out); return out

def _on_cal(series, idx):
    """compound off-calendar days into the next calendar day is done upstream; here: reindex, missing -> 0 (counted)"""
    s = series.reindex(idx)
    return s.values.astype(float), int(np.isnan(s.values[(idx >= series.index.min())]).sum())

_P = {}
def panel(wname, raw=False):
    """dict id -> (RET (P,T) net daily return, INC (P,T) or float, HV) for the world; plus 'meta' (shifts, gaps)."""
    key = (wname, raw)
    if key in _P: return _P[key]
    w = L.world(wname); m = w['m']; ii = w['ii']; idx = w['S'].index
    r = np.nan_to_num(m['r']); rf = np.nan_to_num(m['rf']); P, T = r.shape
    sel = np.zeros((P, T), bool); sel[:, WARM:] = True
    def mean(a): return float(a[sel].mean())
    S = src_series(); out = {}; meta = {'shift': {}, 'gaps': {}, 'missing': [], 'nanfrac': {}}
    # NDX family
    out['QQQ'] = (r - ERQ / 252, 0.0, 1)
    out['QLD'] = (2 * r - rf - 0.017 / 252, 0.0, 1)
    out['TQQQ'] = (3 * r - 2 * rf - 0.0245 / 252, 0.0, 1)
    out['TBILL'] = (rf - 0.001 / 252, 0.0, 2)
    # 10y bond (same series the dfe engine uses: m['rb'], coupon m['cpn'])
    rb = np.nan_to_num(m['rb']); sh = 0.0 if raw else mean(rb - rf)
    if wname in ('S55', 'S29') and sh < 0: sh = 0.0
    meta['shift']['B10'] = sh
    out['B10'] = (rb - sh - 0.0015 / 252, np.nan_to_num(m['cpn']), 1)
    # SPX (anchor, total return) from the source frame
    spx = np.nan_to_num(w['S']['SPX'].values.astype(float)[ii])
    out['SPX'] = (spx - 0.001 / 252, DY / 252, 1)
    spxp = spx - DY / 252
    out['SSO'] = (2 * spxp - rf - 0.017 / 252, 0.0, 1)
    out['UPRO'] = (3 * spxp - 2 * rf - 0.0245 / 252, 0.0, 1)
    mspx = mean(spx)
    for k, (kind, er) in SLEEVES.items():
        if k not in S: meta['missing'].append(k); continue
        s = S[k]
        a, gaps = _on_cal(s, idx); meta['gaps'][k] = gaps
        A = a[ii]; nanfrac = float(np.isnan(A[:, WARM:]).mean())
        meta['nanfrac'][k] = nanfrac
        if nanfrac > 0: meta['missing'].append('%s(nan %.4f)' % (k, nanfrac))
        A = np.nan_to_num(A)
        if raw: sh = 0.0
        elif kind == 'eq': sh = mean(A) - mspx
        else:
            sh = mean(A - rf)
            if wname in ('S55', 'S29') and sh < 0: sh = 0.0
        meta['shift'][k] = sh
        net = A - sh - er / 252
        if kind == 'bond':
            y = S['y30'].reindex(idx).ffill(limit=5); cp = np.r_[np.nan, y.values[:-1]] / 100.0 / 252.0
            out[k] = (net, np.nan_to_num(cp[ii]), 1)
            out['TMF'] = (3 * (A - sh) - 2 * rf - 0.0245 / 252, 0.0, 1)
        elif kind == 'eq':
            out[k] = (net, DY / 252, 1)
        else:
            out[k] = (net, 0.0, 1)
    out['meta'] = meta
    _P[key] = out
    return out

def stack(pan, ids):
    """RET, INC (P,T,K) float64 and HV (K,) for the asset ids, in order"""
    R0 = pan[ids[0]][0]; P, T = R0.shape; K = len(ids)
    RET = np.empty((P, T, K)); INC = np.zeros((P, T, K)); HV = np.zeros(K, np.int64)
    for j, k in enumerate(ids):
        a, inc, hv = pan[k]; RET[:, :, j] = a; INC[:, :, j] = inc; HV[j] = hv
    return RET, INC, HV

def cut3(a, h):
    Th = WARM + h * 252
    return a[:, :Th] if a.ndim == 2 else a[:, :Th, ...]
