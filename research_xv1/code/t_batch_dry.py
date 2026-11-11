"""<= 2014 only: mechanics of batch registration, of the voiding rules (prefix, level-scale, instrument check, output rules,
errors, T0), of the family-wise test and of the guards (source gate, helper hashes, ledger chain, batch numbering, family
rule, hand-written ledger lines, frozen constants), with dummy candidates. The calendar ends 2014-12-31 (so the design
account has no removed rows) and the ledger goes to a scratch folder. Nothing here is a research result."""
import sys, os, json, time, numpy as np
sys.path.insert(0, '/home/user/-/research_xv1/code')
import xv1
# 0 real world: a changed registered constant is refused; without registration no real calendar after 2014 is built
xv1.SEALED = (4, 6)
try: xv1.View(xv1.frame(xv1.OLD_END)); print('0 ERROR: a changed sealing constant was accepted')
except PermissionError as e: print('0 real world, SEALED changed: refused (%s)' % e)
xv1.SEALED = (10, 12)
if not os.path.exists(xv1.REG_OUT + 'HASHES.json'):
    try: xv1.frame(xv1.CAL_END); print('0 ERROR: a real calendar after 2014 was built before registration')
    except PermissionError as e: print('0 real world, calendar to %s before registration: refused' % xv1.CAL_END)
import t_world
t_world.old(); tmp = t_world.scratch(sys.argv[1]); xv1.DESIGN = (1, 3, 5, 7, 9)
try: xv1.frame('2021-12-31'); print('0 ERROR: test world built a calendar after 2014')
except PermissionError as e: print('0 test world, calendar after 2014: refused')
F = '/home/user/-/research_xv1/code/t_cand_dummy.py'; X = xv1.frame(); i0 = len(X) - xv1.View(X).T
day = lambda row: str(X.index[i0 + row].date())
cfgs = [xv1.Config('noise', 'noise%d' % i, F, 'noise_cut', dict(seed=i, share=0.05)) for i in range(6)] + \
       [xv1.Config('leak', 'leak3', F, 'leak', dict(look=3)), xv1.Config('chips', 'chips10', F, 'chips_sleeve', dict(w=0.1), names=('chips',)),
        xv1.Config('state', 'stateful', F, 'stateful'), xv1.Config('era', 'era', F, 'era'), xv1.Config('invent', 'invent', F, 'invent'),
        xv1.Config('brake', 'own_brake', F, 'own_brake'), xv1.Config('write', 'write_input', F, 'write_input'),
        xv1.Config('swap', 'swap_input', F, 'swap_input'), xv1.Config('crash', 'crash', F, 'crash'),
        xv1.Config('late', 'late_ok', F, 'late', dict(row=1900), t0=day(1900)),
        xv1.Config('late', 'late_t0_wrong', F, 'late', dict(row=1900), t0=day(2000)),
        xv1.Config('late', 'late_t0_far', F, 'late', dict(row=3000), t0=day(3000))]
t_ = time.time(); k, sha = xv1.register_batch(cfgs); print('1 registered batch', k, sha[:12])
try: xv1.register_batch(cfgs); print('1 ERROR: second registration accepted')
except PermissionError as e: print('1 second registration refused:', e)
out = xv1.run_batch(1); print('1 batch scored in %.0f s' % (time.time() - t_))
for h, o in out['results'].items():
    if 'void' in o: print('  %-14s VOID (%s)' % (o['name'], o['void']))
    else: print('  %-14s d %+6.2f d* %+6.2f te %5.1f t63 %+5.2f p_family %.3f active blocks %d n %d span %d harm %s g1 %s type %s advance %s g0 %s | extra w %.3f | skew %+.2f ac1 %+.2f' % (
        o['name'], 100 * o['d'], 100 * o['d_star'], 100 * o['te'], o['t63'], o['p_family'], o['active_blocks'], o['n'], o['n_span'], o['harm'],
        ''.join('Y' if x else 'n' for x in o['g1'].values()), o['kind'], o['advance'], o['g0'], o['extra_weight_mean'], o['skew63'], o['ac1_63']))
exp = dict(leak3='prefix test', stateful='prefix test', era='level-scale test', invent='instrument return', own_brake='output rule', write_input='error in candidate code',
           swap_input='changed or replaced', crash='error in candidate code', late_t0_wrong='differs from the reference before T0', late_t0_far='T0 later')
R = {o['name']: o for o in out['results'].values()}
print('1 EXPECTED VOIDS', 'OK' if all(nm in R and wh in R[nm].get('void', '') for nm, wh in exp.items()) and sum('void' in o for o in R.values()) == len(exp) else 'FAIL')
try: xv1.run_batch(1); print('2 ERROR: second scoring accepted')
except PermissionError as e: print('2 second scoring of the batch refused')
c0 = cfgs[0]
def refused(nm, f, kinds=(PermissionError, FileNotFoundError)):
    try: f(); print('  ERROR: %s was allowed' % nm); return False
    except kinds as e: print('  %-44s refused: %s' % (nm, str(e)[:90])); return True
