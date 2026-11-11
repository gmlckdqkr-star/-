"""Synthetic world only: the whole gate chain G1 -> G2 -> G3 with planted edges. Every market value after 2014-12-31 is replaced
by a copy of old (<= 2014) rows before anything is computed, the extra instruments and the signal are seeded noise, the ledger
goes to a scratch folder. Only the calendar DATES after 2014 are real. Nothing here is a research result.
Planted: 'sig' is an on/off signal (on about 30% of rows, in runs); an instrument earns a drift only while the signal was on two
rows earlier (a timing edge), with the sign chosen per era; every instrument has its own signal; 'drift' earns the same drift on every row (pure exposure)."""
import sys, os, json, shutil, hashlib, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/-/research_xv1/code')
import xv1
from xv1 import mkt
tmp = sys.argv[1]; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp); xv1.OUT = tmp + '/'
X = xv1.frame(xv1.CAL_END).copy(); n0 = int(X.index.searchsorted(pd.Timestamp('2015-01-01'))); n1 = len(X) - n0
for c in ('r', 'rf', 'y10', 'y3m', 'cs', 'vix'): X.iloc[n0:, X.columns.get_loc(c)] = X[c].values[n0 - n1 - 500:n0 - 500]
X['rb'] = mkt.bond10(X); X['p'] = (1 + X['r']).cumprod()
xv1._FR.clear(); xv1._FR[xv1.CAL_END] = X; xv1._FR[xv1.A_END] = X.loc[:xv1.A_END]
g = np.random.default_rng(7); n = len(X); yr = X.index.year; sealed = ((yr >= 2016) & (yr <= 2018)) | ((yr >= 2022) & (yr <= 2024))
def signal():
    s = np.zeros(n); i = 0
    while i < n:
        L = int(g.integers(20, 61)); s[i:i + L] = float(g.random() < 0.3); i += L
    return s
MU = 0.015; SYN = {}
for k, mu, mus in (('good', MU, MU), ('rev', MU, -MU), ('flat', MU, 0.0), ('bad', -MU, -MU), ('good3', MU, MU)):
    sg = signal(); SYN['sig_' + k] = sg; SYN[k] = np.where(sealed, mus, mu) * np.r_[0.0, 0.0, sg[:-2]] + g.normal(0, 0.03, n)
SYN['drift'] = 0.008 + g.normal(0, 0.03, n)
SYN['good2'] = 0.9 * SYN['good'] + g.normal(0, 0.003, n); SYN['sig_good2'] = SYN['sig_good']
xv1.extras = lambda names, idx: {k: SYN[k][:len(idx)].copy() for k in names}
xv1._call(xv1.ref, xv1.View(xv1.frame(xv1.A_END)))
F = '/home/user/-/research_xv1/code/t_cand_synth.py'
C = {k: xv1.Config('fam_' + k, k, F, 'timed', dict(name=k, sig='sig_' + k), names=(k, 'sig_' + k)) for k in SYN if k != 'drift' and not k.startswith('sig_')}
C['static'] = xv1.Config('fam_static', 'static', F, 'sleeve', dict(name='drift'), names=('drift',))

# the design account on the full calendar equals the account of the calendar cut at 2015-12-31 on blocks 0-9 (bit for bit)
full = xv1._design_account(xv1.ref); keep_end = xv1.CAL_END; xv1.CAL_END = xv1.A_END; cut = xv1._design_account(xv1.ref); xv1.CAL_END = keep_end
print('design account vs cut calendar, blocks 0-9 bit-identical:', all(np.array_equal(full[b][f], cut[b][f]) for b in range(10) for f in ('x', 'lev', 'a0')),
      '| blocks scored:', sorted(full))


def start(sub):
    xv1.OUT = tmp + '/' + sub + '/'; os.makedirs(xv1.OUT)
    json.dump(dict(prereg_sha256='0' * 64, **xv1.env_hashes()), open(xv1.OUT + 'HASHES.json', 'w'))


def show(out):
    for h, o in out['results'].items():
        if 'void' in o: print('  %-6s VOID %s' % (o['name'], o['void']))
        else: print('  %-6s d %+7.2f d* %+7.2f te %5.1f p_family %.5f p*_family %.5f active blocks %d harm %s g1 %s type %s advance %s' % (
            o['name'], 100 * o['d'], 100 * o['d_star'], 100 * o['te'], o['p_family'], o['p_star_family'], o['active_blocks'], o['harm'],
            ''.join('Y' if x else 'n' for x in o['g1'].values()), o['kind'], o['advance']))
        for r in o.get('blocks', []): assert r['b'] not in xv1.SEALED


