"""TS1 post-2014 bases (results go to the USER ONLY: written under research/theory_sim/holdout/, never to memory or
other threads). Protocol C1-C3 of TEST_PROTOCOL.md.
  C1 real NDX 2015-01-02 -> last close (300-day warm-up before), C2 real NDX 1986-01-02 -> last close,
  C3 C1 period with the actual TQQQ daily total return in place of the synthetic 3x product.
Data: MS1 calendar (jp/md, to 2026-08-31) + panel NDX/IRX/TNX (mkt, to 2026-10-07) + splice to the latest close
(Twelve Data QQQ/TQQQ/QLD closes, Treasury.gov 13-week bill bank discount and 10-year CMT), files in holdout/.
Run: /root/.cache/ts-venv/bin/python -B post2014.py <rule.py> <name> [<out.json>]"""
import sys, os, json, time, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import harness as H  # noqa
import jp, ov, bk, ce, beng, mkt, std  # noqa
HO = '/mnt/project-files/research/theory_sim/holdout/'


def _tsy():
    y = pd.read_csv(HO + 'tsy_daily_treasury_yield_curve_2026.csv'); y.index = pd.to_datetime(y['Date'], format='%m/%d/%Y')
    b = pd.read_csv(HO + 'tsy_daily_treasury_bill_rates_2026.csv'); b.index = pd.to_datetime(b['Date'], format='%m/%d/%Y')
    return y.sort_index(), b.sort_index()


_X = {}
def ndx_now(check=True):
    if _X: return _X['X'], _X['A']
    R, M = jp.calendar('1984-01-03', '2026-08-31'); X = jp.mkX(R, M, 'NDX')[['r', 'rf', 'y10', 'y3m', 'cs', 'vix']]
    N = mkt.ndx(); N = N[N.index > X.index[-1]][['r', 'rf', 'y10', 'y3m', 'cs', 'vix']]
    X = pd.concat([X, N])
    S = pd.read_csv(HO + 'splice_td_20261104.csv', parse_dates=['date']).set_index('date')
    y, b = _tsy(); last = X.index[-1]
    if check:   # overlap check of the splice sources against the panel (days <= last)
        ov_d = S.index[(S.index <= last) & (S.index > last - pd.Timedelta(days=12))]
        q = mkt.pser('QQQ', 3); nd = mkt.pser('_NDX', 4)
        rq = S['QQQ'].pct_change().reindex(ov_d); rn = nd.pct_change().reindex(ov_d)
        irx = mkt.pser('_IRX', 3).reindex(ov_d); tnx = mkt.pser('_TNX', 3, 'panel_ext_f32.npz.xz').reindex(ov_d)
        print('splice check (overlap days %d): |QQQ ret - NDX ret| max %.5f; |TD QQQ close - panel close| max %.4f; '
              '|13w disc - IRX| max %.3f; |10y CMT - TNX| max %.3f' % (len(ov_d), np.nanmax(np.abs(rq - rn)),
              np.nanmax(np.abs(S['QQQ'].reindex(ov_d) - q.reindex(ov_d))),
              np.nanmax(np.abs(b['13 WEEKS BANK DISCOUNT'].reindex(ov_d) - irx)), np.nanmax(np.abs(y['10 Yr'].reindex(ov_d) - tnx))), flush=True)
    new = S.index[S.index > last]
    if len(new):
        E = pd.DataFrame(index=new)
        E['r'] = S['QQQ'].pct_change().reindex(new).values
        d13 = b['13 WEEKS BANK DISCOUNT'].reindex(new).ffill()
        E['rf'] = (d13 / 100 / 252).values; E['y3m'] = d13.values
        E['y10'] = y['10 Yr'].reindex(new).ffill().values
        E['cs'] = X['cs'].iloc[-1]; E['vix'] = np.nan
        X = pd.concat([X, E])
    X = X.ffill(); X['r'] = X['r'].fillna(0.0)
    X['rb'] = mkt.bond10(X); X['p'] = (1 + X['r']).cumprod()
    # actual products: adjusted closes (panel col 4) + splice closes
    A = {}
    for k in ('QQQ', 'QLD', 'TQQQ'):
        s = mkt.pser(k, 4); s = s[s.index <= last]
        ext = S[k][S.index > last]; rr = pd.concat([s.pct_change(), S[k].pct_change()[S.index > last]])
        A[k] = rr.reindex(X.index)
    _X['X'], _X['A'] = X, A
    return X, A


def row_s(fin, E):
    """std.row for short single paths (w7/w12 = NaN when the path is shorter than 7/12 years)"""
    m = ce.mdd(E); n = E.shape[1]
    return dict(cagr=float(np.median(fin)), mdd=float(np.median(m)),
                w7=float(np.median(E[:, 7 * 252 - 1])) if n >= 7 * 252 else float('nan'),
                w12=float(np.median(E[:, 12 * 252 - 1])) if n >= 12 * 252 else float('nan')), fin


def row_for_s(c, B, bfn=None, bp=None, fstep=0.5, **kw):
    bfn = std.ident if bfn is None else bfn; bp = np.zeros(1) if bp is None else bp
    fin, EE = std.engine(c, B, bfn, bp, fstep, **kw); r, f = row_s(fin, EE); return r, f, EE


def ctx_from(X, start):
    F = ov.flags_hist(X); i0 = X.index.searchsorted(pd.Timestamp(start)) - ov.WARM
    ii = np.arange(i0, len(X))[None, :]; return ov.Ctx(X, F, ii), X['y10'].values[ii], X.index[ii[0]]


