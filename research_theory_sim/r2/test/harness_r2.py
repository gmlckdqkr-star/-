"""TS2 (round 2) real-history test harness (orchestrator side; designers never read research/theory_sim/r2/test/).
Same MS1 engine and bases as TS1 (research/theory_sim/test/harness.py, imported unchanged as H), plus the round-2 fixes and
additions fixed in r2/TEST_PROTOCOL_R2.md before any round-2 design work:
  - G1 with each era fed its own market's target (TS1 defect a: SPX-era blocks 1984-85 got the NDX target);
  - causality by FUTURE PERTURBATION (TS1 used truncation) on real NDX <=2014 and multi-path dev250_path;
  - real_spx_29_85 also annualised by calendar years (TS1 defect: 1084 Saturday sessions before 1952);
  - real_ndx_86_14 warm-up sensitivity: closes before 1985-10-01 fed to the rule as NaN (engine unchanged);
  - fresh confirmation E: 8 country funds (adjusted closes, US calendar, US rf/y10/macro) <= 2014, one path each,
    with the round-1 primary L1 as comparator. Refuses to run on the funds before r2/FREEZE_TS2.txt exists.
Run: /root/.cache/ts-venv/bin/python -B harness_r2.py <rule.py> <name> <out.json> [--validate]"""
import sys, os, json, time, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/root/.cache/ts_nb')
sys.path.insert(0, '/mnt/project-files/research/theory_sim/test'); import harness as H  # noqa: TS1 harness, unchanged
import std, jp, ov, mkt, ce  # noqa
R2 = '/mnt/project-files/research/theory_sim/r2/'
R1_PRIMARY = '/mnt/project-files/research/theory_sim/design/L1/rule.py'      # sha256 acc4cf0c... (FREEZE_TS1.txt)
FUNDS = ('EWA', 'EWC', 'EWG', 'EWJ', 'EWU', 'EWT', 'EWY', 'EWZ')
STRESS = (('delay3', dict(delay=3)), ('delay5', dict(delay=5)), ('cost2x', dict(cost=0.006)))


# ---------- G1 with per-era targets ----------
def g1_r2(rule, trials=7):
    sys.path.insert(0, '/mnt/project-files/research/breakthrough/code'); import gate
    Xn = jp.mkX(*jp.calendar('1984-01-03', '2014-12-31'), 'NDX'); Xs = jp.mkX(*jp.calendar('1928-01-03', '1985-12-31'), 'SPX')
    S = {}
    for nm, X in (('ndx', Xn), ('spx', Xs)):
        c = ov.Ctx(X, ov.flags_hist(X), np.arange(len(X))[None, :])
        S[nm] = pd.Series(H.levels(rule, c, X['y10'].values[c.ii])[0], index=X.index).fillna(0.0)
    res = {}
    for nm, f in (('ge1.5', lambda s: s >= 1.5), ('gt0', lambda s: s > 0)):
        gn = gate.test(f(S['ndx']), trials=trials, verbose=False); gs = gate.test(f(S['spx']), trials=trials, verbose=False)
        e = {'ndx_86_14': gn['ndx_86_14'], 'spx_55_85': gs['spx_55_85']}
        low = min(v['hit_deflated'] for v in e.values())
        e = {k: {kk: float(vv) for kk, vv in v.items()} for k, v in e.items()}
        e['low_deflated'] = float(low)
        e['verdict'] = '60%-CANDIDATE' if low >= .77 else 'BUILD' if low >= .70 else 'HOLD' if low >= .65 else 'CLOSE'
        res[nm] = e
    return res


