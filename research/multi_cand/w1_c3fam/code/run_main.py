"""MC1 W1 main run: references + parity, H1 (AV23 anatomy), H4 (order step), H5 (tax-day brake input), H2 (sub-accounts),
H3 (lever generality, selection rule fixed in PRECOMMIT_W1), then stress + time-shift null for passers only.
Output: results/main.json, results/log_main.txt. Usage: nice -n 10 python3 run_main.py"""
import os, sys, json, time, numpy as np
os.environ['NUMBA_NUM_THREADS'] = '2'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m1
from m1 import np, rx, ce, ID, Z, AV23, B85, av, w1b, w1t
RES = '/mnt/project-files/research/multi_cand/w1_c3fam/results/'
T0 = time.time()
LOG = open(RES + 'log_main.txt', 'a')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); LOG.write(s + '\n'); LOG.flush()

def P2(m0, m1_, base=None): return np.concatenate([np.array([float(m0), float(m1_)]), AV23 if base is None else base])

# ---------------------------------------------------------------- config registry
CFG = {
 # components / references (not trials)
 'c3raw':  dict(kind='eng', sig='c3', bfn=ID, bp=Z),
 'av23':   dict(kind='eng', sig='c3', bfn=ce.alt, bp=AV23),
 's085':   dict(kind='eng', sig='c3', bfn=rx.av23s, bp=B85),
 'volsw':  dict(kind='eng', sig='volsw', bfn=ID, bp=Z),
 'macro':  dict(kind='eng', sig='macro', bfn=ID, bp=Z),
 'volsw_av23': dict(kind='eng', sig='volsw', bfn=ce.alt, bp=AV23),
 'macro_av23': dict(kind='eng', sig='macro', bfn=ce.alt, bp=AV23),
 # parity checks (not trials)
 'chk_w1b_raw':  dict(kind='eng', sig='c3', bfn=w1b, bp=P2(1, 1)),
 'chk_w1b_av23': dict(kind='eng', sig='c3', bfn=w1b, bp=P2(0, 0)),
 'chk_w1t_s085': dict(kind='eng', sig='c3', bfn=w1t, bp=P2(0, .85)),
 'chk_w1t_av23': dict(kind='eng', sig='c3', bfn=w1t, bp=P2(0, 1.0)),
 # H1 AV23 anatomy on C3 raw
 'H1a_Nf1_Wraw':        dict(kind='eng', sig='c3', bfn=w1b, bp=P2(0, 1), base=['c3raw', 's085']),
 'H1b_Nraw_Wav23':      dict(kind='eng', sig='c3', bfn=w1b, bp=P2(1, 0), base=['c3raw', 's085']),
 'H1c_Nraw_Wcush':      dict(kind='eng', sig='c3', bfn=w1b, bp=P2(1, 0, av(gs=0, eb=0, rm=0)), base=['c3raw', 's085']),
 'H1d_Nraw_Wcrash':     dict(kind='eng', sig='c3', bfn=w1b, bp=P2(1, 2), base=['c3raw', 's085']),
 'H1e_crash_all':       dict(kind='eng', sig='c3', bfn=w1b, bp=P2(2, 2), base=['c3raw', 's085']),
 'H1f_crash_anti_all':  dict(kind='eng', sig='c3', bfn=w1b, bp=P2(3, 3), base=['c3raw', 's085']),
 'H1g_Nf1_Wcrash':      dict(kind='eng', sig='c3', bfn=w1b, bp=P2(0, 2), base=['c3raw', 's085']),
 'H1h_Ncrashanti_Wav23': dict(kind='eng', sig='c3', bfn=w1b, bp=P2(3, 0), base=['c3raw', 's085']),
 'H1i_av23_no_gcg':     dict(kind='eng', sig='c3', bfn=ce.alt, bp=av(gcg=1.0), base=['av23', 's085']),
 'H1j_av23_no_crash':   dict(kind='eng', sig='c3', bfn=ce.alt, bp=av(gs=0.0), base=['av23', 's085']),
 'H1k_av23_no_anti':    dict(kind='eng', sig='c3', bfn=ce.alt, bp=av(eb=0.0), base=['av23', 's085']),
 # H4 order step
 'H4a_s085_step1':      dict(kind='eng', sig='c3', bfn=rx.av23s, bp=B85, kw=dict(step=1.0), base=['s085']),
 'H4b_av23_step1':      dict(kind='eng', sig='c3', bfn=ce.alt, bp=AV23, kw=dict(step=1.0), base=['av23']),
 'H4c_s085_step025':    dict(kind='eng', sig='c3', bfn=rx.av23s, bp=B85, kw=dict(step=0.25), base=['s085']),
 # H5 tax-day adjusted brake input
 'H5a_s085_taxadj':     dict(kind='eng', sig='c3', bfn=w1t, bp=P2(1, .85), base=['s085']),
 'H5b_av23_taxadj':     dict(kind='eng', sig='c3', bfn=w1t, bp=P2(1, 1.0), base=['av23']),
 # H2 sub-accounts
 'H2a_raw50_av23_never':  dict(kind='mix', A='c3raw', B='av23', x=.5, rebal=False, base=['s085', 'c3raw']),
 'H2b_raw70_av23_never':  dict(kind='mix', A='c3raw', B='av23', x=.7, rebal=False, base=['s085', 'c3raw']),
 'H2c_raw50_s085_never':  dict(kind='mix', A='c3raw', B='s085', x=.5, rebal=False, base=['s085', 'c3raw']),
 'H2d_raw70_s085_never':  dict(kind='mix', A='c3raw', B='s085', x=.7, rebal=False, base=['s085', 'c3raw']),
 'H2e_raw50_av23_yearly': dict(kind='mix', A='c3raw', B='av23', x=.5, rebal=True, base=['s085', 'c3raw']),
 'H2f_raw70_av23_yearly': dict(kind='mix', A='c3raw', B='av23', x=.7, rebal=True, base=['s085', 'c3raw']),
 'H2g_raw50_s085_yearly': dict(kind='mix', A='c3raw', B='s085', x=.5, rebal=True, base=['s085', 'c3raw']),
 'H2h_raw70_s085_yearly': dict(kind='mix', A='c3raw', B='s085', x=.7, rebal=True, base=['s085', 'c3raw']),
}
TRIALS_H1 = [k for k in CFG if k.startswith('H1')]; TRIALS_H2 = [k for k in CFG if k.startswith('H2')]
TRIALS_H45 = [k for k in CFG if k[:2] in ('H4', 'H5')]

