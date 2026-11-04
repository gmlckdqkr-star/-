"""KL1 one-time confirmation (PRECOMMIT_KL1 sec.8) of the frozen top-20 per family, plus same-basis benchmarks,
KR-stream MS1-comparable numbers, Sharpe (G1 rule 5) and G1 (official gate.test + KR-index version) for S2.
Run ONCE after results/top20_<fam>.json exist. Writes results/confirm_<fam>.json."""
import os, sys, json, time, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/claude-0/-home-user--/e60ac389-f078-575c-af9f-bad532fab64a/scratchpad/kl/nb')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import wsdata as WD, wsstk as WS, kl_sig as SG, kl_gen as G, kl_blk as BK, kl_engine as EN, kl_prep as PR, kl_run_blk as RB, kl_run_s2 as R2
CACHE = WD.CACHE; RES = os.path.join(HERE, '..', 'results')
N_TOTAL = 557468
START = {'KR': '1999-01-04', 'US': '1971-01-04'}
SELEND = {'KR': '2008-12-31', 'US': '1999-12-31'}
CONF0 = {'KR': '2009-01-02', 'US': '2000-01-03'}
END = '2014-12-31'
FAIL_MODE = os.environ.get('KL_FAIL', 'conservative')     # sensitivity only: 'lenient'
DELAY = int(os.environ.get('KL_DELAY', '2'))              # sensitivity only: 1
SUFFIX = ('' if FAIL_MODE == 'conservative' else '_' + FAIL_MODE) + ('' if DELAY == 2 else '_d%d' % DELAY)


# ---------------------------------------------------------------- block families
def full_blocks(panel, delay=DELAY):
    """all blocks from START to 2014-12-31 (windows inside), for h in HS: same construction as kl_prep."""
    out = {}
    if panel == 'KR':
        K = WD.load_kr(); X = WD.kr_derived(K); dates = pd.to_datetime(K['dates']); T, N = X['idx'].shape
        elig_d = X['trade'] & (X['age'] >= 20) & (np.nan_to_num(X['adv20']) >= 1e8)
        defs = SG.kr_defs(K, X); names = SG.KR_DEFS
        fail, reuse_row, fail1 = WD.kr_spells(K, X, FAIL_MODE)
        listed = X['listed']; last_row = np.where(listed.any(0), T - 1 - np.argmax(listed[::-1], axis=0), 0).astype(np.int64)
        for h in G.HS:
            t_dec = PR.blocks(dates, h, START['KR'], END, delay)
            el = elig_d[t_dec]
            R, ok = WS._kr_window(X['idx'], X['trade'], X['limdn'], listed, last_row, fail, t_dec + delay - 1, h, el, reuse_row, fail1)
            e0 = t_dec + delay; elig = ok & ~np.isnan(R); entry = elig & X['trade'][e0] & ~X['limup'][e0]
            out[h] = dict(t_dec=t_dec, R=R, elig=elig, entry=entry, sc=np.stack([defs[d][t_dec] for d in names]),
                          hs=X['hs'][t_dec], s20=np.nan_to_num(X['s20'][t_dec], nan=0.05), adv=np.maximum(np.nan_to_num(X['adv20'][t_dec], nan=1e8), 1e6),
                          mcap=np.nan_to_num(K['marcap'][t_dec]), dates=dates[t_dec], end=dates[np.minimum(e0 + h, T - 1)])
        return out, dates
    U = WD.load_us(); dates = U['dates']; mem = U['member']; adjU = U['adj']
    defs, adj = SG.us_defs(U); T = len(dates)
    for h in G.HS:
        t_dec = PR.blocks(dates, h, START['US'], END, delay)
        el = mem[t_dec] & (adjU[t_dec] > 0) & (adjU[t_dec + delay] > 0)
        R, ok = WS._us_window(adjU, t_dec + delay - 1, h, el)
        elig = ok & ~np.isnan(R)
        out[h] = dict(t_dec=t_dec, R=R, elig=elig, entry=elig, sc=np.stack([defs[d][t_dec] for d in SG.US_DEFS]),
                      dates=dates[t_dec], end=dates[np.minimum(t_dec + delay + h, T - 1)])
    return out, dates


