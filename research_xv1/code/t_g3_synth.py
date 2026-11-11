"""Synthetic world only: the whole gate chain G1 -> G2 -> G3 with planted edges. Every market value after 2014-12-31 is replaced
by a copy of old (<= 2014) rows before anything is computed, the extra instruments are seeded noise, the ledger goes to a
scratch folder. Only the calendar DATES after 2014 are real. Nothing here is a research result."""
import sys, os, json, shutil, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/-/research_xv1/code')
import xv1
from xv1 import mkt
tmp = sys.argv[1]; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp); xv1.OUT = tmp + '/'
X = xv1.frame(xv1.CAL_END).copy(); n0 = int(X.index.searchsorted(pd.Timestamp('2015-01-01'))); n1 = len(X) - n0
for c in ('r', 'rf', 'y10', 'y3m', 'cs', 'vix'): X.iloc[n0:, X.columns.get_loc(c)] = X[c].values[n0 - n1 - 500:n0 - 500]
X['rb'] = mkt.bond10(X); X['p'] = (1 + X['r']).cumprod()
xv1._FR.clear(); xv1._FR[xv1.CAL_END] = X; xv1._FR[xv1.A_END] = X.loc[:xv1.A_END]
g = np.random.default_rng(7); yr = X.index.year; sealed = ((yr >= 2016) & (yr <= 2018)) | ((yr >= 2022) & (yr <= 2024))
mk = lambda mu, mus: np.where(sealed, mus, mu) + g.normal(0, 0.03, len(X))
SYN = dict(good=mk(0.008, 0.008), rev=mk(0.008, -0.008), flat=mk(0.008, 0.0), bad=mk(-0.008, -0.008), good3=mk(0.008, 0.008))
SYN['good2'] = 0.9 * SYN['good'] + g.normal(0, 0.003, len(X))
xv1.extras = lambda names, idx: {k: SYN[k][:len(idx)].copy() for k in names}
xv1._call(xv1.ref, xv1.View(xv1.frame(xv1.A_END)))
json.dump(dict(prereg_sha256='0' * 64, **xv1.env_hashes()), open(xv1.OUT + 'HASHES.json', 'w'))
F = '/home/user/-/research_xv1/code/t_cand_synth.py'
C = {k: xv1.Config('fam_' + k, k, F, 'sleeve', dict(name=k), names=(k,)) for k in SYN}


def show(out):
    for h, o in out['results'].items():
        if 'void' in o: print('  %-6s VOID %s' % (o['name'], o['void']))
        else: print('  %-6s d %+7.2f te %5.1f p_family %.4f active blocks %d harm %s g1 %s advance %s' % (
            o['name'], 100 * o['d'], 100 * o['te'], o['p_family'], o['active_blocks'], o['harm'], o['g1'], o['advance']))
        for r in o.get('blocks', []): assert r['b'] not in xv1.SEALED


def tryit(nm, f):
    try: r = f(); print('  %-46s -> %s' % (nm, r)); return r
    except PermissionError as e: print('  %-46s refused: %s' % (nm, e)); return None


xv1.register_batch(1, [C[k] for k in ('good', 'rev', 'flat', 'bad')]); print('batch 1 (alpha %.4f)' % (0.05 / 2)); show(xv1.run_batch(1))
for k in ('good', 'rev', 'flat'):
    o = xv1.weak_eval(C[k]); print('  G2 %-5s d %+7.2f harm %s pass %s' % (k, 100 * o['d'], o['harm'], o['g2_pass']))
tryit('G2 second read of good', lambda: xv1.weak_eval(C['good']))
tryit('G2 for bad (failed G1)', lambda: xv1.weak_eval(C['bad']))
tryit('G3 good without owner authorisation', lambda: xv1.open_g3(C['good']))
for k in ('good', 'rev', 'flat'): xv1.authorise_g3(C[k], 'test-message-id')
h = json.load(open(xv1.OUT + 'HASHES.json')); k0 = sorted(h['data'])[0]; keep = h['data'][k0]
h['data'][k0] = 'x'; json.dump(h, open(xv1.OUT + 'HASHES.json', 'w')); tryit('G3 good with a changed registered hash', lambda: xv1.open_g3(C['good']))
h['data'][k0] = keep; json.dump(h, open(xv1.OUT + 'HASHES.json', 'w'))
w1 = tryit('G3 good (edge everywhere)', lambda: xv1.open_g3(C['good']))
tryit('G3 good a second time', lambda: xv1.open_g3(C['good']))
real_own = xv1._own; state = dict(n=0)
def crash(*a, **k):
    if k.get('_token') is not None and state['n'] == 0: state['n'] = 1; raise RuntimeError('simulated crash after G3-OPEN')
    return real_own(*a, **k)
xv1._own = crash
try: xv1.open_g3(C['rev'])
except RuntimeError as e: print('  %-46s -> %s' % ('G3 rev, first run', e))
w2 = tryit('G3 rev, the one allowed retry (edge reversed)', lambda: xv1.open_g3(C['rev']))
xv1._own = real_own
xv1.register_batch(2, [C['good2']]); print('batch 2 (alpha %.4f)' % (0.05 / 4)); show(xv1.run_batch(2))
print('  G2 good2 pass', xv1.weak_eval(C['good2'])['g2_pass']); xv1.authorise_g3(C['good2'], 'test-message-id')
tryit('G3 good2 (0.9 x good + noise)', lambda: xv1.open_g3(C['good2']))
w3 = tryit('G3 flat (no edge in the sealed years)', lambda: xv1.open_g3(C['flat']))
xv1.register_batch(3, [C['good3']]); print('batch 3 (alpha %.4f)' % (0.05 / 8)); show(xv1.run_batch(3))
print('  G2 good3 pass', xv1.weak_eval(C['good3'])['g2_pass']); xv1.authorise_g3(C['good3'], 'test-message-id')
tryit('G3 good3 (fourth distinct opening)', lambda: xv1.open_g3(C['good3']))
tryit('sealed block without the token', lambda: xv1._own(xv1.ref, (), (10, 12)))
L = xv1.read_ledger(); G = [e for e in L if e['kind'].startswith('G3')]
print('ledger: %d lines; G3 lines: %s' % (len(L), [(e['kind'], e.get('verdict', ''), e.get('retry', '')) for e in G]))
print('keys of G3 ledger lines:', sorted(set(k for e in G for k in e)))
import hashlib
prev = ''; ok = True
body = b''
for line in open(xv1.OUT + 'LEDGER.jsonl', 'rb'):
    ok &= json.loads(line)['prev'] == (hashlib.sha256(body).hexdigest()[:16] if body else ''); body += line
print('ledger hash chain intact:', ok)
print('files written:', sorted(os.path.relpath(os.path.join(d, f), tmp) for d, _, fs in os.walk(tmp) for f in fs))
exp = (w1 == 'CONFIRMED', w2 == 'FAIL', w3 in ('FAIL', 'INCONCLUSIVE'))
print('EXPECTED VERDICTS', 'OK' if all(exp) else 'FAIL', exp)
shutil.rmtree(tmp)
