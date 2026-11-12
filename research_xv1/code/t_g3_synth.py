"""Synthetic world only: the whole gate chain G1 -> G2 -> G3 with planted edges. Every market value after 2014-12-31 is replaced
by a copy of old (<= 2014) rows before anything is computed, the extra instruments and the signals are seeded noise, the ledger
goes to a scratch folder. Only the calendar DATES after 2014 are real. Nothing here is a research result.
Planted: every instrument has its own on/off signal (on about 30% of rows, in runs) and earns a drift only while its signal
was on two rows earlier (a timing edge), with the sign chosen per era; 'drift' earns the same drift on every row (pure
exposure); 'late' exists only from 2013 on."""
import sys, os, json, time, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/-/research_xv1/code')
import xv1, t_world
X = t_world.synth(0, extras=False); tmp = t_world.scratch(sys.argv[1])
g = np.random.default_rng(7); n = len(X); yr = X.index.year; sealed = ((yr >= 2016) & (yr <= 2018)) | ((yr >= 2022) & (yr <= 2024))
def signal():
    s = np.zeros(n); i = 0
    while i < n:
        L = int(g.integers(20, 61)); s[i:i + L] = float(g.random() < 0.3); i += L
    return s
MU = 0.015; SYN = {}
for k, mu, mus in (('good', MU, MU), ('rev', MU, -MU), ('flat', MU, 0.0), ('bad', -MU, -MU), ('good3', MU, MU), ('late', MU, MU)):
    sg = signal(); SYN['sig_' + k] = sg; SYN[k] = np.where(sealed, mus, mu) * np.r_[0.0, 0.0, sg[:-2]] + g.normal(0, 0.03, n)
