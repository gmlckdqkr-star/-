"""<= 2014 only: mechanics of batch registration, prefix and level-scale voiding, family-wise test and the G1 / G2 / G3 guards, with
dummy candidates. The calendar is forced to end 2014-12-31 (so the design account has no removed rows) and the ledger goes to a
scratch folder. Nothing here is a research result."""
import sys, os, json, shutil, numpy as np
sys.path.insert(0, '/home/user/-/research_xv1/code')
import xv1
tmp = sys.argv[1]; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
xv1.OUT = tmp + '/'; xv1.A_END = xv1.OLD_END; xv1.CAL_END = xv1.OLD_END; xv1.DESIGN = (1, 3, 5, 7, 9)
F = '/home/user/-/research_xv1/code/t_cand_dummy.py'
cfgs = [xv1.Config('noise', 'noise%d' % i, F, 'noise_cut', dict(seed=i, share=0.05)) for i in range(6)] + \
       [xv1.Config('leak', 'leak3', F, 'leak', dict(look=3)), xv1.Config('chips', 'chips10', F, 'chips_sleeve', dict(w=0.1), names=('chips',)),
        xv1.Config('state', 'stateful', F, 'stateful'), xv1.Config('era', 'era', F, 'era')]
print('registered batch sha', xv1.register_batch(1, cfgs)[:12])
try: xv1.register_batch(1, cfgs); print('ERROR: second registration accepted')
except FileExistsError: print('second registration refused: ok')
out = xv1.run_batch(1)
for h, o in out['results'].items():
    if 'void' in o: print('%-8s VOID (%s) %s' % (o['name'], o['void'], {k: o['prefix'][k] for k in ('result', 'failed_cuts')}))
    else: print('%-8s d %+6.2f d* %+6.2f te %5.1f t63 %+5.2f p_family %.3f active blocks %d harm %s g1 %s type %s advance %s | extra w %.3f | prefix %s' % (
        o['name'], 100 * o['d'], 100 * o['d_star'], 100 * o['te'], o['t63'], o['p_family'], o['active_blocks'], o['harm'], ''.join('Y' if x else 'n' for x in o['g1'].values()),
        o['kind'], o['advance'], o['extra_weight_mean'], o['prefix']['result']))
c0 = cfgs[0]
for nm, f in (('weak before G1 pass', lambda: xv1.weak_eval(c0)), ('G3 without passes', lambda: xv1.open_g3(c0)),
              ('main account without token', lambda: xv1._main_account(xv1.ref)),
              ('unregistered batch', lambda: xv1.load_batch(2))):
    try: f(); print('ERROR: %s was allowed' % nm)
    except (PermissionError, FileNotFoundError) as e: print('%-28s refused: %s' % (nm, type(e).__name__))
# tamper: change a parameter after registration
b = json.load(open(xv1.OUT + 'BATCH_1.json')); b[0]['params']['share'] = 0.06; json.dump(b, open(xv1.OUT + 'BATCH_1.json', 'w'), indent=1, sort_keys=True)
try: xv1.load_batch(1); print('ERROR: tampered batch accepted')
except PermissionError: print('tampered batch refused: ok')
L = xv1.read_ledger(); print('ledger lines', len(L), 'kinds', sorted(set(e['kind'] for e in L)))
shutil.rmtree(tmp)
