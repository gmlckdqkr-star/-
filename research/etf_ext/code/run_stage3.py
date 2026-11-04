"""ETX1 stage 3 (PRECOMMIT_ETX1_S3.md, sha 05e36d6c): s0.85 on-sleeve 3x breadth (A), bond-trend-gated fills (B), best A + best B (C).
s0.85 levels unchanged (in force, delay 2). <=2014 only.
usage (scratchpad cwd, ms1 venv):
  run_stage3.py screen <basis>[,..] [kind]   all 32 configs (C needs results/stage3_base_dev250_path.json first)
  run_stage3.py null <basis> <n>              time-shift null for the best B (TLT and IEF excess returns shifted together)
  run_stage3.py oracle <basis>                hindsight ceilings: on-sleeve product per on-episode; + fill per idle episode
Outputs results/stage3_<kind>_<basis>.json; every d is paired vs s0.85 under the same stress."""
import sys, os, json, time, gc, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import etxeng as G, etxcands as X, run_stage2 as S2
OUT = '/mnt/project-files/research/etf_ext/results/'
WARM = G.WARM
ON = ['TQQQ', 'UPRO', 'TNA', 'TECL', 'CURE', 'UTSL', 'FAS', 'SOXL', 'WANT', 'DUSL', 'DRN']
UND = {'TQQQ': 'NDX', **{k: G.LEVMAP[k][0] for k in ON if k != 'TQQQ'}}


def configs():
    out = [('A1_' + p, ('A1', p)) for p in ON[1:]]
    out += [('A2_' + p, ('A2', p)) for p in ON[1:]]
    out += [('A3_' + r, ('A3', r)) for r in ('lowvol', 'mom', 'sharpe', 'mom3')]
    out += [('A4_ew', ('A4',))]
    out += [('B_%s_%s' % (f, g), ('B', f, g)) for f in ('TYD', 'TMF') for g in ('GA', 'GB', 'GC')]
    return out


def c_rule():
    R = json.load(open(OUT + 'stage3_base_dev250_path.json'))
    a = max([k for k in R if k.startswith('A')], key=lambda k: R[k]['d_ref'])
    bb = max([k for k in R if k.startswith('B_')], key=lambda k: R[k]['d_ref'])
    return a, bb


def all_configs():
    cf = dict(configs())
    if os.path.exists(OUT + 'stage3_base_dev250_path.json'):
        a, bb = c_rule(); cf['C_' + a + '+' + bb] = ('C', cf[a], cf[bb])
    return cf


# ---------------- trailing information on the path (through row t = WARM + k - 2) ----------------
def und_returns(b, p):
    """(11, T) 1x underlying returns on path p (NaN where missing) and rf (T,)"""
    U = np.stack([b.rN[p] if UND[n] == 'NDX' else b.g(UND[n])[p] for n in ON]); return U, b.rf[p]


def select(b, p, rule):
    """(K, 11) on-sleeve composition from a monthly rule"""
    K = b.K; U, f = und_returns(b, p); comp = np.zeros((K, len(ON))); cur = None
    for k in range(K):
        if k % 21 == 0:
            t = WARM + k - 2; w = U[:, t - 251:t + 1]; ok = np.all(np.isfinite(w), axis=1)
            if rule == 'lowvol': sc = -np.nanstd(w, axis=1)
            elif rule == 'sharpe':
                ex = w - f[t - 251:t + 1]; sc = np.nanmean(ex, axis=1) / np.maximum(np.nanstd(w, axis=1), 1e-12)
            else: sc = np.nansum(np.log1p(U[:, t - 251:t - 20]), axis=1)            # 231 rows ending 21 rows before t
            sc = np.where(ok, sc, -np.inf); cur = np.zeros(len(ON))
            if rule == 'mom3': cur[np.argsort(-sc)[:3]] = 1 / 3
            else: cur[int(np.argmax(sc))] = 1.0
        comp[k] = cur
    return comp


def gate(b, g):
    """(P, K) bool, in force at row k from data through t = k + WARM - 2"""
    f = b.rf; P, T = f.shape
    if g in ('GA', 'GC'):
        src, n = ('TLT', 252) if g == 'GA' else ('IEF', 126)
        x = np.log1p(np.nan_to_num(b.g(src))) - np.log1p(f)
        cs = np.concatenate([np.zeros((P, 1)), np.cumsum(x, axis=1)], axis=1)
        tt = np.arange(WARM, T) - 2; s = cs[:, tt + 1] - cs[:, tt + 1 - n]; return s > 0
    I = np.cumprod(1 + np.nan_to_num(b.g('TLT')), axis=1); cs = np.concatenate([np.zeros((P, 1)), np.cumsum(I, axis=1)], axis=1)
    tt = np.arange(WARM, T) - 2; sma = (cs[:, tt + 1] - cs[:, tt + 1 - 200]) / 200; return I[:, tt] > sma


