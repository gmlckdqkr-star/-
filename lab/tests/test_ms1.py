"""Tests for lab/ms1.py (MS1 headline + G1 gate inside lab). Run as a script, in its own process:
    LAB_HOME=<scratch dir> python3 -B tests/test_ms1.py
(LAB_HOME defaults to a fresh temp dir here, so the shared ledger is never touched). Needs the MS1 interpreter
(env LAB_MS1_PY, or `python3 -B -m lab setup`). Prints PASS / FAIL lines and INFO lines with parity numbers; every
number is a design-side (<= 2014-12-31) MS1 / G1 number.
"""
import json, os, sys, tempfile, time
LAB = __file__.rsplit('/tests/', 1)[0]
if not os.environ.get('LAB_HOME'):
    os.environ['LAB_HOME'] = tempfile.mkdtemp(prefix='lab_ms1_')
sys.path.insert(0, LAB)
import numpy as np, pandas as pd  # noqa: E402
from lab import cli, data, dsl, ledger, ms1  # noqa: E402

FAILS = []
SP = os.path.join(LAB, 'specs')
SEAL = pd.Timestamp('2014-12-31')
# MEASURE_STD_KO.md section 4 (locked, %): hold rows per basis
LOCK = {'hold1x': (11.6, 11.6, 11.5, 9.0, 8.4), 'hold2x': (10.5, 10.5, 10.1, 9.0, 6.0),
        'hold3x': (4.2, 4.2, 3.9, 9.8, 4.4), 'ref_s085': (16.2, 27.0, 31.1, 11.9, 12.6)}
TREND = dict(name='t_trend', family='t_ms1', rules=[dict(when='price(TQQQ) > sma(TQQQ, 200)', hold={'TQQQ': 1.0}),
                                                    {'else': {'CASH': 1.0}}])
MACRO = dict(name='t_macro', family='t_ms1', signals=dict(dn='price(TQQQ) < sma(TQQQ, 200)',
                                                          warn="macro(inv) or macro('shock6m')"),
             rules=[dict(when='dn and warn', hold={'CASH': 1.0}), {'else': {'TQQQ': 1.0}}])


def check(name, ok, extra=''):
    print(f'{"PASS" if ok else "FAIL"}  {name}{("  " + extra) if extra else ""}', flush=True)
    if not ok:
        FAILS.append(name)


def info(name, extra):
    print(f'INFO  {name}  {extra}', flush=True)


def const(s):
    return dict(name=f'const_{s}', family='t_ms1_const', rules=[{'else': {s: 1.0}}])


def short(bn):
    return bn.replace('dev250_', '').replace('real_', '')


def test_guard_and_eligibility():
    print('== (1) version guard, eligibility ==')
    check('guard: std.py / gate.py are the locked versions', ms1.guard() is None, f'std {ms1.STD_SHA} gate {ms1.GATE_SHA}')
    g = ms1.guard(expect_std='000000000000')
    check("guard fires on a fake std sha -> 'MS1 기준 변경됨'", bool(g) and g.startswith('MS1 기준 변경됨'), g)
    g = ms1.guard(expect_gate='ffffffffffff')
    check("guard fires on a fake gate sha", bool(g) and g.startswith('MS1 기준 변경됨') and 'gate' in g, g)
    cases = [('trend_tqqq_200.yaml', True, None), ('qld_088_hold.yaml', True, None),
             ('plugin_reentry.yaml', True, None), ('rotate_dualmom.yaml', False, '보유 SSO,TLT'),
             ('voltarget_qld.yaml', False, '보유 SHY'), ('examples/kr_qld_trend.yaml', False, '계좌 kr_etf'),
             ('examples/bq_I_monthly_semis_vs_ndx.yaml', False, '보유 USD')]
    for f, want, frag in cases:
        ok, why = ms1.eligibility(dsl.load_spec(os.path.join(SP, f)))
        check(f'eligibility {f} -> {"eligible" if want else frag}', ok == want and (want or frag in why),
              '' if ok else why)
    xs = dict(name='x', family='t', rules=[dict(when='price(XLK) > sma(XLK, 200)', hold={'QLD': 1.0}),
                                           {'else': {'CASH': 1.0}}])
    ok, why = ms1.eligibility(xs)
    check("eligibility: reads XLK -> '읽는 계열 XLK'", not ok and why.startswith('읽는 계열 XLK'), why)
    ok, el = ms1.eligibility(MACRO)
    check('eligibility: macro(inv) / macro(shock6m) allowed, keys found', ok and el['macro'] == ['inv', 'shock6m'])
    check('eligibility: month() spec flagged as calendar', ms1.eligibility(dsl.load_spec(
        os.path.join(SP, 'examples/bq_K_seasonal_tqqq.yaml')))[1]['calendar'] is True)


