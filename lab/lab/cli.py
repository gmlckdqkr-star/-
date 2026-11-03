"""python -m lab run <spec or dir ...> [--bar none|quick|full] [--std auto|none|ms1,g1] [--workers N]
       run specs (a directory = every *.yaml / *.yml / *.json in it, sorted), print ONE line each (<= ~400 bytes; the
       only thing an LLM needs to read). A spec with `grid:` runs once per grid point (each its own hash, each counted
       in the family N). With more than one spec, a ranked summary table (<= ~1.5 KB) follows.
       --bar quick (default): '빠른 선별 (기준 아님)' = 10y b63 10M, 400 paths, own window, KRWX, src_end 2014.
       --bar full: the project bar on blackbox2 / d6q (all required versions, ~4 min per version with 4 workers):
                   REJECT | 'REJECT (lab 판정, 미확정)' | 'Q60 미달 (Q 미판정)' (failed gates) or 'PENDING (통합 담당 대기)'.
                   Lab never prints APPLY-Q / APPLY-Q60.
       --bar none: dev summary only.
       A single-stock spec (`universe: sp500`, lab/stocks.py) prints its own dev line (S&P 500 point-in-time members,
       delisted included, stress rows, random-basket null, G1 Sharpe) + 'MS1(수익 흐름 재표본)' (its return stream on
       the MS1 bases) + G1 on its exposure gate if it has one; every bar mode answers '판정 불가 (개별주)'.
       --all-versions (full only): keep running the remaining versions after a REJECT (default: stop, REJECT is final).
       --std auto (default): MS1 headline + G1 gate for MS1-eligible specs (lab/ms1.py, one out-of-process worker per
                   batch; account us, sleeves QQQ / QLD / TQQQ / CASH, reads the NDX level and macro(k) only),
                   'MS1: 해당 없음 (reason)' for the others. --std none: skip. --std ms1 | g1 | ms1,g1: those parts.
   python -m lab setup
       create the MS1 interpreter (LAB_CACHE/ms1-venv, default ~/.cache/lab/ms1-venv: pip install numba scipy xlrd
       numpy pandas pyyaml). `lab run` does this once by itself when it is missing. LAB_MS1_PY overrides.
   python -m lab ledger
       family counts and stored bar results.
Full detail goes to LAB_HOME/out/<hash>_<mode>.json, the batch to LAB_HOME/out/batch_<utc>.json (not meant for
LLM context).
Every number comes from data up to 2014-12-31 (design side); nothing after 2014 is computed."""
import glob, json, os, sys, time
import pandas as pd
from . import data, dsl, gates, ledger, ms1

MAX_LINE = 400
MAX_SUMMARY = 1500


def _cut(s, n=MAX_LINE):
    b = s.encode('utf-8')
    if len(b) <= n:
        return s
    return b[:n - 3].decode('utf-8', 'ignore') + '...'


def _dev_part(s, short=False):
    d, b = s['dev'], s['boot']
    acct = '' if s.get('account', 'us') == 'us' else f"[{s['account']} 13bp·건별15.4%(KR200·KRSEMI 0)] "
    if short:                     # same numbers, fewer words (a line with bar + MS1 + G1 parts); 2 = no baseline
        base = '' if short == 2 else f"({s['baseline']} {d['base_cagr_at']:.1%}/{d['base_mdd']:.0%})"
        return (acct + f"개발{s['dev_start'][2:4]}~14 {d['cagr_at']:.1%}/{d['mdd']:.0%}{base} 12y "
                f"x{b['s_med_y12']:.1f}/x{b['b_med_y12']:.1f} P80 {b['s_p_dd80']:.1%} "
                f"선별{'통과' if s['screen_pass'] else '탈락'}"
                + ('' if (s.get('dev_causality') or {}).get('ok', True) else ' 인과성위반'))
    return (acct + f"개발({s['dev_start'][:4]}~2014) 세후 {d['cagr_at']:.1%} 낙폭 {d['mdd']:.0%} "
            f"({s['baseline']} {d['base_cagr_at']:.1%}/{d['base_mdd']:.0%}) 12년x{b['s_med_y12']:.1f}"
            f"({s['baseline']} x{b['b_med_y12']:.1f}) P80 {b['s_p_dd80']:.1%} "
            f"개발선별 {'통과' if s['screen_pass'] else '탈락'}"
            + ('' if (s.get('dev_causality') or {}).get('ok', True) else ' 개발 인과성 위반'))


