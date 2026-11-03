"""python -m lab run <spec or dir ...> [--bar none|quick|full] [--workers N]
       run specs (a directory = every *.yaml / *.yml / *.json in it, sorted), print ONE line each (<= ~400 bytes; the
       only thing an LLM needs to read). A spec with `grid:` runs once per grid point (each its own hash, each counted
       in the family N). With more than one spec, a ranked summary table (<= ~1.5 KB) follows.
       --bar quick (default): '빠른 선별 (기준 아님)' = 10y b63 10M, 400 paths, own window, KRWX, src_end 2014.
       --bar full: the project bar on blackbox2 / d6q (all required versions, ~4 min per version with 4 workers):
                   REJECT | 'REJECT (lab 판정, 미확정)' | 'Q60 미달 (Q 미판정)' (failed gates) or 'PENDING (통합 담당 대기)'.
                   Lab never prints APPLY-Q / APPLY-Q60.
       --bar none: dev summary only.
       --all-versions (full only): keep running the remaining versions after a REJECT (default: stop, REJECT is final).
   python -m lab ledger
       family counts and stored bar results.
Full detail goes to LAB_HOME/out/<hash>_<mode>.json, the batch to LAB_HOME/out/batch_<utc>.json (not meant for
LLM context).
Every number comes from data up to 2014-12-31 (design side); nothing after 2014 is computed."""
import glob, json, os, sys, time
import pandas as pd
from . import data, dsl, gates, ledger

MAX_LINE = 400
MAX_SUMMARY = 1500


def _cut(s, n=MAX_LINE):
    b = s.encode('utf-8')
    if len(b) <= n:
        return s
    return b[:n - 3].decode('utf-8', 'ignore') + '...'


def _dev_part(s):
    d, b = s['dev'], s['boot']
    acct = '' if s.get('account', 'us') == 'us' else f"[{s['account']} 13bp·해외지수 건별15.4%·국내주식형 0] "
    return (acct + f"개발({s['dev_start'][:4]}~2014) 세후 {d['cagr_at']:.1%} 낙폭 {d['mdd']:.0%} "
            f"({s['baseline']} {d['base_cagr_at']:.1%}/{d['base_mdd']:.0%}) 12년x{b['s_med_y12']:.1f}"
            f"({s['baseline']} x{b['b_med_y12']:.1f}) P80 {b['s_p_dd80']:.1%} "
            f"개발선별 {'통과' if s['screen_pass'] else '탈락'}"
            + ('' if (s.get('dev_causality') or {}).get('ok', True) else ' 개발 인과성 위반'))


def _bar_part(mode, r):
    if r is None:
        return ''
    if r['verdict'].startswith('REJECT (version') or r['verdict'].startswith('판정 불가'):
        return f"기준: {r['verdict']}"
    n = r.get('numbers') or {}
    if mode.startswith('quick'):
        f = ','.join(r['failed']) or '없음'
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


def run_spec(spec, bar='quick', workers=4, early_stop=True):
    """One expanded spec -> (line, record for the batch summary)."""
    t0 = time.time()
    spec = dsl.check_spec(spec)                          # refuse delay < 2 / non-numeric cost before anything runs
    h = dsl.spec_hash(spec); fam = str(spec.get('family', 'unset'))
    name = str(spec.get('name', h))
    s = ledger.get(h)
    cached = s is not None
    if cached and s.get('dev_version') != gates.DEV_VERSION:   # dev summary logic changed: recompute, same row (N same)
        s, cached = None, False
        known = True
    else:
        known = cached
    if not cached:
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
    parts = [f"[{name}] 계열={fam} N={ledger.family_n(fam)}{' (중복)' if known else ''}", _dev_part(s)]
    bcached = False
    rec = dict(name=name, hash=h, family=fam, dev_y12=s['boot']['s_med_y12'], dev_screen=s['screen_pass'])
    if bar != 'none':
        key, r, res, bcached = _bar(spec, h, bar, workers, early_stop)
        detail['bar'] = res if res is not None else dict(r, cached=True)
        parts.append(_bar_part(key, r) + (' (저장값)' if bcached else ''))
        nums = r.get('numbers') or {}
        if bar == 'full' and isinstance(nums.get('own_KRWX'), dict):
            nums = nums['own_KRWX']
        rec.update(verdict=r['verdict'], failed=r['failed'], lg=nums.get('lg_med'), qld=nums.get('qld_lg_med'),
                   qqqm=nums.get('qqqm_lg_med'), mode=key)
    if not (cached and (bar == 'none' or bcached)):        # keep the full detail of the first computation
        os.makedirs(os.path.join(ledger.HOME, 'out'), exist_ok=True)
        with open(os.path.join(ledger.HOME, 'out', f'{h}_{bar}.json'), 'w') as fh:
            json.dump(detail, fh, ensure_ascii=False, indent=1, default=str)
    parts.append(f'{time.time() - t0:.0f}s')
    return _cut(' | '.join(parts)), rec


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


