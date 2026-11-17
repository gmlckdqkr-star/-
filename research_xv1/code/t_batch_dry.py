"""<= 2014 only: mechanics of batch registration, of the voiding rules (prefix, level-scale, instrument check, output rules,
errors, T0), of the family-wise test and of the guards (source gate, helper hashes, ledger chain, batch numbering, family
rule, hand-written ledger lines, frozen constants), with dummy candidates. v7: also the batch order, the refusals at
registration (empty batch, T0, input name), the frozen configuration object, the ledger copy and its repair, a cut partial
file and a machine out of memory. v8: also the gate rules against catching errors and reading per-run values, errors of
candidate code that leave without their text, the same stack room in every call, the fingerprint that ties G2 to the output
tested at G1, the restart flags and a T0 after the last design row. The calendar ends 2014-12-31 (so the design
account has no removed rows) and the ledger goes to a scratch folder. Nothing here is a research result."""
import sys, os, json, time, subprocess, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xv1
assert not sys.flags.hash_randomization, 'run with PYTHONHASHSEED=0'
# v7: with hash randomisation on, the real world refuses (the order of a set would differ between two runs of the same candidate code)
_r = subprocess.run([sys.executable, '-B', '-c', 'import sys; sys.path.insert(0, %r); import xv1\ntry: xv1._guard(); print("ERROR: accepted")\nexcept PermissionError: print("refused")' % os.path.dirname(os.path.abspath(__file__))],
                    env=dict(os.environ, PYTHONHASHSEED='random'), capture_output=True, text=True)
HS = _r.stdout.strip().endswith('refused'); print('0 real world, python started with hash randomisation:', _r.stdout.strip()[-40:] or _r.stderr.strip()[-200:])
_r = subprocess.run([sys.executable, '-B', '-c', 'import sys, numba; sys.path.insert(0, %r)\ntry: import xv1; print("ERROR: accepted")\nexcept ImportError: print("refused")' % os.path.dirname(os.path.abspath(__file__))],
                    env=dict(os.environ, NUMBA_FUNCTION_CACHE_SIZE='128'), capture_output=True, text=True)
HS = HS and _r.stdout.strip().endswith('refused'); print('0 numba imported before xv1 (short function cache):', _r.stdout.strip()[-40:] or _r.stderr.strip()[-200:])
# v8: a real run without the registered numeric environment, or one that may execute compiled files next to the sources, is refused
import tempfile, shutil
_pd, _pe = tempfile.mkdtemp(prefix='xv1_pyc_'), tempfile.mkdtemp(prefix='xv1_pyc_'); os.makedirs(_pd + '/some/folder'); open(_pd + '/some/folder/any.cpython-313.pyc', 'wb').write(b'0')
_E1, _E2 = 'refused: a real run is started with', 'refused: a real run executes the hashed source files'
_noB = {k: v for k, v in os.environ.items() if k != 'PYTHONDONTWRITEBYTECODE'}
for _nm, _env, _fl, _want in (('the registered environment (control)', dict(os.environ), ['-B'], 'accepted'),
                              ('one thread of the linear-algebra library not set', {k: v for k, v in os.environ.items() if k != 'OPENBLAS_NUM_THREADS'}, ['-B'], _E1),
                              ('kernel of the linear-algebra library not set', {k: v for k, v in os.environ.items() if k != 'OPENBLAS_CORETYPE'}, ['-B'], _E1),
                              ('AVX-512 targets of numpy left on', dict(os.environ, NPY_DISABLE_CPU_FEATURES=''), ['-B'], _E1),
                              ('no folder for compiled files set', {k: v for k, v in os.environ.items() if k != 'PYTHONPYCACHEPREFIX'}, ['-B'], _E2),
                              ('a compiled file somewhere in that folder', dict(os.environ, PYTHONPYCACHEPREFIX=_pd), ['-B'], _E2),
                              ('python started without -B (own empty folder)', dict(_noB, PYTHONPYCACHEPREFIX=_pe), [], _E2)):
    _r = subprocess.run([sys.executable] + _fl + ['-c', 'import sys; sys.path.insert(0, %r); import xv1\ntry: xv1._guard(); print("accepted")\nexcept PermissionError as e: print("refused: " + str(e)[:60])' % os.path.dirname(os.path.abspath(__file__))],
                        env=_env, capture_output=True, text=True)
    HS = HS and _r.stdout.strip().split('\n')[-1].startswith(_want); print('0 real world, %s: %s' % (_nm, _r.stdout.strip()[-70:] or _r.stderr.strip()[-200:]))