# ---------- causality by future perturbation ----------
def _cont(g, lv, rf, y, t, kind):
    lv2, rf2 = lv.copy(), rf.copy(); y2 = None if y is None else y.copy(); P, T = lv.shape; n = T - t - 1
    if n <= 0: return lv2, rf2, y2
    if kind == 0:
        ret = g.normal(0.0005, 0.015, (P, n)); r2 = g.uniform(0, 0.0004, (P, n)); yy = g.uniform(1, 9, (P, n))
    elif kind == 1:
        ret = g.normal(0, 0.08, (P, n)); ret[g.random((P, n)) < 0.02] = -0.5; r2 = g.uniform(-0.001, 0.01, (P, n)); yy = g.uniform(-2, 25, (P, n))
    else:
        ret = g.normal(0, 0.03, (P, n)); r2 = g.uniform(0, 0.001, (P, n)); r2[g.random((P, n)) < 0.1] = np.nan
        yy = g.uniform(0, 15, (P, n)); yy[g.random((P, n)) < 0.1] = np.nan
    lv2[:, t + 1:] = lv[:, t:t + 1] * np.cumprod(1 + np.maximum(ret, -0.95), axis=1)
    if kind == 2:
        m = g.random((P, n)); x = lv2[:, t + 1:]
        x[m < 0.05] = np.nan; x[(m >= 0.05) & (m < 0.08)] = 0.0; x[(m >= 0.08) & (m < 0.10)] = -1.0
    rf2[:, t + 1:] = r2
    if y2 is not None: y2[:, t + 1:] = yy
    return lv2, rf2, y2


def _same(a, b): return bool(np.array_equal(a, b, equal_nan=True))


def _tl(rule, lv, rf, y):
    return np.asarray(rule.target_levels(lv.copy(), rf.copy(), None if y is None else y.copy()), dtype=np.float64)


def causality_r2(rule, n_cut=150, seed=20261104):
    C = H.contexts(); use_y = 'y10' in getattr(rule, 'INPUTS', ())
    c, y = C['real_ndx_86_14']; lv, rf = np.array(c.lvl, dtype=np.float64), np.array(c.rf, dtype=np.float64)
    y = np.array(y, dtype=np.float64) if use_y else None; T = lv.shape[1]; g = np.random.default_rng(seed)
    full = _tl(rule, lv, rf, y); det = _same(full, _tl(rule, lv, rf, y))
    cuts = sorted(set(g.integers(0, T - 1, n_cut).tolist() + [0, 1, 2, 19, 20, 21, 59, 60, 61, 119, 120, 121, 251, 252, 253,
                                                               299, 300, 301, 302, T - 3, T - 2]))
    bad, chg, n = [], 0, 0
    for t in cuts:
        for kind in (0, 1, 2):
            lv2, rf2, y2 = _cont(g, lv, rf, y, t, kind); B = _tl(rule, lv2, rf2, y2); n += 1
            if not _same(B[:, :t + 1], full[:, :t + 1]): bad.append((int(t), kind))
            if not _same(B[:, t + 1:], full[:, t + 1:]): chg += 1
    d, yd = C['dev250_path']; dl, dr = np.array(d.lvl, dtype=np.float64), np.array(d.rf, dtype=np.float64)
    yd = np.array(yd, dtype=np.float64) if use_y else None; Td = dl.shape[1]; fd = _tl(rule, dl, dr, yd); bad_mp, leak = [], []
    for t in sorted(set(g.integers(0, Td - 1, 6).tolist() + [299, 300])):
        dl2, dr2, yd2 = _cont(g, dl, dr, yd, t, 1); B = _tl(rule, dl2, dr2, yd2)
        if not _same(B[:, :t + 1], fd[:, :t + 1]): bad_mp.append(int(t))
        dl3, dr3 = dl.copy(), dr.copy(); dl3[7, t + 1:] = dl2[7, t + 1:]; dr3[7, t + 1:] = dr2[7, t + 1:]
        yd3 = None
        if yd is not None: yd3 = yd.copy(); yd3[7, t + 1:] = yd2[7, t + 1:]
        B3 = _tl(rule, dl3, dr3, yd3); oth = np.r_[0:7, 8:dl.shape[0]]
        if not _same(B3[oth], fd[oth]) or not _same(B3[7, :t + 1], fd[7, :t + 1]): leak.append(int(t))
    return dict(deterministic=det, cuts=len(cuts), checks=n, violations=len(bad), first_bad=bad[:10],
                future_changed_share=chg / max(n, 1), multipath_cuts_bad=bad_mp, crosspath_leak=leak)