_RUN = {}
def get(name, kw=None, shift=0, keepE=False):
    kw = dict(kw or {}); key = (name, tuple(sorted(kw.items())), shift)
    if key in _RUN and (not keepE or 'E' in _RUN[key]['dev250_path']):
        return _RUN[key]
    c = CFG[name]
    if c['kind'] == 'eng':
        k2 = dict(c.get('kw', {})); k2.update(kw)
        spec = lambda ctx, bn: (m1.sig(c['sig'], ctx, bn, shift), c['bfn'], c['bp'], 0.1, k2)
        R = m1.run(spec, keepE=keepE)
    else:
        RA = get(c['A'], kw, shift, keepE=True); RB = get(c['B'], kw, shift, keepE=True)
        R = m1.mix(RA, RB, c['x'], rebal=c['rebal'], ttax=c.get('ttax', True))
    _RUN[key] = R
    return R

def evaluate(name, kw=None, shift=0):
    c = CFG[name]; R = get(name, kw, shift)
    refs = {'s085': get('s085', kw, shift)}
    for b in c.get('base', []): refs[b] = get(b, kw, shift)
    st = m1.stats(R, refs)
    out = dict(stats=st)
    if not kw and not shift:
        base_st = {b: m1.stats(get(b), {'s085': get('s085')}) for b in c.get('base', [])}
        out['verdict'] = {b: m1.verdict(st, b, base_st[b]) for b in c.get('base', [])}
    return out

RESULT = dict(meta=dict(note='MS1 std engine via m1.py, <=2014; numbers are fractions', precommit_sha='4a1deb59'), refs={}, parity={}, trials={}, stress={}, null={})
def save(): json.dump(RESULT, open(RES + 'main.json', 'w'), indent=1)

# ---------------------------------------------------------------- 1. references + parity
log('== start', time.strftime('%FT%TZ', time.gmtime()))
RESULT['holds'] = m1.holds(); log('holds', RESULT['holds']['dev250_path'])
for r in ['s085', 'c3raw', 'av23', 'volsw', 'macro', 'volsw_av23', 'macro_av23']:
    st = m1.stats(get(r, keepE=r in ('c3raw', 'av23', 's085', 'volsw', 'macro', 'volsw_av23', 'macro_av23')), {'s085': get('s085')})
    RESULT['refs'][r] = st
    p = st['dev250_path']
    log('REF %-11s path %.2f%% dd80 %.0f%% p10 %.2f | glued %.2f realNDX %.2f SPX55 %.2f SPX70 %.2f  [%.0fs]' % (r, 100 * p['cagr'], 100 * p['dd80'], 100 * p['p10'],
        100 * st['dev250_glued']['cagr'], 100 * st['real_ndx_86_14']['cagr'], 100 * st['real_spx_55_85']['cagr'], 100 * st['real_spx_70_85']['cagr'], time.time() - T0))
