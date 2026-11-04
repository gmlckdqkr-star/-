"""Reference points on the discovery basis (not part of the tested family): s0.85, always-3x, SMA200 3x/cash —
monthly pre-tax log-growth difference vs 1x on S&P 1955-85 + NDX 1986-99, studentized with the same bootstrap as SPA.
Plus distribution summary of the family (share with positive advantage, quantiles)."""
import os, sys, json, numpy as np, pandas as pd
SCR = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m1/'
os.environ['NUMBA_CACHE_DIR'] = SCR + 'nb'
sys.path.insert(0, SCR + 'code')
import m1_engine as EN, m1_search as SE, m1_stats as ST, m1_confirm as CF


def monthly(series_lg, onex_lg, a, b):
    d = (series_lg - onex_lg).loc[a:b]
    return d.groupby([d.index.year, d.index.month]).sum().values


def main():
    E = SE.era_inputs(); s85 = CF.s085_logret()
    ref = {}
    one = {e: pd.Series(np.log1p(E[e]['X'][2]), index=E[e]['dates']) for e in ('spx', 'ndx')}
    m = np.r_[monthly(s85['spx'], one['spx'].reindex(s85['spx'].index), '1955-01-03', '1985-12-31'),
              monthly(s85['ndx'], one['ndx'].reindex(s85['ndx'].index), '1986-01-02', '1999-12-31')]
    ref['s0.85'] = m
    for nm, code in (('always_3x', 0),):
        mm = []
        for e, (a, b) in SE.DISC.items():
            lg = pd.Series(np.log1p(E[e]['X'][code]), index=E[e]['dates'])
            mm.append(monthly(lg, one[e], a, b))
        ref[nm] = np.concatenate(mm)
    Dr = np.vstack([ref[k] for k in ref]).astype(np.float32)
    W = ST.stationary_counts(Dr.shape[1])
    Mb = (W @ Dr.T).astype(np.float64) / Dr.shape[1]
    om = np.sqrt(Mb.var(0) * Dr.shape[1])
    out = {}
    for j, k in enumerate(ref):
        out[k] = dict(adv_ann=float(Dr[j].mean() * 12), t=float(np.sqrt(Dr.shape[1]) * Dr[j].mean() / om[j]),
                      adv_spx=float(Dr[j][:372].mean() * 12), adv_ndx=float(Dr[j][372:].mean() * 12))
    D = np.load(SCR + 'cache/D.npy', mmap_mode='r'); S = np.load(SCR + 'cache/S.npy'); keep = np.load(SCR + 'cache/keep.npy')
    act = S[:, 1] + S[:, 5]; adv = (S[:, 0] + S[:, 4]) / np.maximum(act, 1) * 252
    a = adv[keep]; el = keep[act[keep] >= SE.MIN_ACTIVE]
    out['family'] = dict(n=len(keep), share_pos=float(np.mean(a > 0)), q50=float(np.median(a)), q90=float(np.quantile(a, .9)),
                         q99=float(np.quantile(a, .99)), max=float(a.max()), max_eligible=float(adv[el].max()),
                         n_eligible=int(len(el)))
    fam = np.load(SCR + 'cache/fam.npy'); rules = np.load(SCR + 'cache/rules.npy')
    out['by_family_max_eligible'] = {['single', 'pair', 'triple'][f]: float(adv[el][fam[el] == f].max()) for f in range(3)}
    shp = {tuple(x) for x in EN.SHAPE_CODES.tolist()}
    out['by_shape_max_eligible'] = {str(EN.SHAPES[s]): float(adv[el][(rules[el, 4] == EN.SHAPE_CODES[s, 0]) & (rules[el, 5] == EN.SHAPE_CODES[s, 1])].max())
                                    for s in range(7)}
    out['by_hold_max_eligible'] = {str(h): float(adv[el][rules[el, 6] == h].max()) for h in EN.HOLDS}
    print(json.dumps(out, indent=1))
    json.dump(out, open(SCR + 'out/ref.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