def _bar_part(mode, r, short=False):
    if r is None:
        return ''
    if r['verdict'].startswith('REJECT (version') or r['verdict'].startswith('판정 불가'):
        return f"기준: {r['verdict']}"
    n = r.get('numbers') or {}
    if mode.startswith('quick'):
        f = ','.join(r['failed']) or '없음'
        if short:
            return (f"빠른선별(기준아님) lg {n['lg_med']:.3f}/QQQM {n['qqqm_lg_med']:.3f}/QLD {n['qld_lg_med']:.3f}"
                    f" p10 {n['lg_p10']:.3f} mdd95 {n['mdd95']:.0%} P80 {n['p80']:.1%} 미달 {f}")
        return (f"빠른 선별 (기준 아님) b63·1000만·{n.get('n_paths', '?')}경로: lg {n['lg_med']:.3f}"
                f"/QQQM {n['qqqm_lg_med']:.3f}/QLD {n['qld_lg_med']:.3f} p10 {n['lg_p10']:.3f} "
                f"mdd95 {n['mdd95']:.0%} P80 {n['p80']:.1%} 7년x{n.get('mult_t1764', float('nan')):.1f} 미달 {f}")
    f = _short_failed(r['failed'])
    return f"기준(≤2014 설계측): {r['verdict']}" + (f' 실패 {f}' if f else '')


def _short(g):
    lab = g.endswith('(lab port)'); g = g.replace('(lab port)', '')
    if g.startswith('G60W_'):
        g = g.split('_')[1]                       # W5 / W10
    elif g.startswith('GMKT_'):
        g = '_'.join(g.split('_')[:2])            # GMKT_a / _b / _c
    elif g == 'blackbox_D2':
        g = 'D2'
    elif g[:1] in 'QR' and g[1:2].isdigit():
        g = g.split('_')[0]                       # Q1 .. Q5, R1 .. R3
    return g + ('*' if lab else '')


def _short_failed(failed):
    """'real:G4_dev(lab port)', 'own_KRWX:Q1_...' -> 'real[GMKT_c,G4_dev*] own_KRWX[Q1,...]' (* = lab port; full
    names are in the ledger and the JSON)."""
    groups = {}
    for x in failed:
        v, g = x.split(':', 1) if ':' in x else ('', x)
        groups.setdefault(v, []).append(_short(g))
    return ' '.join(f"{v}[{','.join(gs)}]" if v else ','.join(gs) for v, gs in groups.items())


def _bar(spec, h, mode, workers, early_stop=True):
    from . import bb
    key = f"{mode}{'-all' if mode == 'full' and not early_stop else ''}@{bb.BAR_VERSION}"
    hit = ledger.get_bar(h, key)
    if hit:
        return key, hit, None, True
    if mode == 'quick':
        res = bb.judge(spec, 'quick')
        verdict = res.get('verdict') or f"{bb.QUICK_LABEL} {res['screen']}"
        nums = dict(res.get('numbers') or {}, n_paths=res.get('n_paths'))
    else:
        res = bb.judge(spec, 'full', workers=workers, early_stop=early_stop)
        verdict = res['verdict']
        nums = {v: x.get('numbers', {}).get('10y_b63_1000만원') for v, x in res.get('versions', {}).items()}
        nums['real_path'] = (res.get('real_path') or {}).get('g4')
    ledger.put_bar(h, key, verdict, res['failed'], nums)
    return key, dict(verdict=verdict, failed=res['failed'], numbers=nums), res, False


def run_one(path, bar='quick', workers=4, early_stop=True):
    """One spec file (no grid) -> one line. Kept for callers of v1."""
    spec = dsl.load_spec(path)
    return run_spec(spec, bar, workers, early_stop)[0]


def _line(head, devs, bars, stds, tail):
    """Join the parts, switching to the compact forms (dev, then bar, then MS1 / G1) while the line is > MAX_LINE.
    stds = (full, short[, shortest]) (the shortest form exists for stock specs)."""
    stds = tuple(stds) + tuple(stds[-1:]) * (3 - len(stds))
    for i, j, k in ((0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 1), (2, 1, 1), (2, 1, 2)):
        s = ' | '.join(x for x in (head, devs[i], bars[j], stds[k], tail) if x)
        if len(s.encode('utf-8')) <= MAX_LINE:
            return s
    return _cut(s)


