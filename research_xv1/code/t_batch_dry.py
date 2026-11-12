"""<= 2014 only: mechanics of batch registration, of the voiding rules (prefix, level-scale, instrument check, output rules,
errors, T0), of the family-wise test and of the guards (source gate, helper hashes, ledger chain, batch numbering, family
rule, hand-written ledger lines, frozen constants), with dummy candidates. v7: also the batch order, the refusals at
registration (empty batch, T0, input name), the frozen configuration object, the ledger copy and its repair, a cut partial
file and a machine out of memory. The calendar ends 2014-12-31 (so the design
account has no removed rows) and the ledger goes to a scratch folder. Nothing here is a research result."""
import sys, os, json, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xv1
# 0 real world: a changed registered constant is refused; without registration no real calendar after 2014 is built
xv1.SEALED = (4, 6)
try: xv1.View(xv1.frame(xv1.OLD_END)); print('0 ERROR: a changed sealing constant was accepted')
except PermissionError as e: print('0 real world, SEALED changed: refused (%s)' % e)
xv1.SEALED = (10, 12)
if not os.path.exists(xv1.REG_OUT + 'HASHES.json'):
    try: xv1.frame(xv1.CAL_END); print('0 ERROR: a real calendar after 2014 was built before registration')
    except PermissionError as e: print('0 real world, calendar to %s before registration: refused' % xv1.CAL_END)
# v6 real-world guards (<= 2014 calendar only)
from std import beng
OK0 = []
def ref0(nm, f):
    try: f(); print('0 ERROR: %s was allowed' % nm); OK0.append(False)
    except PermissionError as e: print('0 real world, %-40s refused (%s)' % (nm, str(e)[:70])); OK0.append(True)
keep = beng.F1['tax']; beng.F1['tax'] = 0.0; ref0('engine term changed (tax 0)', lambda: xv1.View(xv1.frame(xv1.OLD_END))); beng.F1['tax'] = keep
v0 = xv1.View(xv1.frame(xv1.OLD_END))
ref0('shadow level read outside candidate code', lambda: v0.ref_target)
ref0('calendar after 2014 outside an entry point', lambda: xv1.frame(xv1.A_END))
ref0('registered folder written by hand', lambda: xv1.ledger(dict(kind='g1', cfg='0' * 64)))
ref0('ledger line about no configuration', lambda: xv1.ledger(dict(kind='g1')))
seen = []
def peek(v):                                                     # a function run as candidate code (no gate): numpy's global slots are reset
    seen.append(np.geterrcall()); seen.append(np.geterr()['under']); return xv1.ref(v)
np.seterrcall(lambda *a: None); np.seterr(under='raise'); xv1._call(peek, v0); np.seterrcall(None); np.seterr(under='ignore')
print('0 numpy error callback / state seen by candidate code:', seen, '(expect [None, \'ignore\'])'); OK0.append(seen == [None, 'ignore'])
def outputs(o):
    def mk(v):
        m = xv1.ref(v); m.update(o); return m
    return mk
for nm, o in (('a string as order step', dict(fstep='0.012345')), ('None as order step', dict(fstep=None)), ('a dict subclass', None)):
    mk = outputs(o) if o is not None else (lambda v: type('D', (dict,), {})(xv1.ref(v)))
    try: xv1._call(mk, v0); print('0 ERROR: %s accepted' % nm); OK0.append(False)
    except xv1.Void as e: print('0 output %-28s VOID (%s)' % (nm, e)); OK0.append(True)
    except Exception as e: print('0 ERROR: %s raised %s outside Void' % (nm, type(e).__name__)); OK0.append(False)
