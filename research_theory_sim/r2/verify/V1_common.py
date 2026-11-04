"""V1 verifier (TS2 round 2), shared helpers. Independent of r2/test/harness_r2.py and of TS1 test/harness.py:
calls the locked MS1 standard (research/measure_std/std.py) directly and rebuilds every basis from the data loaders.
HARD RULE: data <= 2014-12-31 only. Every series is cut at END before any computation.
Run scripts with: NUMBA_CACHE_DIR=<scratch> /root/.cache/ts-venv/bin/python -B <script>"""
import sys, os, io, lzma, json, hashlib, importlib.util, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std  # noqa: sets research paths
import jp, ov, ce  # noqa

TS = '/mnt/project-files/research/theory_sim/'
R2 = TS + 'r2/'
OUT = R2 + 'verify/'
END = pd.Timestamp('2014-12-31')
WARM = ov.WARM
RULES = {'A': R2 + 'design/A/rule.py', 'B': R2 + 'design/B/rule.py', 'C': R2 + 'design/C/rule.py',
         'D': R2 + 'design/D/rule.py', 'L1': TS + 'design/L1/rule.py'}
FUNDS = ('EWA', 'EWC', 'EWG', 'EWJ', 'EWU', 'EWT', 'EWY', 'EWZ')


def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def load_rule(name, params=None):
    p = RULES[name]
    spec = importlib.util.spec_from_file_location('v1rule_%s_%d' % (name, np.random.randint(1 << 30)), p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def targets(rule, lvl, rf, y10=None, params=None):
    """rule output as float64; y10 passed only if the rule declares it (all five here declare close, rf only)."""
    use_y = 'y10' in getattr(rule, 'INPUTS', ())
    args = (np.array(lvl, dtype=np.float64), np.array(rf, dtype=np.float64), np.array(y10, dtype=np.float64) if (use_y and y10 is not None) else None)
    B = rule.target_levels(*args) if params is None else rule.target_levels(*args, params=params)
    return np.asarray(B, dtype=np.float64)


# ---------------- bases ----------------
_B = {}
def bases():
    """MS1's 5 contexts exactly as std.contexts() builds them, + real_spx_29_85 rebuilt here from the protocol text."""
    if _B: return _B
    C = std.contexts()
    for k in ('dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85'): _B[k] = C[k]
    Xs = jp.mkX(*jp.calendar('1928-01-03', '1985-12-31'), 'SPX'); assert Xs.index[-1] <= END
    _B['real_spx_29_85'] = ov.Ctx(Xs, ov.flags_hist(Xs), np.arange(len(Xs))[None, :])
    _B['_spx_dates'] = Xs.index
    Xn = jp.mkX(*jp.calendar('1984-01-03', '2014-12-31'), 'NDX'); assert Xn.index[-1] <= END
    _B['_ndx_dates'] = Xn.index[C['real_ndx_86_14'].ii[0]]
    return _B


def run(c, B, bfn=None, bp=None, fstep=0.5, **kw):
    bfn = std.ident if bfn is None else bfn; bp = np.zeros(1) if bp is None else bp
    return std.engine(c, B, bfn, bp, fstep, **kw)


def s085(c, **kw):
    rB, rbf, rbp, rfs = std.s085(c); return run(c, rB, rbf, rbp, rfs, **kw)


def full_row(c, B, **kw):
    """candidate + same-basis holds + s0.85 at the same delay/cost; holds unstressed (MS1 / protocol)."""
    fc, EE = run(c, B, **kw); cand, _ = std.row(fc, EE)
    fr, Er = s085(c, **kw); ref, _ = std.row(fr, Er)
    h1, E1 = std.hold(c, 1); h2, E2 = std.hold(c, 2); f3, E3 = run(c, np.full(c.r.shape, 3.0))
    d = fc - fr; Bt = B[:, WARM:]
    cand.update(d_vs_s085=float(np.median(d)), pw_vs_s085=float(np.mean(d > 1e-5)), ref_s085=ref['cagr'], ref_s085_mdd=ref['mdd'],
                hold1x=float(np.median(h1)), hold2x=float(np.median(h2)), hold3x=float(np.median(f3)),
                hold1x_mdd=float(np.median(ce.mdd(E1))), hold1x_dd80=float(np.mean(ce.mdd(E1) <= -0.8)),
                avg_target=float(np.nanmean(Bt)), share_cash=float(np.mean(np.nan_to_num(Bt) <= 0)),
                share_ge2=float(np.mean(np.nan_to_num(Bt) >= 2)), nan_after_warm=int(np.isnan(Bt).sum()))
    return cand, fc, fr, h1


# ---------------- fresh confirmation E: country funds (independent build) ----------------
_PZ = {}
def _panel():
    if not _PZ: _PZ['z'] = np.load(io.BytesIO(lzma.open('/mnt/project-files/research/data/panel_f32.npz.xz').read()))
    return _PZ['z']


def fund_close(k):
    """adjusted close (panel column 4), cut at 2014-12-31 BEFORE anything else is computed."""
    z = _panel(); ts = pd.to_datetime(z[k + '|ts'], unit='s').normalize(); v = z[k + '|v'][:, 4].astype(float)
    s = pd.Series(v, index=ts); s = s[s.index <= END]
    s = s[~s.index.duplicated(keep='last')].dropna(); s = s[s > 0]
    return s


_US = {}
def us_frame():
    if 'X' not in _US:
        X = jp.mkX(*jp.calendar('1990-01-02', '2014-12-31'), 'NDX'); X = X[X.index <= END]; _US['X'] = X
    return _US['X']


def fund_ctx(k, method='price'):
    """one real path: fund return on the US calendar, US rf/y10/macro flags; path starts at the fund's first day
    (column 0, r=0) so columns 0..299 are the fund's own warm-up. method 'price': reindex the price onto the US
    calendar, then return (keeps every price move); 'ret': fund pct_change on its own dates, then reindex (harness way)."""
    X = us_frame().copy(); s = fund_close(k); first = s.index[0]
    info = dict(first=str(first.date()), last=str(s.index[-1].date()), n_fund_days=int(len(s)),
                fund_days_not_on_us_cal=[str(d.date()) for d in s.index[~s.index.isin(X.index)]][:20],
                n_fund_days_not_on_us_cal=int((~s.index.isin(X.index)).sum()))
    i0 = int(X.index.searchsorted(first))
    s = s.sort_index(); praw = s.reindex(X.index)
    info['us_days_missing_fund'] = int(praw.iloc[i0:].isna().sum())
    if method == 'price':
        p = s.reindex(X.index, method='ffill'); r = p / p.shift(1) - 1.0
    else:
        r = s.pct_change().reindex(X.index)
    r.iloc[:i0 + 1] = 0.0
    info['nan_returns_after_first'] = int(r.iloc[i0 + 1:].isna().sum())
    r = r.fillna(0.0)
    X['r'] = r.values; X['p'] = (1 + X['r']).cumprod()
    F = ov.flags_hist(X); ii = np.arange(i0, len(X))[None, :]
    c = ov.Ctx(X, F, ii); dates = X.index[ii[0]]
    info.update(path_start=str(dates[0].date()), measured_from=str(dates[WARM].date()), end=str(dates[-1].date()),
                years=round((len(dates) - WARM) / 252, 2), max_abs_move=float(np.max(np.abs(c.r))))
    return c, X['y10'].values[ii], dates, info


def single(c, B, bfn=None, bp=None, fstep=0.5, **kw):
    fin, EE = run(c, B, bfn, bp, fstep, **kw); return float(fin[0]), float(ce.mdd(EE)[0])


def dump(obj, name):
    p = OUT + name
    with open(p, 'w') as f: json.dump(obj, f, indent=1, default=float)
    return p