shutil.rmtree(_pd); shutil.rmtree(_pe)
import numba.core.dispatcher as _nbd
HS = HS and _nbd.Dispatcher._recent.maxlen >= 10 ** 6; print('0 function cache length', _nbd.Dispatcher._recent.maxlen)
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
if os.path.exists(xv1.REG_OUT + 'LEDGER.jsonl') or xv1._mirror_bytes():   # v7: a self-test never tries a write once the structure is registered
    print('0 real world, registered folder written by hand: not tried (the structure is registered)')
else: ref0('registered folder written by hand', lambda: xv1.ledger(dict(kind='g1', cfg='0' * 64)))
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
OK0 += [xv1._ENV_OK[0] is True, xv1._from_pyc() == []]; print('0 real world, this run: environment checked %s, project modules taken from compiled files: %s' % (xv1._ENV_OK[0], xv1._from_pyc()))
OK0.append(HS); print('0 REAL-WORLD GUARDS', 'OK' if all(OK0) else 'FAIL')
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
     # v7: values that can differ between two runs of the same code
     'set_call': 'import xv1\ndef f(v):\n    s = set([1])\n    return xv1.ref(v)\n', 'set_display': 'import xv1\ndef f(v):\n    s = {1, 2}\n    return xv1.ref(v)\n',
     'set_comp': 'import xv1\ndef f(v):\n    s = {x for x in [1]}\n    return xv1.ref(v)\n', 'frozenset_call': 'import xv1\ndef f(v):\n    s = frozenset([1])\n    return xv1.ref(v)\n',
     'str_call': 'import xv1\ndef f(v):\n    s = str(xv1.ref)\n    return xv1.ref(v)\n', 'fstring': 'import xv1\ndef f(v):\n    s = f"{v}"\n    return xv1.ref(v)\n',
     # v8: no caught error, no text of an object, no raw bytes, no set made from dict views
     'try_stmt': 'import xv1\ndef f(v):\n    try: x = 1\n    except Exception: x = 2\n    return xv1.ref(v)\n',
     'percent': 'import xv1\ndef f(v):\n    s = "%r" % (xv1.ref,)\n    return xv1.ref(v)\n',
     'astype_text': 'import numpy as np\nimport xv1\ndef f(v):\n    s = np.array([xv1.ref]).astype("U64")\n    return xv1.ref(v)\n',
     'dtype_text': 'import numpy as np\nimport xv1\ndef f(v):\n    s = np.array([1], dtype="U8")\n    return xv1.ref(v)\n',
     'tobytes': 'import numpy as np\nimport xv1\ndef f(v):\n    s = np.array([xv1.ref]).tobytes()\n    return xv1.ref(v)\n',
     'view_other_type': 'import numpy as np\nimport xv1\ndef f(v):\n    s = np.zeros(2).view(np.int64)\n    return xv1.ref(v)\n',
     'key_set': 'import xv1\ndef f(v):\n    d = dict(a=1)\n    s = d.keys() | d.keys()\n    return xv1.ref(v)\n',
     'keys_value': 'import xv1\ndef f(v):\n    d = dict(a=1)\n    k = d.items()\n    return xv1.ref(v)\n',
     # v8 (second check): further direct forms of "text of an object"
     'np_text_arg': 'import numpy as np\nimport xv1\ndef f(v):\n    s = np.array([xv1.ref], "U64")\n    return xv1.ref(v)\n',
     'dtype_literal': 'import numpy as np\nimport xv1\ndef f(v):\n    k = dict([("dtype", "U64")])\n    return xv1.ref(v)\n',
     'type_attr': 'import numpy as np\nimport xv1\ndef f(v):\n    t = np.zeros(1).dtype.type\n    return xv1.ref(v)\n',
     'fill': 'import numpy as np\nimport xv1\ndef f(v):\n    a = np.zeros(1)\n    a.fill(1)\n    return xv1.ref(v)\n',
     'view_max2': 'import xv1\ndef f(v):\n    d = dict(a=1)\n    k = max(d.keys(), d.keys())\n    return xv1.ref(v)\n',
     'view_sum_start': 'import xv1\ndef f(v):\n    d = dict(a=1)\n    k = sum((), d.items())\n    return xv1.ref(v)\n',
     # v8 (last reading): a file may not bind the name of a built-in; np.array_equal is off the list
     'bind_def': 'import xv1\ndef len(u): return u\ndef f(v):\n    d = dict(a=1)\n    k = len(d.keys())\n    return xv1.ref(v)\n',
     'bind_assign': 'import numpy as np\nimport xv1\ndef f(v):\n    float = 1\n    return xv1.ref(v)\n',
     'bind_param': 'import xv1\ndef g(max): return max\ndef f(v): return xv1.ref(v)\n',
     'bind_star': 'import xv1\ndef g(*list): return 0\ndef f(v): return xv1.ref(v)\n',
     'array_equal': 'import numpy as np\nimport xv1\ndef f(v):\n    b = np.array_equal(np.zeros(2), np.zeros(2))\n    return xv1.ref(v)\n',
     # v8 (own check before registration): a match statement (a class pattern reads an attribute by name, a capture binds a name), async forms, type parameters, an import alias that is a built-in name
     'match_class': 'import numpy as np\nimport xv1\ndef f(v):\n    a = np.float64(1.5)\n    match a:\n        case np.float64(tobytes=g):\n            b = g()\n    return xv1.ref(v)\n',
     'match_capture': 'import numpy as np\nimport xv1\ndef f(v):\n    match 1:\n        case float:\n            pass\n    x = np.zeros(2, dtype=float)\n    return xv1.ref(v)\n',
     'async_def': 'import xv1\nasync def len(u): return u\ndef f(v): return xv1.ref(v)\n',
     'type_param': 'import xv1\ndef g[len](u): return u\ndef f(v): return xv1.ref(v)\n',
     'alias_builtin': 'import numpy as float\nimport xv1\ndef f(v): return xv1.ref(v)\n',
     'async_genexp': 'import xv1\ndef f(v):\n    g = (x async for x in ())\n    return xv1.ref(v)\n',
     'clean': 'import numpy as np\nimport xv1\ndef f(v):\n    o = xv1.ref(v); o["bfn"] = xv1.std.ident; o["bp"] = np.zeros(1, dtype=np.float64); o["fstep"] = 0.5\n'
              '    e = dict(a=1); e2 = dict(e.items()); n2 = len(list(enumerate(e.items()))) + len(list(zip(e.keys(), e.values()))) + max(e.items())[1]\n'
              '    d = dict(a=1); n = len(d.keys()) + len(sorted(d.items())) + sum(x for k, x in d.items()) + len([k for k in d.keys()])\n'
              '    a = np.zeros(2).astype(int); b = np.zeros(2, dtype=a.dtype); c = np.zeros(2, dtype=bool)\n    return o\n'}
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
# v7: the file path is read-only, an unknown key is refused, and a candidate file saved again after its object was made is refused at registration
try: c0.file = F; f5 = False
except AttributeError: f5 = True
try: xv1.Config('k', 'k', F, 'N', calender=True); k5 = False
except TypeError: k5 = True
open(tmp + 'chg.py', 'w').write('import xv1\ndef f(v): return xv1.ref(v)\n'); cc = xv1.Config('chg', 'chg', tmp + 'chg.py', 'f'); hh = cc.hash
open(tmp + 'chg.py', 'w').write('import xv1\ndef f(v):\n    return xv1.ref(v)\n'); nb = sum(1 for e in xv1.read_ledger() if e.get('kind') == 'batch')
try: xv1.register_batch([cc]); r5 = 'registered'
except PermissionError as e: r5 = str(e)
r5 = 'changed since' in r5 and nb == sum(1 for e in xv1.read_ledger() if e.get('kind') == 'batch') and not os.path.exists(xv1.OUT + 'BATCH_%d.json' % (nb + 1))
print('5b file path read-only %s | misspelled key refused %s | file saved again after its object was made: refused at registration, no batch number spent %s' % (f5, k5, r5)); ok += [f5, k5, r5]
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
# v7: a ledger that is behind its copy (a line lost, a cut line whose whole form the copy holds, the file gone) is refused, then restored from the copy and logged
R6 = []
for nm in ('last line lost', 'last line cut', 'file gone'):
    raw = open(xv1.OUT + 'LEDGER.jsonl', 'rb').read(); lines = raw.splitlines(keepends=True)
    if nm == 'file gone': os.remove(xv1.OUT + 'LEDGER.jsonl')
    else: open(xv1.OUT + 'LEDGER.jsonl', 'wb').write(b''.join(lines[:-1]) if nm == 'last line lost' else raw[:-3])
    R6.append(refused('ledger behind its copy (%s)' % nm, xv1.read_ledger)); xv1.repair_ledger(); Lr = xv1.read_ledger()
    R6.append(Lr[-1]['kind'] == 'repair' and Lr[-1]['restored_bytes'] > 0 and open(xv1.OUT + 'LEDGER.jsonl', 'rb').read().startswith(raw) and len(Lr) == len(lines) + 1)
