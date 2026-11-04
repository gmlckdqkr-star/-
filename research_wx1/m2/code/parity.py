"""Parity before the search: (a) screen engine pre-tax CAGR of EW and 12-1 momentum top 20 vs lab cagr_pretax,
(b) lab engine through my own Targets (lab.stocks.Targets + run1, lab code unchanged) vs `lab run` of
specs/examples/stk_mom12_1_top20.yaml (1986-2014 after-tax conservative 8.37%, EW 9.88%).
Known example numbers only (no OAP result read)."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/lab'); sys.path.insert(0, sys.argv[1])
from lab import stocks, dsl
import m2lib as M, labbridge as LB
d = M.load()
P = stocks.load()
assert np.array_equal(d.dec, np.flatnonzero(dsl.reb_rows(P.idx, 'monthly'))[-len(d.dec):])
# 12-1 momentum at decisions (lab window floor)
PP = P.P
mom = np.full((d.nd, d.N), np.nan)
for j, t in enumerate(d.dec):
    ok = (t - 252 >= P.wfloor)
    mom[j] = np.where(ok & d.elig[j], PP[t - 21] / PP[t - 252] - 1.0, np.nan)
spec = dict(name='stk_mom12_1_top20', family='stk_mom', universe='sp500',
            stock=dict(rebalance='month', score='ret(231, 21)', top=20, weight='equal', max_weight=0.10))
tgl = stocks.compile_targets(dsl.check_spec(spec), P)
# compare picks on the decisions inside d.dec
j0 = int(np.searchsorted(d.dd, pd.Timestamp('1986-01-01')))
pk = M.top_picks(mom, 50)
mism = 0
for j in range(j0, d.nd):
    k = int(np.searchsorted(tgl.dec, d.dec[j]))
    a = set(tgl.picks[k].tolist()); b = set(pk[j, :20].tolist()) - {-1}
    mism += int(a != b)
out = {'pick_mismatch_decisions_1986_2014': mism}
# (a) screen engine pre-tax
ones = np.ones(d.nd, np.bool_)
r = M.book_returns(pk, 20, d.HR, d.CR, ones, d.mo, j0, d.nd, 'M')
re = M.ew_returns(d, j0, d.nd)
yrs = (pd.Timestamp('2014-12-31') - d.dd[j0]).days / 365.25
out['screen_mom_pretax'] = float(np.prod(1 + r) ** (1 / yrs) - 1)
out['screen_ew_pretax'] = float(np.prod(1 + re) ** (1 / yrs) - 1)
# lab pre-tax for the same spec and EW (fast_run with tax 0, dtax 0)
st = pd.Timestamp('1986-01-02')
pre = stocks.run1(P, tgl, stocks.H_CONS, st, 0.003, 0.0, 2, dtax=0.0)
out['lab_mom_pretax'] = pre['cagr_at']
ewt = stocks.ew_targets(P)
out['lab_ew_pretax'] = stocks.run1(P, ewt, stocks.H_CONS, st, 0.003, 0.0, 2, dtax=0.0)['cagr_at']
# (b) lab engine through my Targets (monthly decisions from my picks)
tg = LB.targets_from_picks(P, d, pk, 20, rb='M', gate=None)
o = stocks.run1(P, tg, stocks.H_CONS, st, 0.003, 0.22, 2)
out['mytargets_lab_aftertax_cons'] = o['cagr_at']
out['lab_run_aftertax_cons'] = 0.08370149436557406
out['lab_ew_aftertax_cons'] = stocks.ew_row(P, stocks.H_CONS, st, 0.003, 0.22, 2)['cagr_at']
# MS1 stream through the bridge vs lab run's MS1 (9.16%)
s = LB.stream(P, tg)
out['stream_start'] = s['start']; out['stream_turnover'] = s['turnover']
json.dump(out, open(sys.argv[2], 'w'), indent=1)
np.savez(sys.argv[3], dates=np.array(s['dates']), ret=np.array(s['ret']), q=np.array(s['basis_add']), turnover=s['turnover'])
print(json.dumps(out, indent=1))
