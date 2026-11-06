"""KL1 selection screen for the block families S1-KR, S1-US, S3-KR, S3-US (selection blocks only, PRECOMMIT_KL1 sec.6-7).
Writes D (N x months, after-cost pre-tax monthly log excess vs the family benchmark) and per-variant stats to CACHE."""
import os, sys, json, time, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/claude-0/-home-user--/e60ac389-f078-575c-af9f-bad532fab64a/scratchpad/kl/nb')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wsdata as WD, kl_sig as SG, kl_gen as G, kl_blk as BK
from numba import njit, prange

CACHE = WD.CACHE
HS = G.HS
NMON = {'KR': 120, 'US': 348}
SEED_KRW = 1e7


@njit(parallel=True, cache=True)
def s1_group(P, specs, qv, regs, base, R, entry, hsb, impf, kr, seed):
    nv = specs.shape[0]; nb = base.shape[0]
    out = np.zeros((nv, nb)); nh = np.zeros(nv)
    for v in prange(nv):
        defs = specs[v, 2:6].copy()
        r, n = BK.s1_returns(P, defs, specs[v, 1], specs[v, 0], specs[v, 6], qv[v], regs[v], base, R, entry, hsb, impf, kr, seed)
        out[v] = r; nh[v] = n.mean()
    return out, nh


def load_panel(panel):
    B = {}
    for h in HS:
        z = np.load(CACHE + '%s_blk_h%d.npz' % (panel.lower(), h))
        B[h] = {k: z[k] for k in z.files}
    A = np.load(CACHE + '%s_atoms.npy' % panel.lower(), mmap_mode='r')
    meta = json.load(open(CACHE + '%s_atoms_meta.json' % panel.lower()))
    return B, A, meta


def bases(panel, b):
    el = b['elig']
    out = [el]
    if panel == 'KR':
        adv = np.where(el, b['adv'], np.nan); mc = np.where(el, b['mcap'], np.nan)
        med = np.nanmedian(adv, axis=1); p70 = np.nanpercentile(mc, 70, axis=1)
        out.append(el & (b['adv'] >= med[:, None])); out.append(el & (b['mcap'] >= p70[:, None]))
    return out


def cost_arrays(panel, b):
    if panel == 'KR':
        hsb = (0.00015 + b['hs']).astype(np.float64); impf = (0.7 * b['s20'] / np.sqrt(b['adv'])).astype(np.float64)
        return hsb, impf, True
    z = np.zeros((1, 1)); return z, z, False


def prod_windows(panel, b, h):
    """lever / cash / inverse window returns for the blocks of h (entry close t_dec + 2)."""
    e0 = b['t_dec'] + 2
    if panel == 'KR':
        z = np.load(CACHE + 'kr_idx.npz'); X = z['X']; T = X.shape[1]
        return {'lev0': BK.window_prod(X[1], e0, h, T), 'cash': BK.window_prod(X[3], e0, h, T), 'inv': BK.window_prod(X[4], e0, h, T)}
    z = np.load(CACHE + 'us_prod_panelcal.npz'); T = z['L3spx'].shape[0]
    return {'lev0': BK.window_prod(z['L3spx'], e0, h, T), 'lev1': BK.window_prod(z['L3tq'], e0, h, T),
            'cash': BK.window_prod(z['cash'], e0, h, T), 'inv': BK.window_prod(z['inv'], e0, h, T)}


def us_products_panelcal():
    """MS1 product daily returns (S&P 1x/3x, TQQQ-type 3x: S&P <=1985, NDX >=1986) re-based onto the S&P panel calendar."""
    sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std, jp  # noqa
    R, M = jp.calendar('1928-01-03', '2014-12-31')
    spx = R['SPX'].fillna(0.0); ndx = R['NDX'].fillna(0.0); rf = M['rf'].reindex(R.index).ffill().fillna(0.0)
    tq = spx.where(R.index < pd.Timestamp('1986-01-02'), ndx)
    ser = {'L3spx': 3 * spx - 2 * rf - 0.0245 / 252, 'L3tq': 3 * tq - 2 * rf - 0.0245 / 252,
           'cash': np.maximum(rf - 0.02 / 252, 0) * 0.846, 'inv': -spx + 2 * rf - 0.0245 / 252,
           'spx1': spx - 0.002 / 252, 'tq1': tq - 0.002 / 252}
    pdates = pd.to_datetime(np.load(CACHE + 'us_dates.npy'))
    out = {}
    for k, s in ser.items():
        L = (1 + s).cumprod().reindex(pdates, method='ffill')
        v = (L / L.shift(1) - 1).fillna(0.0).values
        out[k] = v
    np.savez(CACHE + 'us_prod_panelcal.npz', **out)
    return dict(n_panel=len(pdates), n_jp=int(((R.index >= pdates[0]) & (R.index <= pdates[-1])).sum()))


