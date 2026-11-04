"""TS1 synthetic tournament (DESIGN_BRIEF.md section 7), blind tournament judge.

Every lane rule x every lane simulator, mechanism ON and OFF, P = 1000 paths, T = 7860, engine defaults
(delay 2, cost 0.003). Fresh seeds: simulator L1 -> 20000, L2 -> 20001, L3 -> 20002; the SAME seed is used for ON and
OFF of one simulator (each lane defines its OFF world as "same seed, same parameter draw"), and all rules and all
reference rows in a cell are run on the same paths.
Score_j = 0.5 * mean over simulators of rule j's median after-tax CAGR (ON) + 0.5 * the same (OFF).
Ties within 0.003 of the top score: the higher worst cell (lowest of the six cell medians) wins.
Primary = winner among lane rules. Its row is then repeated at delay 3, delay 5 and cost 0.006.

NaN convention: a path whose engine CAGR is NaN (the 3x product went below zero on a day with an index move below
-1/3) is counted as CAGR -100% and MDD -100% (ruin), for every row, as lanes L2 and L3 did.

Usage:  python -B tournament.py            (all phases, 3 worker processes)
        python -B tournament.py --jobs 1   (serial)
Reads only the lane sim.py / rule.py files and common/exec_engine.py. Writes only into this folder.
"""
import sys, os, json, time, hashlib, importlib.util
sys.dont_write_bytecode = True                       # never write __pycache__ into lane folders
import numpy as np

ROOT = '/mnt/project-files/research/theory_sim'
OUT = os.path.join(ROOT, 'design', 'tournament')
WORK = os.path.join(OUT, 'work')
LANES = ('L1', 'L2', 'L3')
SEEDS = {'L1': 20000, 'L2': 20001, 'L3': 20002}     # simulator -> seed (used for ON and OFF)
REP_SEEDS = {'L1': 20010, 'L2': 20011, 'L3': 20012} # stability replicate only (reported, never used for the choice)
NBOOT = 2000
P, T = 1000, 300 + 30 * 252
CONST = (0.0, 0.5, 1.0, 2.0, 3.0)                   # 1, 2, 3 required; 0 (cash) and 0.5 added as extra reference rows
TIE = 0.003

sys.path.insert(0, os.path.join(ROOT, 'common'))
import exec_engine as ee


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def sims():
    return {L: _load(os.path.join(ROOT, 'design', L, 'sim.py'), f'sim_{L}') for L in LANES}


def rules():
    return {L: _load(os.path.join(ROOT, 'design', L, 'rule.py'), f'rule_{L}') for L in LANES}


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def fix(res):
    c = np.asarray(res['cagr'], dtype=float); m = np.asarray(res['mdd'], dtype=float)
    bad = ~np.isfinite(c)
    out = dict(res); out['cagr'] = np.where(bad, -1.0, c); out['mdd'] = np.where(bad | ~np.isfinite(m), -1.0, m)
    return out, int(bad.sum())


def S(res):
    r2, nbad = fix(res)
    s = ee.summary(r2)
    d = {k: round(float(s[k]), 6) for k in ('cagr_med', 'cagr_p10', 'cagr_p90', 'mdd_med', 'p_dd80', 'p_dd95')}
    for k in ('trades_per_year_med', 'avg_level_med'):
        if k in s: d[k] = round(float(s[k]), 4)
    d['n_nan_paths'] = nbad
    return d, r2['cagr']


def world(simname, mech, seed=None):
    sm = sims()[simname]
    seed = SEEDS[simname] if seed is None else seed
    with np.errstate(all='ignore'):
        d = sm.simulate(P, T, seed, mechanism=mech)
    r = np.asarray(d['r'], dtype=np.float64); rf = np.asarray(d['rf'], dtype=np.float64)
    return r, rf


def close_from(r):
    with np.errstate(all='ignore'):
        return 100.0 * np.cumprod(1.0 + r, axis=1)