# ---------- extra rows on seen US bases ----------
def spx29_calendar(row):
    C = H.contexts(); d = C['_dates']['real_spx_29_85'][ov.WARM:]
    yrs_cal = (d[-1] - d[0]).days / 365.25 + 1 / 252; yrs_252 = len(d) / 252; k = yrs_252 / yrs_cal
    return dict(yrs_252=yrs_252, yrs_cal=yrs_cal, **{key + '_cal': (1 + row[key]) ** k - 1
                                                     for key in ('cagr', 'ref_s085', 'hold1x', 'hold2x', 'hold3x')})


def nanwarm(rule):
    C = H.contexts(); c, y = C['real_ndx_86_14']; dates = C['_dates']['real_ndx_86_14']
    m = np.asarray(dates < pd.Timestamp('1985-10-01')); lv = np.array(c.lvl, dtype=np.float64); lv[:, m] = np.nan
    yy = np.array(y, dtype=np.float64) if 'y10' in getattr(rule, 'INPUTS', ()) else None
    B = np.asarray(rule.target_levels(lv, np.array(c.rf, dtype=np.float64), yy), dtype=np.float64)
    r, f, _ = H.row_for(c, B); r['nan_days'] = int(m.sum()); return r


# ---------- fresh confirmation E: country funds ----------
_FX = {}
def us_frame(end):
    if end not in _FX:
        X = jp.mkX(*jp.calendar('1990-01-02', end), 'NDX')
        _FX[end] = X
    return _FX[end]


def fund_ctx(k, end='2014-12-31', start=None, X=None):
    """one real path of fund k: adjusted close (panel col 4) on the US calendar, US rf / y10 / macro flags of that date.
    start=None: from the fund's first day (300-day warm-up inside); start=date: 300 days of warm-up before it."""
    X = (us_frame(end) if X is None else X).copy(); X = X[X.index <= pd.Timestamp(end)]
    s = mkt.pser(k, 4); s = s[s.index <= pd.Timestamp(end)]; first = s.index[0]
    r = s.pct_change().reindex(X.index)
    i_first = X.index.searchsorted(first); r.iloc[:i_first + 1] = 0.0
    if r.iloc[i_first + 1:].isna().any(): raise ValueError('%s: missing fund returns on US trading days' % k)
    X['r'] = r.values; X['p'] = (1 + X['r']).cumprod()
    F = ov.flags_hist(X)
    i0 = i_first if start is None else max(i_first, X.index.searchsorted(pd.Timestamp(start)) - ov.WARM)
    ii = np.arange(i0, len(X))[None, :]
    return ov.Ctx(X, F, ii), X['y10'].values[ii], X.index[ii[0]]


def _row(c, B, bfn=None, bp=None, fstep=0.5, **kw):
    """single-path row (any length): median after-tax CAGR (std.engine) and median MDD (ce.mdd, as std.row)"""
    bfn = std.ident if bfn is None else bfn; bp = np.zeros(1) if bp is None else bp
    fin, EE = std.engine(c, B, bfn, bp, fstep, **kw)
    return dict(cagr=float(np.median(fin)), mdd=float(np.median(ce.mdd(EE))), years=round(EE.shape[1] / 252, 2)), fin