print('0 REAL-WORLD GUARDS', 'OK' if all(OK0) else 'FAIL')
import t_world
t_world.old(); tmp = t_world.scratch(sys.argv[1]); xv1.DESIGN = (1, 3, 5, 7, 9)
try: xv1.frame('2021-12-31'); print('0 ERROR: test world built a calendar after 2014')
except PermissionError as e: print('0 test world, calendar after 2014: refused')
F = os.path.join(os.path.dirname(os.path.abspath(__file__)), 't_cand_dummy.py'); X = xv1.frame(); i0 = len(X) - xv1.View(X).T
day = lambda row: str(X.index[i0 + row].date())
cfgs = [xv1.Config('noise', 'noise%d' % i, F, 'noise_cut', dict(seed=i, share=0.05)) for i in range(6)] + \
       [xv1.Config('leak', 'leak3', F, 'leak', dict(look=3)), xv1.Config('jitter', 'jitter_leak', F, 'jitter_leak'), xv1.Config('chips', 'chips10', F, 'chips_sleeve', dict(w=0.1), names=('chips',)),
        xv1.Config('state', 'stateful', F, 'stateful'), xv1.Config('era', 'era', F, 'era'), xv1.Config('invent', 'invent', F, 'invent'),
        xv1.Config('brake', 'own_brake', F, 'own_brake'), xv1.Config('write', 'write_input', F, 'write_input'),
        xv1.Config('swap', 'swap_input', F, 'swap_input'), xv1.Config('crash', 'crash', F, 'crash'),
        xv1.Config('late', 'late_ok', F, 'late', dict(hundreds=19), t0=day(1900)),
        xv1.Config('late', 'late_t0_wrong', F, 'late', dict(hundreds=19), t0=day(2000)),
        xv1.Config('late', 'late_t0_far', F, 'late', dict(hundreds=30), t0=day(3000)),
        xv1.Config('listmem', 'list_mem', F, 'list_mem', dict(mem=[]))]
t_ = time.time(); k, sha = xv1.register_batch(cfgs); print('1 registered batch', k, sha[:12])
try: xv1.register_batch(cfgs); print('1 ERROR: second registration accepted')
except PermissionError as e: print('1 second registration refused:', e)
out = xv1.run_batch(1); print('1 batch scored in %.0f s' % (time.time() - t_))
for h, o in out['results'].items():
    if 'void' in o: print('  %-14s VOID (%s)' % (o['name'], o['void']))
    else: print('  %-14s d %+6.2f d* %+6.2f te %5.1f t63 %+5.2f p_family %.3f active blocks %d n %d span %d harm %s g1 %s type %s advance %s g0 %s | extra w %.3f | skew %+.2f ac1 %+.2f' % (
        o['name'], 100 * o['d'], 100 * o['d_star'], 100 * o['te'], o['t63'], o['p_family'], o['active_blocks'], o['n'], o['n_span'], o['harm'],
        ''.join('Y' if x else 'n' for x in o['g1'].values()), o['kind'], o['advance'], o['g0'], o['extra_weight_mean'], o['skew63'], o['ac1_63']))
exp = dict(leak3='prefix test', jitter_leak='prefix test', stateful='prefix test', era='level-scale test', invent='instrument check', own_brake='output rule', write_input='error in candidate code',
           swap_input='changed or replaced', crash='error in candidate code', late_t0_wrong='differs from the reference before T0', late_t0_far='T0 later',
           list_mem='prefix test')
