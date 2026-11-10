"""CAPIT independent verifier, part 2: kill test B (BRIEF_FINAL1 section 4), EARLY window only, re-implemented from scratch.
- block grid: every 21 trading days from 1986-01-02 on the MS1 calendar; label = synthetic 3x NDX beats the deposit over t+3..t+23.
  The label is built here on a frame that ENDS 1999-12-31 (no later return is ever loaded for the label) and by plain compounding
  (not the gate's log-sum), then compared with gate._frame restricted to blocks ending <= 1999-12-31.
- universe: blocks whose v1 base target (ov1lib.v1_B, the shared reference) is < 3 at close t.
- 'on': my own triggers (verify/v1_signals.py: own RSI, own volume ratio) + my own window logic.
For 2000-2014 only signal-side COUNTS are produced (on-days, on-blocks): no label, no return, no hit rate."""
import sys, json, numpy as np, pandas as pd
LANE = '/mnt/project-files/research/final1/lanes/CAPIT/'
sys.path.insert(0, '/mnt/project-files/research/ov1/code'); sys.path.insert(0, '/mnt/project-files/research/breakthrough/code')
import ov1lib as L, jp, ov  # noqa
out = {}
S = pd.read_pickle('/tmp/final1_CAPIT_verify/sig.pkl'); PN = pd.read_pickle('/tmp/final1_CAPIT_verify/ndx_panel_le2014.pkl')
E0, E1, U0, U1 = map(pd.Timestamp, ('1986-01-02', '1999-12-31', '2000-01-03', '2014-12-31'))

# ---- v1 base target on the real calendar (same construction as std.contexts()['real_ndx_86_14'])
R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX'); cal = X.index; assert cal.max() <= U1
F = ov.flags_hist(X); i0c = cal.searchsorted(E0) - ov.WARM
c = ov.Ctx(X, F, np.arange(i0c, len(X))[None, :]); cidx = cal[c.ii[0]]
B = pd.Series(L.v1_B(c)[0], index=cidx)
Bd = B[(B.index >= E0)]
out['v1_state_share_1986_2014'] = {str(k): round(float(v), 4) for k, v in Bd.value_counts(normalize=True).sort_index().items()}
out['calendar'] = dict(first=str(cal[0].date()), last=str(cal[-1].date()), n=int(len(cal)),
                       panel_dates_not_in_calendar=int((~PN.index.isin(cal)).sum()),
                       calendar_dates_ge_1985_10_01_not_in_panel=int((~cal[cal >= PN.index[0]].isin(PN.index)).sum()))
# vendor close return vs MS1 frame return (alignment of the volume dates with the price frame), early window only
rv = PN.close.pct_change().reindex(cal); m = (cal >= E0) & (cal <= E1)
out['calendar']['early_max_abs_diff_vendor_ret_vs_frame_ret'] = float((rv[m] - X['r'][m]).abs().max())

# ---- my own triggers on the calendar, my own ON window (trigger at any of the closes t-W+1..t)
trig = {v: S[k].reindex(cal).fillna(False).astype(bool) for v, k in (('CAP1', 'cap1'), ('CAP2', 'cap2'))}
W = {'CAP1': 42, 'CAP2': 63}
def on_series(tr, w):
    a = tr.values; o = np.zeros(len(a), bool)
    for i in np.where(a)[0]: o[i:i + w] = True            # trigger close and the next w-1 closes
    return pd.Series(o, index=tr.index)
def on_series_alt(tr, w):                                   # other reading of 'the next W trading days': closes t+1..t+W
    a = tr.values; o = np.zeros(len(a), bool)
    for i in np.where(a)[0]: o[i + 1:i + 1 + w] = True
    return pd.Series(o, index=tr.index)

