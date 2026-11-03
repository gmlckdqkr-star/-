"""python -m lab run <spec...>   : run specs, print ONE line each (the only thing an LLM needs to read)
   python -m lab ledger           : family counts
Full detail goes to var/out/<hash>.json (not meant for LLM context)."""
import json, os, sys, time
from . import data, dsl, gates, ledger


def _line(name, fam, n, s, hv, dt, cached):
    d, b = s['dev'], s['boot']
    return (f"[{name}] 계열={fam} N={n}{' (중복:재계산 안 함)' if cached else ''} | "
            f"개발({s['dev_start'][:4]}~2014) 세후 {d['cagr_at']:.1%} 낙폭 {d['mdd']:.0%} "
            f"({s['baseline']} {d['base_cagr_at']:.1%}/{d['base_mdd']:.0%}) "
            f"회전 {d['turn']:.1f}/년 | 재표본 12년 중앙 x{b['s_med_y12']:.1f} ({s['baseline']} x{b['b_med_y12']:.1f}) "
            f"P(-80%) {b['s_p_dd80']:.1%} | MVP 관문 개발 {'통과' if s['dev_pass'] else '탈락'} · "
            f"봉인 구간 {hv} | {dt:.1f}s")


def run_one(path):
    t0 = time.time()
    spec = dsl.load_spec(path)
    h = dsl.spec_hash(spec); fam = spec.get('family', 'unset')
    hit = ledger.get(h)
    if hit:
        s, hv = hit
        return _line(spec.get('name', h), fam, ledger.family_n(fam), s, hv, time.time() - t0, True)
    sleeves = sorted({a for r in spec['rules'] for a in (r.get('hold') or r.get('else') or {})} - {'CASH'}
                     | {spec.get('baseline', 'QQQ')})
    F, R, rf, SRC = data.build(sleeves)
    W = dsl.compile_weights(spec, F, sleeves)
    s = gates.evaluate(W, R, spec, baseline=spec.get('baseline', 'QQQ'))
    if not s['dev_pass']:
        hv = 'NOT_TRIED'  # holdout is only looked at for dev passers
    elif ledger.holdout_looks(fam) >= ledger.HOLDOUT_LOOKS_PER_FAMILY:
        hv = 'BUDGET'
    else:
        hv = 'PASS' if s['holdout_pass'] else 'REJECT'
    s.pop('holdout_pass')  # never stored or shown as numbers
    ledger.put(h, spec, s, hv)
    os.makedirs(os.path.join(ledger.HOME, 'out'), exist_ok=True)
    json.dump(dict(spec=spec, hash=h, summary=s, holdout=hv),
              open(os.path.join(ledger.HOME, 'out', h + '.json'), 'w'), ensure_ascii=False, indent=1)
    return _line(spec.get('name', h), fam, ledger.family_n(fam), s, hv, time.time() - t0, False)


def main(argv=None):
    a = argv if argv is not None else sys.argv[1:]
    if not a or a[0] not in ('run', 'ledger'):
        print(__doc__); return 2
    if a[0] == 'ledger':
        import sqlite3
        c = sqlite3.connect(os.path.join(ledger.HOME, 'ledger.sqlite'))
        for fam, n, k in c.execute("select family,count(*),sum(holdout in ('PASS','REJECT')) from runs group by family"):
            print(f'{fam}: N={n} 봉인구간 사용={k}/{ledger.HOLDOUT_LOOKS_PER_FAMILY}')
        return 0
    rc = 0
    for p in a[1:]:
        try:
            print(run_one(p))
        except Exception as e:  # one bad spec must not stop the batch
            print(f'[{os.path.basename(p)}] 오류: {type(e).__name__}: {e}'); rc = 1
    return rc