save()
for chk, ref in [('chk_w1b_raw', 'c3raw'), ('chk_w1b_av23', 'av23'), ('chk_w1t_s085', 's085'), ('chk_w1t_av23', 'av23')]:
    A = get(chk); Bq = get(ref)
    mx = max(float(np.max(np.abs(A[b]['fin'] - Bq[b]['fin']))) for b in m1.BASES)
    RESULT['parity'][chk] = mx; log('PARITY %s vs %s max |d cagr| = %.2e' % (chk, ref, mx))
save()

# ---------------------------------------------------------------- 2. trials H1, H4, H5, H2
def do(name):
    o = evaluate(name); RESULT['trials'][name] = o; save()
    st = o['stats']; b0 = CFG[name]['base'][0]
    log(m1.line(name, st, b0), '| verdict', {b: ('IMPROVE' if v['improve'] else 'PARETO' if v['pareto'] else '-') for b, v in o['verdict'].items()}, '[%.0fs]' % (time.time() - T0))
for n in TRIALS_H1 + TRIALS_H45 + TRIALS_H2: do(n)
# H2 reference upper bound (no transfer tax) for the yearly versions: reported only, not a trial
for n in TRIALS_H2:
    if CFG[n]['rebal']:
        nn = n + '_notransfertax'; CFG[nn] = dict(CFG[n]); CFG[nn]['ttax'] = False
        st = evaluate(nn)['stats']; RESULT.setdefault('h2_upper', {})[nn] = st
        log('  upper(no transfer tax)', m1.line(nn, st, 's085'))
save()

# ---------------------------------------------------------------- 3. H3 selection rule (fixed in PRECOMMIT_W1)
def rank_key(n):
    v = RESULT['trials'][n]['verdict']; st = RESULT['trials'][n]['stats']['dev250_path']
    return (any(x['improve'] for x in v.values()), any(x['pareto'] for x in v.values()), st['d_s085'])
cand = TRIALS_H1 + TRIALS_H2
best = max(cand, key=rank_key); RESULT['h3_lever'] = best; log('H3 lever =', best, rank_key(best))
bc = CFG[best]
for sg, base in (('volsw', 'volsw'), ('macro', 'macro')):
    tag = 'H3a' if sg == 'volsw' else 'H3b'
    if bc['kind'] == 'eng':
        CFG[tag + '_' + sg + '_' + best] = dict(kind='eng', sig=sg, bfn=bc['bfn'], bp=bc['bp'], kw=bc.get('kw', {}), base=[base, 's085'])
    else:
        brk = sg + '_av23' if bc['B'] == 'av23' else None
        if brk is None:   # B = s085-type brake on this signal
            CFG[sg + '_s085'] = dict(kind='eng', sig=sg, bfn=rx.av23s, bp=B85); brk = sg + '_s085'
        CFG[tag + '_' + sg + '_' + best] = dict(kind='mix', A=sg, B=brk, x=bc['x'], rebal=bc['rebal'], base=[base, 's085'])
    tagc = 'H3c' if sg == 'volsw' else 'H3d'
    CFG[tagc + '_' + sg + '_raw50_av23_never'] = dict(kind='mix', A=sg, B=sg + '_av23', x=.5, rebal=False, base=[base, 's085'])
TRIALS_H3 = [k for k in CFG if k.startswith('H3')]
for n in TRIALS_H3: do(n)

# ---------------------------------------------------------------- 4. stress + null for passers only
passers = [n for n in RESULT['trials'] if any(v['improve'] or v['pareto'] for v in RESULT['trials'][n]['verdict'].values())]
RESULT['passers'] = passers; log('passers:', passers); save()
for n in passers:
    for lab, kw in (('delay3', dict(delay=3)), ('delay5', dict(delay=5)), ('cost2x', dict(cost=0.006))):
        st = evaluate(n, kw=kw)['stats']; RESULT['stress'].setdefault(n, {})[lab] = st
        log('  STRESS %s %s' % (lab, m1.line(n, st, CFG[n]['base'][0])))
        save()
    for sh in (1800, 2700, 3600):
        st = evaluate(n, shift=sh)['stats']; RESULT['null'].setdefault(n, {})[str(sh)] = st
        log('  NULL shift %d %s' % (sh, m1.line(n, st, CFG[n]['base'][0])))
        save()
log('== done [%.0fs]' % (time.time() - T0))
