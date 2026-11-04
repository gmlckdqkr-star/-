"""ETX1 stage 2 (PRECOMMIT_ETX1.md sha d8ca5d31): pre-registered combos C1-C4 + conservative checks. <=2014 only.
usage (run from the scratchpad cwd with the ms1 venv):
  run_stage2.py combos <basis>              C1-C4 built by the precommit rule from screen_dev250_path.json
  run_stage2.py stress <basis> <kind>[,..]  kinds: base cost2x delay3 sgov levx1 bondhc05 drift15 drift0 trendhalf fee10 rp1 fee10rp1
  run_stage2.py null <basis> <n> <cand>     time-shift null: the fill's bond EXCESS return (over rf) circularly shifted, rf kept in place
  run_stage2.py spxext                      real_spx_55_85 / 70_85 with Treasuries extended 1953-61 from FRED GS20 / GS10 monthly
  run_stage2.py holds <basis>               same-engine 1x / 2x / 3x NDX holds
  run_stage2.py proxy                       synthetic vs ACTUAL TLT (2002-07+) / TMF (2009-04+) + standalone Sharpe (real 1986-2014)
  run_stage2.py oracle <basis>              hindsight ceiling of the idle-fill axis (per idle episode the best product, NOT tradable)
Outputs: results/stage2_*.json. Every d is the same-path paired difference vs s0.85 run under the SAME stress."""
import sys, os, json, time, gc, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import etxeng as G, etxcands as X, etxdata as XD
OUT = '/mnt/project-files/research/etf_ext/results/'
FILLS = ['S2_TMF', 'S2_TYD', 'S2_UBT', 'S2_EDV', 'S2_UST', 'S2_TLT']
CFG = dict(X.configs())


# ---------------- pre-registered combos ----------------
def combo_rule():
    S = json.load(open(OUT + 'screen_dev250_path.json'))
    fills = [k for k in S if k.startswith(('S2_', 'S3_'))]
    A = max(fills, key=lambda k: S[k]['d_ref'])
    B, seen = [], set()
    for k in sorted([k for k in S if k.startswith('S1_')], key=lambda k: -S[k]['d_ref']):
        n = k.split('_')[1]; g = X.GROUP[n]
        if g in seen: continue
        seen.add(g); B.append((n, k, S[k]['d_ref']))
        if len(B) == 3: break
    return A, B


def combos():
    A, B = combo_rule(); b1, b2, b3 = [x[0] for x in B]
    return {'C1': (A, [(b1, 0.30)]), 'C2': (A, [(b1, 0.15), (b2, 0.15)]),
            'C3': (A, [(b1, 0.10), (b2, 0.10), (b3, 0.10)]), 'C4': (A, [(b1, 0.15)])}


def build_any(b, L, name):
    if name == 's085': return ['TQQQ', 'CASH'], [G.sl_s085(L)], [1.0]
    if name in CFG: return X.build(b, L, CFG[name])
    A, Bs = combos()[name]; kind, an = A.split('_', 1); mixA, _ = X.mix_of(an)
    prods = set(mixA); sls = [G.sl_s085(L, mixA, mode='all' if kind == 'S2' else 'deep')]; ws = [1 - sum(w for _, w in Bs)]
    for n, w in Bs:
        mix, rd = X.mix_of(n); prods |= set(mix); sls.append(G.sl_static(mix, rd)); ws.append(w)
    return ['TQQQ', 'CASH'] + sorted(prods), G.bind(b, sls), ws


# ---------------- stress switches ----------------
_RF = {}
def rf_by_date():
    """daily rf on the NDX calendar 1984~2014 (from the MS1 real context; identical to every NDX-calendar context)"""
    if 'rf' not in _RF:
        c, dates = G.context('real_ndx_86_14'); _RF['rf'] = pd.Series(np.asarray(c.rf, float)[0], index=dates[c.ii[0]])
    return _RF['rf']


_DD = {}
def dedrift(target):
    """bond streams with their 1986~2014 mean excess return over rf replaced by `target` per year (timing kept, secular rally removed)"""
    if target in _DD: return _DD[target]
    D = XD.by_date().copy(); rf = rf_by_date(); w = rf.index[rf.index >= pd.Timestamp('1986-01-02')]
    info = {}
    for col in ['SHY', 'IEF', 'TLT', 'EDV']:
        x = D[col].reindex(w); ok = x.notna()
        m = float((x[ok] - rf[w][ok]).mean())
        D[col] = D[col] - (m - target / 252.0); info[col] = m * 252
    _DD[target] = D; _DD['info'] = info; return D


