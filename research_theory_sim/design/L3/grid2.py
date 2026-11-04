"""Stage-2/3 evaluation of explicit variant lists on a given design seed. Every variant is logged (counts toward N)."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L3')
import design_lib as dl, rules_lib as rl
tag, seed, P = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
variants = json.loads(open(sys.argv[4]).read())
OUT = f'/mnt/project-files/research/theory_sim/design/L3/runs_{tag}.jsonl'
W = {m: dl.get(seed, m, P) for m in (True, False)}
C = {m: dl.close_from(W[m][0]) for m in W}
FN = dict(kz=rl.fam_kz, kelly=rl.fam_kelly, cusum=rl.fam_cusum, latch=rl.fam_latch, vt=rl.fam_vt, dd=rl.fam_dd)
with open(OUT, 'a') as fo:
    for g in variants:
        g = dict(g); fam = g.pop('fam')
        row = dict(fam=fam, seed=seed, P=P, **g)
        for m in (True, False):
            B = FN[fam](C[m], W[m][1], **g)
            s = dl.evaluate(W[m][0], W[m][1], B)
            k = 'on' if m else 'off'
            row[k] = round(s['cagr_med'], 5); row[k + '_p10'] = round(s['cagr_p10'], 5)
            row[k + '_dd80'] = round(s['p_dd80'], 4); row[k + '_tpy'] = round(s['trades_per_year_med'], 2)
            row[k + '_lev'] = round(s['avg_level_med'], 3)
        row['J'] = round(0.5 * row['on'] + 0.5 * row['off'], 5)
        fo.write(json.dumps(row) + '\n'); fo.flush()
        print(row, flush=True)