def conf_one(rule, r1, k, end='2014-12-31', start=None, X=None, **kw):
    """rule, round-1 primary and s0.85 at the same delay/cost; holds unstressed (as TS1 harness.measure)"""
    c, y, dates = fund_ctx(k, end, start, X)
    B = H.levels(rule, c, y); cand, _ = _row(c, B, **kw)
    B1 = H.levels(r1, c, y); ref1, _ = _row(c, B1, **kw)
    rB, rbf, rbp, rfs = std.s085(c); s85, _ = _row(c, rB, rbf, rbp, rfs, **kw)
    h1, E1 = std.hold(c, 1); h2, E2 = std.hold(c, 2); h3, _ = _row(c, np.full(c.r.shape, 3.0))
    Bt = np.nan_to_num(B[:, ov.WARM:])
    return dict(fund=k, start=str(dates[ov.WARM].date()), end=str(dates[-1].date()), rule=cand, r1_L1=ref1, s085=s85,
                hold1x=float(np.median(h1)), hold1x_mdd=float(np.median(ce.mdd(E1))), hold2x=float(np.median(h2)),
                hold2x_mdd=float(np.median(ce.mdd(E2))), hold3x=h3['cagr'], hold3x_mdd=h3['mdd'],
                avg_target=float(Bt.mean()), share_cash=float((Bt <= 0).mean()))


def summarise(rows):
    def cmp(key):
        d = np.array([x['rule']['cagr'] - key(x) for x in rows]); return dict(median=float(np.median(d)), wins=int((d > 1e-5).sum()), n=len(d))
    return dict(vs_r1_L1=cmp(lambda x: x['r1_L1']['cagr']), vs_s085=cmp(lambda x: x['s085']['cagr']),
                vs_hold1x=cmp(lambda x: x['hold1x']), vs_hold2x=cmp(lambda x: x['hold2x']), vs_hold3x=cmp(lambda x: x['hold3x']),
                rule_median=float(np.median([x['rule']['cagr'] for x in rows])),
                r1_median=float(np.median([x['r1_L1']['cagr'] for x in rows])),
                s085_median=float(np.median([x['s085']['cagr'] for x in rows])),
                hold1x_median=float(np.median([x['hold1x'] for x in rows])))


def conf(rule, r1, funds=FUNDS, validate=False, **kw):
    if not validate and not os.path.exists(R2 + 'FREEZE_TS2.txt'):
        raise SystemExit('confirmation funds stay closed until r2/FREEZE_TS2.txt exists')
    rows = [conf_one(rule, r1, k, **kw) for k in funds]
    for x in rows:
        print('  conf %-5s %s..%s rule %.4f r1 %.4f s085 %.4f 1x %.4f 2x %.4f 3x %.4f avg %.2f' % (
            x['fund'], x['start'], x['end'], x['rule']['cagr'], x['r1_L1']['cagr'], x['s085']['cagr'], x['hold1x'],
            x['hold2x'], x['hold3x'], x['avg_target']), flush=True)
    return dict(rows=rows, summary=summarise(rows))


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]; validate = '--validate' in sys.argv
    path, name, outp = a[0], a[1], a[2]
    rule = H.load_rule(path); r1 = H.load_rule(R1_PRIMARY)
    R = dict(rule=path, name=name, t0=time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime()))
    R['causality'] = causality_r2(rule); print('causality', R['causality'], flush=True)
    R['base'] = H.measure(rule, name)
    R['spx29_calendar'] = spx29_calendar(R['base']['real_spx_29_85'])
    for lab, kw in STRESS:
        R[lab] = H.measure(rule, name + '|' + lab, bases=('dev250_path', 'real_ndx_86_14'), **kw)
    R['nanwarm_real_ndx_86_14'] = nanwarm(rule); print('nanwarm', R['nanwarm_real_ndx_86_14'], flush=True)
    R['g1'] = g1_r2(rule); print('G1', json.dumps({k: (v['verdict'], round(v['low_deflated'], 4)) for k, v in R['g1'].items()}), flush=True)
    funds = ('QQQ',) if validate else FUNDS          # validation runs the fund pipeline on QQQ (US data, already seen)
    R['conf'] = conf(rule, r1, funds, validate=validate)
    for lab, kw in (('delay3', dict(delay=3)), ('cost2x', dict(cost=0.006))):
        R['conf_' + lab] = conf(rule, r1, funds, validate=validate, **kw)
    R['t1'] = time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())
    json.dump(R, open(outp, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