def engine_r(c, r_use, B, bfn, bp, fstep, **kw):
    """MS1 engine with the product return driven by r_use (features from the real index ctx)."""
    k = dict(beng.F1); k['fstep'] = fstep; k.update(kw); pp, D = beng._args(k)
    o, EE = ce.runPE(np.ascontiguousarray(r_use), np.ascontiguousarray(c.rf), np.ascontiguousarray(B, dtype=np.float64),
                     np.ascontiguousarray(bk.features(c)), int(pp['delay']), pp['cost'], pp['tax'], D, int(pp['harvest']), pp['hthr'],
                     pp['cspr'], pp['er3'], pp['step'], bfn, np.asarray(bp, dtype=np.float64), float(pp['fstep']))
    yrs = EE.shape[1] / 252
    return np.maximum(o[:, 0], 1e-9) ** (1 / yrs) - 1, EE


def hold_actual(ret, dates, tax=0.22):
    x = ret.reindex(dates).fillna(0.0).values[ov.WARM:]; E = np.cumprod(1 + x); yrs = len(x) / 252
    fin = E[-1] * (1 - 0.003) - tax * max(E[-1] * (1 - 0.003) - 1, 0); pk = np.maximum.accumulate(np.maximum(E, 1.0))
    return dict(cagr=float(max(fin, 1e-9) ** (1 / yrs) - 1), mdd=float(min((E / pk - 1).min(), 0.0)))


def yearly(EE, dates):
    s = pd.Series(EE[0], index=dates[ov.WARM:]); ye = s.groupby(s.index.year).last(); prev = ye.shift(1); prev.iloc[0] = 1.0
    return {int(k): float(v) for k, v in (ye / prev - 1).items()}


def run(rule, name, delay=2, cost=0.003):
    X, A = ndx_now(); out = {'last_close': str(X.index[-1].date())}
    for bn, start in (('C1_ndx_2015_now', '2015-01-02'), ('C2_ndx_1986_now', '1986-01-02')):
        c, y, dates = ctx_from(X, start)
        B = H.levels(rule, c, y)
        cand, fc, EE = row_for_s(c, B, delay=delay, cost=cost)
        rB, rbf, rbp, rfs = std.s085(c); ref, fr, EEr = row_for_s(c, rB, rbf, rbp, rfs, delay=delay, cost=cost)
        q, _ = row_s(*std.hold(c, 1)); l, _ = row_s(*std.hold(c, 2)); t3, _, _ = row_for_s(c, np.full(c.r.shape, 3.0))
        Bt = np.nan_to_num(B[:, ov.WARM:])
        cand.update(ref_s085=ref['cagr'], ref_s085_mdd=ref['mdd'], hold1x=q['cagr'], hold2x=l['cagr'], hold3x=t3['cagr'],
                    hold1x_mdd=q['mdd'], avg_target=float(Bt.mean()), share_cash=float((Bt <= 0).mean()),
                    years=round((c.T - ov.WARM) / 252, 2), start=str(dates[ov.WARM].date()))
        if bn.startswith('C1'):
            cand['yearly_rule'] = yearly(EE, dates); cand['yearly_s085'] = yearly(EEr, dates)
            Ec = np.cumprod(1 + c.r[0, ov.WARM:] - 0.002 / 252); s = pd.Series(Ec, index=dates[ov.WARM:])
            ye = s.groupby(s.index.year).last(); pv = ye.shift(1); pv.iloc[0] = 1.0
            cand['yearly_hold1x_pretax'] = {int(k): float(v) for k, v in (ye / pv - 1).items()}
            # C3: actual TQQQ in place of the synthetic 3x product
            tq = A['TQQQ'].reindex(dates).values
            if np.isfinite(tq[ov.WARM:]).all():
                r_eff = ((np.nan_to_num(tq) + 2 * c.rf[0] + (0.0095 + 0.015) / 252) / 3)[None, :]; r_eff[:, 0] = 0
                f1, E1 = engine_r(c, r_eff, B, std.ident, np.zeros(1), 0.5, delay=delay, cost=cost)
                f2, E2 = engine_r(c, r_eff, rB, rbf, rbp, rfs, delay=delay, cost=cost)
                f3, E3 = engine_r(c, r_eff, np.full(c.r.shape, 3.0), std.ident, np.zeros(1), 0.5)
                out['C3_actual_tqqq_2015_now'] = dict(rule=row_s(f1, E1)[0], s085=row_s(f2, E2)[0], tqqq_hold=row_s(f3, E3)[0],
                                                      qqq_hold_actual=hold_actual(A['QQQ'], dates), qld_hold_actual=hold_actual(A['QLD'], dates))
            else:
                out['C3_actual_tqqq_2015_now'] = 'omitted: TQQQ returns missing in the C1 window'
        out[bn] = cand
        print('%-12s %-18s %s' % (name, bn, ' '.join('%s=%.3f' % kv for kv in cand.items() if isinstance(kv[1], float))), flush=True)
    if isinstance(out.get('C3_actual_tqqq_2015_now'), dict):
        print('%-12s C3_actual_tqqq   ' % name + json.dumps({k: round(v['cagr'], 4) for k, v in out['C3_actual_tqqq_2015_now'].items()}), flush=True)
    return out


if __name__ == '__main__':
    path, name = sys.argv[1], sys.argv[2]; outp = sys.argv[3] if len(sys.argv) > 3 else None
    if outp and not os.path.abspath(outp).startswith(HO): raise SystemExit('post-2014 results must be written under ' + HO)
    rule = H.load_rule(path); R = dict(rule=path, name=name, t0=time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime()))
    R['base'] = run(rule, name)
    for lab, kw in (('delay3', dict(delay=3)), ('delay5', dict(delay=5)), ('cost2x', dict(cost=0.006))):
        R[lab] = run(rule, name + '|' + lab, **kw)
    R['t1'] = time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())
    if outp: json.dump(R, open(outp, 'w'), indent=1, default=float)
