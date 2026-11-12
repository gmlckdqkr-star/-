"""FRESH1 C-VT: volatility-scaled trend ladder, exactly as PREREG_C1_FRESH1.md. Locked MS1 engine, <=2014 only.
Usage: python -B c_vt.py   (run from /home/user)"""
import sys, json, itertools, numpy as np
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std
ov = std.ov
C = std.contexts()
BASES = ['dev250_path', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85']
OUT = {}


def trend_T(c):
    lvl = c.lvl; P, T = lvl.shape
    cash = np.cumprod(1 + c.rf, axis=1)
    a = lvl > c.sma(200)                                             # NaN sma -> False
    b = np.zeros((P, T), bool); b[:, 126:] = lvl[:, 126:] / lvl[:, :-126] > cash[:, 126:] / cash[:, :-126]
    d = np.zeros((P, T), bool); d[:, 252:] = lvl[:, 252:] / lvl[:, :-252] > cash[:, 252:] / cash[:, :-252]
    return (a.astype(float) + b + d) / 3


def ew_sigma(c, hl):
    lam = 0.5 ** (1 / hl); r2 = c.r * c.r; P, T = r2.shape
    v = np.empty((P, T)); x = r2[:, 1:61].mean(axis=1)               # seed: first 60 real days (r[:,0] is forced to 0)
    for t in range(T):
        if t >= 61: x = lam * x + (1 - lam) * r2[:, t]
        v[:, t] = x
    return np.sqrt(252 * v)


def make_B(c, target, hl, cap):
    B = trend_T(c) * np.minimum(cap, target / np.maximum(ew_sigma(c, hl), 1e-9))
    B[:, :252] = 0.0
    return B


def run(c, target, hl, band, cap, **kw):
    B = make_B(c, target, hl, cap)
    return std.engine(c, B, std.ident, np.zeros(1), band, step=band, **kw)


def boot_p(d, block=250, n=2000, seed=11):
    g = np.random.default_rng(seed); L = len(d); nb = L // block + 1
    st = g.integers(0, L - block, (n, nb)); idx = (st[:, :, None] + np.arange(block)[None, None, :]).reshape(n, -1)[:, :L]
    m = d[idx].mean(axis=1)
    return float(np.mean(m > 0)), float(np.percentile(m, 10) * 252), float(d.mean() * 252)


V1 = {}
for bn in BASES:
    c = C[bn]; B, bfn, bp, fs = std.s085(c); V1[bn] = std.engine(c, B, bfn, bp, fs)
ref = {bn: float(np.median(V1[bn][0])) for bn in BASES}
OUT['v1'] = dict(ref, dd80_path=float(np.mean(std.ce.mdd(V1['dev250_path'][1]) <= -0.8)))
print('v1', OUT['v1'], flush=True)

# ---- primary and CAP 2
for nm, cap in (('PRIMARY_cap3', 3.0), ('cap2', 2.0)):
    o = {}
    for bn in BASES:
        c = C[bn]; f, E = run(c, 0.40, 20, 0.25, cap); m = std.ce.mdd(E); d = f - V1[bn][0]
        o[bn] = dict(cagr=float(np.median(f)), mdd=float(np.median(m)), d_vs_v1=float(np.median(d)))
        if bn == 'dev250_path':
            o[bn].update(p10=float(np.percentile(f, 10)), p90=float(np.percentile(f, 90)), dd80=float(np.mean(m <= -0.8)), win_share=float(np.mean(d > 1e-5)))
            f7, _ = run(c, 0.40, 20, 0.25, cap, delay=7); o[bn]['delay7_cagr'] = float(np.median(f7)); o[bn]['delay7_d_vs_v1'] = float(np.median(f7 - V1[bn][0]))
            B = make_B(c, 0.40, 20, cap); o[bn]['mean_target_level'] = float(B[:, ov.WARM:].mean())
    if nm == 'PRIMARY_cap3':
        dl = []
        for bn in ('real_spx_55_85', 'real_ndx_86_14'):
            _, E = run(C[bn], 0.40, 20, 0.25, cap); dl.append(np.diff(np.log(E[0])) - np.diff(np.log(V1[bn][1][0])))
        d = np.concatenate(dl); p, lo10, mean = boot_p(d)
        o['gate_i'] = dict(p_gt0=p, lo10_dlog=lo10, mean_dlog=mean, te=float(d.std() * np.sqrt(252)))
    OUT[nm] = o
    print(nm, json.dumps(o), flush=True)

# ---- designer's declared sensitivity grid (27 cells), path + real NDX
grid = {}
for tg, hl, band in itertools.product((0.30, 0.40, 0.50), (10, 20, 40), (0.15, 0.25, 0.35)):
    fp, Ep = run(C['dev250_path'], tg, hl, band, 3.0); fr, _ = run(C['real_ndx_86_14'], tg, hl, band, 3.0)
    grid['t%.2f_h%d_b%.2f' % (tg, hl, band)] = dict(path=float(np.median(fp)), real_ndx=float(fr[0]), dd80=float(np.mean(std.ce.mdd(Ep) <= -0.8)))
    print('grid', tg, hl, band, grid['t%.2f_h%d_b%.2f' % (tg, hl, band)], flush=True)
OUT['grid'] = grid
n_above = sum(v['path'] > ref['dev250_path'] for v in grid.values())
P = OUT['PRIMARY_cap3']; pp = P['dev250_path']
edge = pp['cagr'] - ref['dev250_path']
OUT['verdict'] = dict(
    i=bool(P['gate_i']['p_gt0'] >= 0.90), ii=bool(pp['cagr'] > ref['dev250_path']), iii=bool(pp['dd80'] <= OUT['v1']['dd80_path']),
    iv=bool(edge > 0 and (pp['delay7_cagr'] - ref['dev250_path']) >= 0.5 * edge), v=bool(n_above >= 18), grid_cells_above_v1=int(n_above),
    grid_best_path=float(max(v['path'] for v in grid.values())), grid_best_real=float(max(v['real_ndx'] for v in grid.values())),
    project_rule=bool(P['real_ndx_86_14']['cagr'] > ref['real_ndx_86_14'] and pp['cagr'] > ref['dev250_path']))
OUT['verdict']['PASS'] = bool(all(OUT['verdict'][k] for k in ('i', 'ii', 'iii', 'iv', 'v')))
print('verdict', OUT['verdict'], flush=True)
json.dump(OUT, open('/mnt/project-files/research/fresh1/results/c_vt.json', 'w'), indent=1)