def rf_blocks(panel, b, h, dates):
    if panel == 'KR':
        z = np.load(CACHE + 'kr_idx.npz'); X = z['X']; T = X.shape[1]
        e0 = b['t_dec'] + DELAY
        return BK.window_prod(z['rf'], e0, h, T), {'lev0': BK.window_prod(X[1], e0, h, T), 'cash': BK.window_prod(X[3], e0, h, T),
                                                   'inv': BK.window_prod(X[4], e0, h, T), 'idx1': BK.window_prod(X[2], e0, h, T)}
    if not os.path.exists(CACHE + 'us_prod_panelcal.npz'):
        RB.us_products_panelcal()
    z = np.load(CACHE + 'us_prod_panelcal.npz'); T = z['L3spx'].shape[0]; e0 = b['t_dec'] + DELAY
    pw = {'lev0': BK.window_prod(z['L3spx'], e0, h, T), 'lev1': BK.window_prod(z['L3tq'], e0, h, T), 'cash': BK.window_prod(z['cash'], e0, h, T),
          'inv': BK.window_prod(z['inv'], e0, h, T), 'idx1': BK.window_prod(z['spx1'], e0, h, T), 'tq1': BK.window_prod(z['tq1'], e0, h, T)}
    return pw['cash'], pw


def perf_blocks(r, years, h, tax, paths=500, seed=11):
    B = WS.Blocks(); B.h = h; B.years = years; B.tax = tax
    return WS.perf(B, np.asarray(r, float), paths=paths, seed=seed)


def sharpe(r, rf, h):
    x = np.asarray(r) - np.asarray(rf)
    return float(x.mean() / x.std(ddof=1) * np.sqrt(252 / h)) if x.std() > 0 else float('nan')


def s3_aftertax_kr(rs, g, cw, gi, w, on, om, cs, ce):
    """same as BK.s3_returns + 15.4% tax on each block's positive KRLEV / KRINV sleeve gain (rebalanced = sold, no offset)."""
    r = BK.s3_returns(rs, g, cw, gi, w, on, om, cs, ce)
    tl = np.where(on == 1, w, 0.0); ti = np.where((on == 0) & (om == 3), w, 0.0)
    return r - 0.154 * np.maximum(tl * g, 0) - 0.154 * np.maximum(ti * gi, 0)