def stressed(kind):
    """returns (run kwargs, delay) and sets G.STRESS"""
    G.STRESS.update(lev_extra=0.0, bond_haircut=0.0, trend_scale=1.0, by_date=None)
    kw, delay = {}, 2
    for k in kind.split('+'):
        if k == 'base': pass
        elif k == 'cost2x': kw['cost'] = 0.006
        elif k == 'delay3': delay = 3
        elif k == 'sgov': kw['cash_kind'] = 'sgov'
        elif k == 'levx1': G.STRESS['lev_extra'] = 0.01
        elif k == 'bondhc05': G.STRESS['bond_haircut'] = 0.005
        elif k == 'drift15': G.STRESS['by_date'] = lambda: dedrift(0.015)
        elif k == 'drift0': G.STRESS['by_date'] = lambda: dedrift(0.0)
        elif k == 'trendhalf': G.STRESS['trend_scale'] = 0.5
        elif k == 'fee10': kw['cost'] = 0.0015
        elif k == 'rp1': kw['cash_kind'] = 'rp1'
        elif k == 'fee10rp1': kw['cost'] = 0.0015; kw['cash_kind'] = 'rp1'
        elif k == 'ext': G.STRESS['by_date'] = XD.by_date_ext
        else: raise KeyError(k)
    return kw, delay


def run_set(bn, names, kind='base', tag=None):
    t0 = time.time(); kw, delay = stressed(kind)
    b = G.Basis(bn); L = G.s085_levels(bn, delay=delay)
    ref = G.run(b, ['TQQQ', 'CASH'], [G.sl_s085(L)], [1.0], **kw)
    res = {'_meta': dict(basis=bn, kind=kind, P=b.P, years=b.K / 252), 's085': G.row(ref)}
    if kind in ('drift15', 'drift0'): res['_meta']['bond_excess_86_14_pa'] = _DD['info']
    paths = {'s085': ref['cagr']}
    for n in names:
        prods, sl, ws = build_any(b, L, n)
        r = G.run(b, prods, sl, ws, **kw); rw = G.row(r, ref)
        cov = [G.coverage(b, p) for p in prods if p not in ('TQQQ', 'CASH')]
        rw['cover'] = min(cov) if cov else 1.0
        res[n] = rw; paths[n] = r['cagr']
        print(bn, kind, n, 'cagr %.4f d %+.4f pw %.2f dd80 %.3f cov %.2f' % (rw['cagr'], rw['d_ref'], rw['pw_ref'], rw['dd80'], rw['cover']),
              '%.0fs' % (time.time() - t0), flush=True)
        del r; gc.collect()
    fn = OUT + 'stage2_%s_%s_%s.json' % (tag or 'stress', bn, kind)
    json.dump(res, open(fn, 'w'), indent=1)
    if b.P > 1: np.savez_compressed(fn.replace('.json', '_paths.npz'), **paths)
    G.STRESS.update(lev_extra=0.0, bond_haircut=0.0, trend_scale=1.0, by_date=None)
    return res


# ---------------- time-shift null ----------------
def null(bn, n, cand):
    t0 = time.time(); stressed('base')
    b0 = G.Basis(bn); L = G.s085_levels(bn)
    ref = G.run(b0, ['TQQQ', 'CASH'], [G.sl_s085(L)], [1.0])
    prods, sl, ws = build_any(b0, L, cand); act = G.run(b0, prods, sl, ws)
    d_act = float(np.median(act['cagr'] - ref['cagr'])); c_act = float(np.median(act['cagr']))
    cols = sorted({s for p in prods if p not in ('TQQQ', 'CASH') for s in G.product(b0, p)[3]})
    # by-date rf on this basis calendar (gathered rf is the same for every path at the same row)
    rfd = np.full(len(b0.D), np.nan); rfd[b0.c.ii.ravel()] = np.asarray(b0.c.rf, float).ravel()
    chk = np.full(len(b0.D), np.nan); chk[b0.c.ii[::-1].ravel()] = np.asarray(b0.c.rf, float)[::-1].ravel()
    ok_rf = np.isfinite(rfd) & np.isfinite(chk); assert np.nanmax(np.abs(rfd[ok_rf] - chk[ok_rf])) < 1e-12
    rfd = pd.Series(rfd).ffill().bfill().values
    rng = np.random.default_rng(20261104); out = []
    base_cols = {c: b0.D[c].values.astype(float).copy() for c in cols}
    for i in range(n):
        b = G.Basis(bn)
        x0 = base_cols[cols[0]]; idx = np.where(np.isfinite(x0))[0]; k = int(rng.integers(252, len(idx) - 252))
        for c in cols:                                  # same shift for every column of the fill (keeps their cross-relation)
            x = base_cols[c].copy(); ii = np.where(np.isfinite(x))[0]
            ex = x[ii] - rfd[ii]; x[ii] = np.roll(ex, k) + rfd[ii]; b.D[c] = x
        b._g = {}
        prods, sl, ws = build_any(b, L, cand); r = G.run(b, prods, sl, ws)
        out.append(dict(k=k, d=float(np.median(r['cagr'] - ref['cagr'])), cagr=float(np.median(r['cagr']))))
        if (i + 1) % 10 == 0: print(bn, cand, 'null', i + 1, '%.0fs' % (time.time() - t0), flush=True)
        del r, b; gc.collect()
    ds = np.array([o['d'] for o in out])
    res = dict(basis=bn, cand=cand, shifted_cols=cols, n=n, d_actual=d_act, cagr_actual=c_act, ref=float(np.median(ref['cagr'])),
               null_d_mean=float(ds.mean()), null_d_p50=float(np.median(ds)), null_d_p95=float(np.percentile(ds, 95)),
               null_d_max=float(ds.max()), p_value=float((np.sum(ds >= d_act) + 1) / (n + 1)), draws=out)
    json.dump(res, open(OUT + 'stage2_null_%s_%s.json' % (bn, cand), 'w'), indent=1)
    print('null done', json.dumps({k: v for k, v in res.items() if k != 'draws'}), flush=True)