def run_spec(spec, bar='quick', workers=4, early_stop=True, ses=None):
    """One expanded spec -> (line, record for the batch summary). ses: an ms1.Session (MS1 / G1 parts) or None."""
    t0 = time.time()
    spec = dsl.check_spec(spec)                          # refuse delay < 2 / non-numeric cost before anything runs
    h = dsl.spec_hash(spec); fam = str(spec.get('family', 'unset'))
    name = str(spec.get('name', h))
    stock = dsl.is_universe(spec)                        # single-stock spec (lab/stocks.py): own dev summary
    if stock:
        from . import stocks
    s = ledger.get(h)
    cached = s is not None
    stale = cached and (s.get('stock_version') != stocks.STOCK_VERSION if stock
                        else s.get('dev_version') != gates.DEV_VERSION)
    if stale:                                            # dev summary logic changed: recompute, same row (N same)
        s, cached = None, False
        known = True
    else:
        known = cached
    if not cached and stock:
        s = stocks.evaluate(spec)
        ledger.put(h, spec, s)
    elif not cached:
        sleeves = sorted(set(dsl.held_sleeves(spec)) | {spec.get('baseline', 'QQQ')})
        F, R, rf, SRC = data.build(sleeves)
        F = F[F.index <= gates.DEV_END]; R = R[R.index <= gates.DEV_END]      # nothing after 2014 enters
        W = dsl.compile_weights(spec, F, sleeves, R)
        s = gates.evaluate(W, R, spec, baseline=spec.get('baseline', 'QQQ'))
        # dev-side causality (truncation at random cuts, the same test the bar runs on its paths)
        tc = dsl.truncation_check(spec, F, sleeves, R)
        s['dev_causality'] = dict(tc, violations=tc['violations'][:3])
        if not tc['ok']:
            s['screen_pass'] = False
        ledger.put(h, spec, s)
    detail = dict(spec=spec, hash=h, dev_summary=s)
    head = f"[{name}] 계열={fam} N={ledger.family_n(fam)}{' (중복)' if known else ''}"
    if stock:
        devs = (stocks.dev_part(s), stocks.dev_part(s, compact=True), stocks.dev_part(s, compact=2))
    else:
        devs = (_dev_part(s), _dev_part(s, short=True), _dev_part(s, short=2))
    bars, stds = ('', ''), ('', '')
    bcached = False
    rec = dict(name=name, hash=h, family=fam, dev_y12=None if stock else s['boot']['s_med_y12'],
               dev_screen=s['screen_pass'])
    if stock:
        rec['stock_cagr'] = s['windows']['w86']['cons']['cagr_at']
    st = None
    if ses is not None:               # the MS1 worker computes while the bar runs
        st = (ms1.begin_stock(spec, h, fam, ses, lambda: stocks.ms1_stream(spec)) if stock
              else ms1.begin(spec, h, fam, ses))
    if bar != 'none':
        try:
            key, r, res, bcached = _bar(spec, h, bar, workers, early_stop)
        except BaseException:
            ms1.abandon(st)
            raise
        detail['bar'] = res if res is not None else dict(r, cached=True)
        tag = ' (저장값)' if bcached else ''
        bars = (_bar_part(key, r) + tag, _bar_part(key, r, short=True) + tag)
        nums = r.get('numbers') or {}
        if bar == 'full' and isinstance(nums.get('own_KRWX'), dict):
            nums = nums['own_KRWX']
        rec.update(verdict=r['verdict'], failed=r['failed'], lg=nums.get('lg_med'), qld=nums.get('qld_lg_med'),
                   qqqm=nums.get('qqqm_lg_med'), mode=key)
    scached = True
    if st is not None:
        m = ms1.finish(st)
        scached = m['cached']
        stds = (m['text'], m.get('short') or m['text'], m.get('shortest') or m.get('short') or m['text'])
        rec.update(ms1=m['ms1'], g1=m['g1'])
        if m['detail'] is not None:
            detail['std'] = dict(m['detail'], key=m.get('key') or ms1.cache_key(), label=m.get('label') or ms1.LABEL,
                                 cached=m['cached'])
    if not (cached and (bar == 'none' or bcached) and scached):   # keep the full detail of the first computation
        os.makedirs(os.path.join(ledger.HOME, 'out'), exist_ok=True)
        with open(os.path.join(ledger.HOME, 'out', f'{h}_{bar}.json'), 'w') as fh:
            json.dump(detail, fh, ensure_ascii=False, indent=1, default=str)
    return _line(head, devs, bars, stds, f'{time.time() - t0:.0f}s'), rec


