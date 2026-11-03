"""python -m lab run <spec...> [--bar none|quick|full] [--workers N]
       run specs, print ONE line each (<= ~400 bytes; the only thing an LLM needs to read).
       --bar quick (default): '빠른 선별 (기준 아님)' = 10y b63 10M, 400 paths, own window, KRWX, src_end 2014.
       --bar full: the project bar on blackbox2 / d6q (all required versions, ~4 min per version with 4 workers):
                   REJECT | 'REJECT (lab 판정, 미확정)' | 'Q60 미달 (Q 미판정)' (failed gates) or 'PENDING (통합 담당 대기)'.
                   Lab never prints APPLY-Q / APPLY-Q60.
       --bar none: dev summary only.
       --all-versions (full only): keep running the remaining versions after a REJECT (default: stop, REJECT is final).
   python -m lab ledger
       family counts and stored bar results.
Full detail goes to LAB_HOME/out/<hash>_<mode>.json (not meant for LLM context).
Every number comes from data up to 2014-12-31 (design side); nothing after 2014 is computed."""
import json, os, sys, time
import pandas as pd
from . import data, dsl, gates, ledger

MAX_LINE = 400


def _cut(s, n=MAX_LINE):
    b = s.encode('utf-8')
    if len(b) <= n:
        return s
    return b[:n - 3].decode('utf-8', 'ignore') + '...'


def _dev_part(s):
    d, b = s['dev'], s['boot']
    return (f"개발({s['dev_start'][:4]}~2014) 세후 {d['cagr_at']:.1%} 낙폭 {d['mdd']:.0%} "
            f"({s['baseline']} {d['base_cagr_at']:.1%}/{d['base_mdd']:.0%}) 12년x{b['s_med_y12']:.1f}"
            f"({s['baseline']} x{b['b_med_y12']:.1f}) P80 {b['s_p_dd80']:.1%} "
            f"개발선별 {'통과' if s['screen_pass'] else '탈락'}")


def _bar_part(mode, r):
    if r is None:
        return ''
    if r['verdict'].startswith('REJECT (version'):
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
    t0 = time.time()
    spec = dsl.check_spec(dsl.load_spec(path))           # refuse delay < 2 / non-numeric cost before anything runs
    h = dsl.spec_hash(spec); fam = spec.get('family', 'unset')
    name = spec.get('name', h)
    s = ledger.get(h)
    cached = s is not None
    if not cached:
        sleeves = sorted({a for r in spec['rules'] for a in (r.get('hold') or r.get('else') or {})} - {'CASH'}
                         | {spec.get('baseline', 'QQQ')})
        F, R, rf, SRC = data.build(sleeves)
        F = F[F.index <= gates.DEV_END]; R = R[R.index <= gates.DEV_END]      # nothing after 2014 enters
        W = dsl.compile_weights(spec, F, sleeves)
        s = gates.evaluate(W, R, spec, baseline=spec.get('baseline', 'QQQ'))
        ledger.put(h, spec, s)
    detail = dict(spec=spec, hash=h, dev_summary=s)
    parts = [f"[{name}] 계열={fam} N={ledger.family_n(fam)}{' (중복)' if cached else ''}", _dev_part(s)]
    bcached = False
    if bar != 'none':
        key, r, res, bcached = _bar(spec, h, bar, workers, early_stop)
        detail['bar'] = res if res is not None else dict(r, cached=True)
        parts.append(_bar_part(key, r) + (' (저장값)' if bcached else ''))
    if not (cached and (bar == 'none' or bcached)):        # keep the full detail of the first computation
        os.makedirs(os.path.join(ledger.HOME, 'out'), exist_ok=True)
        with open(os.path.join(ledger.HOME, 'out', f'{h}_{bar}.json'), 'w') as fh:
            json.dump(detail, fh, ensure_ascii=False, indent=1, default=str)
    parts.append(f'{time.time() - t0:.0f}s')
    return _cut(' | '.join(parts))


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
    rc = 0
    for p in specs:
        try:
            print(run_one(p, bar, workers, early_stop), flush=True)
        except Exception as e:  # one bad spec must not stop the batch
            print(_cut(f'[{os.path.basename(p)}] 오류: {type(e).__name__}: {e}'), flush=True); rc = 1
    return rc