R = {o['name']: o for o in out['results'].values()}
print('1 EXPECTED VOIDS', 'OK' if all(nm in R and wh in R[nm].get('void', '') for nm, wh in exp.items()) and sum('void' in o for o in R.values()) == len(exp) else 'FAIL')
# 1b (v7) a look-ahead that only HOLDS the level on two rows makes no event row: the sampled test can miss it, the every-row test cannot
ch = xv1.Config('hold', 'hold_leak', F, 'hold_leak', dict(thr=-0.045)); ph = xv1._prepare(ch.fresh(), ())
sm = [xv1.prefix_test(None, (), n_rand=60, seed=sd, fresh=ch.fresh, pre=ph)['result'] for sd in range(2)]
ev = xv1.prefix_test(None, (), n_rand=0, seed=0, noise=False, step=1, fresh=ch.fresh, pre=ph)
print('1b hold look-ahead on two rows: sampled test, seeds 0-1: %s | every-row test: %s (%d cuts, %d failed)' % (sm, ev['result'], ev['cuts'], ev['failed_cuts']))
OK1B = ev['result'] == 'FAIL' and ev['failed_cuts'] == 2
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
N = lambda i, fam='noise', **kw: xv1.Config(fam, 'noise%d' % i, F, 'noise_cut', dict(seed=i, share=0.05), **kw)
ok.append(refused('a configuration of batch 1 in a later batch', lambda: xv1.register_batch(cfgs[:1])))
ok.append(refused('one function under a second family label', lambda: xv1.register_batch([N(10, 'other')])))
VE = (ValueError,)                                               # v7: slips that would stop a batch run for good are refused before the batch file is written
ok += [refused('empty batch', lambda: xv1.register_batch([]), VE), refused('T0 that is not a date', lambda: xv1.register_batch([N(13, t0='2013-02-30')]), VE),
       refused('T0 that is not ISO text', lambda: xv1.register_batch([N(13, t0='1 Jan 2013')]), VE),
       refused('an input name that cannot be read', lambda: xv1.register_batch([N(13, names=('no_such_input',))]), VE)]
k2, _ = xv1.register_batch([N(9)]); print('3 next batch number', k2, '(level %.4f): the refusals above spent no number' % (0.05 / 2 ** k2))
ok.append(k2 == 2 and not os.path.exists(xv1.OUT + 'BATCH_3.json'))
ok.append(refused('a third batch while batch 2 is not scored', lambda: xv1.register_batch([N(10)])))
o2 = xv1.run_batch(2); print('  batch 2 scored at level %.4f' % o2['alpha']); ok.append(o2['alpha'] == 0.0125)
# source gate
G = {'import_os': 'import os\nimport xv1\ndef f(v): return xv1.ref(v)\n', 'from_import': 'from xv1 import ref\ndef f(v): return ref(v)\n',
     'inner_import': 'import xv1\ndef f(v):\n    import json\n    return xv1.ref(v)\n', 'evaluator': 'import xv1\ndef f(v): return xv1._eng(v)\n',
     'other_xv1': 'import xv1\ndef f(v): return xv1.frame()\n', 'row_index': 'import xv1\ndef f(v): return v.c.ii\n',
     'open_file': 'import xv1\ndef f(v):\n    open("x")\n    return xv1.ref(v)\n', 'getattr': 'import xv1\ndef f(v): return getattr(v, "c")\n',
     'random': 'import numpy as np\nimport xv1\ndef f(v): return np.random.default_rng(0)\n', 'setflags': 'import xv1\ndef f(v):\n    v.c.r.setflags(write=True)\n    return xv1.ref(v)\n',
     'module_attr': 'import numpy as np\nimport xv1\ndef f(v):\n    np.load = None\n    return xv1.ref(v)\n', 'global': 'import xv1\nS = 0\ndef f(v):\n    global S\n    return xv1.ref(v)\n',
     # v6: routes that passed the v5 gate (verification 2026-11-12)
     'np_chain': 'import numpy as np\nimport xv1\ndef f(v):\n    b = np.ma.core.builtins\n    return xv1.ref(v)\n',
     'np_ctypes': 'import numpy as np\nimport xv1\ndef f(v):\n    np.ctypeslib.load_library("x", ".")\n    return xv1.ref(v)\n',
     'np_fromregex': 'import numpy as np\nimport xv1\ndef f(v):\n    np.fromregex("x", "y", float)\n    return xv1.ref(v)\n',
     'np_seterrcall': 'import numpy as np\nimport xv1\ndef f(v):\n    np.seterrcall(None)\n    return xv1.ref(v)\n',
     'errstate_call': 'import numpy as np\nimport xv1\ndef f(v):\n    with np.errstate(call=None):\n        return xv1.ref(v)\n',
     'format_walk': 'import xv1\ndef f(v):\n    s = "{0.x}".format(xv1.ref)\n    return xv1.ref(v)\n',
     'gen_frame': 'import xv1\ndef f(v):\n    g = (x for x in [1])\n    b = g.gi_frame.f_builtins\n    return xv1.ref(v)\n',
     'func_attr_store': 'import xv1\ndef f(v):\n    r = xv1.ref\n    r.stash = 1\n    return xv1.ref(v)\n',
     'module_value': 'import numpy as np\nimport xv1\ndef f(v):\n    m = np\n    return xv1.ref(v)\n',
     'class_def': 'import xv1\nclass K:\n    pass\ndef f(v): return xv1.ref(v)\n',
     'dunder': 'import xv1\ndef f(v):\n    k = v.c.sma.__func__\n    return xv1.ref(v)\n',
     'ref_attr': 'import xv1\ndef f(v):\n    k = xv1.ref.x\n    return xv1.ref(v)\n',
     'helper_np': 'import xv1\nimport hlpnp\ndef f(v):\n    k = hlpnp.np.load\n    return xv1.ref(v)\n',
     'clean': 'import numpy as np\nimport xv1\ndef f(v):\n    o = xv1.ref(v); o["bfn"] = xv1.std.ident; o["bp"] = np.zeros(1); o["fstep"] = 0.5\n    return o\n'}
