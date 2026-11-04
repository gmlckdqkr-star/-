"""selection grid on selection seeds (2, 3), P=1000 each, mechanism ON and OFF."""
from harness import *
from clock import clock_rule
import itertools, pickle
SEEDS = (2, 3); P = 1000
W = {}
def get(sd, mech):
    if (sd, mech) not in W:
        w = sim.simulate(P, T, sd, mechanism=mech); w.pop('y10'); W[(sd, mech)] = w
    return W[(sd, mech)]
BASE_FILE = 'base_s23.json'
def base():
    try: return json.load(open(BASE_FILE))
    except Exception: pass
    out = {}
    for mech in (True, False):
        r = [baselines(get(sd, mech)) for sd in SEEDS]
        out['ON' if mech else 'OFF'] = dict(hold1=np.mean([x['hold1'] for x in r]),
            const={str(L): np.mean([x['const'][L] for x in r]) for L in r[0]['const']})
    json.dump(out, open(BASE_FILE, 'w')); return out
def run_variant(name, kw, fn=clock_rule):
    res = {}
    for mech in (True, False):
        cs = []
        for sd in SEEDS:
            w = get(sd, mech); B = fn(close_of(w['r']), **kw); s = evaluate(B, w)
            cs.append((s['cagr_med'], s['avg_level_med'], s['trades_per_year_med']))
        res['ON' if mech else 'OFF'] = tuple(np.mean(cs, axis=0))
    n = bump(1, name)
    b = base()
    on, off = res['ON'], res['OFF']
    bc_on = max(b['ON']['const'].values()); bc_off = max(b['OFF']['const'].values())
    print('%-58s ON %+.4f (vs h1 %+.4f, vs bc %+.4f; L %.2f tr %.1f) OFF %+.4f (vs bc %+.4f; L %.2f tr %.1f) N=%d' % (
        name, on[0], on[0] - b['ON']['hold1'], on[0] - bc_on, on[1], on[2], off[0], off[0] - bc_off, off[1], off[2], n), flush=True)
    return res
if __name__ == '__main__':
    print(json.dumps(base()))
    for p0, th, hm in itertools.product((0.0, 0.01, 0.02), (1.25, 1.3, 1.35, 1.45), (25, 40)):
        run_variant('exit p0=%.2f th=%.2f hl_m=%d' % (p0, th, hm), dict(p0=p0, th_c=th, hl_m=hm, L_r=0.0))