def sleeve(b, L, cfg):
    """returns (prods, sleeve fn f(p, J) -> (W, flags))"""
    kind = cfg[0]; K = b.K
    if kind == 'C': a_cfg, b_cfg = cfg[1], cfg[2]
    else: a_cfg = cfg if kind.startswith('A') else None; b_cfg = cfg if kind == 'B' else None
    onp = ['TQQQ']
    if a_cfg is not None:
        if a_cfg[0] == 'A1': onp = [a_cfg[1]]
        elif a_cfg[0] == 'A2': onp = ['TQQQ', a_cfg[1]]
        else: onp = list(ON)
    fillp = [b_cfg[1]] if b_cfg is not None else []
    GT = gate(b, b_cfg[2]) if b_cfg is not None else None
    prods = list(dict.fromkeys(['TQQQ', 'CASH'] + onp + fillp))
    def f(p, J):
        lv = L[p]; on = lv / 3; idle = 1 - on; W = np.zeros((K, len(J))); fl = np.r_[True, np.diff(lv) != 0]
        if a_cfg is None or a_cfg[0] == 'A1': W[:, J[onp[0]]] += on
        elif a_cfg[0] == 'A2': W[:, J['TQQQ']] += on * 0.5; W[:, J[a_cfg[1]]] += on * 0.5
        else:
            if a_cfg[0] == 'A4': comp = np.full((K, len(ON)), 1 / len(ON)); m = np.zeros(K, bool); m[::21] = True; fl = fl | m
            else:
                comp = select(b, p, a_cfg[1]); fl = fl | np.r_[True, np.any(np.diff(comp, axis=0) != 0, axis=1)]
            for j, n in enumerate(ON): W[:, J[n]] += on * comp[:, j]
        if GT is None: W[:, J['CASH']] += idle
        else:
            gt = GT[p].astype(float); W[:, J[fillp[0]]] += idle * gt; W[:, J['CASH']] += idle * (1 - gt)
            fl = fl | np.r_[True, np.diff(gt) != 0]
        return W, fl
    return prods, f


def stressed(kind):
    G.STRESS['eq_bonus'] = 0.0
    if kind == 'nohc': kw, d = S2.stressed('base'); G.STRESS['eq_bonus'] = 0.012; return kw, d
    return S2.stressed(kind)


def screen(bn, kind='base', names=None):
    t0 = time.time(); kw, delay = stressed(kind)
    b = G.Basis(bn); L = G.s085_levels(bn, delay=delay)
    ref = G.run(b, ['TQQQ', 'CASH'], [G.sl_s085(L)], [1.0], **kw)
    res = {'_meta': dict(basis=bn, kind=kind, P=b.P), 's085': G.row(ref)}; paths = {'s085': ref['cagr']}
    for n, cfg in all_configs().items():
        if names and n not in names: continue
        prods, f = sleeve(b, L, cfg); r = G.run(b, prods, [f], [1.0], **kw); rw = G.row(r, ref)
        rw['cover'] = min([G.coverage(b, q) for q in prods if q not in ('TQQQ', 'CASH')], default=1.0)
        res[n] = rw; paths[n] = r['cagr']
        print(bn, kind, n, 'cagr %.4f d %+.4f pw %.2f dd80 %.3f cov %.2f' % (rw['cagr'], rw['d_ref'], rw['pw_ref'], rw['dd80'], rw['cover']),
              '%.0fs' % (time.time() - t0), flush=True)
        del r; gc.collect()
    fn = OUT + 'stage3_%s_%s.json' % (kind, bn); json.dump(res, open(fn, 'w'), indent=1)
    if b.P > 1: np.savez_compressed(fn.replace('.json', '_paths.npz'), **paths)
    S2.stressed('base'); G.STRESS['eq_bonus'] = 0.0