open(tmp + 'hlpnp.py', 'w').write('import numpy as np\nW = 0.1\n')
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
# v7: a configuration object is fixed when it is made
hc = c0.hash; pc = c0.params; pc['share'] = 0.9
try: c0.func = 'leak'; frozen = False
except AttributeError: frozen = True
lm = cfgs[-1]; xv1._call(lm.fresh(), xv1.View(X)); kept = lm.params == dict(mem=[])
print('5b configuration object: attribute assignment refused %s | a changed copy of the parameters reaches neither the hash nor a call %s | list parameter after a call unchanged %s' % (
    frozen, c0.hash == hc and c0.params['share'] == 0.05, kept)); ok += [frozen, c0.hash == hc and c0.params['share'] == 0.05, kept]
# tamper: change a parameter after registration
b1 = open(xv1.OUT + 'BATCH_1.json').read()
b = json.loads(b1); b[0]['params']['share'] = 0.06; json.dump(b, open(xv1.OUT + 'BATCH_1.json', 'w'), indent=1, sort_keys=True)
ok.append(refused('tampered batch file', lambda: xv1.load_batch(1)))
open(xv1.OUT + 'BATCH_1.json', 'w').write(b1); ok.append(len(xv1.load_batch(1)[0]) == len(cfgs))
# ledger chain
L = xv1.read_ledger(); print('6 ledger lines', len(L), 'kinds', sorted(set(e['kind'] for e in L)))
raw = open(xv1.OUT + 'LEDGER.jsonl').read().splitlines(keepends=True)
open(xv1.OUT + 'LEDGER.jsonl', 'w').write(''.join(raw[:3] + raw[4:])); ok.append(refused('ledger with a line removed', xv1.read_ledger))
open(xv1.OUT + 'LEDGER.jsonl', 'w').write(''.join(raw[:3] + [raw[3].replace('design', 'DESIGN')] + raw[4:])); ok.append(refused('ledger with a line edited', xv1.read_ledger))
open(xv1.OUT + 'LEDGER.jsonl', 'w').write(''.join(raw)); print('  restored ledger reads:', len(xv1.read_ledger()) == len(L))
existed = os.path.exists(xv1.REG_OUT); xv1.OUT, keep_out = xv1.REG_OUT, xv1.OUT; ok.append(refused('test world writing into the registered folder', lambda: xv1.ledger(dict(kind='g1')))); xv1.OUT = keep_out
ok.append(existed or not os.path.exists(xv1.REG_OUT))
# 6b (v7) the copy of the ledger (in the real world: research_xv1/registry/, committed after every step) and the repair of a cut line
xv1.MIRROR = tmp + 'mirror/'; xv1.ledger(dict(kind='note', text='copy starts')); raw = open(xv1.OUT + 'LEDGER.jsonl', 'rb').read()
same = open(xv1.MIRROR + 'LEDGER.jsonl', 'rb').read() == raw; lines = raw.splitlines(keepends=True)
open(xv1.OUT + 'LEDGER.jsonl', 'wb').write(b''.join(lines[:-1])); ok.append(refused('ledger with its last line removed (chain intact)', xv1.read_ledger))
os.remove(xv1.OUT + 'LEDGER.jsonl'); ok.append(refused('ledger file removed', xv1.read_ledger))
open(xv1.OUT + 'LEDGER.jsonl', 'wb').write(raw + b'{"kind": "g1", "cfg"'); ok.append(refused('ledger with a cut last line', xv1.read_ledger))
ok.append(refused('append to a ledger with a cut last line', lambda: xv1.ledger(dict(kind='note'))))
xv1.repair_ledger(); L2 = xv1.read_ledger()
print('6b copy equals the ledger after a line: %s | after repair_ledger: %d lines, last kind %s, copy equal: %s' % (
    same, len(L2), L2[-1]['kind'], open(xv1.MIRROR + 'LEDGER.jsonl', 'rb').read() == open(xv1.OUT + 'LEDGER.jsonl', 'rb').read()))