def test_parity(W):
    print('== (2) parity: sleeve engine vs std.hold rows / std.measure ==')
    dev = W.call(dict(op='sleeve_parity'))['dev']
    check('pre-tax sleeve curves (QQQ r-0.2%, QLD 2r-rf-2.45%, TQQQ 3r-2rf-2.45%) proportional to std.hold curves, '
          'all 5 bases', max(dev.values()) < 1e-9, f'max rel dev {max(dev.values()):.1e}')
    res = {}
    for s in ('QQQ', 'QLD', 'TQQQ'):
        res[s] = W.call(dict(op='spec', spec=const(s), parts=['ms1']))['ms1']
    r3 = res['TQQQ']
    gap3 = max(abs(r3[bn]['cagr'] - r3[bn]['hold3x']) for bn in ms1.BASES)
    check('constant TQQQ = std 3x hold row on all 5 bases (exact)', gap3 < 5e-6, f'max gap {100 * gap3:.4f}pp; ' +
          ' '.join(f"{short(bn)} {100 * r3[bn]['cagr']:.2f}" for bn in ms1.BASES))
    for i, bn in enumerate(ms1.BASES):
        lk = [abs(100 * r3[bn][k] - LOCK[k][i]) < 0.051 for k in ('hold1x', 'hold2x', 'hold3x', 'ref_s085')]
        check(f'{bn}: std rows measured in the worker = locked MS1 table (1x 2x 3x s0.85)', all(lk),
              ' '.join(f"{k} {100 * r3[bn][k]:.2f}" for k in ('hold1x', 'hold2x', 'hold3x', 'ref_s085')))
    for s, col in (('QQQ', 'hold1x'), ('QLD', 'hold2x')):
        r = res[s]
        gaps = {bn: 100 * (r[bn]['cagr'] - r[bn][col]) for bn in ms1.BASES}
        info(f'constant {s} (MS1 engine) vs std.hold {col}', ' '.join(
            f"{short(bn)} {100 * r[bn]['cagr']:.2f}/{100 * r[bn][col]:.2f} ({gaps[bn]:+.3f}pp)" for bn in ms1.BASES))
        # known, explained gap: the engine applies std's own year-end harvest of the 2.5M deduction (beng harvest=3,
        # as for s0.85 and the 3x row); std.hold's 1x / 2x formula taxes the whole gain at the end with no deduction.
        check(f'constant {s}: gap to std.hold {col} is >= 0 (deduction harvest) and <= 0.6pp on every basis; '
              f'headline basis <= 0.15pp', all(-0.01 <= g <= 0.6 for g in gaps.values())
              and gaps['dev250_path'] <= 0.15, f"path {gaps['dev250_path']:+.3f}pp")
    specs = [('trend_tqqq_200', dsl.load_spec(os.path.join(SP, 'trend_tqqq_200.yaml')), True),
             ('t_macro (macro flags)', MACRO, True),
             ('TQQQ 0.5 (level 1.5)', dict(name='th', family='t_ms1', rules=[{'else': {'TQQQ': 0.5}}]), True),
             ('TQQQ vol-scaled (continuous weight)', dict(name='tv', family='t_ms1',
                                                         signals={'w': 'min(1, 0.25 / vol(QQQ, 20) / 3)'},
                                                         rules=[{'else': {'TQQQ': 'w'}}]), False)]
    for tag, sp, exact in specs:
        a = W.call(dict(op='spec', spec=sp, parts=['ms1']))['ms1']
        b = W.call(dict(op='std_measure_tqqq', spec=sp, fstep=0.1))['T']
        gaps = {bn: 100 * (a[bn]['cagr'] - b[bn]['cagr']) for bn in ms1.BASES}
        txt = ' '.join(f"{short(bn)} {100 * a[bn]['cagr']:.2f}/{100 * b[bn]['cagr']:.2f}" for bn in ms1.BASES)
        dd = (a['dev250_path']['dd80'], b['dev250_path']['dd80'], a['dev250_path']['pw_vs_s085'],
              b['dev250_path']['pw_vs_s085'])
        if exact:
            check(f'{tag}: sleeve engine = std.measure on the same spec (all bases, dd80, win share)',
                  max(abs(g) for g in gaps.values()) < 5e-4 and abs(dd[0] - dd[1]) < 1e-9 and abs(dd[2] - dd[3]) < 1e-9,
                  txt)
        else:
            info(f'{tag}: sleeve engine vs std.measure (order-step rule: beng rounds the level to 0.1 / 0.5 steps '
                 f'and trades only when it moves a step; lab trades every weight change at 0.3%)',
                 txt + f" trades/yr {a['dev250_path']['trades_yr']:.0f}")
            check(f'{tag}: gap is the order-step rule (sleeve engine trades far more, so lower)',
                  gaps['dev250_path'] < 0 and a['dev250_path']['trades_yr'] > 50)


