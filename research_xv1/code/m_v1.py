"""First XV1 measurement (PREREG section 3): v1, 1x hold and 3x hold on every DESIGN and WEAK block. No candidate, no pass / fail.

Run only after (1) the structure is registered, (2) the evaluator and the sealing passed the independent verification and
(3) m_checks.py passed (its ledger line is required). The script refuses to score if the registered hashes do not match or if
v1 fails the prefix test. Scalars only, from the design account (one continuous account on the calendar without the sealed
rows); nothing is produced for the sealed blocks 10 and 12."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xv1
_S = xv1.scope(); _S.__enter__()                       # an evaluator script: it may read the registered calendar

reg = json.load(open(xv1.OUT + 'HASHES.json'))
pre = xv1._prepare(xv1.ref, (), xv1.OLD_END)                # load the whole chain before the hashes are compared
xv1._check_env()
if not xv1._checks_passed(): print('m_checks.py has not passed under the registered hashes'); sys.exit(2)
pt = xv1.prefix_test(xv1.ref, n_rand=200, seed=int(reg['prereg_sha256'][:8], 16), step=1)   # v7: a cut after every account row
pt = dict(result=pt['result'])                             # no count is kept: the number of cuts depends on v1's signal on sealed rows
print('prefix test of v1 on the full calendar:', pt)
if pt['result'] != 'PASS': sys.exit(3)

xv1.ledger(dict(kind='reference_table', cfg='REF', set='design+weak'))
T = xv1.reference_table(); T['model_check'] = xv1.model_check(); T['prefix_test_v1'] = pt
pc = lambda x: '%+7.2f' % (100 * x)
print('block  years   kind account      n    v1     1x     3x   | mean level  changes  in-block drawdown | level shares')
for r in T['blocks']:
    print('b%-4d %s  %s  %-10s %4d %s %s %s |   %.2f      %3d       %6.1f%%        | %s' % (
        r['b'], r['years'], r['kind'], r['account'], r['n'], pc(r['v1']), pc(r['hold1']), pc(r['hold3']), r['mean_level'], r['changes'],
        100 * r['dd_inblock'], r['share']))
for nm, s in T['sets'].items():
    a, b = s['D_A_v1_minus_3x'], s['D_B_v1_minus_1x']
    print('%-16s n=%5d  v1 %s  1x %s  3x %s | v1-3x %s [%s, %s] | v1-1x %s [%s, %s]' % (
        nm, s['n'], pc(s['v1']), pc(s['hold1']), pc(s['hold3']), pc(a['d']), pc(a['ci90'][0]), pc(a['ci90'][1]), pc(b['d']), pc(b['ci90'][0]), pc(b['ci90'][1])))
    a, b = s['tax0']['D_A_v1_minus_3x'], s['tax0']['D_B_v1_minus_1x']
    print('%-16s tax 0:   v1 %s  1x %s  3x %s | v1-3x %s [%s, %s] | v1-1x %s [%s, %s]' % (
        '', pc(s['tax0']['v1']), pc(s['tax0']['hold1']), pc(s['tax0']['hold3']), pc(a['d']), pc(a['ci90'][0]), pc(a['ci90'][1]), pc(b['d']), pc(b['ci90'][0]), pc(b['ci90'][1])))
# the reading fixed in section 3: a sentence only when the whole 90% interval is on one side of 0 with tax 0.22 AND with tax 0
P = T['sets']['design_post2014']; WORDS = dict(
    D_A_v1_minus_3x=("v1's de-risking cost growth in the post-2014 design blocks", "v1's de-risking added growth in the post-2014 design blocks"),
    D_B_v1_minus_1x=('the v1 package grew less than the 1x index hold in the post-2014 design blocks', 'the v1 package grew more than the 1x index hold in the post-2014 design blocks'))
T['reading'] = {}
for k, (neg, pos) in WORDS.items():
    a, b = P[k]['ci90'], P['tax0'][k]['ci90']
    T['reading'][k] = neg if (a[1] < 0 and b[1] < 0) else (pos if (a[0] > 0 and b[0] > 0) else 'not distinguishable from zero on 5.2 years')
    print('READING %s: %s' % (k, T['reading'][k]))
print('model check (actual TQQQ minus modelled 3x, annualised log, scored rows):')
for r in T['model_check']: print('  ', r)
os.makedirs(xv1.OUT + 'results', exist_ok=True)
json.dump(T, open(xv1.OUT + 'results/v1_blocks.json', 'w'), indent=1)