ok += [same, len(L2) == len(lines) + 1 and L2[-1]['kind'] == 'repair' and L2[-1]['dropped_bytes'] == 20, refused('repair of a whole ledger', xv1.repair_ledger)]
xv1.MIRROR = None
# 7 (v7) the every-row test inside run_batch: the sampled test is made to pass and the G1 size is lowered in this test world
real_pt = xv1.prefix_test; seen7 = []
def spy(*a, **k):
    seen7.append(k.get('step', 5)); return dict(result='PASS') if k.get('step', 5) != 1 else real_pt(*a, **k)
xv1.prefix_test = spy; keepd = xv1.D_MIN_G1; xv1.D_MIN_G1 = -9.9
k3, _ = xv1.register_batch([ch]); o3 = list(xv1.run_batch(k3)['results'].values())[0]
xv1.prefix_test = real_pt; xv1.D_MIN_G1 = keepd
print('7 every-row test inside the batch run: steps of its prefix tests', seen7, '| outcome:', o3.get('void')); ok.append(o3.get('void') == 'prefix test: every row' and seen7 == [5, 1])
# 8 (v7) a machine out of memory is not the candidate's rule break: the run stops and is logged; the second time on the same configuration it is
# void. A partial result file that was cut while it was written counts as missing. (The sampled prefix test is skipped here to save time.)
xv1.prefix_test = lambda *a, **k: dict(result='PASS')
cm = [N(11), xv1.Config('oom', 'oom', F, 'oom')]; k4, _ = xv1.register_batch(cm)
try: xv1.run_batch(k4); first = 'not stopped'
except MemoryError: first = 'stopped'
Lm = xv1.read_ledger(); pf = xv1.OUT + 'results/partial_%d/%s.json' % (k4, cm[0].hash); whole = open(pf).read()
open(pf, 'w').write(whole[:len(whole) // 2])                    # the finished configuration's partial file, cut
o4 = xv1.run_batch(k4)['results']; xv1.prefix_test = real_pt
print('8 out of memory: first run %s, ledger line %s, results file written %s | second run: %s; the configuration with the cut partial file was scored again: %s' % (
    first, Lm[-1]['kind'], os.path.exists(xv1.OUT + 'results/batch_%d.json' % k4), o4[cm[1].hash].get('void'), 'd' in o4[cm[0].hash] and json.load(open(pf))['o']['d'] == o4[cm[0].hash]['d']))
ok += [first == 'stopped', Lm[-1]['kind'] == 'out-of-memory' and Lm[-1]['cfg'] == cm[1].hash, 'out of memory twice' in o4[cm[1].hash].get('void', ''), 'd' in o4[cm[0].hash]]
print('GUARDS', 'OK' if all(ok) and all(OK0) and OK1B else 'FAIL')