# ---------------- holds ----------------
def holds(bn):
    stressed('base'); b = G.Basis(bn); res = {}
    for n in ('QQQ', 'QLD', 'TQQQ'):
        r = G.run(b, [n, 'CASH'], G.bind(b, [G.sl_static({n: 1.0})]), [1.0]); res[n] = G.row(r)
        print(bn, 'hold', n, '%.4f' % res[n]['cagr'], flush=True)
    json.dump(res, open(OUT + 'stage2_holds_%s.json' % bn, 'w'), indent=1)


# ---------------- proxy check + standalone Sharpe ----------------
def proxy():
    import bdata as BD
    rf = rf_by_date(); A = XD.by_date(); S = BD.by_date(actual=False)
    def stats(a, s, lab):
        j = a.index.intersection(s.index).intersection(rf.index); a = a[j]; s = s[j]; y = len(j) / 252
        ca = float(np.prod(1 + a) ** (1 / y) - 1); cs = float(np.prod(1 + s) ** (1 / y) - 1)
        d = s - a
        return dict(what=lab, start=str(j[0].date()), end=str(j[-1].date()), cagr_actual=ca, cagr_proxy=cs, gap_pa=cs - ca,
                    te_pa=float(d.std() * np.sqrt(252)), corr=float(np.corrcoef(a, s)[0, 1]), beta=float(np.cov(s, a)[0, 1] / a.var()))
    out = []
    tlt_a = BD.panel_ret('TLT'); out.append(stats(tlt_a, S['TLT'], 'TLT: H.15 합성 vs 실제 TLT'))
    ief_a = BD.panel_ret('IEF'); out.append(stats(ief_a, S['IEF'], 'IEF: H.15 합성 vs 실제 IEF'))
    tmf_a = BD.panel_ret('TMF'); j = tmf_a.index.intersection(rf.index)
    syn_from_act = 3 * tlt_a.reindex(j) - 2 * rf[j] - 0.0245 / 252
    syn_full = 3 * S['TLT'].reindex(j) - 2 * rf[j] - 0.0245 / 252
    out.append(stats(tmf_a[j], syn_from_act, 'TMF: 실제 TLT×3 공식 vs 실제 TMF'))
    out.append(stats(tmf_a[j], syn_full, 'TMF: H.15 합성 TLT×3 공식 vs 실제 TMF'))
    for k in ('TQQQ', 'UPRO'):
        try:
            a = BD.panel_ret(k); jj = a.index.intersection(rf.index)
            out.append(dict(what=k + ' (참고: 실제 거래 시작)', start=str(jj[0].date())))
        except Exception as e: out.append(dict(what=k, err=str(e)[:80]))
    # standalone after-fee Sharpe of every product on real NDX 1986~2014 (G1 for non-timing streams: ~1.1)
    stressed('base'); b = G.Basis('real_ndx_86_14'); f = b.rf[0, G.WARM:]; sh = {}
    for n in ['TQQQ', 'QQQ'] + X.ALL31[:-3] + ['QLD']:
        if n in ('HFEA', 'DEF3', 'TRIO'): continue
        r = G.product(b, n)[0][0, G.WARM:]; ex = r - f; cov = G.coverage(b, n)
        sh[n] = dict(sharpe=float(ex.mean() / ex.std() * np.sqrt(252)), ann_ret=float(np.prod(1 + r) ** (252 / len(r)) - 1), cover=cov)
    res = dict(proxy=out, standalone_sharpe_real_ndx_86_14=sh)
    json.dump(res, open(OUT + 'stage2_proxy.json', 'w'), indent=1, ensure_ascii=False)
    for o in out: print(o)
    for k, v in sh.items(): print(k, '%.2f %.3f cov %.2f' % (v['sharpe'], v['ann_ret'], v['cover']))


