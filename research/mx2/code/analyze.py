"""MX2 analysis: walk-forward selection from R1 (+R2), OOS stream (linear model), exact MS1-engine re-check, placebo rank."""
import sys, os, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/mx2/code'); import lib
R = lib.R
parts = [p for p in ('R1', 'R2') if os.path.exists(R + 'results/raw_%s.bin' % p)]
loaded = [lib.read_out(R + 'results/raw_%s.bin' % p) for p in parts]
S, C, _ = loaded[0]; merge = [(s, c) for s, c, _ in loaded[1:]]
evals = int(sum(x[2] for x in loaded))
out = dict(parts=parts, evals=evals, procs={})
for pname, st, topn in (('main_t_top20', 0, 20), ('t_top1', 0, 1), ('sum_top20', 1, 20)):
    sel = lib.select(S, C, st, topn, merge or None)
    oos = lib.wf_oos(sel, lib.D0, lib.CB0)
    yrs = list(range(1966, 2015))
    # training (selected) value of the same ensemble for contrast: mean training score of chosen rules
    out['procs'][pname] = dict(oos_year=dict(zip(yrs, oos.round(5).tolist())), oos_sum=float(oos.sum()),
                               oos_spx_66_85=float(oos[:20].sum()), oos_ndx_86_14=float(oos[20:].sum()),
                               ndx_pos_years=int((oos[20:] > 0).sum()), ndx_neg_years=int((oos[20:] < 0).sum()),
                               last_sel=[lib.rule_name(cd) for _, cd in sel[-1][:10]],
                               act_mix={a: int(sum((cd >> 62) == i for lst in sel for _, cd in lst)) for i, a in enumerate(['CUT1', 'CUT0', 'ADD3', 'ADD1'])})
    if pname == 'main_t_top20':
        main_sel = {1966 + c: [cd for _, cd in lst] for c, lst in enumerate(sel)}
json.dump(main_sel, open(R + 'results/main_sel_%s.json' % '_'.join(parts), 'w'))
if os.path.exists(R + 'results/sub_placebo.json') and os.path.exists(R + 'results/sub_real.json'):
    pl = json.load(open(R + 'results/sub_placebo.json')); real = json.load(open(R + 'results/sub_real.json'))
    rs = float(np.sum(real['oos'])); ps = np.array([p['oos_sum'] for p in pl])
    out['P1_subset'] = dict(real_oos_sum=rs, real_ndx=float(np.sum(real['oos'][20:])), n_placebo=len(ps),
                            placebo_median=float(np.median(ps)), placebo_p90=float(np.percentile(ps, 90)),
                            p=float((1 + np.sum(ps >= rs)) / (1 + len(ps))))
if '--exact' in sys.argv:
    import exact
    out['exact'] = exact.evaluate(main_sel, '_'.join(parts))
json.dump(out, open(R + 'results/analysis_%s.json' % '_'.join(parts), 'w'), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != 'procs'}, indent=1))
for k, v in out['procs'].items(): print(k, 'oos_sum %.3f spx %.3f ndx %.3f +yrs %d -yrs %d' % (v['oos_sum'], v['oos_spx_66_85'], v['oos_ndx_86_14'], v['ndx_pos_years'], v['ndx_neg_years']), v['act_mix'])
