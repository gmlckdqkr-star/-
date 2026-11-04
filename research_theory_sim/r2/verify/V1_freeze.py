"""V1 check 1: freeze integrity. Every sha256 in r2/FREEZE_TS2.txt vs the current file; rule.py hashes inside git commit
4a57503 (read-only git show); t0/t1 of test/out/real_*.json vs the freeze time. No market data touched."""
import re, os, json, hashlib, subprocess, datetime as dt
TS = '/mnt/project-files/research/theory_sim/'; R2 = TS + 'r2/'; REPO = '/home/user/-'
lines = open(R2 + 'FREEZE_TS2.txt').read().splitlines()
res = dict(header=lines[:2], entries=0, match=0, mismatch=[], missing=[], unlisted_design_files=[])
listed = set()
for l in lines:
    m = re.match(r'^([0-9a-f]{64})  (.+)$', l)
    if not m: continue
    h, p = m.groups(); listed.add(p); res['entries'] += 1
    fp = (TS if p in ('common/exec_engine.py', 'design/L1/rule.py') else R2) + p
    if not os.path.exists(fp): res['missing'].append(p); continue
    hh = hashlib.sha256(open(fp, 'rb').read()).hexdigest()
    if hh == h: res['match'] += 1
    else: res['mismatch'].append((p, h, hh))
for root, ds, fs in os.walk(R2 + 'design'):
    for f in fs:
        p = os.path.relpath(os.path.join(root, f), R2)
        if '__pycache__' not in p and not p.endswith('.pyc') and p not in listed: res['unlisted_design_files'].append(p)


def git(*a): return subprocess.run(['git', '-C', REPO] + list(a), capture_output=True, text=True).stdout


res['commit'] = git('log', '-1', '--format=%H %cI %s', '4a57503').strip()
res['commit_on_remote_branch'] = 'origin/claude/project-thread-hhwozh' in git('branch', '-a', '--contains', '4a57503')
fz = {l.split()[1]: l.split()[0] for l in lines if re.match(r'^[0-9a-f]{64}  ', l)}
res['git_rule_hashes'] = {}
for L in 'ABCD':
    b = subprocess.run(['git', '-C', REPO, 'show', '4a57503:research_theory_sim/r2/design/%s/rule.py' % L], capture_output=True).stdout
    g = hashlib.sha256(b).hexdigest(); cur = hashlib.sha256(open(R2 + 'design/%s/rule.py' % L, 'rb').read()).hexdigest()
    res['git_rule_hashes'][L] = dict(git=g, freeze=fz['design/%s/rule.py' % L], current=cur, all_equal=(g == cur == fz['design/%s/rule.py' % L]))
b = subprocess.run(['git', '-C', REPO, 'show', '4a57503:research_theory_sim/r2/FREEZE_TS2.txt'], capture_output=True).stdout
res['git_freeze_file_equal'] = hashlib.sha256(b).hexdigest() == hashlib.sha256(open(R2 + 'FREEZE_TS2.txt', 'rb').read()).hexdigest()
# git tree vs freeze list for design files
tree = set(x[len('research_theory_sim/r2/'):] for x in git('ls-tree', '-r', '--name-only', '4a57503').split() if x.startswith('research_theory_sim/r2/design/'))
res['git_tree_design_files'] = len(tree); res['freeze_design_files'] = sum(1 for p in fz if p.startswith('design/') and p != 'design/L1/rule.py')
res['design_files_in_freeze_not_in_git'] = sorted(p for p in fz if p.startswith('design/') and p != 'design/L1/rule.py' and p not in tree)
# git blob hashes for every frozen design file
bad = []
for p in sorted(fz):
    if not p.startswith('design/') or p == 'design/L1/rule.py': continue
    b = subprocess.run(['git', '-C', REPO, 'show', '4a57503:research_theory_sim/r2/' + p], capture_output=True).stdout
    if hashlib.sha256(b).hexdigest() != fz[p]: bad.append(p)
res['git_blob_vs_freeze_mismatch'] = bad
# also test code + std.py
res['harness_r2_sha_now'] = hashlib.sha256(open(R2 + 'test/harness_r2.py', 'rb').read()).hexdigest()
res['std_py_sha12'] = hashlib.sha256(open('/mnt/project-files/research/measure_std/std.py', 'rb').read()).hexdigest()[:12]
ft = dt.datetime.strptime(lines[0].split()[2], '%Y-%m-%dT%H:%MZ')
res['freeze_time'] = lines[0].split()[2]
res['real_json_times'] = {}
for L in 'ABCD':
    R = json.load(open(R2 + 'test/out/real_%s.json' % L))
    t0 = dt.datetime.strptime(R['t0'], '%Y-%m-%dT%H:%MZ')
    res['real_json_times'][L] = dict(t0=R['t0'], t1=R['t1'], t0_ge_freeze=t0 >= ft, t0_gt_freeze_minute=t0 > ft,
                                     json_mtime=dt.datetime.utcfromtimestamp(os.path.getmtime(R2 + 'test/out/real_%s.json' % L)).isoformat())
res['val_runs'] = {f: dt.datetime.utcfromtimestamp(os.path.getmtime(R2 + 'test/out/' + f)).isoformat() for f in os.listdir(R2 + 'test/out') if f.startswith('val_')}
print(json.dumps(res, indent=1))
json.dump(res, open(R2 + 'verify/V1_freeze.json', 'w'), indent=1)