def block_family(fam):
    panel = fam[2:]; top = json.load(open(os.path.join(RES, 'top20_%s.json' % fam)))['top20']
    FB, dates = full_blocks(panel)
    A = np.load(CACHE + '%s_atoms.npy' % panel.lower(), mmap_mode='r')
    out = []
    bench_cache = {}
    for t in top:
        row = np.array(t['row'], np.int64)
        if fam.startswith('S1'):
            hi, fi = int(row[8]), int(row[9])
        else:
            hi, fi = int(row[4]), 0
        h = G.HS[hi]; b = FB[h]
        bl = RB.bases(panel, b) if panel == 'KR' else [b['elig']]
        base = bl[fi]
        if panel == 'KR':
            hsb = 0.00015 + b['hs']; impf = 0.7 * b['s20'] / np.sqrt(b['adv']); kr = True
        else:
            hsb = np.zeros((1, 1)); impf = np.zeros((1, 1)); kr = False
        nd_all = b['sc'].shape[0]
        P = np.stack([BK.pct_ranks(b['sc'][d].astype(np.float32), base) for d in range(nd_all)])
        nb = base.shape[0]
        R = b['R'].astype(np.float64)
        rfb, PW = rf_blocks(panel, b, h, dates)
        key = (h, fi)
        if key not in bench_cache:
            rb, _ = BK.s1_returns(P, np.zeros(4, np.int64), 0, 0, 0, 0.0, np.ones(nb, np.int8), base, R, b['entry'], hsb, impf, kr, 1e7)
            bench_cache[key] = rb
        rb = bench_cache[key]
        if fam.startswith('S1'):
            form = row[0] - 3 if row[0] >= 3 else row[0]
            reg = np.ones(nb, np.int8)
            if row[10] >= 0:
                reg = (np.asarray(A[row[10]])[b['t_dec']] == row[11]).astype(np.int8)
            rv, nh = BK.s1_returns(P, row[2:6].copy(), int(row[1]), int(form), int(row[6]), float(G.Q1[row[7]]), reg, base, R, b['entry'], hsb, impf, kr, 1e7)
            r_at, rb_at = rv, rb                       # KR: no capital-gains tax (transaction tax in costs); US: yearly 22% in perf
            extra = dict(mean_held=float(nh.mean()))
        else:
            spec = np.array([row[1], row[2] if row[0] == 1 else -1, -1, -1], np.int64)
            rs, nh = BK.s1_returns(P[:G.NCORE], spec, 1 if row[0] == 0 else 2, int(row[0]), 0, float(G.Q3[row[3]]), np.ones(nb, np.int8), base, R, b['entry'], hsb, impf, kr, 1e7)
            w = (G.W_KR if panel == 'KR' else G.W_US)[row[5]]
            g = PW['lev%d' % row[6]] if panel == 'US' else PW['lev0']
            on = np.ones(nb, np.int8)
            if row[7] >= 0:
                st = np.asarray(A[row[7]])[b['t_dec']]; on = np.where(st == 0, 0, 1).astype(np.int8)
            cs, ce = BK.C_STK[panel], BK.C_ETF[panel]
            rv = BK.s3_returns(rs, g, PW['cash'], PW['inv'], w, on, int(row[8]), cs, ce)
            rb2 = BK.s3_returns(rb, g, PW['cash'], PW['inv'], w, np.ones(nb, np.int8), 0, cs, ce)
            if panel == 'KR':
                r_at = s3_aftertax_kr(rs, g, PW['cash'], PW['inv'], w, on, int(row[8]), cs, ce)
                rb_at = s3_aftertax_kr(rb, g, PW['cash'], PW['inv'], w, np.ones(nb, np.int8), 0, cs, ce)
            else:
                r_at, rb_at = rv, rb2
            rb = rb2
            extra = dict(on_share=float((on == 1).mean()), w=w)
        sel = np.asarray(b['end'] <= pd.Timestamp(SELEND[panel]))
        conf = np.asarray(b['dates'] >= pd.Timestamp(CONF0[panel]))
        lg = np.log1p(np.maximum(rv, -0.999999)) - np.log1p(np.maximum(rb, -0.999999))
        yrs = pd.DatetimeIndex(b['end']).year.values
        tax = panel == 'US'
        cr = perf_blocks(r_at[conf], yrs[conf], h, tax); cb = perf_blocks(rb_at[conf], yrs[conf], h, tax)
        sr_ = perf_blocks(r_at[sel], yrs[sel], h, tax); sb = perf_blocks(rb_at[sel], yrs[sel], h, tax)
        fr = perf_blocks(r_at, yrs, h, tax); fb = perf_blocks(rb_at, yrs, h, tax)
        sel_adv = float(lg[sel].mean() * 252 / h); conf_adv = float(lg[conf].mean() * 252 / h)
        rec = dict(rank=t['rank'], row=t['row'], h=h, raw_adv_sel_frozen=t['raw_adv_ann'], sel_adv_recomputed=sel_adv, conf_adv=conf_adv,
                   decay=conf_adv / sel_adv if sel_adv else None, conf_pass_ii=bool(conf_adv > 0 and conf_adv >= 0.5 * sel_adv),
                   sel_real_cagr=sr_[0], sel_bench_real=sb[0], conf_real_cagr=cr[0], conf_bench_real=cb[0],
                   conf_resample_med=cr[1], full_real=fr[0], full_resample_med=fr[1], full_headline=min(fr[0], fr[1]),
                   bench_full_real=fb[0], bench_full_resample_med=fb[1], bench_full_headline=min(fb[0], fb[1]),
                   sharpe_sel=sharpe(rv[sel], rfb[sel], h), sharpe_conf=sharpe(rv[conf], rfb[conf], h),
                   sharpe_exc_sel=float(lg[sel].mean() / lg[sel].std(ddof=1) * np.sqrt(252 / h)), sharpe_exc_conf=float(lg[conf].mean() / lg[conf].std(ddof=1) * np.sqrt(252 / h)),
                   n_conf_blocks=int(conf.sum()), **extra)
        out.append(rec)
        print(fam, t['rank'], 'h', h, 'sel adv %.4f -> conf adv %.4f | conf real %.4f vs bench %.4f | full headline %.4f vs bench %.4f | SR sel %.2f conf %.2f' % (
            sel_adv, conf_adv, cr[0], cb[0], rec['full_headline'], rec['bench_full_headline'], rec['sharpe_sel'], rec['sharpe_conf']), flush=True)
    # same-basis passive references (block level, h = 21)
    b = FB[21]; rfb, PW = rf_blocks(panel, b, 21, dates); yrs = pd.DatetimeIndex(b['end']).year.values
    conf = np.asarray(b['dates'] >= pd.Timestamp(CONF0[panel]))
    refs = {}
    for nm in (['idx1', 'lev0'] if panel == 'KR' else ['idx1', 'tq1', 'lev0', 'lev1']):
        x = PW[nm]
        x_at = x - 0.154 * np.maximum(x, 0) if (panel == 'KR' and nm == 'lev0') else x
        tax = panel == 'US'
        refs[nm] = dict(full=perf_blocks(x_at, yrs, 21, tax)[:2], conf=perf_blocks(x_at[conf], yrs[conf], 21, tax)[:2])
    return dict(fam=fam, rows=out, passive_refs=refs, note='KR: no capital-gains tax on stocks (0.3% transaction tax in costs), KRLEV/KRINV 15.4% per block gain; US: WS1 perf yearly 22% (all P&L treated as realized, conservative)')