ok = [refused('weak before G1 pass', lambda: xv1.weak_eval(c0)), refused('G3 without passes', lambda: xv1.open_g3(c0)),
      refused('main account outside an opening', lambda: xv1._main_account(xv1.ref)), refused('unregistered batch', lambda: xv1.load_batch(2))]
# a hand-written G1 line has no results file behind it
xv1.ledger(dict(kind='g1', cfg=c0.hash, batch=1, passed=True, advance=True, family='noise'))
ok.append(refused('weak after a hand-written G1 line', lambda: xv1.weak_eval(c0)))
# batch numbering and the family rule
k2, _ = xv1.register_batch([xv1.Config('noise', 'noise9', F, 'noise_cut', dict(seed=9, share=0.05))]); print('3 next batch number', k2, '(level %.4f)' % (0.05 / 2 ** k2))
ok.append(k2 == 2)
ok.append(refused('one function under a second family label', lambda: xv1.register_batch([xv1.Config('other', 'noise10', F, 'noise_cut', dict(seed=10))])))
# source gate
G = {'import_os': 'import os\nimport xv1\ndef f(v): return xv1.ref(v)\n', 'from_import': 'from xv1 import ref\ndef f(v): return ref(v)\n',
     'inner_import': 'import xv1\ndef f(v):\n    import json\n    return xv1.ref(v)\n', 'evaluator': 'import xv1\ndef f(v): return xv1._eng(v)\n',
     'other_xv1': 'import xv1\ndef f(v): return xv1.frame()\n', 'row_index': 'import xv1\ndef f(v): return v.c.ii\n',
     'open_file': 'import xv1\ndef f(v):\n    open("x")\n    return xv1.ref(v)\n', 'getattr': 'import xv1\ndef f(v): return getattr(v, "c")\n',
     'random': 'import numpy as np\nimport xv1\ndef f(v): return np.random.default_rng(0)\n', 'setflags': 'import xv1\ndef f(v):\n    v.c.r.setflags(write=True)\n    return xv1.ref(v)\n',
     'module_attr': 'import numpy as np\nimport xv1\ndef f(v):\n    np.load = None\n    return xv1.ref(v)\n', 'global': 'import xv1\nS = 0\ndef f(v):\n    global S\n    return xv1.ref(v)\n',
     'clean': 'import numpy as np\nimport xv1\ndef f(v):\n    o = xv1.ref(v); o["bfn"] = xv1.std.ident; o["bp"] = np.zeros(1); o["fstep"] = 0.5\n    return o\n'}
bad = []
for nm, src in G.items():
    p = tmp + 'g_' + nm + '.py'; open(p, 'w').write(src); v = xv1.gate(p)
    if (nm == 'clean') != (not v): bad.append(nm)
print('4 source gate: %d planted violations refused, clean file accepted: %s %s' % (len(G) - 1, not bad, bad)); ok.append(not bad)
ok.append(refused('registration of a file that fails the gate', lambda: xv1.register_batch([xv1.Config('g', 'g', tmp + 'g_import_os.py', 'f')])))
# helper files are part of the configuration hash
open(tmp + 'hlp.py', 'w').write('W = 0.1\n'); open(tmp + 'usehelper.py', 'w').write('import xv1\nimport hlp\ndef f(v): return xv1.ref(v)\n')
h1 = xv1.Config('h', 'h', tmp + 'usehelper.py', 'f').hash; open(tmp + 'hlp.py', 'w').write('W = 0.3\n'); h2 = xv1.Config('h', 'h', tmp + 'usehelper.py', 'f').hash
print('5 helper file changed: configuration hash changed:', h1 != h2); ok.append(h1 != h2)
# tamper: change a parameter after registration
b = json.load(open(xv1.OUT + 'BATCH_1.json')); b[0]['params']['share'] = 0.06; json.dump(b, open(xv1.OUT + 'BATCH_1.json', 'w'), indent=1, sort_keys=True)
ok.append(refused('tampered batch file', lambda: xv1.load_batch(1)))
# ledger chain
L = xv1.read_ledger(); print('6 ledger lines', len(L), 'kinds', sorted(set(e['kind'] for e in L)))
raw = open(xv1.OUT + 'LEDGER.jsonl').read().splitlines(keepends=True)
open(xv1.OUT + 'LEDGER.jsonl', 'w').write(''.join(raw[:3] + raw[4:])); ok.append(refused('ledger with a line removed', xv1.read_ledger))
open(xv1.OUT + 'LEDGER.jsonl', 'w').write(''.join(raw[:3] + [raw[3].replace('design', 'DESIGN')] + raw[4:])); ok.append(refused('ledger with a line edited', xv1.read_ledger))
open(xv1.OUT + 'LEDGER.jsonl', 'w').write(''.join(raw)); print('  restored ledger reads:', len(xv1.read_ledger()) == len(L))
print('GUARDS', 'OK' if all(ok) else 'FAIL')