# ---------------- hindsight ceiling of the fill axis ----------------
ORC = ['SHY', 'IEF', 'TLT', 'EDV', 'UST', 'TYD', 'UBT', 'TMF', 'GLD', 'GDX', 'DBMF', 'KMLM', 'XLU', 'XLP', 'XLV']
def oracle(bn, opts=None, seg=0, q=1.0, default='CASH', tag=''):
    """NOT tradable: per idle episode (maximal run of L < 3; seg > 0 -> also cut every `seg` rows inside the episode) the option with
    the best compound return over that segment (CASH included). q < 1: information ladder, the oracle pick is used with prob q per
    segment (fixed seed), else `default`. A ceiling for 'what a fill rule on this structure could add'."""
    stressed('base'); t0 = time.time(); opts = list(ORC if opts is None else opts)
    b = G.Basis(bn); L = G.s085_levels(bn); K = b.K; rng = np.random.default_rng(7)
    if default not in opts and default != 'CASH': opts.append(default)
    ref = G.run(b, ['TQQQ', 'CASH'], [G.sl_s085(L)], [1.0])
    names = ['CASH'] + opts
    lr = np.stack([np.log1p(np.maximum(G.product(b, n)[0][:, G.WARM:], -0.99)) for n in names])   # (O,P,K)
    pick = np.zeros((len(names),))
    def sl(p, J):
        lv = L[p]; W = np.zeros((K, len(J))); W[:, J['TQQQ']] = lv / 3; idle = 1 - lv / 3
        cs = np.concatenate([np.zeros((len(names), 1)), np.cumsum(lr[:, p, :], axis=1)], axis=1)
        isd = lv < 3 - 1e-9; k = 0
        while k < K:
            if not isd[k]: k += 1; continue
            e = k
            while e < K and isd[e] and (seg == 0 or e - k < seg): e += 1
            j = int(np.argmax(cs[:, e] - cs[:, k]))
            if q < 1.0 and rng.random() >= q: j = names.index(default)
            pick[j] += 1
            W[k:e, J[names[j]]] += idle[k:e]; k = e
        fl = np.r_[True, np.diff(lv) != 0] | np.r_[True, np.any(np.diff(W, axis=0) != 0, axis=1)]
        return W, fl
    r = G.run(b, ['TQQQ'] + names, [sl], [1.0]); rw = G.row(r, ref)
    rw['picks'] = {names[j]: int(pick[j]) for j in range(len(names)) if pick[j]}
    res = {'s085': G.row(ref), 'oracle_fill': rw, 'opts': names, 'seg': seg, 'q': q, 'default': default}
    json.dump(res, open(OUT + 'stage2_oracle_%s%s.json' % (bn, tag), 'w'), indent=1)
    print(bn, 'oracle', json.dumps(rw), '%.0fs' % (time.time() - t0), flush=True)


if __name__ == '__main__':
    part = sys.argv[1]
    if part == 'combos':
        A, B = combo_rule(); print('rule: A =', A, 'B =', B, flush=True)
        run_set(sys.argv[2], ['C1', 'C2', 'C3', 'C4'], 'base', tag='combos')
    elif part == 'stress':
        for kind in sys.argv[3].split(','):
            run_set(sys.argv[2], FILLS + ['C1', 'C2', 'C3', 'C4'], kind)
    elif part == 'null': null(sys.argv[2], int(sys.argv[3]), sys.argv[4])
    elif part == 'spxext':
        for bn in ('real_spx_55_85', 'real_spx_70_85'): run_set(bn, FILLS + ['C1', 'C2', 'C3', 'C4'], 'ext', tag='spxext')
    elif part == 'holds': holds(sys.argv[2])
    elif part == 'proxy': proxy()
    elif part == 'oracle': oracle(sys.argv[2])
    elif part == 'oracle_x':                      # sanity + monthly ceiling + information ladder
        bn = sys.argv[2]
        oracle(bn, opts=[], tag='_chk_cashonly')                       # must equal s0.85
        oracle(bn, opts=['TMF'], tag='_chk_tmf')                       # cash/TMF per episode
        oracle(bn, seg=21, tag='_seg21')                               # monthly perfect foresight among 16 options
        for qq in (0.25, 0.5, 0.75): oracle(bn, q=qq, default='TMF', tag='_q%02d' % int(qq * 100))
    elif part == 'oracle_y':                      # fixed cash-only check + monthly information ladder
        bn = sys.argv[2]
        oracle(bn, opts=[], tag='_chk_cashonly')
        for qq in (0.1, 0.2, 0.3, 0.5): oracle(bn, seg=21, q=qq, default='TMF', tag='_seg21_q%02d' % int(qq * 100))
    else: raise SystemExit(__doc__)