def test_series(W):
    print('== (3) measure_series (IS1 method) ==')
    nd = data.series('_NDX'); nd = nd[nd.index <= SEAL]
    r = nd.pct_change().dropna() - 0.002 / 252
    t0 = time.time()
    res = W.call(dict(op='series', dates=[d.strftime('%Y-%m-%d') for d in r.index], ret=r.values.tolist(),
                      label='ndx1x', turnover=0.0))['series']
    dt = time.time() - t0
    g = {bn: 100 * (res[bn]['cagr'] - res[bn]['hold1x']) for bn in ('dev250_path', 'dev250_glued', 'real_ndx_86_14')}
    check('NDX 1x stream (lab panel _NDX - 0.2%/yr, turnover 0) = 1x hold rows within 0.1pp',
          all(abs(x) < 0.1 for x in g.values()), ' '.join(f"{short(bn)} {100 * res[bn]['cagr']:.2f} ({x:+.3f}pp)"
                                                         for bn, x in g.items()) + f' {dt:.1f}s')
    check('stream starting 1985: SPX bases -> None', res['real_spx_55_85'] is None and res['real_spx_70_85'] is None,
          f"cover {res['cover']['real_spx_55_85']:.3f}")
    check("label 'MS1 (수익 흐름 재표본, 경로 재계산 없음)'", res['label'].startswith(ms1.SERIES_LABEL))
    check('HEADLINE / FLOOR from dev250_path / real_ndx', abs(res['HEADLINE_MS1'] - res['dev250_path']['cagr']) < 1e-12
          and abs(res['FLOOR_MS1'] - min(res['dev250_path']['cagr'], res['real_ndx_86_14']['cagr'])) < 1e-12)
    # seal: a stream running past 2014 gives the same numbers as the stream cut at 2014-12-31 (rows dropped)
    ext = pd.concat([r, pd.Series(0.10, index=pd.bdate_range('2015-01-02', '2016-06-30'))])
    res2 = W.call(dict(op='series', dates=[d.strftime('%Y-%m-%d') for d in ext.index], ret=ext.values.tolist(),
                       label='ext', turnover=0.0))['series']
    same = all(res2[bn] == res[bn] for bn in ms1.BASES)
    check('seal: rows after 2014-12-31 are dropped (same numbers as the cut stream)',
          same and res2['cut_after_seal'] == len(ext) - len(r), f"dropped {res2['cut_after_seal']}")
    res3 = W.call(dict(op='series', dates=[d.strftime('%Y-%m-%d') for d in r.index], ret=r.values.tolist(),
                       label='ndx1x', turnover=1.0))['series']
    check('turnover 1 (every year\'s gain realized) is below buy-and-hold', res3['dev250_path']['cagr'] <
          res['dev250_path']['cagr'], f"path {100 * res3['dev250_path']['cagr']:.2f}")
    sh = W.call(dict(op='hold_stream', cal='spx'))
    res4 = W.call(dict(op='series', dates=sh['dates'], ret=sh['ret'], label='spx1x', turnover=0.0))['series']
    check('SPX 1x stream 1928-1985: SPX55-85 = 1x hold row within 0.1pp, NDX bases None',
          abs(res4['real_spx_55_85']['cagr'] - res4['real_spx_55_85']['hold1x']) < 1e-3 and res4['dev250_path'] is None,
          f"{100 * res4['real_spx_55_85']['cagr']:.2f}/{100 * res4['real_spx_55_85']['hold1x']:.2f}")


