"""Registration of the XV1 structure. Run once, after the self-tests and the independent verification, before any real row
after 2014-12-31 is read by the evaluator.

Writes to research/xv1/: PREREG_XV1_STRUCTURE.md (copy of the registered text), HASHES.json (sha256 of the text, of every
data file of the chain, of the evaluator files and of every project code file loaded by a full exercise of the evaluator on
the <= 2014 calendar, the package versions and the registered constants) and ledger line 0 (kind 'registration': the sha256
of the text, the sha256 of HASHES.json and the id of the owner's message). Nothing after 2014 is read here.

  python m_register.py                    the one-time registration
  python m_register.py --amend FILE.md    v7: take the registry again after a change that section 7 of the text allows
                                          (FILE.md says what changed and lists every output that existed before)"""
import os
import sys, json, shutil, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xv1, m_batch1

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'PREREG_XV1_STRUCTURE.md')
OWNER_MESSAGE = 'cmsg_013GuJ2gSecTDkpekhQ7SWhg47X7ADtvr4d67q4nBbKHKk'
AMEND = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == '--amend' else None
assert xv1.WORLD is None and xv1.OUT == xv1.REG_OUT
if AMEND is None and os.path.exists(xv1.OUT + 'LEDGER.jsonl'): sys.exit('already registered')   # v7: a registry file without ledger line 0 (interrupted run) is written again
if AMEND is not None and not os.path.exists(xv1.OUT + 'LEDGER.jsonl'): sys.exit('not registered: nothing to amend')
# exercise every code path on the <= 2014 calendar, so that every project code file is loaded before the hashes are taken
X = xv1.frame(xv1.OLD_END); pre = xv1._prepare(xv1.ref, (), xv1.OLD_END); xv1._design_account(pre=pre)
for mk in (xv1.hold1, xv1.hold3): xv1._design_account(mk, end=xv1.OLD_END)
names = sorted(set(n for c in m_batch1.configs() for n in c.names) | {'ret:TQQQ'}); xv1.extras(names, X.index)
r1 = xv1.prefix_test(xv1.ref, end=xv1.OLD_END, n_rand=5, n_event=20, pre=pre)['result']
r2 = xv1.raw_extras_test(names, end=xv1.OLD_END, n_rand=2)['result']
print('prefix test of v1 (<= 2014):', r1, '| raw-level test of the inputs (<= 2014):', r2)
if r1 != 'PASS' or r2 != 'PASS': sys.exit('a self-check failed: nothing written')              # v7
if AMEND is not None:
    n = xv1.amend(AMEND); assert xv1._registered(); xv1._check_env()
    print('amendment', n, '| ledger line:', xv1.read_ledger()[-1]); sys.exit(0)
os.makedirs(xv1.OUT, exist_ok=True); shutil.copyfile(SRC, xv1.OUT + 'PREREG_XV1_STRUCTURE.md')
sha = xv1._sha(xv1.OUT + 'PREREG_XV1_STRUCTURE.md'); body = xv1.registry_body(sha); H = json.loads(body)
xv1._write_registry(body)
xv1.ledger(dict(kind='registration', sha256=sha, owner_message=OWNER_MESSAGE, hashes_sha256=hashlib.sha256(body).hexdigest()))
assert xv1._registered(); xv1._check_env()
print('registered text sha256', sha)
print('data files', len(H['data']), '| code files', len(H['code']), '| scripts', len(H['scripts']), '| packages', H['packages'])
print('ledger line 0:', xv1.read_ledger()[0])