# ---------------------------------------------------------------- S2 families
def kr_aftertax(X, dec, t0, t1, cost=0.0015):
    """after-cost after-tax daily equity (KRLEV/KRINV: 15.4% of each sale gain, no offset; KR200/cash 0)."""
    v = 1.0; cur = 3; basis = 1.0; E = np.empty(t1 - t0)
    NC = np.array([1, 1, 1, 0, 1])
    for i in range(t0, t1):
        p = dec[i - 3] if i >= 3 else 2
        if p != cur:
            if cur in (1, 4) and v > basis:
                v -= 0.154 * (v - basis)
            v *= 1 - cost * (NC[cur] + NC[p]); cur = p; basis = v
        v *= 1 + X[p, i]
        E[i - t0] = v
    return E


def kr_gate(sig, X, dates, a, b, trials):
    ex = np.log1p(X[1]) - np.log1p(X[3]); cs = np.r_[0, np.cumsum(ex)]
    i0 = int(np.searchsorted(dates.values, np.datetime64(a))); i1 = int(np.searchsorted(dates.values, np.datetime64(b), side='right'))
    s = pd.Series(sig, index=dates)
    hits = []; ups = []
    for t in range(i0, i1 - 24, 21):
        y = cs[t + 24] - cs[t + 3] > 0
        hits.append(bool(s.iloc[t]) == y); ups.append(y)
    n = len(hits); hit = float(np.mean(hits)); se = (hit * (1 - hit) / n) ** .5
    return dict(n=n, hit=hit, always_up=float(np.mean(ups)), hit_deflated=hit - 2 * se * (1 + np.log(max(trials, 1))) ** .5)