def test_macro(W):
    print('== (4) macro() on the dev summary vs ov.flags_hist ==')
    fh = W.call(dict(op='flags_hist'))
    F, R, rf, SRC = data.build(['QQQ'])
    F = F[F.index <= SEAL]
    fn = dsl._mk(F, R)
    bad, n = {}, 0
    for cal, sel in (('ndx', lambda d: d >= data.MACRO_SPLICE), ('spx', lambda d: d < data.MACRO_SPLICE)):
        d = pd.DatetimeIndex(fh[cal]['dates'])
        for k in data.MACRO_KEYS:
            ref = pd.Series(np.asarray(fh[cal]['flags'][k], bool), index=d)
            m = fn['macro'](k)
            common = m.index.intersection(ref.index[sel(ref.index)])
            n += len(common)
            x = int((m.loc[common].values != ref.loc[common].values).sum())
            if x:
                bad[f'{cal}:{k}'] = x
    check('macro(k) on lab\'s calendar == ov.flags_hist on shared dates (8 keys; spx cal < 1986-01-02, ndx after)',
          not bad and n > 0, f'{n} key-days compared, mismatches {bad or 0}')
    T = data.macro_table()
    check('macro table <= 2014-12-31 (committed file)', T.index.max() <= SEAL, str(T.index.max().date()))
    spec = dict(MACRO)
    W1 = dsl.compile_weights(spec, F, ['TQQQ'], R)
    tc = dsl.truncation_check(spec, F, ['TQQQ'], R)
    check('macro spec: dev weights causal (truncation test)', tc['ok'], f"{tc['cuts']} cuts")
    check('macro spec: the flags change the weights on the dev frame', (W1['TQQQ'] == 0).any() and (W1['TQQQ'] == 1).any())


def test_g1(W):
    print('== (5) G1 ==')
    sc = W.call(dict(op='gate_selfcheck'))
    check('gate self-check: always in = 55.46 / 55.68, CLOSE', abs(sc['always']['ndx_86_14'] - .5546) < 5e-5
          and abs(sc['always']['spx_55_85'] - .5568) < 5e-5 and sc['always_verdict'] == 'CLOSE',
          f"{100 * sc['always']['ndx_86_14']:.2f}/{100 * sc['always']['spx_55_85']:.2f}")
    check('gate self-check: look-ahead oracle -> hit 1.0', sc['oracle_ndx'] == 1.0, f"{sc['oracle_ndx']}")
    g = W.call(dict(op='spec', spec=dsl.load_spec(os.path.join(SP, 'trend_tqqq_200.yaml')), parts=['g1']))['g1']
    ev = ms1.g1_eval(g, 1)
    check('SMA200 via the spec (trend_tqqq_200): 52.87 / 52.97, always-in 55.46 / 55.68, CLOSE',
          abs(g['ndx_86_14']['hit'] - .5287) < 5e-5 and abs(g['spx_55_85']['hit'] - .5297) < 5e-5
          and abs(g['ndx_86_14']['always_up'] - .5546) < 5e-5 and g['binary'] and ev['verdict'] == 'CLOSE'
          and g['ndx_86_14']['n'] == 348, ms1.fmt_g1(g, ev, 1))
    ev3 = ms1.g1_eval(g, 20)
    check('deflation uses the family N (N=20 lower than N=1, = gate.py formula)', ev3['low'] < ev['low'] and abs(
        ev['deflated']['ndx_86_14'] - (g['ndx_86_14']['hit'] - 2 * g['ndx_86_14']['se'])) < 1e-12)
    h = W.call(dict(op='spec', spec=dsl.load_spec(os.path.join(SP, 'qld_088_hold.yaml')), parts=['g1']))['g1']
    txt = ms1.fmt_g1(h, ms1.g1_eval(h, 1), 1)
    check("always-in spec -> 'G1 해당 없음 (상시 보유)' + classic Sharpe vs 1.1", not h['binary'] and
          txt.startswith('G1 해당 없음 (상시 보유)') and set(h['sharpe']) == {'real_ndx_86_14', 'real_spx_55_85'}, txt)