def summary(recs, bar):
    """Compact ranked table (<= MAX_SUMMARY bytes): top 10 by the quick screen's median log growth (10y b63 10M,
    full: own_KRWX), or by the dev 12y bootstrap multiple when no bar ran. Errors are counted, not listed."""
    ok = [r for r in recs if 'error' not in r]
    by_lg = any(r.get('lg') is not None for r in ok)
    key = (lambda r: (r.get('lg') is not None, r.get('lg') or 0.0)) if by_lg else (lambda r: r.get('dev_y12') or 0.0)
    rows = sorted(ok, key=key, reverse=True)[:10]
    what = ('lg 중앙값(10y b63 1000만' + (', own_KRWX' if bar == 'full' else '') + ')') if by_lg else '개발 12년 배수'
    lines = [f"== 요약: {what} 순 상위 {len(rows)}/{len(recs)}"
             + (f", 오류 {len(recs) - len(ok)}" if len(ok) < len(recs) else '')
             + (' — 빠른 선별 (기준 아님)' if bar == 'quick' else '') + ' ==']
    lines.append(' # 이름 hash  lg/QLD/QQQM  개발12y  판정')
    for i, r in enumerate(rows, 1):
        lg = '-' if r.get('lg') is None else f"{r['lg']:.3f}/{r.get('qld') or 0:.3f}/{r.get('qqqm') or 0:.3f}"
        nm = _cut(str(r['name']), 34)
        lines.append(_cut(f"{i:>2} {nm} {r['hash'][:6]} {lg} x{r.get('dev_y12') or 0:.1f} {_verdict_short(r)}", 140))
    return _cut('\n'.join(lines), MAX_SUMMARY)


def main(argv=None):
    a = list(argv if argv is not None else sys.argv[1:])
    if not a or a[0] not in ('run', 'ledger'):
        print(__doc__); return 2
    if a[0] == 'ledger':
        fam, bar = ledger.rows()
        for f, n in fam:
            print(f'{f}: N={n}')
        for f, mode, v, n in bar:
            print(f'  {f} {mode}: {v} x{n}')
        return 0
    bar, workers, specs, early_stop = 'quick', 4, [], True
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
        else:
            specs.append(x)
    if bar not in ('none', 'quick', 'full'):
        print(f'--bar must be none|quick|full, not {bar!r}'); return 2
    rc, recs, files = 0, [], collect(specs)
    done = 0
    try:
        for p in files:
            try:
                members = dsl.expand_grid(dsl.load_spec(p))
            except Exception as e:  # one bad spec must not stop the batch
                print(_cut(f'[{os.path.basename(p)}] 오류: {type(e).__name__}: {e}'), flush=True); rc = 1
                recs.append(dict(name=os.path.basename(p), error=f'{type(e).__name__}: {e}'))
                done += 1
                continue
            for sp in members:
                try:
                    line, rec = run_spec(sp, bar, workers, early_stop)
                    print(line, flush=True); recs.append(rec)
                except Exception as e:
                    nm = str(sp.get('name', os.path.basename(p)))
                    print(_cut(f'[{nm}] 오류: {type(e).__name__}: {e}'), flush=True); rc = 1
                    recs.append(dict(name=nm, error=f'{type(e).__name__}: {e}'))
            done += 1
    finally:                 # the table and the batch JSON are written even if the batch is interrupted
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
