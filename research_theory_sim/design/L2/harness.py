"""Design harness for lane L2 (synthetic data only). Every evaluated variant is appended to variants_log.jsonl.
Selection uses seeds 1-999 only; final numbers use fresh seeds >= 10000 (see final_eval.py)."""
import sys, json, time
import numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
import exec_engine as ee
import sim

HERE = '/mnt/project-files/research/theory_sim/design/L2/'
T = 7860
_W = {}


def world(seed, P=1000, mech=True):
    key = (seed, P, mech)
    if key not in _W:
        d = sim.simulate(P, T, seed, mech)
        d['close'] = np.cumprod(1 + d['r'], axis=1) * 37.0      # arbitrary normalisation (rule must be scale-invariant)
        _W[key] = d
    return _W[key]


def ewm_mean(x, hl, init=None):
    """bias-corrected EWMA along axis 1 (NaN treated as missing)."""
    lam = 0.5 ** (1.0 / hl)
    P, n = x.shape
    out = np.empty_like(x); m = np.zeros(P); w = np.zeros(P)
    for t in range(n):
        v = x[:, t]; ok = ~np.isnan(v)
        m = np.where(ok, lam * m + (1 - lam) * np.where(ok, v, 0.0), m)
        w = np.where(ok, lam * w + (1 - lam), w)
        out[:, t] = np.where(w > 0, m / np.maximum(w, 1e-300), np.nan)
    return out


def ewm_sum(x, hl):
    lam = 0.5 ** (1.0 / hl)
    P, n = x.shape
    out = np.empty_like(x); s = np.zeros(P)
    for t in range(n):
        v = x[:, t]
        s = lam * s + np.where(np.isnan(v), 0.0, v)
        out[:, t] = s
    return out


def log_variant(rec):
    rec['ts'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    with open(HERE + 'variants_log.jsonl', 'a') as f:
        f.write(json.dumps(rec) + '\n')


def evaluate(B_fn, seeds=(1,), P=1000, mechs=(True, False), delay=2, cost=0.003, name='', prm=None, log=True):
    out = {}
    for mech in mechs:
        cs = []; res_all = []
        for s in seeds:
            d = world(s, P, mech)
            B = B_fn(d)
            res = ee.run(d['r'], d['rf'], B, delay=delay, cost=cost)
            res_all.append(res)
        cat = {k: np.concatenate([r[k] for r in res_all]) for k in ('cagr', 'mdd', 'trades_per_year', 'avg_level', 'w7', 'w12')}
        bad = ~np.isfinite(cat['cagr']); cat['cagr'][bad] = -1.0; cat['mdd'][~np.isfinite(cat['mdd'])] = -1.0   # 3x product went negative -> ruin
        sm = ee.summary(cat)
        out['on' if mech else 'off'] = sm
    if log:
        log_variant(dict(name=name, prm=prm, seeds=list(seeds), P=P, delay=delay, cost=cost,
                         on=out.get('on', {}).get('cagr_med'), off=out.get('off', {}).get('cagr_med'),
                         on_p10=out.get('on', {}).get('cagr_p10'), off_p10=out.get('off', {}).get('cagr_p10'),
                         on_dd80=out.get('on', {}).get('p_dd80'), tpy=out.get('on', {}).get('trades_per_year_med'),
                         lev=out.get('on', {}).get('avg_level_med')))
    return out


def holds(seeds=(1,), P=1000, mech=True):
    o = {}
    for lev in (1, 2, 3):
        c = np.concatenate([ee.hold(world(s, P, mech)['r'], world(s, P, mech)['rf'], lev)['cagr'] for s in seeds])
        c[~np.isfinite(c)] = -1.0
        o[lev] = float(np.median(c))
    return o


# ---------------- candidate rule family (same arithmetic as rule.py; numpy only) ----------------
def family(close, rf, y10, q):
    """q: hv (days), H (years), a0, a1, a2 (spread), a3 (rf gap), lw_c, lw_d (ledger carry / duration weights),
    demean (0/1), vfloor."""
    P, n = close.shape
    c = np.where(close > 0, close, np.nan)
    lc = np.log(c)
    lr = np.full((P, n), np.nan); lr[:, 1:] = lc[:, 1:] - lc[:, :-1]
    rfa = rf * 252.0
    e = lr - rf
    var = ewm_mean(lr ** 2, q.get('hv', 40)) * 252.0
    var = np.maximum(var, q.get('vfloor', 0.0004))
    inc = np.where(np.isnan(e), 0.0, e)
    if q.get('demean', 0):
        cm = np.cumsum(inc, axis=1); cnt = np.cumsum(~np.isnan(e), axis=1)
        inc = inc - np.where(cnt > 0, cm / np.maximum(cnt, 1), 0.0)
    if y10 is not None and (q.get('lw_c', 0) or q.get('lw_d', 0) or q.get('a2', 0)):
        s = y10 / 100.0 - rfa
        sb = ewm_mean(s, 5 * 252)
        ds = s - sb
        dy = np.zeros_like(s); dy[:, 1:] = y10[:, 1:] / 100.0 - y10[:, :-1] / 100.0
        dy = np.where(np.isnan(dy), 0.0, dy)
        inc = inc + q.get('lw_c', 0) * np.where(np.isnan(ds), 0.0, ds) / 252.0 - q.get('lw_d', 0) * dy
    else:
        ds = np.zeros((P, n))
    led = ewm_sum(inc, q.get('H', 1.0) * 252)
    mu = q.get('a0', 0.03) - q.get('a1', 0.0) * led + q.get('a2', 0.0) * np.where(np.isnan(ds), 0.0, ds)
    if q.get('a3', 0):
        rg = rfa - ewm_mean(rfa, q.get('Hr', 3.0) * 252)
        mu = mu + q['a3'] * np.where(np.isnan(rg), 0.0, rg)
    L = np.clip(q.get('c', 1.0) * mu / var, 0.0, 3.0)
    L[:, :20] = np.nan
    return L


def fam_fn(q):
    return lambda d: family(d['close'], d['rf'], d['y10'] if q.get('use_y10', 0) else None, q)