def test_cli(W):
    print('== (6) CLI: one line, cache, guard, seal ==')
    ses = ms1.Session(('ms1', 'g1')); ses.w = W; ses.tried = True
    spec = dict(TREND, name='t_cli_trend')
    t0 = time.time(); line1, rec1 = cli.run_spec(dict(spec), 'none', ses=ses); t1 = time.time() - t0

    class NoWorker(ms1.Session):
        def worker(self):
            raise AssertionError('worker asked for on a cached spec')
    t0 = time.time(); line2, rec2 = cli.run_spec(dict(spec), 'none', ses=NoWorker(('ms1', 'g1'))); t2 = time.time() - t0
    print('   ' + line1)
    check('line has the MS1 headline and the G1 part', 'MS1 경로 ' in line1 and '(하한 ' in line1 and 's0.85대비' in line1
          and '§5엔진' in line1 and '| G1 NDX' in line1)
    check('line <= 400 bytes', len(line1.encode()) <= 400, f'{len(line1.encode())} bytes')
    check('rerun: MS1 / G1 from the ledger (no worker), same numbers', rec2['ms1'] == rec1['ms1'] and
          rec2['g1'] == rec1['g1'] and line2.split(' | ')[2:4] == line1.split(' | ')[2:4], f'{t1:.1f}s -> {t2:.1f}s')
    h = dsl.spec_hash(dsl.check_spec(dict(spec)))
    check('ledger std row keyed by spec hash + std / gate sha + engine version',
          ledger.get_std(h, ms1.cache_key()) is not None and ms1.STD_SHA in ms1.cache_key())
    old = ms1.STD_SHA
    try:
        ms1.STD_SHA = 'deadbeef0000'
        line3, rec3 = cli.run_spec(dict(spec), 'none', ses=NoWorker(('ms1', 'g1')))
    finally:
        ms1.STD_SHA = old
    check("guard in the CLI: fake std sha -> 'MS1 기준 변경됨', no number", 'MS1 기준 변경됨' in line3 and
          rec3['ms1'] is None and 'MS1 경로' not in line3)
    line4, rec4 = cli.run_spec(dsl.load_spec(os.path.join(SP, 'rotate_dualmom.yaml')), 'none', ses=NoWorker(('ms1', 'g1')))
    check("ineligible spec -> 'MS1: 해당 없음 (...)'", 'MS1: 해당 없음 (보유 SSO,TLT' in line4, line4.split(' | ')[-2])
    # crowded line: a quick-bar part + MS1 + G1 still fits (compact forms)
    s = ledger.get(dsl.spec_hash(dsl.check_spec(dict(spec))))
    r = dict(verdict='x', failed=['Q1', 'Q3', 'R2', 'W5'], numbers=dict(lg_med=0.1234, qqqm_lg_med=0.1111, qld_lg_med=0.1222,
                                                                   lg_p10=0.0123, mdd95=-0.65, p80=0.123, mult_t1764=2.3,
                                                                   n_paths=400))
    m = ms1.report(dict(spec), h, 't_ms1', NoWorker(('ms1', 'g1')))
    ln = cli._line('[grid_trend_qld_long_name[N=250,X=0.35]] 계열=price_trend_family N=12 (중복)',
                   (cli._dev_part(s), cli._dev_part(s, True), cli._dev_part(s, 2)),
                   (cli._bar_part('quick@3', r), cli._bar_part('quick@3', r, True)), (m['text'], m['short']), '123s')
    check('crowded line (long name + quick bar + MS1 + G1) <= 400 bytes and keeps the MS1 headline and G1 verdict',
          len(ln.encode()) <= 400 and 'MS1 경로' in ln and 'CLOSE' in ln, f'{len(ln.encode())} bytes')
    sl = W.call(dict(op='seal'))
    dates = list(sl['bases'].values()) + list(sl['g1'].values()) + list(sl['labels'].values())
    check('seal: every MS1 basis source date, G1 frame and gate label <= 2014-12-31', max(dates) <= '2014-12-31',
          f'max {max(dates)}')


