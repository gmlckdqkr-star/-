"""Registration of the XV1 structure. Run once, after the self-tests and the independent verification, before any real row
after 2014-12-31 is read by the evaluator.

Writes to research/xv1/: PREREG_XV1_STRUCTURE.md (copy of the registered text), HASHES.json (sha256 of the text, of every
data file of the chain, of the evaluator files and of every project code file loaded by a full exercise of the evaluator on
the <= 2014 calendar, the package versions and the registered constants) and ledger line 0 (kind 'registration': the sha256
of the text and the id of the owner's message). Nothing after 2014 is read here."""
import sys, os, json, shutil, hashlib
sys.path.insert(0, '/home/user/-/research_xv1/code')
import xv1, m_batch1

SRC = '/home/user/-/research_xv1/PREREG_XV1_STRUCTURE.md'
OWNER_MESSAGE = 'cmsg_013GuJ2gSecTDkpekhQ7SWhg47X7ADtvr4d67q4nBbKHKk'
assert xv1.WORLD is None and xv1.OUT == xv1.REG_OUT
if os.path.exists(xv1.OUT + 'HASHES.json') or os.path.exists(xv1.OUT + 'LEDGER.jsonl'): sys.exit('already registered')
# exercise every code path on the <= 2014 calendar, so that every project code file is loaded before the hashes are taken
X = xv1.frame(xv1.OLD_END); pre = xv1._prepare(xv1.ref, (), xv1.OLD_END); xv1._design_account(pre=pre)
for mk in (xv1.hold1, xv1.hold3): xv1._design_account(mk, end=xv1.OLD_END)
names = sorted(set(n for c in m_batch1.configs() for n in c.names) | {'ret:TQQQ'}); xv1.extras(names, X.index)
print('prefix test of v1 (<= 2014):', xv1.prefix_test(None, end=xv1.OLD_END, n_rand=5, n_event=20, pre=pre)['result'],
      '| raw-level test of the inputs (<= 2014):', xv1.raw_extras_test(names, end=xv1.OLD_END, n_rand=2)['result'])
os.makedirs(xv1.OUT, exist_ok=True); shutil.copyfile(SRC, xv1.OUT + 'PREREG_XV1_STRUCTURE.md')
sha = xv1._sha(xv1.OUT + 'PREREG_XV1_STRUCTURE.md'); H = dict(prereg_sha256=sha, **xv1.env_hashes())
d = os.path.dirname(os.path.abspath(__file__))
H['scripts'] = {f: xv1._sha(os.path.join(d, f)) for f in sorted(os.listdir(d)) if f.endswith('.py') and os.path.join(d, f) not in H['code']}   # recorded, not enforced
json.dump(H, open(xv1.OUT + 'HASHES.json', 'w'), indent=1, sort_keys=True)
xv1.ledger(dict(kind='registration', sha256=sha, owner_message=OWNER_MESSAGE, hashes_sha256=xv1._sha(xv1.OUT + 'HASHES.json')))
assert xv1._registered(); xv1._check_env()
print('registered text sha256', sha)
print('data files', len(H['data']), '| code files', len(H['code']), '| packages', H['packages'])
print('ledger line 0:', xv1.read_ledger()[0])
