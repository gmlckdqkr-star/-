"""verify4/stress (b): real NDX split 1986-1999 / 2000-2014, and single-path delay3 / cost1.5x separately. <=2014 only.
Method A (primary, standalone): slice every (1,T) context column array of real_ndx_86_14 so a fresh account starts at the half's first
  trading day with the 300-day warm-up taken from the preceding real days (signals keep their full-history values, which use only past data);
  engine as usual -> after-tax CAGR incl. final liquidation tax, MDD inside the half.
Method B (cross-check, continuous account): one full 1986-2014 run with recon=True; CAGR = E[end]/E[start-1] over the half's days
  (after yearly taxes, before final liquidation tax), MDD of E inside the half with the peak reset at the half's start."""
import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, df4cfg
W = dfe.WARM; CID = 'v1|s0.3|L1.5|K0|RC'; cfg = df4cfg.cfg_of(CID)
OUT = dict(cfg=cfg, rows={})
def sstat(o, T): cg, md = dfe.stats(o, T); return dict(cagr=float(cg[0]), mdd=float(md[0]))
m = DC.market('real_ndx_86_14'); d = pd.DatetimeIndex(m['X_index'][m['ctx'].ii[0]]); T = m['r'].shape[1]
assert d[-1] <= pd.Timestamp('2014-12-31')
KEYS = [k for k, v in m.items() if isinstance(v, np.ndarray) and v.ndim == 2 and v.shape == m['r'].shape]
print('sliced arrays', KEYS)
def sub(s, e):           # s, e column indices (inclusive) of evaluation window; keep W warm-up columns before s
    mm = {k: (m[k][:, s - W:e + 1].copy() if k in KEYS else m[k]) for k in m}; mm['r'][:, 0] = 0.0; mm['rb'][:, 0] = 0.0; mm['cpn'][:, 0] = 0.0
    return mm
HALVES = (('1986-1999', '1986-01-01', '1999-12-31'), ('2000-2014', '2000-01-01', '2014-12-31'), ('full_check', '1986-01-01', '2014-12-31'))
L = DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax'])
oc, Ec = dfe.run(m, L, roff=0, kon=0, recon=True); oq, Eq = dfe.run(m, np.full(m['r'].shape, 1.0), recon=True)
assert abs(dfe.stats(oc, T)[0][0] - dfe.stats(df4cfg.run_any(cfg, m), T)[0][0]) < 1e-12
for nm, a, b in HALVES:
    s = int(d.searchsorted(pd.Timestamp(a))); e = int(d.searchsorted(pd.Timestamp(b), side='right')) - 1
    assert s >= W
    mm = sub(s, e); TT = mm['r'].shape[1]
    A = dict(cand=sstat(df4cfg.run_any(cfg, mm), TT), qqq=sstat(dfe.run(mm, np.full(mm['r'].shape, 1.0))[0], TT))
    A['beats_both'] = bool(A['cand']['cagr'] > A['qqq']['cagr'] and A['cand']['mdd'] > A['qqq']['mdd'])
    def win(E):
        x = E[0, s - W - 1:e - W + 1] if s > W else np.r_[1.0, E[0, :e - W + 1]]; n = len(x) - 1
        return dict(cagr=float((x[-1] / x[0]) ** (252 / n) - 1), mdd=float((x / np.maximum.accumulate(x) - 1).min()), days=n)
    B = dict(cand=win(Ec), qqq=win(Eq)); B['beats_both'] = bool(B['cand']['cagr'] > B['qqq']['cagr'] and B['cand']['mdd'] > B['qqq']['mdd'])
    OUT['rows'][nm] = dict(window=[str(d[s].date()), str(d[e].date())], days=e - s + 1, warm_from=str(d[s - W].date()), A_standalone=A, B_continuous=B)
    print('%-11s %s..%s (%d d, warm from %s)' % (nm, d[s].date(), d[e].date(), e - s + 1, d[s - W].date()))
    for k, r in (('A standalone', A), ('B continuous', B)):
        print('   %-13s cand %6.2f / %6.1f | QQQ %6.2f / %6.1f | beats both %s' % (k, r['cand']['cagr']*100, r['cand']['mdd']*100, r['qqq']['cagr']*100, r['qqq']['mdd']*100, r['beats_both']))
# single-path: delay3, cost1.5x separately (both-together already in s1_main)
for bn in ('real_ndx_86_14', 'real_spx_55_85', 'real_spx_29_54', 'real_spx_29_54_B', 'real_spx_70_85'):
    mb = DC.market(bn); TT = mb['r'].shape[1]
    for k, kw in (('delay3', dict(delay=3)), ('cost1.5x', dict(cost=0.0045))):
        r = dict(cand=sstat(df4cfg.run_any(cfg, mb, **kw), TT), qqq=sstat(dfe.run(mb, np.full(mb['r'].shape, 1.0), **kw)[0], TT))
        r['beats_both'] = bool(r['cand']['cagr'] > r['qqq']['cagr'] and r['cand']['mdd'] > r['qqq']['mdd'])
        OUT['rows'][bn + '|' + k] = r
        print('%-16s %-9s cand %6.2f / %6.1f | QQQ %6.2f / %6.1f | beats both %s' % (bn, k, r['cand']['cagr']*100, r['cand']['mdd']*100, r['qqq']['cagr']*100, r['qqq']['mdd']*100, r['beats_both']))
json.dump(OUT, open('/mnt/project-files/research/df1/verify4/stress/s3_halves.json', 'w'), indent=1); print('saved')
