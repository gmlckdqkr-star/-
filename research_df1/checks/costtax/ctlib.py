"""costtax check library (DF1/DF2 'other checks', ID costtax). <=2014 data only.
Variants of costs / taxes / bond model on the DF1 engine; synthetic bonds (10y and the 7y rebuild) are NON-ACTUAL reconstructions."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2, std, jp, iv, mkt
import lh1run as LH

W = dfe.WARM
SELM = ('dev250_path', 'real_ndx_86_14', 'real_spx_29_54')
END = pd.Timestamp('2014-12-31')

def bond_n(X, n):
    """mkt.bond10 formula verbatim with the number of semiannual periods as a parameter (n=20 -> mkt.bond10). NON-ACTUAL."""
    y = X['y10'] / 100; y0 = y.shift(1); dy = (y - y0).fillna(0)
    h = y0 / 2
    D = (1 / y0) * (1 - 1 / (1 + h) ** n)
    C = 2 * D / y0 - 2 * n / (y0 * y0) / (1 + h) ** (n + 1) * 0.5
    C = C.clip(lower=0).fillna(0)
    return (y0 / 252 - D * dy + 0.5 * C * dy * dy).fillna(0)

def source_X(name):
    """the X frame dfctx.market builds for this basis (same calendar), <=2014."""
    if name.startswith('dev250'):
        a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX')
    elif name == 'real_ndx_86_14':
        R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX')
    elif name == 'real_spx_29_54':
        X = LH.build(LH.END, 'A')
    else:
        raise ValueError(name)
    assert X.index.max() <= END
    return X

_X = {}
def getX(name):
    if name not in _X: _X[name] = source_X(name)
    return _X[name]

def with_bond(m, name, n):
    """market dict with rb rebuilt from y10 using n half-years (bondup rebuilt the same way as dfctx._finish)."""
    X = getX(name); c = m['ctx']
    assert np.array_equal(np.asarray(m['X_index']), np.asarray(X.index))
    rb10 = mkt.bond10(X).values; rbn20 = bond_n(X, 20).values
    assert np.allclose(np.nan_to_num(rb10), np.nan_to_num(rbn20), atol=1e-15, equal_nan=True)
    rb = np.nan_to_num(bond_n(X, n).values[c.ii], nan=0.0); rb[:, 0] = 0.0
    bl = np.cumprod(1 + rb, axis=1); s = DC._sma(bl, 200)
    bu = np.where(np.isnan(s), False, bl > np.nan_to_num(s, nan=np.inf))
    m2 = dict(m); m2['rb'] = rb; m2['bondup'] = bu
    return m2

def ex_src(name, n):
    """DF1 s5 'bond excess 0' shift as fixed by gate_fix.py: mean(rb - rf) over the basis' SOURCE period."""
    X = getX(name); rb = (mkt.bond10(X) if n == 20 else bond_n(X, n)).values
    return float(np.mean(rb[1:] - X['rf'].values[1:]))

W0D = lambda w0: 2.5e6 / w0
# variant -> (bond half-years, dfe engine kwargs, std.engine (v1) kwargs)
VARIANTS = {
    'base':       (20, {}, {}),
    'W0_30M':     (20, dict(D=W0D(30e6)), dict(W0=30e6)),
    'W0_100M':    (20, dict(D=W0D(100e6)), dict(W0=100e6)),
    'W0_300M':    (20, dict(D=W0D(300e6)), dict(W0=300e6)),
    'bond7y':     (14, {}, {}),
    'bondER25':   (20, dict(erb=0.0025), {}),
    'harvest0':   (20, dict(harvest=0), dict(harvest=0)),
    'cost020':    (20, dict(cost=0.002), dict(cost=0.002)),
    'cost045':    (20, dict(cost=0.0045), dict(cost=0.0045)),
    # extra combinations (not single assumptions)
    'combo_mid':  (14, dict(D=W0D(30e6), erb=0.0025), dict(W0=30e6)),
    'combo_adv':  (14, dict(D=W0D(100e6), erb=0.0025, cost=0.0045), dict(W0=100e6, cost=0.0045)),
}

_MK = {}
def markets(vname):
    n = VARIANTS[vname][0]
    if n not in _MK:
        _MK[n] = {}
        for b in SELM:
            m = DC.market(b); _MK[n][b] = m if n == 20 else with_bond(m, b, n)
    return _MK[n]

def metrics(o, T, path):
    cg, md = dfe.stats(o, T)
    if path: return dict(cagr=float(np.median(cg)), mdd_p10=float(np.percentile(md, 10)), mdd_med=float(np.median(md)), cagr_p10=float(np.percentile(cg, 10)))
    return dict(cagr=float(cg[0]), mdd=float(md[0]))

def run_cfg_all(cfg, vname, mk=None, extra_kw=None):
    """cfg on the 3 selection bases under a variant -> compact row with WD."""
    n, kw, _ = VARIANTS[vname]; mk = mk or markets(vname); kw = dict(kw); kw.update(extra_kw or {})
    row = {}
    for b in SELM:
        m = mk[b]; T = m['r'].shape[1]
        row[b] = metrics(R2.run_cfg(cfg, m, **kw), T, b == 'dev250_path')
    row['wd'] = min(row['dev250_path']['mdd_p10'], row['real_ndx_86_14']['mdd'], row['real_spx_29_54']['mdd'])
    return row

def all_configs():
    C = {c['id']: c for c in RG.configs()}; C.update({c['id']: c for c in R2.configs()}); return C

# ---------------- KRW (FRED DEXKOUS raw, <=2014 rows only; ACTUAL FX data, A10-1 quality gate FAIL -> stress version) ----------------
FXRAW = '/mnt/project-files/research/data/fx_dexkous/raw/DEXKOUS_raw.csv'
def fx_on(dates):
    d = pd.read_csv(FXRAW)
    d['observation_date'] = pd.to_datetime(d['observation_date']); d = d[d['observation_date'] <= END]
    s = pd.to_numeric(d['DEXKOUS'], errors='coerce'); s.index = d['observation_date'].values; s = s.dropna()
    dates = pd.DatetimeIndex(dates); assert dates.max() <= END
    pos = s.index.searchsorted(dates, side='right') - 1          # last observation dated <= day (A10-1 clean rule)
    assert (pos >= 0).all()
    return s.values[pos], (~pd.Index(dates).isin(s.index)).sum()

def krw_stats(EE, fin, fxl):
    """EE (P, T-W) USD account values from k=0, fin (P,) final after-tax USD value, fxl (P, T-W) KRW per USD aligned to EE."""
    rel = fxl / fxl[:, :1]
    Ek = EE * rel
    md = (Ek / np.maximum.accumulate(Ek, axis=1) - 1).min(axis=1)
    mdu = (EE / np.maximum.accumulate(EE, axis=1) - 1).min(axis=1)
    yrs = EE.shape[1] / 252
    cgk = np.maximum(fin * rel[:, -1], 1e-9) ** (1 / yrs) - 1
    cgu = np.maximum(fin, 1e-9) ** (1 / yrs) - 1
    return cgu, mdu, cgk, md