def collect(args):
    """Files and directories -> spec file list (a directory gives its *.yaml / *.yml / *.json, sorted, not
    recursive)."""
    out = []
    for a in args:
        if os.path.isdir(a):
            out += sorted(f for e in ('*.yaml', '*.yml', '*.json') for f in glob.glob(os.path.join(a, e)))
        else:
            out.append(a)
    return out


def _verdict_short(rec):
    v = rec.get('verdict')
    if v is None:
        return '개발선별 ' + ('통과' if rec.get('dev_screen') else '탈락')
    if v.startswith('REJECT (version'):
        return '판 불가'
    if v.startswith('판정 불가'):
        return v
    if str(rec.get('mode', '')).startswith('quick'):
        f = [g for g in rec.get('failed') or []]
        return '통과' if not f else '미달 ' + ','.join(f)
    f = _short_failed(rec.get('failed') or [])
    return v + (f' {f}' if f else '')


def _ms_col(r, std):
    """' 5.7%·CLOSE' (MS1 headline · G1 verdict), ' -' without a headline, '' when no spec of the batch has MS1."""
    if not std:
        return ''
    return (' -' if r.get('ms1') is None else f" {r['ms1']:.1%}") + (f"·{r['g1']}" if r.get('g1') else '')


def summary(recs, bar):
    """Compact ranked table (<= MAX_SUMMARY bytes): top 10 by the quick screen's median log growth (10y b63 10M,
    full: own_KRWX); when no bar ran, by the MS1 headline (specs without one after, by the dev 12y bootstrap
    multiple). Single-stock specs get their own block (conservative headline order). Errors are counted, not listed."""
    ok = [r for r in recs if 'error' not in r]
    stk = sorted((r for r in ok if r.get('stock_cagr') is not None), key=lambda r: r['stock_cagr'], reverse=True)
    ok = [r for r in ok if r.get('stock_cagr') is None]
    by_lg = any(r.get('lg') is not None for r in ok)
    by_ms1 = not by_lg and any(r.get('ms1') is not None for r in ok)    # no bar ran: the MS1 headline ranks first
    if by_lg:
        key = lambda r: (r.get('lg') is not None, r.get('lg') or 0.0)
    elif by_ms1:
        key = lambda r: (r.get('ms1') is not None, r.get('ms1') or 0.0, r.get('dev_y12') or 0.0)
    else:
        key = lambda r: r.get('dev_y12') or 0.0
    rows = sorted(ok, key=key, reverse=True)[:10]
    what = ('lg 중앙값(10y b63 1000만' + (', own_KRWX' if bar == 'full' else '') + ')') if by_lg else \
        'MS1 경로(없으면 개발 12년 배수)' if by_ms1 else '개발 12년 배수'
    nerr = len(recs) - len(ok) - len(stk)
    std = any('ms1' in r for r in ok + stk)
    if ok or not stk:
        lines = [f"== 요약: {what} 순 상위 {len(rows)}/{len(recs) - len(stk)}"
                 + (f", 오류 {nerr}" if nerr else '')
                 + (' — 빠른 선별 (기준 아님)' if bar == 'quick' and ok else '') + ' ==']
    else:
        lines = ['== 요약' + (f': 오류 {nerr}' if nerr else '') + ' ==']
    if rows:
        lines.append(' # 이름 hash  lg/QLD/QQQM  개발12y' + ('  MS1경로·G1' if std else '') + '  판정')
    for i, r in enumerate(rows, 1):
        lg = '-' if r.get('lg') is None else f"{r['lg']:.3f}/{r.get('qld') or 0:.3f}/{r.get('qqqm') or 0:.3f}"
        nm = _cut(str(r['name']), 34)
        lines.append(_cut(f"{i:>2} {nm} {r['hash'][:6]} {lg} x{r.get('dev_y12') or 0:.1f}{_ms_col(r, std)} "
                          f"{_verdict_short(r)}", 140))
    if stk:                  # single-stock specs (universe: sp500): own block, ranked by the conservative headline
        lines.append(f"-- 개별주 {min(len(stk), 5)}/{len(stk)}: 1986~2014 세후 보수 순"
                     + (' · MS1 = 수익 흐름 재표본 경로' if std else '') + ' (기준 판정 불가, 개발 요약만)')
        for i, r in enumerate(stk[:5], 1):
            nm = _cut(str(r['name']), 34)
            lines.append(_cut(f"{i:>2} {nm} {r['hash'][:6]} 세후보수 {r['stock_cagr']:.1%}"
                              + (f" MS1{_ms_col(r, True)}" if std else '')
                              + f" Sharpe G1 {'통과' if r.get('dev_screen') else '미달'}", 140))
    return _cut('\n'.join(lines), MAX_SUMMARY)