SYN['drift'] = 0.008 + g.normal(0, 0.03, n)
SYN['good2'] = 0.9 * SYN['good'] + g.normal(0, 0.003, n); SYN['sig_good2'] = SYN['sig_good']
n13 = int(X.index.searchsorted(pd.Timestamp('2013-01-02'))); SYN['late'][:n13] = np.nan; SYN['sig_late'][:n13 + 40] = 0.0
SYN['ret:TQQQ'] = np.r_[np.full(n // 2, np.nan), g.normal(0, 0.03, n - n // 2)]    # for model_check (made-up values)
xv1.extras = lambda names, idx: {k: SYN[k][:len(idx)].copy() for k in names}
def tryit(nm, f):
    try: r = f(); print('  %-52s -> %s' % (nm, r)); return r
    except PermissionError as e: print('  %-52s refused: %s' % (nm, e)); return None
tryit('calendar after 2014 outside an entry point', lambda: xv1.frame(xv1.A_END))
_S = xv1.scope(); _S.__enter__()                       # the test drives internal functions directly: one scope for the whole script
xv1._call(xv1.ref, xv1.View(xv1.frame(xv1.A_END)))
F = '/home/user/-/research_xv1/code/t_cand_synth.py'; nm = lambda k: (k, 'sig_' + k)
C = {k: xv1.Config('fam_' + k, k, F, k, {}, names=nm(k)) for k in ('good', 'rev', 'flat', 'bad', 'good2', 'good3')}
C['goodb'] = xv1.Config('fam_good', 'goodb', F, 'good', dict(w=0.2), names=nm('good'))
C['static'] = xv1.Config('fam_static', 'static', F, 'sleeve', dict(name='drift'), names=('drift',))
C['late'] = xv1.Config('fam_late', 'late', F, 'timed', dict(name='late'), names=nm('late'), t0='2013-02-20')
C['static0'] = xv1.Config('fam_static0', 'static0', F, 'static0', dict(name='drift'), names=('drift',))
MSG = 'cmsg_test_message_id'

# the design account on the full calendar equals the account of the calendar cut at 2015-12-31 on blocks 0-9 (bit for bit)
full = xv1._design_account(xv1.ref); cut = xv1._design_account(xv1.ref, end=xv1.A_END)
print('design account vs cut calendar, blocks 0-9 bit-identical:', all(np.array_equal(full[b][f], cut[b][f]) for b in range(10) for f in ('x', 'lev', 'a0')),
      '| blocks scored:', sorted(full))


def start(sub):
    xv1.OUT = tmp + sub + '/'; os.makedirs(xv1.OUT)
    json.dump(dict(prereg_sha256='0' * 64, **xv1.env_hashes()), open(xv1.OUT + 'HASHES.json', 'w'))


def batch(keys):
    t_ = time.time(); k, sha = xv1.register_batch([C[q] for q in keys]); out = xv1.run_batch(k)
    print('batch %d (alpha %.5f), %.0f s' % (k, out['alpha'], time.time() - t_))
    for h, o in out['results'].items():
        if 'void' in o: print('  %-6s VOID %s' % (o['name'], o['void']))
        else: print('  %-6s d %+7.2f d* %+7.2f te %5.1f p_family %.5f p*_family %.5f active blocks %d n %d span %d harm %s g1 %s type %s advance %s g0 %s' % (
            o['name'], 100 * o['d'], 100 * o['d_star'], 100 * o['te'], o['p_family'], o['p_star_family'], o['active_blocks'], o['n'], o['n_span'], o['harm'],
            ''.join('Y' if x else 'n' for x in o['g1'].values()), o['kind'], o['advance'], o['g0']))
        for r in o.get('blocks', []): assert r['b'] not in xv1.SEALED
    return {o['name']: o for o in out['results'].values()}


start('a')
r1 = batch(('good', 'rev', 'flat', 'bad'))
for k in ('good', 'rev', 'flat'):
    o = xv1.weak_eval(C[k]); print('  G2 %-5s d %+7.2f limit %+6.2f harm %s pass %s' % (k, 100 * o['d'], 100 * o['set_limit'], o['harm'], o['g2_pass']))
tryit('G2 second read of good', lambda: xv1.weak_eval(C['good']))
tryit('G2 for bad (failed G1)', lambda: xv1.weak_eval(C['bad']))
tryit('G3 good without owner authorisation', lambda: xv1.open_g3(C['good']))
tryit('authorisation without a message id', lambda: xv1.authorise_g3(C['good'], None))
tryit('authorisation of bad (no G1 pass)', lambda: xv1.authorise_g3(C['bad'], MSG))
for k in ('good', 'rev', 'flat'): xv1.authorise_g3(C[k], MSG)
h = json.load(open(xv1.OUT + 'HASHES.json')); k0 = sorted(h['data'])[0]; keep = h['data'][k0]
h['data'][k0] = 'x'; json.dump(h, open(xv1.OUT + 'HASHES.json', 'w')); tryit('G3 good with a changed registered hash', lambda: xv1.open_g3(C['good']))
h['data'][k0] = keep; json.dump(h, open(xv1.OUT + 'HASHES.json', 'w'))
open(xv1.OUT + 'G3.lock', 'w').close(); tryit('G3 good while another opening holds the lock', lambda: xv1.open_g3(C['good'])); os.remove(xv1.OUT + 'G3.lock')
t_ = time.time(); w1 = tryit('G3 good (timing edge everywhere)', lambda: xv1.open_g3(C['good'])); print('  (one opening: %.0f s)' % (time.time() - t_))
tryit('G3 good a second time', lambda: xv1.open_g3(C['good']))
real_main = xv1._main_account; state = dict(n=0)
def crash(*a, **k):
    if state['n'] == 0: state['n'] = 1; raise RuntimeError('simulated crash after G3-OPEN, with a sealed number 0.123 in its text')
    return real_main(*a, **k)
xv1._main_account = crash; ABORT = []
try: xv1.open_g3(C['rev'])
except RuntimeError as e:
    print('  %-52s -> %s' % ('G3 rev, first run', e))
    tb = e.__traceback__.tb_next; names = set()                     # the frames below this test script
    while tb is not None: names |= set(tb.tb_frame.f_locals); tb = tb.tb_next
    ABORT += [e.__context__ is None and e.__cause__ is None, not (names & {'Cs', 'Rs', 'ds', 'd', 'dn', 'rows', 'act', 'prem'}),
              xv1.read_ledger()[-1]['kind'] == 'G3-ABORT', '0.123' not in str(e)]
    try: xv1._main_account(xv1.ref); ABORT.append(False)
    except PermissionError: ABORT.append(True)
print('  after the crash: no context, no sealed frame locals, ledger ends G3-ABORT, no error text, main account refused:', ABORT)
w2 = tryit('G3 rev, the one allowed retry (edge reversed)', lambda: xv1.open_g3(C['rev']))
xv1._main_account = real_main
r2 = batch(('good2', 'goodb'))
print('  good2 (0.9 x good + noise, own label) and goodb (label of good): G1 passed %s, advance %s' % (
    [bool(r2[k].get('g1_pass')) for k in ('good2', 'goodb')], [r2[k]['advance'] for k in ('good2', 'goodb')]))
tryit('G2 good2 (same family as good by correlation)', lambda: xv1.weak_eval(C['good2']))
tryit('G2 goodb (same family as good by label)', lambda: xv1.weak_eval(C['goodb']))
w3 = tryit('G3 flat (no edge in the sealed years)', lambda: xv1.open_g3(C['flat']))
r3 = batch(('good3', 'late'))
print('  G2 good3 pass', xv1.weak_eval(C['good3'])['g2_pass']); xv1.authorise_g3(C['good3'], MSG)
tryit('G3 good3 (fourth distinct opening)', lambda: xv1.open_g3(C['good3']))
o = xv1.weak_eval(C['late']); print('  G2 late (inputs from 2013: %d weak rows on or after T0) available %s pass %s' % (o['n'], o['available'], o['g2_pass']))
tryit('authorisation of late (no G2 pass)', lambda: xv1.authorise_g3(C['late'], MSG)); tryit('G3 late (no G2 exists for it)', lambda: xv1.open_g3(C['late']))
tryit('main account outside an opening', lambda: xv1._main_account(xv1.ref))
L = xv1.read_ledger(); G = [e for e in L if e['kind'].startswith('G3')]
print('ledger: %d lines, chain verified on read; G3 lines: %s' % (len(L), [(e['kind'], e.get('verdict', ''), e.get('retry', '')) for e in G]))
print('keys of G3 ledger lines:', sorted(set(k for e in G for k in e)))
raw = open(xv1.OUT + 'LEDGER.jsonl').read().splitlines(keepends=True)
open(xv1.OUT + 'LEDGER.jsonl', 'w').write(''.join(x for x in raw if '"G3-' not in x))
tryit('G3 good again on a ledger with the G3 lines removed', lambda: xv1.open_g3(C['good']))
open(xv1.OUT + 'LEDGER.jsonl', 'w').write(''.join(raw))
cut = max(i for i, x in enumerate(raw) if '"G3-OPEN"' in x)          # the tail from the last opening on cut off: the chain still holds
open(xv1.OUT + 'LEDGER.jsonl', 'w').write(''.join(raw[:cut]))
MARK = tryit('G3 flat again on a ledger cut before its opening', lambda: xv1.open_g3(C['flat']))
open(xv1.OUT + 'LEDGER.jsonl', 'w').write(''.join(raw))
print('files written:', sorted(os.path.relpath(os.path.join(d, f), xv1.OUT) for d, _, fs in os.walk(xv1.OUT) for f in fs if 'partial' not in d))

start('b'); print('second ledger: a pure exposure candidate (constant sleeve in an instrument that drifts up on every row)')
batch(('static',))
print('  G2 static pass', xv1.weak_eval(C['static'])['g2_pass']); xv1.authorise_g3(C['static'], MSG)
w4 = tryit('G3 static (holds more, no timing)', lambda: xv1.open_g3(C['static']))
start('c'); print('third ledger: no v1 level, constant weight, re-set every 252 rows (input-free)')
batch(('static0',))
print('  G2 static0 pass', xv1.weak_eval(C['static0'])['g2_pass']); xv1.authorise_g3(C['static0'], MSG)
w5 = tryit('G3 static0 (input-free)', lambda: xv1.open_g3(C['static0']))
start('d'); print('fourth ledger (v6): main-view checks inside an opening, authorisation order, end date, close')
def refused(nm, f):
    try: f(); print('  %-52s not refused' % nm); return False
    except PermissionError as e: print('  %-52s refused: %s' % (nm, e)); return True
batch(('good', 'good3'))
R4 = [refused('authorisation before the G2 pass', lambda: xv1.authorise_g3(C['good'], MSG))]
for k in ('good', 'good3'): xv1.weak_eval(C[k]); xv1.authorise_g3(C[k], MSG)
real_pt = xv1.prefix_test
xv1.prefix_test = lambda *a, **k: dict(result='FAIL') if k.get('account') == 'main' else real_pt(*a, **k)
w6 = tryit('G3 good, main-view prefix test fails', lambda: xv1.open_g3(C['good'])); xv1.prefix_test = real_pt
real_prep = xv1._prepare
def prep_void(make, names=(), end=None, account='design'):
    if account == 'main': raise xv1.Void('output rule: planted on the main view')
    return real_prep(make, names, end, account)
xv1._prepare = prep_void; w7 = tryit('G3 good3, a void on the main view', lambda: xv1.open_g3(C['good3'])); xv1._prepare = real_prep
end0 = xv1.G3_END; xv1.G3_END = '2000-01-01'
R4.append(refused('G3 after the end date', lambda: xv1.open_g3(C['good3']))); xv1.G3_END = end0
R4.append(refused('close G3 with a malformed message id', lambda: xv1.close_g3('cmsg_')))
xv1.close_g3(MSG); R4.append(refused('G3 after G3 was closed for good', lambda: xv1.open_g3(C['good3'])))
kinds = [e.get('kind') for e in xv1.read_ledger()]; R4.append(kinds.count('G3-OPEN') == 2 and kinds[-1] == 'G3-CLOSED')
print('  verdicts', w6, w7, '| refusals and ledger', R4)
_S.__exit__(None, None, None)
mc = tryit('model check through its own entry point (outside the script scope)', lambda: len(xv1.model_check()))
exp = (w1 == 'CONFIRMED', w2 == 'FAIL', w3 in ('FAIL', 'INCONCLUSIVE'), w4 == 'CONSISTENT', r2['good2']['advance'] is False, r2['goodb']['advance'] is False,
       r3['late'].get('g1_pass') is True, all(ABORT) and len(ABORT) == 5, MARK is None, w5 is None, mc is not None,
       w6 == 'FAIL', w7 == 'FAIL', all(R4) and len(R4) == 5)
print('EXPECTED VERDICTS', 'OK' if all(exp) else 'FAIL', exp)