def tryit(nm, f):
    try: r = f(); print('  %-46s -> %s' % (nm, r)); return r
    except PermissionError as e: print('  %-46s refused: %s' % (nm, e)); return None


start('a')
xv1.register_batch(1, [C[k] for k in ('good', 'rev', 'flat', 'bad')]); print('batch 1 (alpha %.4f)' % (0.05 / 2)); show(xv1.run_batch(1))
for k in ('good', 'rev', 'flat'):
    o = xv1.weak_eval(C[k]); print('  G2 %-5s d %+7.2f limit %+6.2f harm %s pass %s' % (k, 100 * o['d'], 100 * o['set_limit'], o['harm'], o['g2_pass']))
tryit('G2 second read of good', lambda: xv1.weak_eval(C['good']))
tryit('G2 for bad (failed G1)', lambda: xv1.weak_eval(C['bad']))
tryit('G3 good without owner authorisation', lambda: xv1.open_g3(C['good']))
for k in ('good', 'rev', 'flat'): xv1.authorise_g3(C[k], 'test-message-id')
h = json.load(open(xv1.OUT + 'HASHES.json')); k0 = sorted(h['data'])[0]; keep = h['data'][k0]
h['data'][k0] = 'x'; json.dump(h, open(xv1.OUT + 'HASHES.json', 'w')); tryit('G3 good with a changed registered hash', lambda: xv1.open_g3(C['good']))
h['data'][k0] = keep; json.dump(h, open(xv1.OUT + 'HASHES.json', 'w'))
w1 = tryit('G3 good (timing edge everywhere)', lambda: xv1.open_g3(C['good']))
tryit('G3 good a second time', lambda: xv1.open_g3(C['good']))
real_main = xv1._main_account; state = dict(n=0)
def crash(*a, **k):
    if state['n'] == 0: state['n'] = 1; raise RuntimeError('simulated crash after G3-OPEN')
    return real_main(*a, **k)
xv1._main_account = crash
try: xv1.open_g3(C['rev'])
except RuntimeError as e: print('  %-46s -> %s' % ('G3 rev, first run', e))
w2 = tryit('G3 rev, the one allowed retry (edge reversed)', lambda: xv1.open_g3(C['rev']))
xv1._main_account = real_main
xv1.register_batch(2, [C['good2']]); print('batch 2 (alpha %.4f)' % (0.05 / 4)); show(xv1.run_batch(2))
print('  G2 good2 pass', xv1.weak_eval(C['good2'])['g2_pass']); xv1.authorise_g3(C['good2'], 'test-message-id')
tryit('G3 good2 (0.9 x good + noise)', lambda: xv1.open_g3(C['good2']))
w3 = tryit('G3 flat (no edge in the sealed years)', lambda: xv1.open_g3(C['flat']))
xv1.register_batch(3, [C['good3']]); print('batch 3 (alpha %.4f)' % (0.05 / 8)); show(xv1.run_batch(3))
print('  G2 good3 pass', xv1.weak_eval(C['good3'])['g2_pass']); xv1.authorise_g3(C['good3'], 'test-message-id')
tryit('G3 good3 (fourth distinct opening)', lambda: xv1.open_g3(C['good3']))
tryit('main account without the token', lambda: xv1._main_account(xv1.ref))
L = xv1.read_ledger(); G = [e for e in L if e['kind'].startswith('G3')]
print('ledger: %d lines; G3 lines: %s' % (len(L), [(e['kind'], e.get('verdict', ''), e.get('retry', '')) for e in G]))
print('keys of G3 ledger lines:', sorted(set(k for e in G for k in e)))
body = b''; ok = True
for line in open(xv1.OUT + 'LEDGER.jsonl', 'rb'):
    ok &= json.loads(line)['prev'] == (hashlib.sha256(body).hexdigest()[:16] if body else ''); body += line
print('ledger hash chain intact:', ok)
print('files written:', sorted(os.path.relpath(os.path.join(d, f), xv1.OUT) for d, _, fs in os.walk(xv1.OUT) for f in fs))

start('b'); print('second ledger: a pure exposure candidate (constant sleeve in an instrument that drifts up on every row)')
xv1.register_batch(1, [C['static']]); show(xv1.run_batch(1))
print('  G2 static pass', xv1.weak_eval(C['static'])['g2_pass']); xv1.authorise_g3(C['static'], 'test-message-id')
w4 = tryit('G3 static (holds more, no timing)', lambda: xv1.open_g3(C['static']))
exp = (w1 == 'CONFIRMED', w2 == 'FAIL', w3 in ('FAIL', 'INCONCLUSIVE'), w4 == 'CONSISTENT')
print('EXPECTED VERDICTS', 'OK' if all(exp) else 'FAIL', exp)
shutil.rmtree(tmp)
