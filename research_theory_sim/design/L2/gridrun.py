"""Parallel grid evaluation on SELECTION seeds only (1-999). Results logged by the parent to variants_log.jsonl."""
import itertools, json, sys, multiprocessing as mp
import numpy as np, harness as H

SEEDS = (1,); P = 1000


def _job(q):
    o = H.evaluate(H.fam_fn(q), seeds=SEEDS, P=P, log=False)
    return q, o['on']['cagr_med'], o['off']['cagr_med'], o['on']['cagr_p10'], o['on']['p_dd80'], o['on']['trades_per_year_med'], o['on']['avg_level_med']


def run_grid(configs, tag, seeds=(1,), nproc=4):
    global SEEDS
    SEEDS = tuple(seeds)
    for s in SEEDS:
        for m in (True, False): H.world(s, P, m)
    with mp.get_context('fork').Pool(nproc) as pool:
        out = pool.map(_job, configs, chunksize=1)
    rows = []
    for q, on, off, p10, dd, tpy, lev in out:
        H.log_variant(dict(name=tag, prm=q, seeds=list(SEEDS), P=P, on=on, off=off, on_p10=p10, on_dd80=dd, tpy=tpy, lev=lev))
        rows.append(dict(q=q, on=on, off=off, J=0.5 * (on + off), p10=p10, dd80=dd, tpy=tpy, lev=lev))
    rows.sort(key=lambda z: -z['J'])
    return rows


def show(rows, n=15):
    for z in rows[:n]:
        print('J %.4f ON %.4f OFF %.4f p10 %.4f dd80 %.3f tpy %.1f lev %.2f  %s' % (z['J'], z['on'], z['off'], z['p10'], z['dd80'], z['tpy'], z['lev'], json.dumps(z['q'])))