def _std_parts(std):
    if std in ('auto', 'ms1,g1', 'g1,ms1'):
        return ('ms1', 'g1')
    if std == 'none':
        return ()
    if std in ('ms1', 'g1'):
        return (std,)
    return None


def _needs_std(sp, parts):
    try:
        sp = dsl.check_spec(dict(sp))
        return ms1.needs_compute(sp, dsl.spec_hash(sp), parts)
    except Exception:
        return False


def main(argv=None):
    a = list(argv if argv is not None else sys.argv[1:])
    if not a or a[0] not in ('run', 'ledger', 'setup'):
        print(__doc__); return 2
    if a[0] == 'setup':
        return 0 if ms1.setup(verbose=True) else 1
    if a[0] == 'ledger':
        fam, bar = ledger.rows()
        for f, n in fam:
            print(f'{f}: N={n}')
        for f, mode, v, n in bar:
            print(f'  {f} {mode}: {v} x{n}')
        for k, n in ledger.std_rows():
            print(f'  MS1·G1 {k}: x{n}')
        return 0
    bar, workers, specs, early_stop, std = 'quick', 4, [], True, 'auto'
    it = iter(a[1:])
    for x in it:
        if x == '--bar':
            bar = next(it)
        elif x.startswith('--bar='):
            bar = x.split('=', 1)[1]
        elif x == '--all-versions':
            early_stop = False
        elif x == '--workers':
            workers = int(next(it))
        elif x == '--std':
            std = next(it)
        elif x.startswith('--std='):
            std = x.split('=', 1)[1]
        else:
            specs.append(x)
    if bar not in ('none', 'quick', 'full'):
        print(f'--bar must be none|quick|full, not {bar!r}'); return 2
    parts = _std_parts(std)
    if parts is None:
        print(f'--std must be auto|none|ms1|g1|ms1,g1, not {std!r}'); return 2
    rc, recs, files = 0, [], collect(specs)
    loaded = []
    for p in files:                       # load + expand first: start the MS1 worker early only if it has work
        try:
            loaded.append((p, dsl.expand_grid(dsl.load_spec(p)), None))
        except Exception as e:  # one bad spec must not stop the batch
            loaded.append((p, None, e))
    ses = ms1.Session(parts) if parts else None
    if ses is not None and any(_needs_std(sp, parts) for _, m, _ in loaded for sp in (m or [])):
        ses.worker()                      # its cold start (~10-40 s) overlaps the first dev summaries
    done = 0
    try:
        for p, members, err in loaded:
            if err is not None:
                e = err
                print(_cut(f'[{os.path.basename(p)}] 오류: {type(e).__name__}: {e}'), flush=True); rc = 1
                recs.append(dict(name=os.path.basename(p), error=f'{type(e).__name__}: {e}'))
                done += 1
                continue
            for sp in members:
                try:
                    line, rec = run_spec(sp, bar, workers, early_stop, ses)
                    print(line, flush=True); recs.append(rec)
                except Exception as e:
                    nm = str(sp.get('name', os.path.basename(p)))
                    print(_cut(f'[{nm}] 오류: {type(e).__name__}: {e}'), flush=True); rc = 1
                    recs.append(dict(name=nm, error=f'{type(e).__name__}: {e}'))
            done += 1
    finally:                 # the table and the batch JSON are written even if the batch is interrupted
        if ses is not None:
            ses.close()
        not_run = [os.path.basename(p) for p in files[done:]]
        if not_run:
            rc = rc or 1
            print(_cut(f'== 중단: 실행 안 된 명세 {len(not_run)}개: {", ".join(not_run)}'), flush=True)
        if len(recs) > 1 or not_run:
            txt = summary(recs, bar)
            print(txt, flush=True)
            os.makedirs(os.path.join(ledger.HOME, 'out'), exist_ok=True)
            fn = os.path.join(ledger.HOME, 'out', time.strftime('batch_%Y%m%dT%H%M%SZ.json', time.gmtime()))
            with open(fn, 'w') as fh:
                json.dump(dict(bar=bar, records=recs, summary=txt, not_run=not_run), fh, ensure_ascii=False,
                          indent=1, default=str)
    return rc
