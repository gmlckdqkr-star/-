"""Blind synthetic tournament of lane TS2, round 2 (judge script).

Reproduces tournament.json (all numbers) and the tables of RESULT_TOURNAMENT.md.
  /root/.cache/ts-venv/bin/python -I -B tournament.py            # full run, P = 1000, 4 worker processes
  /root/.cache/ts-venv/bin/python -I -B tournament.py --P 50     # quick smoke test (writes tournament_smoke.json)

What it does (DESIGN_BRIEF_R2.md section 7):
  * every lane rule (A, B, C, D) x every lane simulator (A, B, C, D), mechanism ON and OFF = 8 cells, P = 1000 paths,
    T = 300 + 30*252 = 7860, engine defaults (delay 2, cost 0.003);
  * one fresh seed per cell (SEEDS below, 20000-20007); within a cell all rules and reference rows use the same paths;
  * per cell: the rule's median after-tax CAGR, p10, P(MDD <= -80%), average level; same-basis hold 1x / 2x / 3x and the
    constant levels 0.5 ... 3 on the same paths;
  * Score_j = 0.5 * mean over simulators of the cell median CAGR (ON) + 0.5 * the same (OFF); ties within 0.003 of the top
    score are broken by the higher worst cell (lowest of the 8 cell medians); PRIMARY = winner among the lane rules;
  * the same score for the holds and each constant level (reference rows), the best single constant level;
  * for the primary only: the same 8 cells (same seeds, same paths) at delay 3, delay 5 and cost 0.006;
  * a paired bootstrap over paths (within cells) of the score differences, for the caveats.
Nothing is read except the lane files (rule.py, sim.py) and common/exec_engine.py. No market data, no network.
No file is written outside this folder; no cache is written (results pass between processes in memory).
"""
import sys
sys.dont_write_bytecode = True
import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
import json
import time
import hashlib
import argparse
import importlib.util
import multiprocessing as mp
import numpy as np

ROOT = '/mnt/project-files/research/theory_sim'
DESIGN = ROOT + '/r2/design'
OUTDIR = DESIGN + '/tournament'
sys.path.insert(0, ROOT + '/common')
import exec_engine as ee  # noqa: E402

ALL_LANES = ['A', 'B', 'C', 'D']
LANES = list(ALL_LANES)            # lanes left after excluding audit FAILs (set in main; all four passed)
WORLDS = [(s, m) for s in LANES for m in (True, False)]
SEEDS = {('A', True): 20000, ('A', False): 20001, ('B', True): 20002, ('B', False): 20003,
         ('C', True): 20004, ('C', False): 20005, ('D', True): 20006, ('D', False): 20007}
T = ee.WARM + 30 * 252
LEVELS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
TIE = 0.003
NBOOT = 2000
BOOT_SEED = 777


def cell_name(s, m):
    return '%s_%s' % (s, 'ON' if m else 'OFF')