STK_GATE = dict(name='t_stk_gate', family='t_ms1_stk', universe='sp500',
                signals={'up': 'price(_NDX) > sma(_NDX, 200)'},
                stock={'rebalance': 'quarter', 'score': 'ret(126)', 'top': 20, 'exposure': 'up'})
STK_PLAIN = dict(name='t_stk_plain', family='t_ms1_stk', universe='sp500',
                 stock={'rebalance': 'quarter', 'score': '-vol(63)', 'top': 30})


def test_stocks(W):
    print('== (8) single-stock specs: MS1 return stream + G1 (Sharpe branch, exposure gate) ==')
    from lab import stocks
    P = stocks.load()
    st = stocks.ms1_stream(dict(STK_PLAIN), P)
    d = pd.DatetimeIndex(st['dates'])
    check('stream: real stock dates, starts 1970 (first PIT member day), ends <= 2014-12-31, turnover share in [0, 1]',
          st['start'] == '1970-01-02' and d.max() <= SEAL and d.is_monotonic_increasing and 0 <= st['turnover'] <= 1,
          f"{st['start']}..{d.max().date()} n={len(d)} share {st['turnover']:.2f}")
    sp = dsl.check_spec(dict(STK_PLAIN))
    tg = stocks.compile_targets(sp, P)
    o = stocks.fast_run(P, tg, stocks.H_CONS, pd.Timestamp(st['start']), 0.003, 0.0, 2, want_E=True)
    gr = float(np.prod(1 + np.asarray(st['ret'])))
    check('stream = the CONSERVATIVE (h=0.30) book after cost, before tax (compounds to its pre-tax equity)',
          abs(gr - o['E'][0][-1] / o['E'][0][0]) < 1e-9 and abs(o['cagr_pre'][0] - stocks.run1(
              P, tg, stocks.H_CONS, pd.Timestamp(st['start']), 0.003, 0.0, 2)['cagr_pre']) < 1e-12, f'x{gr:.2f}')
    sg = stocks.ms1_stream(dict(STK_GATE), P)
    check('gated spec: stream starts when the gate data starts (lab _NDX, 1985)', sg['start'] >= '1985', sg['start'])
    gs = stocks.gate_spec(dict(STK_GATE))
    check('gate_spec: QQQ weighted by the exposure, else cash, same family', gs['rules'] == [{'else': {'QQQ': 'up'}}]
          and gs['family'] == 't_ms1_stk' and stocks.gate_spec(dict(STK_PLAIN)) is None)
    g = W.call(dict(op='stock', parts=['g1'], gate=gs))['g1']
    check('G1 on the gate _NDX > SMA200 = the SMA200 signal (52.87 / 52.97, CLOSE)', g['binary'] and abs(
        g['ndx_86_14']['hit'] - .5287) < 5e-5 and abs(g['spx_55_85']['hit'] - .5297) < 5e-5 and 'sharpe' not in g,
          ms1.fmt_gate(g, 1)[0])
    ok, why = ms1._stock_gate(dict(STK_GATE, signals={'up': 'price(SPY) > sma(SPY, 200)'}))
    check("gate reading SPY -> not on the G1 frames ('읽는 계열 SPY')", not ok and why.startswith('읽는 계열 SPY'), why)
    mg = dict(STK_GATE, name='t_stk_macro', signals={'up': 'not macro(inv)'})
    check('stock gate may read macro(k) (dev: historical flags on the stock calendar)',
          dsl.check_spec(dict(mg)) is not None and 0 < stocks.exposure(dsl.check_spec(dict(mg)), P).mean() < 1)
    ses = ms1.Session(('ms1', 'g1')); ses.w = W; ses.tried = True
    lines = {}
    for spec in (STK_PLAIN, STK_GATE):
        t0 = time.time()
        line, rec = cli.run_spec(dict(spec), 'quick', ses=ses)
        lines[spec['name']] = (line, rec, time.time() - t0)
        print('   ' + line)
    lp, rp, tp = lines['t_stk_plain']
    lg, rg, tg_ = lines['t_stk_gate']
    check("stock line: 'MS1(수익 흐름 재표본) 경로 x% (s0.85 16.2·1x 11.6)' (or its short form), Sharpe G1 kept, "
          "bar 판정 불가, <= 400 bytes", all(('MS1(수익 흐름 재표본) 경로 ' in x or 'MS1흐름 경로 ' in x) and
                                          '(s0.85 16.2·1x 11.6)' in x and 'G1 1.1' in x and '판정 불가 (개별주)' in x
                                          and len(x.encode()) <= 400 for x in (lp, lg)),
          f'{len(lp.encode())} / {len(lg.encode())} bytes, {tp:.0f}s / {tg_:.0f}s')
    check('stock line: G1 gate part only with an exposure gate', 'G1게이트' in lg or 'G1 게이트' in lg)
    check('stock line: no G1 gate part without a gate', 'G1게이트' not in lp and 'G1 게이트' not in lp)
    h = dsl.spec_hash(dsl.check_spec(dict(STK_PLAIN)))
    row = ledger.get_std(h, ms1.stock_key())
    ref = W.call(dict(op='series', dates=st['dates'], ret=st['ret'], label='x', turnover=st['turnover']))['series']
    check('stock MS1 = measure_series of the stream (ledger row, headline, SPX70-85 covered, SPX55-85 None)',
          row is not None and abs(rp['ms1'] - ref['HEADLINE_MS1']) < 1e-12 and row['ms1']['real_spx_70_85'] is not None
          and row['ms1']['real_spx_55_85'] is None,
          ' '.join(f"{short(bn)} {'-' if row['ms1'][bn] is None else round(100 * row['ms1'][bn]['cagr'], 2)}"
                   for bn in ms1.BASES))

    class NoWorker(ms1.Session):
        def worker(self):
            raise AssertionError('worker asked for on a cached spec')
    check('needs_compute: stock spec cached -> False, uncached -> True',
          not ms1.needs_compute(dsl.check_spec(dict(STK_PLAIN)), h, ('ms1', 'g1'))
          and ms1.needs_compute(dsl.check_spec(dict(STK_PLAIN, name='t_new', stock=dict(STK_PLAIN['stock'], top=31))),
                                'nohash', ('ms1', 'g1')))
    line2, rec2 = cli.run_spec(dict(STK_PLAIN), 'quick', ses=NoWorker(('ms1', 'g1')))
    check('stock rerun: MS1 from the ledger (no worker), same headline', rec2['ms1'] == rp['ms1'] and '(중복)' in line2)
    t = cli.summary([rp, rg, dict(rec2, name='x')], 'quick')
    check('summary: the stock block shows the MS1 headline', '-- 개별주' in t and f"MS1 {rp['ms1']:.1%}" in t, t.split(
        '\n')[-1])
    recs = [dict(name=f'e{i}', hash=f'{i:012d}', family='f', dev_y12=float(9 - i), dev_screen=False, ms1=m, g1=None)
            for i, m in enumerate([None, 0.05, 0.11, None, 0.08])] + [rp]
    t = cli.summary(recs, 'none')
    body = [x.split()[1] for x in t.splitlines()[2:7]]
    check('summary without a bar: ranked by the MS1 headline, specs without one after (by dev 12y)',
          body == ['e2', 'e4', 'e1', 'e0', 'e3'] and 'MS1 경로' in t.splitlines()[0], ' '.join(body))


def test_bar():
    print('== (7) bar refuses macro() ==')
    from lab import bb
    r = bb.judge(dict(MACRO), 'quick')
    check("bar: macro() spec -> 'REJECT (version impossible)' (NotJudgeable)", r['verdict'] == 'REJECT (version impossible)'
          and 'macro:inv' in r.get('reason', ''), r.get('reason', ''))


def main():
    t0 = time.time()
    test_guard_and_eligibility()
    py = ms1.interpreter()
    check('MS1 interpreter available (LAB_MS1_PY or lab setup)', py is not None, str(py))
    if py:
        W = ms1.Worker(py)
        try:
            rd = W.wait_ready()
            check('worker ready (std contexts, s0.85 reference)', rd.get('ok'), f"{rd.get('secs')}s")
            test_parity(W)
            test_series(W)
            test_macro(W)
            test_g1(W)
            test_cli(W)
            test_stocks(W)
        finally:
            W.close()
    test_bar()
    print(f'FAILS: {FAILS or "none"}  ({time.time() - t0:.0f}s)')
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