# ---- EARLY labels on a frame cut at 1999-12-31, plain compounding
Re, Me = jp.calendar('1984-01-03', '1999-12-31'); Xe = jp.mkX(Re, Me, 'NDX'); ce = Xe.index; assert ce.max() <= E1
x3 = (3 * Xe['r'] - 2 * Xe['rf'] - 0.0245 / 252).values; dep = (np.maximum(Xe['rf'].values - 0.02 / 252, 0) * (1 - 0.154))
j0 = ce.searchsorted(E0); rows = []
t = j0
while t + 23 <= len(ce) - 1:
    a = np.prod(1 + x3[t + 3:t + 24]); b = np.prod(1 + dep[t + 3:t + 24])
    rows.append((ce[t], ce[t + 23], a > b, a / b - 1)); t += 21
blk = pd.DataFrame(rows, columns=['t', 'end', 'win', 'excess']).set_index('t')
# same label from the VENDOR close (panel) instead of the MS1 frame return
rve = PN.close.pct_change().reindex(ce).fillna(0.0).values; x3v = 3 * rve - 2 * Xe['rf'].values - 0.0245 / 252
blk['win_vendor'] = [np.prod(1 + x3v[ce.get_loc(d) + 3:ce.get_loc(d) + 24]) > np.prod(1 + dep[ce.get_loc(d) + 3:ce.get_loc(d) + 24]) for d in blk.index]
Bt = B.reindex(blk.index); assert Bt.notna().all()
uni = blk[Bt.values < 3]
early = dict(n_blocks=int(len(blk)), first_block=str(blk.index[0].date()), last_block=str(blk.index[-1].date()), last_block_end=str(blk['end'].iloc[-1].date()),
             always_in_hit=float(blk.win.mean()), wins_all=int(blk.win.sum()), n_universe=int(len(uni)),
             universe_v1B_counts={str(k): int(v) for k, v in Bt[Bt < 3].value_counts().sort_index().items()},
             base=float(uni.win.mean()), base_wins=int(uni.win.sum()), label_vendor_close_disagreements=int((blk.win != blk.win_vendor).sum()),
             min_abs_excess=float(blk.excess.abs().min()), v1_below3_days=int((B[(B.index >= E0) & (B.index <= E1)] < 3).sum()), variants={})
for v in ('CAP1', 'CAP2'):
    on = on_series(trig[v], W[v]); ona = on_series_alt(trig[v], W[v])
    de = (cal >= E0) & (cal <= E1)
    ob = on.reindex(uni.index).values; y = uni.win[ob]; n = int(len(y))
    cond = float(y.mean()) if n else None
    early['variants'][v] = dict(trigger_days=int(trig[v][de].sum()), on_days=int(on[de].sum()), on_days_v1_below3=int((on[de] & (B.reindex(cal)[de] < 3)).sum()),
                                n_on=n, n_on_alt_window_reading=int(ona.reindex(uni.index).sum()), n_on_any_v1_state=int(on.reindex(blk.index).sum()),
                                wins=int(y.sum()), cond=cond, cond_minus_base=(cond - early['base']) if n else None,
                                pass_B=bool(n >= 8 and cond is not None and cond >= early['base'] + 0.10 and cond >= 0.60))
out['early'] = early
print('EARLY', json.dumps(early))

# ---- gate._frame cross-check, early blocks only (the gate computes all labels internally; only blocks ending <= 1999-12-31 are read)
import gate
g = gate._frame('NDX', '1984-01-03', '2014-12-31', '1986-01-02'); pos = cal.get_indexer(g.index); gend = cal[np.minimum(pos + 23, len(cal) - 1)]
ge = g[(g.index >= E0) & (gend <= E1)]
out['gate_crosscheck_early'] = dict(n=int(len(ge)), same_dates=bool(len(ge) == len(blk) and (ge.index == blk.index).all()),
                                    label_disagreements=int((ge.values.astype(bool) != blk.win.values).sum()) if len(ge) == len(blk) else None)
print('GATE', json.dumps(out['gate_crosscheck_early']))