print('6b ledger behind its copy: refused, then restored by repair_ledger and logged:', R6); ok += R6
# v7: with the lock file of an opening present the repair is refused before the file is touched (its line could not be written)
raw = open(xv1.OUT + 'LEDGER.jsonl', 'rb').read(); open(xv1.OUT + 'LEDGER.jsonl', 'wb').write(raw[:-3]); open(xv1.OUT + 'G3.lock', 'w').close()
R7 = [refused('repair while the lock file of an opening exists', xv1.repair_ledger), open(xv1.OUT + 'LEDGER.jsonl', 'rb').read() == raw[:-3]]
os.remove(xv1.OUT + 'G3.lock'); xv1.repair_ledger(); Lr = xv1.read_ledger(); R7.append(Lr[-1]['kind'] == 'repair' and open(xv1.OUT + 'LEDGER.jsonl', 'rb').read().startswith(raw))
print('6b repair under a stale lock: refused with the file untouched, then done and logged:', R7); ok += R7
xv1.MIRROR = None
keepo = xv1.OUT; xv1.OUT = tmp + 'empty/'; os.makedirs(xv1.OUT); open(xv1.OUT + 'LEDGER.jsonl', 'wb').close()   # v7: an empty file (line 0 was cut and removed) is no ledger
xv1.ledger(dict(kind='note', text='first line')); e0 = xv1.read_ledger(); xv1.OUT = keepo
print('6b first line into an empty ledger file: read back', len(e0) == 1 and e0[0]['prev'] == ''); ok.append(len(e0) == 1 and e0[0]['prev'] == '')
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
try: xv1.run_batch(k4); first = 'not stopped'; mt = None
except MemoryError as e: first = 'stopped'; mt = (str(e), e.__context__)
try: xv1._call(cm[1].fresh(), xv1.View(X)); ct = None
except MemoryError as e: ct = (e.args, e.__context__)
Lm = xv1.read_ledger(); pf = xv1.OUT + 'results/partial_%d/%s.json' % (k4, cm[0].hash); whole = open(pf).read()
open(pf, 'w').write(whole[:len(whole) // 2])                    # the finished configuration's partial file, cut
o4 = xv1.run_batch(k4)['results']; xv1.prefix_test = real_pt
print('8 out of memory: first run %s, ledger line %s, results file written %s | second run: %s; the configuration with the cut partial file was scored again: %s' % (
    first, Lm[-1]['kind'], os.path.exists(xv1.OUT + 'results/batch_%d.json' % k4), o4[cm[1].hash].get('void'), 'd' in o4[cm[0].hash] and json.load(open(pf))['o']['d'] == o4[cm[0].hash]['d']))
ok += [first == 'stopped', Lm[-1]['kind'] == 'out-of-memory' and Lm[-1]['cfg'] == cm[1].hash, 'out of memory twice' in o4[cm[1].hash].get('void', ''), 'd' in o4[cm[0].hash]]
# v8: a result that follows a stop says so (the configuration with the cut file and the one that ran out of memory were both begun twice)
fl8 = [o4[cm[1].hash].get('oom_stop') is True and o4[cm[1].hash].get('restarts') == 1, o4[cm[0].hash].get('restarts') == 1 and o4[cm[0].hash].get('oom_stop') is False,
       all(o.get('restarts') == 0 and o.get('oom_stop') is False for o in R.values())]
print('8 restart flags: out-of-memory configuration, configuration with the cut file, batch 1 (run in one go):', fl8); ok += fl8
notext = ct == ((), None) and mt is not None and mt[1] is None and 'shape' not in mt[0] and '999' not in mt[0]   # v7: numpy's text names the shape candidate code asked for
print('8 the out-of-memory error leaves candidate code without text and without the first error as context: %s (%s)' % (notext, mt[0] if mt else None)); ok.append(notext)
# 9 (v7) the last G1 line of a configuration counts (a batch resumed after an amendment can write a second one)
L9 = xv1.read_ledger(); adv = [e for e in L9 if e.get('kind') == 'g1' and e.get('advance')]
if adv:
    n9 = len(xv1._advanced_before(99, L9)); a = adv[0]
    xv1.ledger(dict(kind='g1', cfg=a['cfg'], batch=a['batch'], family=a['family'], passed=False, advance=False, type='exposure', calendar=False, supersedes_earlier_line=True))
    ok.append(len(xv1._advanced_before(99, xv1.read_ledger())) == n9 - 1); print('9 a later G1 line of a configuration replaces its earlier one in the family rule:', ok[-1])
else: ok.append(False); print('9 ERROR: no advanced configuration in this test ledger')
# 10 (v8) an error of candidate code leaves without the text it wrote: no context, no cause, and with the real calendar's handling
# (switched on here by _QUIET) not even its class name; an entry point reduces every other error the same way
v8 = xv1.View(X)
def tell(v): raise KeyError((123456, 654321))
def err_of(f):
    try: f(); return None
    except BaseException as e: return e
bare = lambda e, txt, cls=xv1.Void: type(e) is cls and str(e) == txt and e.__context__ is None and e.__cause__ is None
e1 = err_of(lambda: xv1._call(tell, v8)); xv1._QUIET[0] = True; e2 = err_of(lambda: xv1._call(tell, v8)); xv1._QUIET[0] = False
open(tmp + 'loaderr.py', 'w').write('import xv1\nraise ValueError((123, 456))\ndef f(v): return xv1.ref(v)\n'); cl = xv1.Config('le', 'le', tmp + 'loaderr.py', 'f')
e3 = err_of(lambda: xv1._call(cl.fresh(), v8))
R10 = [bare(e1, 'error in candidate code: KeyError'), bare(e2, 'error in candidate code'), bare(e3, 'error while loading candidate code: ValueError')]
real_g1 = xv1._g1_of; cr = [c for c in cfgs if c.name == 'crash'][0]; c9 = N(9); c1 = cfgs[1]
xv1._g1_of = lambda h, L=None: dict(g1_pass=True, advance=True, g0='not available', out_sha256='0' * 64, out_env=xv1._out_env())
xv1._QUIET[0] = True; e4 = err_of(lambda: xv1.weak_eval(cr)); xv1._QUIET[0] = False        # the candidate's own error at G2
g9 = dict(o2['results'][c9.hash], g1_pass=True, advance=True, g0='not available'); xv1._g1_of = lambda h, L=None: g9
real_da = xv1._design_account
def boom(*a, **k): raise ValueError('a number 0.123 computed from the output')
xv1._design_account = boom; xv1._QUIET[0] = True; e5 = err_of(lambda: xv1.weak_eval(c9)); xv1._QUIET[0] = False; xv1._design_account = real_da
R10 += [bare(e4, 'error in candidate code'), type(e5) is xv1.Stopped and '0.123' not in str(e5) and 'ValueError' in str(e5) and e5.__context__ is None and e5.__cause__ is None]
print('10 errors of candidate code: test world %r | real handling %r | at load %r | at G2 %r | evaluator error at G2 %r | %s' % (
    str(e1), str(e2), str(e3), str(e4), str(e5), R10)); ok += R10
# 11 (v8) G2 reads only the output that was tested at G1 (fingerprint stored with the G1 record); another output is refused and the read is used
w9 = xv1.weak_eval(c9)                                         # second read of this configuration (the first one stopped above): the tested output is accepted
g1b = dict(R[c1.name], g1_pass=True, advance=True, g0='not available', out_sha256='0' * 64); xv1._g1_of = lambda h, L=None: g1b
def msg(f):
    try: f(); return ''
    except PermissionError as e: return str(e)
m11 = [msg(lambda: xv1.weak_eval(c1)) for _ in range(3)]; xv1._g1_of = real_g1
R11 = ['g2_pass' in w9, 'out_sha256' in R[c1.name] and len(R[c1.name]['out_sha256']) == 64, 'differs from the one tested at G1' in m11[0], 'differs from the one tested at G1' in m11[1], 'already read' in m11[2]]
print('11 G2 on the tested output: accepted %s | on an output with another fingerprint: %s' % (R11[0], m11)); ok += R11
# 12 (v8) candidate code finds the same room on the stack in every call, however deep the evaluator was called
seen12 = []
def probe(v):
    def f(n):
        try: return f(n + 1)
        except RecursionError: return n
    seen12.append(f(0)); return xv1.ref(v)
def deeper(k): return xv1._call(probe, v8) if k == 0 else deeper(k - 1)
lim12 = sys.getrecursionlimit(); deeper(0); deeper(1); deeper(40)
R12 = [len(seen12) == 3 and len(set(seen12)) == 1, sys.getrecursionlimit() == lim12]
print('12 frames candidate code can open, called at three depths: %s | limit restored: %s' % (seen12, R12[1])); ok += R12
# 13 (v8) a T0 after the last design row is a void, not an error that stops the batch run (the T0 input rule is switched off for this case)
keep_t0 = xv1._t0_ok; xv1._t0_ok = lambda pre, t0: True
ce = xv1.Config('late', 'late_end', F, 'late', dict(hundreds=999), t0='2015-01-05'); e13 = err_of(lambda: xv1._design(ce, False)); xv1._t0_ok = keep_t0
print('13 T0 after the last design row: %r' % str(e13)); ok.append(bare(e13, 'no scored design row on or after T0'))
# 14 (v8, second check) a view whose mapping candidate code changed is a void (the fingerprint of the view cannot be taken: not an
# error that stops the run); a void of the output rules carries no context; the operator's stop leaves without a frame of candidate code
def dmg(v):
    o = xv1.ref(v); v.m[0] = 1; return o
def stopit(v): raise KeyboardInterrupt()
e14 = err_of(lambda: xv1._call(dmg, xv1.View(X))); e14b = err_of(lambda: xv1._call(outputs(dict(G=np.zeros(7))), v8)); e14c = err_of(lambda: xv1._call(stopit, v8))
fr = []; tb = e14c.__traceback__
while tb is not None: fr.append(tb.tb_frame.f_code.co_name); tb = tb.tb_next
R14 = [bare(e14, 'candidate code changed or replaced an input'), bare(e14b, 'output rule: shape of G or Wt'),
       type(e14c) is KeyboardInterrupt and 'stopit' not in fr and e14c.__context__ is None]
def nomem(*a, **k): raise MemoryError('a text of numpy')
real_norm = xv1._norm; xv1._norm = nomem; e14d = err_of(lambda: xv1._call(xv1.ref, v8)); xv1._norm = real_norm     # out of memory in the evaluator's own checks: not a void
real_dig = xv1._digest; cnt = [0]
def dig2(v):
    cnt[0] += 1
    if cnt[0] == 2: raise MemoryError('a text of numpy')
    return real_dig(v)
xv1._digest = dig2; e14e = err_of(lambda: xv1._call(xv1.ref, v8)); xv1._digest = real_dig
R14 += [type(e) is MemoryError and e.args == () and e.__context__ is None for e in (e14d, e14e)]
real_n2n = np.nan_to_num                                          # out of memory INSIDE the output check (one of its three conversions): not a shape error
def n2n(*a, **k):
    if sys._getframe(1).f_code.co_name == '_norm': raise MemoryError('Unable to allocate 59.5 KiB')
    return real_n2n(*a, **k)
np.nan_to_num = n2n; e14f = err_of(lambda: xv1._call(outputs(dict(RB=np.zeros(v8.T))), v8)); np.nan_to_num = real_n2n
def passes_void(v): raise xv1.Void('output rule: planted in code that candidate code called')
e14g = err_of(lambda: xv1._call(passes_void, v8)); fr2 = []; tb = e14g.__traceback__
while tb is not None: fr2.append(tb.tb_frame.f_code.co_name); tb = tb.tb_next
os.makedirs(tmp + 'adir.json'); open(tmp + 'cut.json', 'w').write('{"o": {"d": 0.0')
try: xv1._read_json(tmp + 'adir.json'); rj = False
except OSError: rj = True
R14 += [type(e14f) is MemoryError and e14f.args == () and e14f.__context__ is None, bare(e14g, 'output rule: planted in code that candidate code called') and 'passes_void' not in fr2,
        rj and xv1._read_json(tmp + 'cut.json') is None and xv1._read_json(tmp + 'nofile.json') is None]
class Bomb:                                                       # v8 (last reading): an object whose conversion to an array runs out of memory, at the two other conversions of the output check, and the compile step
    def __array__(self, *a, **k): raise MemoryError('Unable to allocate 1.00 GiB')
e14h = err_of(lambda: xv1._call(outputs(dict(G=Bomb())), v8)); e14i = err_of(lambda: xv1._call(outputs(dict(up=Bomb())), v8))
xv1.compile = nomem; e14j = err_of(lambda: xv1.Config('oomc', 'oomc', F, 'late', dict(hundreds=999))._code()); del xv1.compile
R14 += [type(e) is MemoryError and e.args == () and e.__context__ is None for e in (e14h, e14i, e14j)]
print('14 changed mapping of the view: %r | output rule without context: %r | stop by the operator: frames %s | %s' % (str(e14), str(e14b), fr, R14)); ok += R14
# 15 (v8, second check) whatever stops the run on one configuration twice: no third start (the configuration is void, the batch goes on)
cs = [N(14)]; k5, _ = xv1.register_batch(cs)
def halt(*a, **k): raise RuntimeError('the machine stops here')
xv1.prefix_test = halt; st = [type(err_of(lambda: xv1.run_batch(k5))).__name__ for _ in range(2)]
xv1.prefix_test = lambda *a, **k: dict(result='PASS'); o5 = xv1.run_batch(k5)['results'][cs[0].hash]; xv1.prefix_test = real_pt
L15 = [e['kind'] for e in xv1.read_ledger() if e.get('cfg') == cs[0].hash and e.get('batch') == k5]
R15 = [st == ['RuntimeError', 'RuntimeError'], 'run stopped twice' in o5.get('void', ''), o5.get('restarts') == 2, L15[:3] == ['score', 'restart', 'restart']]
print('15 two stops on one configuration: %s | third start: %r | ledger lines %s | %s' % (st, o5.get('void'), L15, R15)); ok += R15
# 16 (v8, second check) G2 under another machine, other packages or a changed data file is refused before anything is logged or read
c2 = cfgs[2]; g16 = dict(R[c2.name], g1_pass=True, advance=True, g0='not available', out_env='another machine'); xv1._g1_of = lambda h, L=None: g16
n16 = len(xv1.read_ledger()); m16 = msg(lambda: xv1.weak_eval(c2))
g16 = dict(g16, out_env=xv1._out_env(), data_hashes={'a data file of the batch run': '0' * 64}); m16b = msg(lambda: xv1.weak_eval(c2)); xv1._g1_of = real_g1
R16 = ['nothing was read' in m16, 'nothing was read' in m16b, len(xv1.read_ledger()) == n16, len(R[c2.name].get('out_env', '')) == 16, xv1._out_env() == R[c2.name].get('out_env'),
       xv1._env_same(dict(out_env=xv1._out_env(), data_hashes=None)), not xv1._env_same(dict(out_env=xv1._out_env(), data_hashes={'x': '0'}))]
print('16 G2 under another environment: %r | ledger untouched %s | %s' % (m16[:60], R16[2], R16)); ok += R16
# 17 (v8, last reading) a read error on the registry is an error (only a missing file is "no registry"); a read error on the
# partial result of a configuration not yet begun stops the run before its score line (it costs none of its two starts)
keep_out = xv1.OUT; os.makedirs(tmp + 'regdir/HASHES.json'); xv1.OUT = tmp + 'regdir/'; e17 = err_of(xv1._registry)
xv1.OUT = tmp + 'noreg/'; r17 = xv1._registry(); xv1.OUT = keep_out
cs7 = [N(15)]; k7, _ = xv1.register_batch(cs7); real_rj = xv1._read_json
def rj_err(p):
    if '/partial_' in p: raise OSError(5, 'Input/output error')
    return real_rj(p)
xv1._read_json = rj_err; e17b = err_of(lambda: xv1.run_batch(k7)); xv1._read_json = real_rj
L17 = [e['kind'] for e in xv1.read_ledger() if e.get('cfg') == cs7[0].hash and e.get('batch') == k7]
R17 = [isinstance(e17, OSError), r17 == {}, isinstance(e17b, OSError), L17 == []]
print('17 read error on the registry: %s | on a partial result before the score line: %s, ledger lines of the configuration %s | %s' % (type(e17).__name__, type(e17b).__name__, L17, R17)); ok += R17
print('GUARDS', 'OK' if all(ok) and all(OK0) and OK1B else 'FAIL')
