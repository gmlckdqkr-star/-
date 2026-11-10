"""Fill the report templates with tables generated from the result files.
  python -B code/build_report.py        -> RESULT_ONF1_KO.md (<=2014 only)
  ONF1_ALLOW_HOLDOUT=1 python -B code/build_report.py   -> also holdout/RESULT_ONF1_FULL_KO.md (contains post-2014 numbers)"""
import subprocess, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
PY = sys.executable; H = paths.ROOT + '/'
def tab(which): return subprocess.run([PY, '-B', H + 'code/make_tables.py', which], capture_output=True, text=True, check=True).stdout.strip()
def fill(tmpl, tabs):
    t = open(tmpl).read()
    for k, v in tabs.items(): t = t.replace('{{%s}}' % k, v)
    assert '{{' not in t, [x.split('}}')[0] for x in t.split('{{')[1:]]
    return t
T = dict(MS1_TABLE=tab('ms1'), SENS_TABLE=tab('sens'), DEV_TABLE=tab('dev'), DEVX_TABLE=tab('devx'))
le = fill(H + 'code/report_le2014.tmpl.md', T)
open(H + 'RESULT_ONF1_KO.md', 'w').write(le); print('ok le2014', len(le))
if os.environ.get('ONF1_ALLOW_HOLDOUT') == '1':
    T.update(HOLD_TABLE=tab('holdout'), HOLDX_TABLE=tab('holdx'))
    full = fill(H + 'holdout/report_full.tmpl.md', T)
    open(H + 'holdout/RESULT_ONF1_FULL_KO.md', 'w').write(full); print('ok full', len(full))