def cell(args):
    """One cell = (simulator, mechanism). Runs all three lane rules and all reference rows on the same paths."""
    simname, mech = args[:2]
    seed = args[2] if len(args) > 2 else SEEDS[simname]
    tag = args[3] if len(args) > 3 else 'main'
    t0 = time.time()
    r, rf = world(simname, mech, seed)
    C = close_from(r)
    rl = rules()
    out = {'simulator': simname, 'mechanism': 'on' if mech else 'off', 'seed': seed, 'P': P, 'T': T,
           'world': {'finite_r': bool(np.isfinite(r).all()), 'min_daily_r': float(np.min(r)),
                     'paths_with_day_below_-1/3': int(np.sum((r < -1 / 3).any(axis=1))),
                     'ann_vol_med': float(np.median(np.log1p(r[:, 300:]).std(axis=1) * np.sqrt(252))),
                     'ann_logdrift_med': float(np.median(np.log1p(r[:, 300:]).mean(axis=1) * 252)),
                     'rf_mean_med': float(np.median(rf[:, 300:].mean(axis=1) * 252))},
           'rules': {}, 'ref': {}}
    with np.errstate(all='ignore'):
        h1, h1c = S(ee.hold(r, rf, 1))
        for L in (1, 2, 3):
            out['ref'][f'hold{L}x'] = h1 if L == 1 else S(ee.hold(r, rf, L))[0]
        for c in CONST:
            out['ref'][f'const{c:g}'] = S(ee.run(r, rf, np.full(r.shape, c)))[0]
        per_path = {'hold1x': h1c}
        for L in LANES:
            B = rl[L].target_levels(C, rf)
            d, rc = S(ee.run(r, rf, B))
            d['share_paths_gt_hold1x'] = round(float(np.mean(rc > h1c)), 4)
            out['rules'][L] = d; per_path[L] = rc
    out['seconds'] = round(time.time() - t0, 1)
    json.dump(out, open(os.path.join(WORK, f'cell_{tag}_{simname}_{out["mechanism"]}.json'), 'w'), indent=1)
    np.savez(os.path.join(WORK, f'cagr_{tag}_{simname}_{out["mechanism"]}.npz'), **per_path)
    print(f'cell {tag} {simname} {out["mechanism"]} seed {seed} done in {out["seconds"]}s', flush=True)
    return out


def robust(args):
    """Primary rule's row repeated at delay 3, delay 5 and cost 0.006 (same seeds -> same paths as the main cell)."""
    simname, mech, prim = args
    r, rf = world(simname, mech)
    C = close_from(r)
    B = rules()[prim].target_levels(C, rf)
    out = {'simulator': simname, 'mechanism': 'on' if mech else 'off', 'seed': SEEDS[simname]}
    with np.errstate(all='ignore'):
        out['base'] = S(ee.run(r, rf, B))[0]
        out['delay3'] = S(ee.run(r, rf, B, delay=3))[0]
        out['delay5'] = S(ee.run(r, rf, B, delay=5))[0]
        out['cost0.006'] = S(ee.run(r, rf, B, cost=0.006))[0]
    print(f'robust {prim} on {simname} {out["mechanism"]} done', flush=True)
    return out


def score(cells):
    tab = {}
    for j in LANES:
        on = [cells[(s, True)]['rules'][j]['cagr_med'] for s in LANES]
        off = [cells[(s, False)]['rules'][j]['cagr_med'] for s in LANES]
        tab[j] = dict(on_mean=float(np.mean(on)), off_mean=float(np.mean(off)),
                      score=0.5 * float(np.mean(on)) + 0.5 * float(np.mean(off)), worst_cell=float(min(on + off)),
                      on_by_sim=dict(zip(LANES, on)), off_by_sim=dict(zip(LANES, off)))
    for j in LANES:                                  # diagnostic only: score without the rule's own simulator
        oth = [s for s in LANES if s != j]
        tab[j]['score_excl_own_sim'] = 0.5 * float(np.mean([tab[j]['on_by_sim'][s] for s in oth])) + \
            0.5 * float(np.mean([tab[j]['off_by_sim'][s] for s in oth]))
    best = max(tab[j]['score'] for j in LANES)
    tied = [j for j in LANES if tab[j]['score'] >= best - TIE]
    prim = max(tied, key=lambda j: (tab[j]['worst_cell'], tab[j]['score']))
    return tab, tied, prim


def ref_score(cells, key):
    on = [cells[(s, True)]['ref'][key]['cagr_med'] for s in LANES]
    off = [cells[(s, False)]['ref'][key]['cagr_med'] for s in LANES]
    return dict(on_mean=float(np.mean(on)), off_mean=float(np.mean(off)), score=0.5 * np.mean(on) + 0.5 * np.mean(off),
                worst_cell=float(min(on + off)))