def run_s1(panel, rows, B, A):
    t0 = time.time()
    nm = NMON[panel]; N = len(rows)
    D = np.zeros((N, nm), np.float32); stat = np.zeros((N, 4))
    ndef = len(SG.KR_DEFS if panel == 'KR' else SG.US_DEFS)
    bench = {}
    for hi, h in enumerate(HS):
        b = B[h]; bl = bases(panel, b); hsb, impf, kr = cost_arrays(panel, b)
        R = np.nan_to_num(b['R'].astype(np.float64), nan=np.nan)
        for fi, base in enumerate(bl):
            sel = np.flatnonzero((rows[:, 8] == hi) & (rows[:, 9] == fi))
            if len(sel) == 0:
                continue
            P = np.stack([BK.pct_ranks(b['sc'][d], base) for d in range(ndef)])
            nb = base.shape[0]
            rb, nhb = s1_group(P, np.zeros((1, 7), np.int64), np.zeros(1), np.ones((1, nb), np.int8), base, R, b['entry'], hsb, impf, kr, SEED_KRW)
            bench[(h, fi)] = rb[0]
            sp = rows[sel]
            form = np.where(sp[:, 0] >= 3, sp[:, 0] - 3, sp[:, 0])
            specs = np.column_stack([form, sp[:, 1], sp[:, 2:6], sp[:, 6]]).astype(np.int64)
            qv = np.array(G.Q1)[sp[:, 7]]
            regs = np.ones((len(sel), nb), np.int8)
            rg = np.flatnonzero(sp[:, 10] >= 0)
            if len(rg):
                st = np.asarray(A[sp[rg, 10]][:, b['t_dec']])
                regs[rg] = (st == sp[rg, 11][:, None]).astype(np.int8)
            ch = 4000
            for i in range(0, len(sel), ch):
                rv, nh = s1_group(P, specs[i:i + ch], qv[i:i + ch], regs[i:i + ch], base, R, b['entry'], hsb, impf, kr, SEED_KRW)
                lg = np.log1p(np.maximum(rv, -0.999999)) - np.log1p(np.maximum(rb[0], -0.999999))[None, :]
                for j in range(len(rv)):
                    D[sel[i + j]] = BK.monthly(lg[j], b['mon'], nm)
                stat[sel[i:i + ch], 0] = nh; stat[sel[i:i + ch], 1] = nb
                stat[sel[i:i + ch], 2] = lg.mean(1) * 252 / h          # annualized block log excess
                stat[sel[i:i + ch], 3] = len(np.unique(b['mon']))
            print('S1', panel, 'h', h, 'f', fi, 'n', len(sel), '%.0fs' % (time.time() - t0), flush=True)
            del P
    return D, stat, bench


def run_s3(panel, rows, B, A):
    t0 = time.time()
    nm = NMON[panel]; N = len(rows)
    D = np.zeros((N, nm), np.float32); stat = np.zeros((N, 4))
    W = G.W_KR if panel == 'KR' else G.W_US
    cs, ce = BK.C_STK[panel], BK.C_ETF[panel]
    for hi, h in enumerate(HS):
        b = B[h]; base = b['elig']; hsb, impf, kr = cost_arrays(panel, b)
        R = b['R'].astype(np.float64)
        sel = np.flatnonzero(rows[:, 4] == hi)
        nb = base.shape[0]
        P = np.stack([BK.pct_ranks(b['sc'][d], base) for d in range(G.NCORE)])
        PW = prod_windows(panel, b, h)
        rb, _ = s1_group(P, np.zeros((1, 7), np.int64), np.zeros(1), np.ones((1, nb), np.int8), base, R, b['entry'], hsb, impf, kr, SEED_KRW)
        rb = rb[0]
        sp = rows[sel]
        specs = np.zeros((len(sel), 7), np.int64)
        specs[:, 0] = sp[:, 0]; specs[:, 1] = np.where(sp[:, 0] == 0, 1, 2); specs[:, 2] = sp[:, 1]; specs[:, 3] = sp[:, 2]
        specs[:, 4:6] = -1
        qv = np.array(G.Q3)[sp[:, 3]]
        rs, _ = s1_group(P, specs, qv, np.ones((len(sel), nb), np.int8), base, R, b['entry'], hsb, impf, kr, SEED_KRW)
        for j, k in enumerate(sel):
            row = rows[k]; w = W[row[5]]
            g = PW['lev%d' % row[6]] if panel == 'US' else PW['lev0']
            if row[7] >= 0:
                st = np.asarray(A[row[7]][b['t_dec']])
                on = np.where(st == 0, 0, 1).astype(np.int8)        # unknown -> on (static combo)
            else:
                on = np.ones(nb, np.int8)
            r = BK.s3_returns(rs[j], g, PW['cash'], PW['inv'], w, on, int(row[8]), cs, ce)
            r0 = BK.s3_returns(rb, g, PW['cash'], PW['inv'], w, np.ones(nb, np.int8), 0, cs, ce)
            lg = np.log1p(np.maximum(r, -0.999999)) - np.log1p(np.maximum(r0, -0.999999))
            D[k] = BK.monthly(lg, b['mon'], nm)
            stat[k, 0] = (on == 1).mean(); stat[k, 1] = nb; stat[k, 2] = lg.mean() * 252 / h; stat[k, 3] = len(np.unique(b['mon']))
        print('S3', panel, 'h', h, 'n', len(sel), '%.0fs' % (time.time() - t0), flush=True)
    return D, stat


if __name__ == '__main__':
    fam = sys.argv[1]                  # S1KR S1US S3KR S3US
    panel = fam[2:]
    if fam == 'S3US' and not os.path.exists(CACHE + 'us_prod_panelcal.npz'):
        print('us products', us_products_panelcal(), flush=True)
    rows = np.load(CACHE + 'gen_%s.npy' % fam)
    B, A, meta = load_panel(panel)
    if fam.startswith('S1'):
        D, stat, bench = run_s1(panel, rows, B, A)
    else:
        D, stat = run_s3(panel, rows, B, A)
    np.save(CACHE + 'D_%s.npy' % fam, D); np.save(CACHE + 'stat_%s.npy' % fam, stat)
    print('done', fam, D.shape, flush=True)