def null(bn, n):
    stressed('base'); t0 = time.time()
    R = json.load(open(OUT + 'stage3_base_dev250_path.json'))
    best = max([k for k in R if k.startswith('B_')], key=lambda k: R[k]['d_ref']); cfg = all_configs()[best]
    b0 = G.Basis(bn); L = G.s085_levels(bn); ref = G.run(b0, ['TQQQ', 'CASH'], [G.sl_s085(L)], [1.0])
    prods, f = sleeve(b0, L, cfg); act = G.run(b0, prods, [f], [1.0]); d_act = float(np.median(act['cagr'] - ref['cagr']))
    rfd = np.full(len(b0.D), np.nan); rfd[b0.c.ii.ravel()] = np.asarray(b0.c.rf, float).ravel(); rfd = pd.Series(rfd).ffill().bfill().values
    base = {c: b0.D[c].values.astype(float).copy() for c in ('TLT', 'IEF')}
    rng = np.random.default_rng(20261104); out = []
    for i in range(n):
        b = G.Basis(bn); idx = np.where(np.isfinite(base['TLT']))[0]; k = int(rng.integers(252, len(idx) - 252))
        for c in ('TLT', 'IEF'):
            x = base[c].copy(); ii = np.where(np.isfinite(x))[0]; ex = x[ii] - rfd[ii]; x[ii] = np.roll(ex, k) + rfd[ii]; b.D[c] = x
        b._g = {}; prods, f = sleeve(b, L, cfg); r = G.run(b, prods, [f], [1.0])
        out.append(float(np.median(r['cagr'] - ref['cagr'])))
        if (i + 1) % 20 == 0: print(bn, best, 'null', i + 1, '%.0fs' % (time.time() - t0), flush=True)
        del r, b; gc.collect()
    ds = np.array(out)
    res = dict(basis=bn, cand=best, n=n, d_actual=d_act, null_mean=float(ds.mean()), null_p95=float(np.percentile(ds, 95)),
               p_value=float((np.sum(ds >= d_act) + 1) / (n + 1)), draws=out)
    json.dump(res, open(OUT + 'stage3_null_%s.json' % bn, 'w'), indent=1)
    print('null done', {k: v for k, v in res.items() if k != 'draws'}, flush=True)


def oracle(bn, q=1.0, tags=('on_only', 'on_and_fill')):
    """NOT tradable. (1) per on-episode (maximal run of L > 0) the 3x product with the best compound return, idle cash;
    (2) same + per idle episode the best of the stage-2 fill options (CASH incl.). q < 1: the on-episode oracle pick is used
    with prob q (fixed seed), else TQQQ (= s0.85) -> information ladder."""
    stressed('base'); t0 = time.time(); b = G.Basis(bn); L = G.s085_levels(bn); K = b.K; rng = np.random.default_rng(11)
    ref = G.run(b, ['TQQQ', 'CASH'], [G.sl_s085(L)], [1.0])
    lr_on = np.stack([np.log1p(np.maximum(G.product(b, n)[0][:, WARM:], -0.99)) for n in ON])
    fills = ['CASH'] + S2.ORC
    lr_f = np.stack([np.log1p(np.maximum(G.product(b, n)[0][:, WARM:], -0.99)) for n in fills])
    def runs(mask):
        k = 0; out = []
        while k < K:
            if not mask[k]: k += 1; continue
            e = k
            while e < K and mask[e]: e += 1
            out.append((k, e)); k = e
        return out
    res = {'s085': G.row(ref)}
    for tag, with_fill in [x for x in (('on_only', False), ('on_and_fill', True)) if x[0] in tags]:
        def f(p, J):
            lv = L[p]; W = np.zeros((K, len(J))); on = lv / 3; idle = 1 - on
            cs = np.concatenate([np.zeros((len(ON), 1)), np.cumsum(lr_on[:, p], axis=1)], axis=1)
            for k, e in runs(lv > 1e-9):
                j = int(np.argmax(cs[:, e] - cs[:, k]))
                if q < 1.0 and rng.random() >= q: j = 0
                W[k:e, J[ON[j]]] += on[k:e]
            if with_fill:
                cf = np.concatenate([np.zeros((len(fills), 1)), np.cumsum(lr_f[:, p], axis=1)], axis=1)
                for k, e in runs(lv < 3 - 1e-9):
                    j = int(np.argmax(cf[:, e] - cf[:, k])); W[k:e, J[fills[j]]] += idle[k:e]
            else: W[:, J['CASH']] += idle
            fl = np.r_[True, np.any(np.diff(W, axis=0) != 0, axis=1)]
            return W, fl
        prods = list(dict.fromkeys(['TQQQ', 'CASH'] + ON + (fills if with_fill else [])))
        r = G.run(b, prods, [f], [1.0]); res[tag] = G.row(r, ref)
        print(bn, 'oracle', tag, json.dumps(res[tag]), '%.0fs' % (time.time() - t0), flush=True)
    json.dump(res, open(OUT + 'stage3_oracle_%s%s.json' % (bn, '' if q >= 1 else '_q%02d' % int(q * 100)), 'w'), indent=1)


if __name__ == '__main__':
    part = sys.argv[1]
    if part == 'screen':
        for bn in sys.argv[2].split(','):
            for kind in (sys.argv[3].split(',') if len(sys.argv) > 3 else ['base']): screen(bn, kind)
    elif part == 'null': null(sys.argv[2], int(sys.argv[3]))
    elif part == 'oracle': oracle(sys.argv[2])
    elif part == 'oracle_q':
        for qq in (0.5, 0.75, 0.9): oracle(sys.argv[2], q=qq, tags=('on_only',))
    else: raise SystemExit(__doc__)
