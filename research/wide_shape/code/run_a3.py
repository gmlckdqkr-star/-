"""WS1 A3: user frame = stocks (top-K by IC oracle rho) in predicted-up blocks, inverse index ETF in predicted-down
blocks (direction oracle p_m, symmetric, on the index window return). <=2014.
US500 + synthetic -3x S&P (-3r + rf - 2.45%/252 - 3*3.5%/252), 22% yearly tax on all P&L.
KRALL + synthetic -1x / -2x KOSPI-like cap-weighted all-stock index (-Lr - 0.64%/252 - L*1.5%/252, rf 0),
inverse gains taxed 15.4% per sale without loss offset; stocks no CGT."""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/wide_shape/code')
import wsdata as D, wsstk as S

univ = sys.argv[1]
SC = '/tmp/claude-0/-home-user--/c6bd4d9c-b328-5e0a-b6d0-48efd454b715/scratchpad/ws/'
PM = [.5, .6, .7, .8, .9, 1.0]; RHO = [0, .05, .10, .20, .30, 1.0]
t0 = time.time()


def index_series_us(dates):
    z = np.load(SC + 'idx_panel.npz')
    d = pd.to_datetime(z['_GSPC_ts'], unit='s').normalize(); v = z['_GSPC_v'][:, 3].astype(float)
    di = pd.to_datetime(z['_IRX_ts'], unit='s').normalize(); iv = z['_IRX_v'][:, 3].astype(float)
    px = pd.Series(v, d).groupby(level=0).last().reindex(dates).ffill()
    irx = pd.Series(iv, di).groupby(level=0).last().reindex(dates).ffill().fillna(5.0)
    r = px.pct_change().fillna(0).values
    rf = irx.values / 100 / 252
    return r, rf


def index_series_kr(K, X):
    mc = np.nan_to_num(K['marcap']); rc = X['rc']
    w = np.vstack([np.zeros((1, mc.shape[1])), mc[:-1]])     # yesterday cap weights
    w = np.where(X['listed'], w, 0.0)
    r = (w * rc).sum(1) / np.maximum(w.sum(1), 1)
    return r, np.zeros_like(r)


def run_cell(B, rI, pk, down, L, tax_mode):
    """pk [nb,K] stock picks; down [nb] bool (hold inverse). rI [T] daily inverse product return."""
    pk2 = pk.copy(); pk2[down] = -1
    r, g, c = S.run_picks(B, pk2)
    nb = len(r); held = False; basis_gain = 0.0
    E = 1.0; Ein = 0.0
    out = r.copy()
    for b in range(nb):
        e0 = B.t_dec[b] + 1; e1 = min(e0 + B.h, len(rI) - 1)
        if down[b]:
            gi = np.prod(1 + rI[e0 + 1:e1 + 1]) - 1
            cst = 0.0 if held else 0.003
            add = gi - cst
            if tax_mode == 'kr':
                basis_gain = (1 + basis_gain) * (1 + gi) - 1 if held else gi
            out[b] += add; held = True
            nxt_down = down[b + 1] if b + 1 < nb else False
            if not nxt_down:
                out[b] -= 0.003
                if tax_mode == 'kr':
                    out[b] -= 0.154 * max(0.0, basis_gain)
                held = False; basis_gain = 0.0
    return out


if univ == 'US500':
    U = D.load_us(); rM, rf = index_series_us(U['dates'])
    INV = {3: -3 * rM + rf - 0.0245 / 252 - 3 * 0.035 / 252}
    tax_mode = 'us'
else:
    K_ = D.load_kr(); X_ = D.kr_derived(K_); rM, rf = index_series_kr(K_, X_)
    INV = {L: -L * rM - 0.0064 / 252 - L * 0.015 / 252 for L in (1, 2)}
    tax_mode = 'kr'
res = {'univ': univ, 'cells': {}}
for h in (21, 5):
    B = S.build_us(U, h) if univ == 'US500' else S.build_kr(K_, X_, h)
    nb = len(B.t_dec)
    mret = np.array([np.prod(1 + rM[B.t_dec[b] + 2:min(B.t_dec[b] + 2 + h, len(rM))]) - 1 for b in range(nb)])
    upmask = mret > 0
    print(univ, h, 'up-block share %.3f' % upmask.mean(), flush=True)
    for L, rI in INV.items():
        for K in (5, 20):
            for rho in RHO:
                for pm in PM:
                    vals = []
                    for sd in range(6):
                        rng = np.random.default_rng(300 + sd)
                        s = rho * B.z + np.sqrt(max(0, 1 - rho * rho)) * rng.standard_normal(B.z.shape)
                        s = np.where(B.elig, s, np.nan)
                        pk = S.topk_from_signal(s, K)
                        corr = rng.random(nb) < pm
                        pred_up = np.where(corr, upmask, ~upmask)
                        r = run_cell(B, rI, pk, ~pred_up, L, tax_mode)
                        vals.append(S.perf(B, r)[:2])
                    key = 'h%d_L%d_K%d_rho%g_pm%g' % (h, L, K, rho, pm)
                    res['cells'][key] = {'real': float(np.median([v[0] for v in vals])), 'res': float(np.median([v[1] for v in vals]))}
            print(univ, h, L, K, ' '.join('%s:%.2f' % (k.split('_rho')[1], v['real']) for k, v in res['cells'].items()
                                          if k.startswith('h%d_L%d_K%d_' % (h, L, K))), '%.0fs' % (time.time() - t0), flush=True)
json.dump(res, open('/mnt/project-files/research/wide_shape/results/a3_%s.json' % univ, 'w'), indent=1)