# ---- 2000-2014: SIGNAL-SIDE COUNTS ONLY (block dates on the same 21-day grid, v1 state, ON flag). No label, no return.
grid = cal[np.arange(cal.searchsorted(E0), len(cal) - 24, 21)]            # same grid rule as the gate (t + 24 <= len - 1)
ub = grid[(grid >= U0) & (grid <= U1)]; Bu = B.reindex(ub); uu = ub[Bu.values < 3]
cnt = dict(n_blocks=int(len(ub)), n_universe=int(len(uu)), universe_v1B_counts={str(k): int(v) for k, v in Bu[Bu < 3].value_counts().sort_index().items()},
           v1_below3_days=int((B[(B.index >= U0) & (B.index <= U1)] < 3).sum()), variants={})
for v in ('CAP1', 'CAP2'):
    on = on_series(trig[v], W[v]); du = (cal >= U0) & (cal <= U1)
    cnt['variants'][v] = dict(trigger_days=int(trig[v][du].sum()), trigger_days_v1_below3=int((trig[v][du] & (B.reindex(cal)[du] < 3)).sum()),
                              on_days=int(on[du].sum()), on_days_v1_below3=int((on[du] & (B.reindex(cal)[du] < 3)).sum()),
                              n_on=int(on.reindex(uu).sum()), n_on_any_v1_state=int(on.reindex(ub).sum()),
                              on_block_dates=[str(d.date()) for d in uu[on.reindex(uu).values]])
out['unseen_signal_counts_only'] = cnt
print('UNSEEN COUNTS', json.dumps(cnt))

# ---- compare with the builder's files
kb = json.load(open(LANE + 'results/killB_early.json')); su = json.load(open(LANE + 'results/signal_counts_unseen.json')); cmp = {}
def put(k, a, b): cmp[k] = dict(mine=a, builder=b, equal=bool(a == b or (isinstance(a, float) and isinstance(b, float) and abs(a - b) < 1e-12)))
for v in ('CAP1', 'CAP2'):
    kv = kb['variants'][v]; ev = early['variants'][v]
    put(v + '.early.n_blocks', early['n_blocks'], kv['n_blocks']); put(v + '.early.n_universe', early['n_universe'], kv['n_universe'])
    put(v + '.early.universe_v1B_counts', early['universe_v1B_counts'], kv['universe_v1B_counts'])
    put(v + '.early.base', early['base'], kv['base']); put(v + '.early.always_in_hit', early['always_in_hit'], kv['always_in_hit'])
    put(v + '.early.trigger_days', ev['trigger_days'], kv['signal']['trigger_days']); put(v + '.early.on_days', ev['on_days'], kv['signal']['on_days'])
    put(v + '.early.n_on', ev['n_on'], kv['n_on']); put(v + '.early.v1_below3_days', early['v1_below3_days'], kv['signal']['v1_below3_days'])
    put(v + '.early.pass_B', ev['pass_B'], kv['pass_B'])
    sv = su['variants'][v]; cv = cnt['variants'][v]
    put(v + '.unseen.n_blocks', cnt['n_blocks'], sv['n_blocks']); put(v + '.unseen.n_universe', cnt['n_universe'], sv['n_universe'])
    put(v + '.unseen.universe_v1B_counts', cnt['universe_v1B_counts'], sv['universe_v1B_counts'])
    for k in ('trigger_days', 'trigger_days_v1_below3', 'on_days', 'on_days_v1_below3'): put(v + '.unseen.' + k, cv[k], sv['signal'][k])
    put(v + '.unseen.n_on', cv['n_on'], sv['n_on']); put(v + '.unseen.n_on_any_v1_state', cv['n_on_any_v1_state'], sv['n_on_any_v1_state'])
    put(v + '.unseen.on_block_dates', cv['on_block_dates'], [d['t'] for d in sv['on_block_dates']])
out['compare_mine_vs_builder'] = cmp
bad = [k for k, x in cmp.items() if not x['equal']]
for k, x in cmp.items(): print('CMP', k, x)
print('MISMATCHES', bad)
out['mismatches'] = bad
json.dump(out, open(LANE + 'verify/v2_killB.json', 'w'), indent=1)
print('v1 share 1986-2014', out['v1_state_share_1986_2014'], 'calendar', out['calendar'])
print('saved verify/v2_killB.json')
