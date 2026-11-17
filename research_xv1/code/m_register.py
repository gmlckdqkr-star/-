"""Registration of the XV1 structure. Run once, after the self-tests and the independent verification, before any real row
after 2014-12-31 is read by the evaluator.

Writes to research/xv1/: PREREG_XV1_STRUCTURE.md (copy of the registered text), HASHES.json (sha256 of the text, of every
data file of the chain, of the evaluator files and of every project code file loaded by a full exercise of the evaluator on
the <= 2014 calendar, the package versions and the registered constants) and ledger line 0 (kind 'registration': the sha256
of the text, the sha256 of HASHES.json and the id of the owner's message). Nothing after 2014 is read here.

  python m_register.py                    the one-time registration
  python m_register.py --amend FILE.md [--drop KEY,KEY]
                                          v7: take the registry again after a change that section 7 of the text allows
                                          (FILE.md says what changed and lists every output that existed before; --drop
                                          names registry keys of code files that left the chain)

v8: the files of the repository folder research_xv1 are committed and pushed first; the script refuses otherwise and prints
the commit (it hashes the bytes of the working tree, and a container that is replaced keeps only what was pushed)."""
import os
import sys, json, shutil, hashlib, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xv1, m_batch1

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'PREREG_XV1_STRUCTURE.md')
OWNER_MESSAGE = 'cmsg_013GuJ2gSecTDkpekhQ7SWhg47X7ADtvr4d67q4nBbKHKk'
AMEND = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == '--amend' else None
DROP = tuple(sys.argv[4].split(',')) if len(sys.argv) > 4 and sys.argv[3] == '--drop' else ()
assert xv1.WORLD is None and xv1.OUT == xv1.REG_OUT
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_git = lambda *a: subprocess.run(('git', '-C', _REPO) + a, capture_output=True, text=True)
_st, _hd, _up = _git('status', '--porcelain', '--', 'research_xv1'), _git('rev-parse', 'HEAD'), _git('rev-parse', '@{u}')
if _st.returncode != 0 or _hd.returncode != 0 or _st.stdout.strip():   # v8
    sys.exit('files of research_xv1 are not committed (git status is not clean): commit and push first; nothing written')
if _up.returncode != 0 or _up.stdout.strip() != _hd.stdout.strip():
    sys.exit('the commit of research_xv1 is not pushed (HEAD differs from its upstream branch): push first; nothing written')
print('repository commit of the files:', _hd.stdout.strip())
LED = xv1.OUT + 'LEDGER.jsonl'; HAS = os.path.exists(LED) and os.path.getsize(LED) > 0   # v7: an empty file (line 0 was cut and removed) is no ledger
if AMEND is None and (HAS or xv1._mirror_bytes()):   # v7: a registry file without ledger line 0 (interrupted run) is written again
    sys.exit('already registered (a ledger that is missing or behind its repository copy is restored by xv1.repair_ledger)')
if AMEND is not None and not HAS:
    sys.exit('the ledger is missing or empty but its repository copy exists: run xv1.repair_ledger() first' if xv1._mirror_bytes() else 'not registered: nothing to amend')
# exercise every code path on the <= 2014 calendar, so that every project code file is loaded before the hashes are taken
X = xv1.frame(xv1.OLD_END); pre = xv1._prepare(xv1.ref, (), xv1.OLD_END); xv1._design_account(pre=pre)
for mk in (xv1.hold1, xv1.hold3): xv1._design_account(mk, end=xv1.OLD_END)
names = sorted(set(n for c in m_batch1.configs() for n in c.names) | {'ret:TQQQ'}); xv1.extras(names, X.index)
r1 = xv1.prefix_test(xv1.ref, end=xv1.OLD_END, n_rand=5, n_event=20, pre=pre)['result']
r2 = xv1.raw_extras_test(names, end=xv1.OLD_END, n_rand=2)['result']
print('prefix test of v1 (<= 2014):', r1, '| raw-level test of the inputs (<= 2014):', r2)
if r1 != 'PASS' or r2 != 'PASS': sys.exit('a self-check failed: nothing written')              # v7
if AMEND is not None:
    n = xv1.amend(AMEND, DROP); assert xv1._registered(); xv1._check_env()
    print('amendment', n, '| ledger line:', xv1.read_ledger()[-1]); sys.exit(0)
os.makedirs(xv1.OUT, exist_ok=True); shutil.copyfile(SRC, xv1.OUT + 'PREREG_XV1_STRUCTURE.md')
sha = xv1._sha(xv1.OUT + 'PREREG_XV1_STRUCTURE.md'); body = xv1.registry_body(sha); H = json.loads(body)
xv1._write_registry(body)
xv1.ledger(dict(kind='registration', sha256=sha, owner_message=OWNER_MESSAGE, hashes_sha256=hashlib.sha256(body).hexdigest()))
assert xv1._registered(); xv1._check_env()
print('registered text sha256', sha)
print('data files', len(H['data']), '| code files', len(H['code']), '| scripts', len(H['scripts']), '| packages', H['packages'])
print('ledger line 0:', xv1.read_ledger()[0])