def s2_family(fam):
    panel = fam[2:]
    sys.path.insert(0, '/mnt/project-files/research/breakthrough/code'); import gate
    top = json.load(open(os.path.join(RES, 'top20_%s.json' % fam)))['top20']
    I = R2.inputs(panel); dates = I['dates']; X = I['X']; A = I['A']
    t1 = int(np.searchsorted(dates.values, np.datetime64(END), side='right'))
    msel, w0, w1 = R2.month_slots(dates, START[panel], SELEND[panel])
    c0 = int(np.searchsorted(dates.values, np.datetime64(CONF0[panel])))
    out = []
    for t in top:
        row = np.array(t['row'], np.int64)
        dec, act, g = EN.one_path(A, X, row, t1, I['cost'])
        sel_adv = float(g[w0:w1].sum() / ((w1 - w0) / 252.0)) if False else float(pd.Series(g[w0:w1], index=dates[w0:w1]).resample('ME').sum().mean() * 12)
        conf_adv = float(pd.Series(g[c0:t1], index=dates[c0:t1]).resample('ME').sum().mean() * 12)
        on = int(row[4])
        sig = (dec == on) | (act == 0)
        sigS = pd.Series(sig[:t1], index=dates[:t1])
        g1 = gate.test(sigS.astype(bool), trials=N_TOTAL, name=str(t['rank']), verbose=False)
        g1s = {k: (dict(hit=v['hit'], n=v['n'], always=v['always_up'], hit_defl=v['hit_deflated']) if isinstance(v, dict) else v)
               for k, v in g1.items() if k in ('ndx_86_14', 'spx_55_85', 'verdict')}
        rec = dict(rank=t['rank'], row=t['row'], raw_adv_sel_frozen=t['raw_adv_ann'], sel_adv_recomputed=sel_adv, conf_adv=conf_adv,
                   decay=conf_adv / sel_adv if sel_adv else None, conf_pass_ii=bool(conf_adv > 0 and conf_adv >= 0.5 * sel_adv),
                   active_share_conf=float(act[c0 - 3:t1 - 3].mean()), g1=g1s)
        lg1 = np.log1p(X[2, c0:t1]); yrs = (t1 - c0) / 252
        rec['conf_pretax_cagr'] = float(np.exp((g[c0:t1] + lg1).sum() / yrs) - 1); rec['conf_1x_cagr'] = float(np.exp(lg1.sum() / yrs) - 1)
        if panel == 'KR':
            E = kr_aftertax(X, dec, c0, t1); rec['conf_aftertax_cagr'] = float(E[-1] ** (1 / yrs) - 1)
            E0 = kr_aftertax(X, np.full_like(dec, 2), c0, t1); rec['conf_1x_aftertax'] = float(E0[-1] ** (1 / yrs) - 1)
            rec['g1_kr'] = dict(sel=kr_gate(sig, X, dates, '2000-01-03', SELEND['KR'], N_TOTAL), conf=kr_gate(sig, X, dates, CONF0['KR'], END, N_TOTAL),
                                full=kr_gate(sig, X, dates, '2000-01-03', END, N_TOTAL))
            # KR-stream MS1-comparable over 2000-2014 (daily stream, 250-day chunks)
            s0 = int(np.searchsorted(dates.values, np.datetime64('2000-01-03')))
            Ef = kr_aftertax(X, dec, s0, t1); rr = np.r_[Ef[0] - 1, Ef[1:] / Ef[:-1] - 1]
            B = WS.Blocks(); B.h = 1; B.years = dates[s0:t1].year.values; B.tax = False
            rec['full_kr_stream'] = WS.perf(B, rr)[:2]
            E1 = kr_aftertax(X, np.full_like(dec, 2), s0, t1); r1 = np.r_[E1[0] - 1, E1[1:] / E1[:-1] - 1]
            rec['full_kr_stream_1x'] = WS.perf(B, r1)[:2]
        out.append(rec)
        print(fam, t['rank'], 'sel adv %.4f -> conf adv %.4f | conf pretax %.4f vs 1x %.4f | G1 %s' % (sel_adv, conf_adv, rec['conf_pretax_cagr'], rec['conf_1x_cagr'], g1s['verdict']),
              (' KR-G1 sel %.3f(up %.3f) conf %.3f(up %.3f) defl full %.3f' % (rec['g1_kr']['sel']['hit'], rec['g1_kr']['sel']['always_up'], rec['g1_kr']['conf']['hit'],
                                                                         rec['g1_kr']['conf']['always_up'], rec['g1_kr']['full']['hit_deflated'])) if panel == 'KR' else '', flush=True)
    return dict(fam=fam, rows=out)


if __name__ == '__main__':
    for fam in sys.argv[1:]:
        t0 = time.time()
        res = s2_family(fam) if fam.startswith('S2') else block_family(fam)
        res['secs'] = time.time() - t0
        json.dump(res, open(os.path.join(RES, 'confirm_%s%s.json' % (fam, SUFFIX)), 'w'), indent=1, default=float)
        print('saved', fam, '%.0fs' % res['secs'], flush=True)
