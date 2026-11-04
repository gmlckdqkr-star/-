"""TS1 real-history test harness (orchestrator side; designers never read research/theory_sim/test/).
Runs a frozen rule (rule.py: INPUTS, PARAMS, target_levels(close, rf, y10=None, params)) on the MS1 standard bases
exactly as research/measure_std/std.py does (same contexts, same engine F1, identity brake, fstep 0.5), plus
real_spx_29_85, stresses (delay 3/5, cost 0.6%), G1 and a real-data causality test.
Post-2014 bases live in post2014.py and write only to research/theory_sim/holdout/.
Run with /root/.cache/ts-venv/bin/python -B harness.py <rule.py> <name> [<out.json>]"""
import sys, os, json, time, importlib.util, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/root/.cache/ts_nb')
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std  # noqa: sets research paths
import jp, ov, bk, ce, beng, rx, iv  # noqa

STD_BASES = ('dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85')


def load_rule(path):
    spec = importlib.util.spec_from_file_location('ts1_rule_' + os.path.basename(os.path.dirname(path)), path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def path_y10(X0, ii):
    """y10 rebuilt along a resampled path exactly as std.path_flags does (start value + cumulated resampled changes)."""
    v = X0['y10'].values; d = np.r_[0, np.diff(v)]; out = np.empty(ii.shape)
    for i in range(ii.shape[0]):
        pos = ii[i]; out[i] = v[pos[0]] + np.cumsum(np.r_[0, d[pos][1:]])
    return out


_C = {}
def contexts():
    """the 5 MS1 contexts (std.contexts objects, identical) + real_spx_29_85, each with its y10 input matrix"""
    if _C: return _C
    CT = std.contexts()
    Xn = jp.mkX(*jp.calendar('1984-01-03', '2014-12-31'), 'NDX')
    a, b, P, blk, seed = iv.POOLS['dev250']; Xd = jp.mkX(*jp.calendar(a, b), 'NDX')
    Xs = jp.mkX(*jp.calendar('1928-01-03', '1985-12-31'), 'SPX')
    Y = {'real_ndx_86_14': Xn['y10'].values[CT['real_ndx_86_14'].ii],
         'dev250_glued': Xd['y10'].values[CT['dev250_glued'].ii],
         'dev250_path': path_y10(Xd, CT['dev250_path'].ii),
         'real_spx_55_85': Xs['y10'].values[CT['real_spx_55_85'].ii],
         'real_spx_70_85': Xs['y10'].values[CT['real_spx_70_85'].ii]}
    for k in STD_BASES: _C[k] = (CT[k], Y[k])
    F = ov.flags_hist(Xs); ii = np.arange(0, len(Xs))[None, :]
    _C['real_spx_29_85'] = (ov.Ctx(Xs, F, ii), Xs['y10'].values[ii])
    _C['_dates'] = {'real_ndx_86_14': Xn.index[CT['real_ndx_86_14'].ii[0]], 'real_spx_29_85': Xs.index,
                    'real_spx_55_85': Xs.index[CT['real_spx_55_85'].ii[0]], 'real_spx_70_85': Xs.index[CT['real_spx_70_85'].ii[0]]}
    return _C


def levels(rule, c, y):
    y10 = np.array(y, dtype=np.float64) if 'y10' in getattr(rule, 'INPUTS', ()) else None
    B = rule.target_levels(np.array(c.lvl, dtype=np.float64), np.array(c.rf, dtype=np.float64), y10)
    B = np.asarray(B, dtype=np.float64)
    if B.shape != c.r.shape: raise ValueError('rule output shape %s != %s' % (B.shape, c.r.shape))
    return B


def row_for(c, B, bfn=None, bp=None, fstep=0.5, **kw):
    bfn = std.ident if bfn is None else bfn; bp = np.zeros(1) if bp is None else bp
    fin, EE = std.engine(c, B, bfn, bp, fstep, **kw)
    r, f = std.row(fin, EE); return r, f, EE


def measure(rule, name, bases=None, verbose=True, **kw):
    """one row per basis: candidate + same-basis 1x/2x/3x hold + s0.85 (same delay/cost) + paired difference"""
    C = contexts(); out = {}
    for bn in (bases or (STD_BASES + ('real_spx_29_85',))):
        c, y = C[bn]; t0 = time.time()
        B = levels(rule, c, y)
        cand, fc, EE = row_for(c, B, **kw)
        rB, rbf, rbp, rfs = std.s085(c); ref, fr, _ = row_for(c, rB, rbf, rbp, rfs, **kw)
        q, _ = std.row(*std.hold(c, 1)); l, _ = std.row(*std.hold(c, 2))
        t3, _, _ = row_for(c, np.full(c.r.shape, 3.0))
        d = fc - fr; Bt = B[:, ov.WARM:]
        cand.update(d_vs_s085=float(np.median(d)), pw_vs_s085=float(np.mean(d > 1e-5)), ref_s085=ref['cagr'],
                    hold1x=q['cagr'], hold2x=l['cagr'], hold3x=t3['cagr'],
                    avg_target=float(np.nanmean(Bt)), share_cash=float(np.mean(np.nan_to_num(Bt) <= 0)),
                    share_ge2=float(np.mean(np.nan_to_num(Bt) >= 2)), secs=round(time.time() - t0, 1))
        out[bn] = cand
        if verbose: print('%-14s %-15s %s' % (name, bn, ' '.join('%s=%.3f' % kv for kv in cand.items())), flush=True)
    if 'dev250_path' in out:
        out['HEADLINE_MS1'] = out['dev250_path']['cagr']
        if 'real_ndx_86_14' in out: out['FLOOR_MS1'] = min(out['dev250_path']['cagr'], out['real_ndx_86_14']['cagr'])
    return out


def g1(rule, trials=3):
    """G1 gate on the rule's real-history targets (NDX 1986-2014 and SPX 1955-85 eras of gate.py)."""
    sys.path.insert(0, '/mnt/project-files/research/breakthrough/code'); import gate
    res = {}
    Xn = jp.mkX(*jp.calendar('1984-01-03', '2014-12-31'), 'NDX'); Xs = jp.mkX(*jp.calendar('1928-01-03', '1985-12-31'), 'SPX')
    parts = []
    for X in (Xs, Xn):
        F = ov.flags_hist(X); ii = np.arange(0, len(X))[None, :]; c = ov.Ctx(X, F, ii)
        B = levels(rule, c, X['y10'].values[ii])[0]; parts.append(pd.Series(B, index=X.index))
    s = pd.concat(parts); s = s[~s.index.duplicated(keep='last')].fillna(0.0)
    for nm, sig in (('ge1.5', s >= 1.5), ('gt0', s > 0)):
        g = gate.test(sig, trials=trials, name=nm, verbose=False)
        res[nm] = {k: (v if not isinstance(v, dict) else {kk: float(vv) for kk, vv in v.items()}) for k, v in g.items()}
    return res


def causality(rule, n_cut=120, seed=5):
    """truncation test on real <=2014 NDX (one path from 1984-01-03): B computed on data[:t+1] must equal B_full[:t+1]."""
    X = jp.mkX(*jp.calendar('1984-01-03', '2014-12-31'), 'NDX'); F = ov.flags_hist(X)
    ii = np.arange(0, len(X))[None, :]; c = ov.Ctx(X, F, ii); y = X['y10'].values[ii]
    lv, rf = np.array(c.lvl, dtype=np.float64), np.array(c.rf, dtype=np.float64)
    use_y = 'y10' in getattr(rule, 'INPUTS', ())
    full = np.asarray(rule.target_levels(lv.copy(), rf.copy(), y.copy() if use_y else None), dtype=np.float64)
    g = np.random.default_rng(seed); T = lv.shape[1]
    cuts = sorted(set(g.integers(1, T - 1, n_cut).tolist() + [5, 50, 299, 300, 301, T - 2]))
    bad = []
    for t in cuts:
        part = np.asarray(rule.target_levels(lv[:, :t + 1].copy(), rf[:, :t + 1].copy(), y[:, :t + 1].copy() if use_y else None), dtype=np.float64)
        a, b = full[:, :t + 1], part
        same = (a == b) | (np.isnan(a) & np.isnan(b))
        if not same.all(): bad.append(int(t))
    return dict(cuts=len(cuts), violations=len(bad), first_bad=bad[:10])


if __name__ == '__main__':
    path, name = sys.argv[1], sys.argv[2]
    outp = sys.argv[3] if len(sys.argv) > 3 else None
    rule = load_rule(path); R = dict(rule=path, name=name, t0=time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime()))
    R['causality'] = causality(rule); print('causality', R['causality'], flush=True)
    R['base'] = measure(rule, name)
    for lab, kw in (('delay3', dict(delay=3)), ('delay5', dict(delay=5)), ('cost2x', dict(cost=0.006))):
        R[lab] = measure(rule, name + '|' + lab, bases=('dev250_path', 'real_ndx_86_14'), **kw)
    R['g1'] = g1(rule); print('G1', json.dumps(R['g1'])[:600], flush=True)
    R['t1'] = time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())
    if outp: json.dump(R, open(outp, 'w'), indent=1, default=float)