def main():
    jobs = 3
    if '--jobs' in sys.argv: jobs = int(sys.argv[sys.argv.index('--jobs') + 1])
    os.makedirs(WORK, exist_ok=True)
    files = [os.path.join(ROOT, 'design', L, f) for L in LANES for f in ('sim.py', 'rule.py')] + \
            [os.path.join(ROOT, 'common', 'exec_engine.py')]
    h_before = {f: sha(f) for f in files}
    t0 = time.time()
    tasks = [(s, m) for s in LANES for m in (True, False)]
    if jobs > 1:
        import multiprocessing as mp
        with mp.get_context('fork').Pool(jobs) as pool:
            res = pool.map(cell, tasks, chunksize=1)
    else:
        res = [cell(a) for a in tasks]
    cells = {(c['simulator'], c['mechanism'] == 'on'): c for c in res}
    tab, tied, prim = score(cells)
    print('scores', json.dumps(tab, indent=0), 'tied', tied, 'primary', prim, flush=True)
    rt = [(s, m, prim) for s in LANES for m in (True, False)]
    if jobs > 1:
        with mp.get_context('fork').Pool(jobs) as pool:
            rob = pool.map(robust, rt, chunksize=1)
    else:
        rob = [robust(a) for a in rt]
    rows = {}
    for k in ('base', 'delay3', 'delay5', 'cost0.006'):
        on = [x[k]['cagr_med'] for x in rob if x['mechanism'] == 'on']
        off = [x[k]['cagr_med'] for x in rob if x['mechanism'] == 'off']
        rows[k] = dict(on_mean=float(np.mean(on)), off_mean=float(np.mean(off)),
                       score=0.5 * float(np.mean(on)) + 0.5 * float(np.mean(off)), worst_cell=float(min(on + off)))
    # paired path bootstrap of the score (paths resampled within each cell, same indices for all rules)
    g = np.random.default_rng(12345)
    arr = {(s, m): np.load(os.path.join(WORK, f'cagr_main_{s}_{"on" if m else "off"}.npz')) for s, m in tasks}
    bs = {j: np.zeros(NBOOT) for j in LANES}
    for b in range(NBOOT):
        acc = {j: 0.0 for j in LANES}
        for (s, m), a in arr.items():
            ix = g.integers(0, P, P)
            for j in LANES: acc[j] += np.median(a[j][ix]) / 6.0
        for j in LANES: bs[j][b] = acc[j]
    win = {j: float(np.mean([max(LANES, key=lambda q: bs[q][b]) == j for b in range(NBOOT)])) for j in LANES}
    boot = dict(n_boot=NBOOT, score_ci90={j: [float(np.percentile(bs[j], 5)), float(np.percentile(bs[j], 95))]
                                          for j in LANES},
                share_of_resamples_won=win,
                primary_minus_others_ci90={j: [float(np.percentile(bs[prim] - bs[j], 5)),
                                               float(np.percentile(bs[prim] - bs[j], 95))] for j in LANES if j != prim})
    # stability replicate on other fresh seeds (reported only; the choice above is final)
    rtasks = [(s, m, REP_SEEDS[s], 'rep') for s in LANES for m in (True, False)]
    if jobs > 1:
        with mp.get_context('fork').Pool(jobs) as pool:
            rres = pool.map(cell, rtasks, chunksize=1)
    else:
        rres = [cell(a) for a in rtasks]
    rcells = {(c['simulator'], c['mechanism'] == 'on'): c for c in rres}
    rtab, rtied, rprim = score(rcells)
    replicate = dict(seeds=REP_SEEDS, scores=rtab, tied_within_0p003=rtied, winner=rprim,
                     hold1x=ref_score(rcells, 'hold1x'), const0p5=ref_score(rcells, 'const0.5'))
    h_after = {f: sha(f) for f in files}
    out = dict(
        generated=time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime()), P=P, T=T, engine_defaults=dict(delay=2, cost=0.003),
        seeds={f'sim_{s}': {'on': SEEDS[s], 'off': SEEDS[s]} for s in LANES},
        seed_note='simulator L1 seed 20000, L2 seed 20001, L3 seed 20002; ON and OFF of a simulator use the same seed '
                  '(same parameter draw, as each lane defines its OFF world); all rows of a cell use the same paths',
        nan_convention='NaN engine CAGR counted as -1 (and MDD -1)', tie_rule=f'within {TIE}: higher worst cell wins',
        excluded_lanes=[], audit_verdicts={L: 'PASS' for L in LANES},
        cells=[cells[(s, m)] for s in LANES for m in (True, False)],
        scores=tab, ref_scores={k: ref_score(cells, k) for k in cells[('L1', True)]['ref']},
        tied_within_0p003=tied, primary=prim,
        primary_robustness=dict(cells=rob, summary=rows), bootstrap=boot, stability_replicate=replicate,
        sha256_before=h_before, sha256_after=h_after, lane_files_unchanged=h_before == h_after,
        runtime_s=round(time.time() - t0, 1))
    json.dump(out, open(os.path.join(OUT, 'tournament.json'), 'w'), indent=1, default=float)
    print('primary', prim, 'robustness', json.dumps(rows), 'unchanged', h_before == h_after, flush=True)


if __name__ == '__main__':
    main()