def sha256(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def lane_hashes():
    h = {'common/exec_engine.py': sha256(ROOT + '/common/exec_engine.py')}
    for L in ALL_LANES:
        for fn in ('rule.py', 'sim.py'):
            h['%s/%s' % (L, fn)] = sha256('%s/%s/%s' % (DESIGN, L, fn))
    return h


def audit_verdicts():
    """verdict line of each lane's AUDIT.md ('Verdict: PASS' / 'Verdict: FAIL')."""
    out = {}
    for L in ALL_LANES:
        txt = open('%s/%s/AUDIT.md' % (DESIGN, L)).read()
        i = txt.find('Verdict:')
        seg = txt[i:i + 40].upper() if i >= 0 else ''
        out[L] = 'FAIL' if 'FAIL' in seg else ('PASS' if 'PASS' in seg else 'UNKNOWN')
    return out


def load(lane, name):
    spec = importlib.util.spec_from_file_location('ts2r2_%s_%s' % (lane, name), '%s/%s/%s.py' % (DESIGN, lane, name))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pack(res):
    out = dict(cagr=np.asarray(res['cagr'], float), mdd=np.asarray(res['mdd'], float))
    if 'avg_level' in res:
        out['avg_level'] = np.asarray(res['avg_level'], float)
        out['trades_per_year'] = np.asarray(res['trades_per_year'], float)
    return out


def rule_levels(lane, close, rf, y10):
    mod = load(lane, 'rule')
    c_in, f_in = close.copy(), rf.copy()
    kw = {}
    if 'y10' in tuple(mod.INPUTS):
        kw['y10'] = None if y10 is None else y10.copy()
    t0 = time.time()
    B = mod.target_levels(c_in, f_in, **kw)
    dt = time.time() - t0
    B = np.asarray(B)
    fin = np.isfinite(B)
    chk = dict(seconds=round(dt, 2), shape_ok=bool(B.shape == close.shape), dtype=str(B.dtype),
               inputs_unchanged=bool(np.array_equal(c_in, close) and np.array_equal(f_in, rf)),
               n_nan=int((~fin).sum()), n_out_of_range=int(((B < 0) | (B > 3)).sum(where=fin)),
               n_inf=int(np.isinf(B).sum()))
    return np.asarray(B, dtype=np.float64), chk


def world_stats(r, rf):
    W = ee.WARM
    rr, ff = r[:, W:], rf[:, W:]
    prem = (rr - ff).mean(axis=1) * 252
    vol = rr.std(axis=1) * np.sqrt(252)
    lp = np.cumsum(np.log1p(rr), axis=1)
    mdd = np.expm1((lp - np.maximum.accumulate(np.maximum(lp, 0.0), axis=1)).min(axis=1))
    return dict(premium_arith_med=float(np.median(prem)), vol_med=float(np.median(vol)),
                index_mdd_med=float(np.median(mdd)), rf_mean_med=float(np.median(ff.mean(axis=1) * 252)))


def run_cell(task):
    """task = (sim_lane, mechanism, seed, P, mode, primary). mode 'main' or 'stress'. Returns per-path arrays."""
    s, m, seed, P, mode, primary = task
    t0 = time.time()
    sim = load(s, 'sim')
    d = sim.simulate(P, T, seed, mechanism=m)
    r = np.ascontiguousarray(d['r'], dtype=np.float64)
    rf = np.ascontiguousarray(d['rf'], dtype=np.float64)
    y10 = d.get('y10')
    y10 = None if y10 is None else np.ascontiguousarray(y10, dtype=np.float64)
    del d
    assert r.shape == (P, T) and rf.shape == (P, T)
    close = np.cumprod(1.0 + r, axis=1)            # index level, close[:, 0] = 1 (rules are scale-invariant)
    r_sha = hashlib.sha256(r.tobytes()).hexdigest()[:16]
    t_sim = time.time() - t0
    series, checks = {}, {}
    if mode == 'main':
        for L in LANES:
            B, chk = rule_levels(L, close, rf, y10)
            checks['rule_' + L] = chk
            series['rule_' + L] = pack(ee.run(r, rf, B))
            del B
        series['hold1'] = pack(ee.hold(r, rf, 1))
        series['hold2'] = pack(ee.hold(r, rf, 2))
        for lev in LEVELS:
            series['const_%.1f' % lev] = pack(ee.run(r, rf, np.full((P, T), lev)))
        series['hold3'] = series['const_3.0']       # ee.hold(r, rf, 3) is exactly run(r, rf, B = 3) with defaults
        ws = world_stats(r, rf)
    else:
        B, chk = rule_levels(primary, close, rf, y10)
        checks['rule_' + primary] = chk
        series['rule_%s_delay3' % primary] = pack(ee.run(r, rf, B, delay=3))
        series['rule_%s_delay5' % primary] = pack(ee.run(r, rf, B, delay=5))
        series['rule_%s_cost0.006' % primary] = pack(ee.run(r, rf, B, cost=0.006))
        del B
        for lev in LEVELS:                          # constant levels under the same stress (reference)
            series['const_%.1f_cost0.006' % lev] = pack(ee.run(r, rf, np.full((P, T), lev), cost=0.006))
            series['const_%.1f_delay5' % lev] = pack(ee.run(r, rf, np.full((P, T), lev), delay=5))
        ws = None
    return dict(sim=s, mechanism=m, seed=seed, P=P, mode=mode, seconds_sim=round(t_sim, 1),
                seconds_total=round(time.time() - t0, 1), series=series, checks=checks, world=ws, r_sha=r_sha)


def summ(a):
    c, md = a['cagr'], a['mdd']
    out = dict(cagr_med=float(np.median(c)), cagr_p10=float(np.percentile(c, 10)),
               cagr_p90=float(np.percentile(c, 90)), p_dd80=float(np.mean(md <= -0.8)),
               mdd_med=float(np.median(md)))
    if 'avg_level' in a:
        out['avg_level_med'] = float(np.median(a['avg_level']))
        out['avg_level_mean'] = float(np.mean(a['avg_level']))
        out['trades_per_year_med'] = float(np.median(a['trades_per_year']))
    return out


def score_of(meds):
    """meds: dict cell_name -> median CAGR for one series. Returns score, ON mean, OFF mean, worst cell."""
    on = [meds[cell_name(s, True)] for s in LANES]
    off = [meds[cell_name(s, False)] for s in LANES]
    allc = {k: meds[k] for k in [cell_name(s, m) for s, m in WORLDS]}
    wk = min(allc, key=allc.get)
    return dict(score=0.5 * float(np.mean(on)) + 0.5 * float(np.mean(off)), on_mean=float(np.mean(on)),
                off_mean=float(np.mean(off)), worst_cell=float(allc[wk]), worst_cell_name=wk)


def pick_winner(sc):
    """sc: dict name -> dict(score, worst_cell). Ties within TIE of the top score: the higher worst cell wins."""
    top = max(v['score'] for v in sc.values())
    tied = [k for k, v in sc.items() if v['score'] >= top - TIE]
    win = max(tied, key=lambda k: (sc[k]['worst_cell'], sc[k]['score']))
    return win, sorted(tied, key=lambda k: -sc[k]['score'])


def bootstrap(cells, names, primary, best_const, nboot=NBOOT):
    """paired bootstrap over paths within each cell (same resampled paths for every series of a cell)."""
    g = np.random.default_rng(BOOT_SEED)
    keys = [cell_name(s, m) for s, m in WORLDS]
    med = {n: {} for n in names}
    for k in keys:
        P = cells[k]['series'][names[0]]['cagr'].size
        idx = g.integers(0, P, (nboot, P))
        for n in names:
            med[n][k] = np.median(cells[k]['series'][n]['cagr'][idx], axis=1)
    sc = {}
    for n in names:
        on = np.mean([med[n][cell_name(s, True)] for s in LANES], axis=0)
        off = np.mean([med[n][cell_name(s, False)] for s in LANES], axis=0)
        worst = np.min([med[n][k] for k in keys], axis=0)
        sc[n] = dict(score=0.5 * on + 0.5 * off, worst=worst)
    out = dict(n_boot=nboot, seed=BOOT_SEED, diffs={})
    for n in names:
        if n == primary:
            continue
        dd = sc[primary]['score'] - sc[n]['score']
        out['diffs']['%s_minus_%s' % (primary, n)] = dict(
            sd=float(dd.std()), ci90=[float(np.percentile(dd, 5)), float(np.percentile(dd, 95))],
            p_gt0=float(np.mean(dd > 0)))
    cand = [n for n in names if n.startswith('rule_')]
    wins = {n: 0 for n in cand}
    for b in range(nboot):
        sb = {n: dict(score=float(sc[n]['score'][b]), worst_cell=float(sc[n]['worst'][b])) for n in cand}
        wins[pick_winner(sb)[0]] += 1
    out['winner_share'] = {n: wins[n] / nboot for n in cand}
    out['score_sd'] = {n: float(sc[n]['score'].std()) for n in names}
    return out


def pct(x, nd=2):
    return '%.*f' % (nd, 100 * x)


def md_tables(d):
    """markdown tables of RESULT_TOURNAMENT.md, built from tournament.json (numbers in % per year unless stated)."""
    lanes = [c.split('_')[1] for c in d['candidates']]
    keys = list(d['cells'].keys())
    C = d['cells']
    o = []
    o.append('### Table 1. Scores (median after-tax 30y CAGR, %/yr)\n')
    o.append('| row | kind | score | mean ON | mean OFF | worst cell | worst cell is |')
    o.append('|---|---|---|---|---|---|---|')
    order = d['candidates'] + ['hold1', 'hold2', 'hold3'] + ['const_%.1f' % v for v in d['meta']['levels']] + \
        ['const_best_per_cell_hindsight']
    for n in order:
        s = d['scores'][n]
        kind = 'candidate' if n.startswith('rule_') else 'reference'
        lab = n.replace('rule_', 'rule ').replace('const_best_per_cell_hindsight', 'best constant per cell (hindsight)')
        if n == d['primary_name']:
            lab = '**%s (PRIMARY)**' % lab
        o.append('| %s | %s | %s | %s | %s | %s | %s |' % (lab, kind, pct(s['score']), pct(s['on_mean']),
                                                         pct(s['off_mean']), pct(s['worst_cell']), s['worst_cell_name']))
    o.append('')
    hdr = '| row | ' + ' | '.join('%s (seed %d)' % (k, C[k]['seed']) for k in keys) + ' |'
    sep = '|---|' + '---|' * len(keys)

    def mat(title, rows, fn):
        o.append(title + '\n'); o.append(hdr); o.append(sep)
        for lab, get in rows:
            o.append('| %s | ' % lab + ' | '.join(fn(get(C[k])) for k in keys) + ' |')
        o.append('')
    rr = [('rule ' + L, (lambda L: lambda c: c['stats']['rule_' + L])(L)) for L in lanes]
    refs = [('hold 1x', lambda c: c['stats']['hold1']), ('hold 2x', lambda c: c['stats']['hold2']),
            ('hold 3x', lambda c: c['stats']['hold3'])] + \
        [('const %.1f' % v, (lambda v: lambda c: c['stats']['const_%.1f' % v])(v)) for v in d['meta']['levels']]
    mat('### Table 2. Cross-matrix: median after-tax CAGR (%/yr), rule x simulator world', rr + refs,
        lambda s: pct(s['cagr_med']))
    o.append('Best constant level per cell: ' + ', '.join('%s %.1f (%s)' % (k, C[k]['best_const_level'],
                                                                         pct(C[k]['best_const_cagr_med'])) for k in keys))
    o.append('')
    mat('### Table 3. p10 of after-tax CAGR (%/yr)', rr + refs, lambda s: pct(s['cagr_p10']))
    mat('### Table 4. P(MDD <= -80%) (share of paths)', rr + refs, lambda s: '%.3f' % s['p_dd80'])
    mat('### Table 5. Rules: average held level (median over paths; mean in brackets) and trades per year (median)',
        rr, lambda s: '%.2f (%.2f); %.1f tr/yr' % (s['avg_level_med'], s['avg_level_mean'], s['trades_per_year_med']))
    mat('### Table 6. Rules: share of paths beating the same-basis hold 1x / the cell\'s best constant level', rr,
        lambda s: '%.2f / %.2f' % (s['frac_paths_beats_hold1'], s['frac_paths_beats_cell_best_const']))
    pr = d['primary_name']
    o.append('### Table 7. Primary (%s) under stress: median after-tax CAGR (%%/yr) per cell and score\n' % pr)
    o.append('| setting | ' + ' | '.join(keys) + ' | score | mean ON | mean OFF | worst cell | best single constant score, same setting |')
    o.append('|---|' + '---|' * (len(keys) + 5))
    base = d['scores'][pr]
    o.append('| delay 2, cost 0.003 (default) | ' + ' | '.join(pct(C[k]['stats'][pr]['cagr_med']) for k in keys) +
             ' | %s | %s | %s | %s | %s |' % (pct(base['score']), pct(base['on_mean']), pct(base['off_mean']),
                                              pct(base['worst_cell']), pct(d['best_single_constant']['score'])))
    for tag, lab in (('delay3', 'delay 3'), ('delay5', 'delay 5'), ('cost0.006', 'cost 0.006')):
        v = d['stress'][tag]
        o.append('| %s | ' % lab + ' | '.join(pct(v['cells'][k]['cagr_med']) for k in keys) +
                 ' | %s | %s | %s | %s | %s (level %.1f) |' % (pct(v['score']), pct(v['on_mean']), pct(v['off_mean']),
                                                             pct(v['worst_cell']), pct(v['reference']['best_const_score']),
                                                             v['reference']['best_const_level']))
    o.append('')
    o.append('### Table 8. Paired bootstrap over paths (%d resamples within each cell): score differences (pp)\n'
             % d['bootstrap']['n_boot'])
    o.append('| difference | point | sd | 90% interval | share of resamples > 0 |')
    o.append('|---|---|---|---|---|')
    for k, v in d['bootstrap']['diffs'].items():
        a, b = k.split('_minus_')
        pt = d['scores'][a]['score'] - d['scores'][b]['score']
        o.append('| %s minus %s | %s | %s | [%s, %s] | %.3f |' % (a, b, pct(pt), pct(v['sd']), pct(v['ci90'][0]),
                                                                pct(v['ci90'][1]), v['p_gt0']))
    o.append('')
    o.append('Share of bootstrap resamples in which each candidate wins under the full scoring rule (tie window and '
             'tie-break included): ' + ', '.join('%s %.3f' % (k, v) for k, v in d['bootstrap']['winner_share'].items()))
    o.append('')
    o.append('### Table 9. The synthetic worlds of the cells (medians over paths of the 30 traded years)\n')
    o.append('| cell | seed | arithmetic premium of the index over rf | volatility | worst index drawdown | mean rf |')
    o.append('|---|---|---|---|---|---|')
    for k in keys:
        w = C[k]['world']
        o.append('| %s | %d | %s | %s | %s | %s |' % (k, C[k]['seed'], pct(w['premium_arith_med']), pct(w['vol_med']),
                                                    pct(w['index_mdd_med'], 1), pct(w['rf_mean_med'])))
    o.append('')
    return '\n'.join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--P', type=int, default=1000)
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--tables', action='store_true', help='print the markdown tables from tournament.json and exit')
    a = ap.parse_args()
    if a.tables:
        with open(OUTDIR + '/tournament.json') as f:
            print(md_tables(json.load(f)))
        return
    P = a.P
    smoke = P != 1000
    t_start = time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())
    hashes0 = lane_hashes()
    verdicts = audit_verdicts()
    excluded = {L: 'audit verdict ' + v for L, v in verdicts.items() if v != 'PASS'}
    if excluded:
        global LANES, WORLDS
        LANES = [L for L in ALL_LANES if L not in excluded]
        WORLDS = [(s, m) for s in LANES for m in (True, False)]
    if not LANES:
        print('every lane failed its audit: no tournament'); return
    tasks = [(s, m, SEEDS[(s, m)], P, 'main', None) for s, m in WORLDS]
    ctx = mp.get_context('fork')
    with ctx.Pool(a.jobs) as pool:
        res = pool.map(run_cell, tasks, chunksize=1)
    cells = {cell_name(x['sim'], x['mechanism']): x for x in res}
    names = ['rule_' + L for L in LANES] + ['hold1', 'hold2', 'hold3'] + ['const_%.1f' % v for v in LEVELS]
    table = {}
    for k, x in cells.items():
        st = {n: summ(x['series'][n]) for n in names}
        bc = max(LEVELS, key=lambda v: st['const_%.1f' % v]['cagr_med'])
        for L in LANES:                             # paired share of paths on which the rule beats the reference
            c = x['series']['rule_' + L]['cagr']
            st['rule_' + L]['frac_paths_beats_hold1'] = float(np.mean(c > x['series']['hold1']['cagr']))
            st['rule_' + L]['frac_paths_beats_cell_best_const'] = float(np.mean(
                c > x['series']['const_%.1f' % bc]['cagr']))
        table[k] = dict(sim_lane=x['sim'], mechanism='ON' if x['mechanism'] else 'OFF', seed=x['seed'], P=x['P'],
                        seconds=x['seconds_total'], world=x['world'], checks=x['checks'], stats=st,
                        best_const_level=bc, best_const_cagr_med=st['const_%.1f' % bc]['cagr_med'],
                        hold1_cagr_med=st['hold1']['cagr_med'], r_sha256_16=x['r_sha'])
    scores = {n: score_of({k: table[k]['stats'][n]['cagr_med'] for k in table}) for n in names}
    scores['const_best_per_cell_hindsight'] = score_of({k: table[k]['best_const_cagr_med'] for k in table})
    cand = {n: scores[n] for n in names if n.startswith('rule_')}
    primary_name, tied = pick_winner(cand)
    primary = primary_name.split('_')[1]
    const_names = ['const_%.1f' % v for v in LEVELS]
    best_const_name = max(const_names, key=lambda n: scores[n]['score'])
    # stress rows for the primary (same seeds, same paths)
    tasks2 = [(s, m, SEEDS[(s, m)], P, 'stress', primary) for s, m in WORLDS]
    with ctx.Pool(a.jobs) as pool:
        res2 = pool.map(run_cell, tasks2, chunksize=1)
    stress = {}
    for tag in ('delay3', 'delay5', 'cost0.006'):
        nm = 'rule_%s_%s' % (primary, tag)
        st = {cell_name(x['sim'], x['mechanism']): summ(x['series'][nm]) for x in res2}
        sc = score_of({k: v['cagr_med'] for k, v in st.items()})
        ref = {}
        if tag in ('cost0.006', 'delay5'):
            cst = {lv: score_of({cell_name(x['sim'], x['mechanism']): float(np.median(
                x['series']['const_%.1f_%s' % (lv, tag)]['cagr'])) for x in res2}) for lv in LEVELS}
            blv = max(LEVELS, key=lambda v: cst[v]['score'])
            ref = dict(best_const_level=blv, best_const_score=cst[blv]['score'],
                       const_scores={'%.1f' % v: cst[v]['score'] for v in LEVELS})
        else:   # constant levels are delay-invariant (the engine pre-fills its order queue at the end of warm-up)
            ref = dict(best_const_level=float(best_const_name.split('_')[1]),
                       best_const_score=scores[best_const_name]['score'], note='constant levels do not depend on delay')
        stress[tag] = dict(cells=st, **sc, reference=ref)
    same_paths = {cell_name(x['sim'], x['mechanism']): bool(x['r_sha'] == cells[cell_name(x['sim'], x['mechanism'])]['r_sha'])
                  for x in res2}
    boot = bootstrap(cells, ['rule_' + L for L in LANES] + ['hold1', best_const_name], primary_name, best_const_name)
    hashes1 = lane_hashes()
    t_end = time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())
    out = dict(
        meta=dict(judge='blind tournament judge, lane TS2 round 2', started_utc=t_start, finished_utc=t_end,
                  python=sys.version.split()[0], numpy=np.__version__, P=P, T=T, warm=ee.WARM,
                  engine_defaults=dict(delay=2, cost=0.003), levels=LEVELS, tie_window=TIE,
                  seeds={cell_name(s, m): SEEDS[(s, m)] for s, m in WORLDS},
                  seed_note='one fresh seed per cell; every rule and reference row of a cell runs on the same paths; '
                            'the stress rows of the primary reuse the same seed, hence the same paths',
                  close_construction='close = cumprod(1 + r) along time (close[:, 0] = 1); rules get close and rf '
                                     '(y10 only if a rule declares it in INPUTS; none does)',
                  hold3_note='hold 3x = run(r, rf, B = 3) with engine defaults, identical to the constant level 3.0',
                  file_sha256_before=hashes0, file_sha256_after=hashes1,
                  lane_files_unchanged=bool(hashes0 == hashes1)),
        audit_verdicts=verdicts, excluded_lanes=excluded,
        cells=table,
        scores=scores,
        candidates=[n for n in names if n.startswith('rule_')],
        tie_set=tied, primary=primary, primary_name=primary_name,
        best_single_constant=dict(name=best_const_name, level=float(best_const_name.split('_')[1]),
                                  **scores[best_const_name]),
        primary_beats_best_constant=bool(scores[primary_name]['score'] > scores[best_const_name]['score']),
        primary_beats_hold1=bool(scores[primary_name]['score'] > scores['hold1']['score']),
        stress=stress, stress_same_paths_as_main=same_paths,
        bootstrap=boot,
    )
    fn = OUTDIR + ('/tournament_smoke.json' if smoke else '/tournament.json')
    with open(fn, 'w') as f:
        json.dump(out, f, indent=1)
    print('wrote', fn)
    print('primary', primary_name, 'tie set', tied)
    for n in names + ['const_best_per_cell_hindsight']:
        s = scores[n]
        print('%-10s score %.4f  ON %.4f  OFF %.4f  worst %.4f (%s)' % (n, s['score'], s['on_mean'], s['off_mean'],
                                                                      s['worst_cell'], s['worst_cell_name']))
    for tag, v in stress.items():
        print('stress %-9s score %.4f ON %.4f OFF %.4f worst %.4f; ref best const %.4f' % (
            tag, v['score'], v['on_mean'], v['off_mean'], v['worst_cell'], v['reference']['best_const_score']))


if __name__ == '__main__':
    main()
