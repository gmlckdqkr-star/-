"""neigh part 1: one-at-a-time neighbours (parameters outside the pre-registered grid) + joint random neighbours, per adopted pick.
Selection bases only (dev250_path 500 paths, real NDX 1986-2014, real S&P 1929-54 fill A). <=2014 data. Writes local.json."""
import sys, json, time, copy, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/checks/neigh')
import neighlib as NL
DC = NL.DC
t0 = time.time()
BASE = {bn: DC.market(bn) for bn in DC.SEL}
M3c = {}
def M3(**e):
    key = tuple(sorted(e.items()))
    if key not in M3c:
        if len(M3c) > 6: M3c.clear()
        M3c[key] = {bn: NL.env(BASE[bn], **e) for bn in DC.SEL}
    return M3c[key]

# sanity: the default-environment rebuild must reproduce grid numbers exactly
U = NL.grid_union(); F = NL.frontier(U)
for p, cid in NL.PICKS.items():
    d = NL.run3(NL.ALLC[cid], M3(), {}); g = U[cid]
    assert abs(d['dev250_path']['cagr'] - g['dev250_path']['cagr']) < 1e-12 and abs(d['wd'] - NL.wd_of(g)) < 1e-12, p
# own vol-cap rebuild equals px1lib at default
c = BASE['real_ndx_86_14']['ctx']
assert np.array_equal(NL.sig_F1(c), NL.PX.signal(c, DC.V1S))
print('repro ok %.0fs' % (time.time() - t0), flush=True)

def variants(cfg):
    """(group, name, env kwargs, engine kwargs, cfg change). CORE = the families named in the task; EXTRA = additional probes."""
    s = cfg['sig']; V = []
    for x in (0.8, 1.2): V.append(('core', 'knee', 'knee_x%.1f' % x, {}, dict(ks=x), {}))
    for f in (0.0, 0.5): V.append(('core', 'kfloor', 'kfloor_%.2f' % f, {}, dict(kfl=f), {}))
    for n in (10, 40, 60): V.append(('core', 'volwin', 'volwin_%d' % n, dict(vwin=n), {}, {}))
    for n in (150, 250): V.append(('core', 'sma', 'sma_%d' % n, dict(sl=n), {}, {}))
    for b in (0.01, 0.03): V.append(('core', 'band', 'band_%.2f' % b, dict(bd=b), {}, {}))
    for v in (0.35, 0.45): V.append(('core', 'vcap', 'vcap_%.2f' % v, dict(vc=v), {}, {}))
    for ds in (-0.025, 0.025): V.append(('core', 'sigma', 'sigma_%+.3f' % ds, {}, {}, dict(sig=round(s + ds, 4))))
    for sl in (0.05, 0.15): V.append(('core', 'steplo', 'steplo_%.2f' % sl, {}, dict(step_lo=sl), {}))
    # extras (not in the task list): step_hi, idxup SMA for the knee floor, vol window applied to the 0.40 vol cap too
    for sh in (0.20, 0.30): V.append(('extra', 'stephi', 'stephi_%.2f' % sh, {}, dict(step_hi=sh), {}))
    for n in (150, 250): V.append(('extra', 'idxsma', 'idxsma_%d' % n, dict(idx_sma=n), {}, {}))
    for n in (10, 40, 60): V.append(('extra', 'volwin_both', 'volwin_both_%d' % n, dict(vwin=n, vwin_cap=n), {}, {}))
    return V

OUT = dict(picks={}, notes='NON-ACTUAL dev250_path bootstrap + real NDX 86-14 + real S&P 29-54 (fill A); all <=2014.')
for p, cid in NL.PICKS.items():
    cfg0 = NL.ALLC[cid]; bud = NL.BUD[p]
    b = NL.flat(NL.run3(cfg0, M3(), {})); rows = []
    for grp, fam, nm, e, k, cc in variants(cfg0):
        cfg = dict(cfg0); cfg.update(cc)
        kw = NL.eng_kw(cfg, **k)
        r = NL.flat(NL.run3(cfg, M3(**e), kw))
        r.update(group=grp, fam=fam, name=nm, in_tier=bool(r['wd'] >= bud), dpath=r['path'] - b['path'],
                 frontier_at_wd=F(r['wd']), gap_vs_frontier=r['path'] - F(r['wd']))
        rows.append(r)
        print('%-6s %-18s path %6.2f (%+5.2f) mddp10 %6.2f ndx %6.2f/%6.2f spx29mdd %6.2f WD %6.2f %s gap %+5.2f' % (
            p, nm, 100 * r['path'], 100 * r['dpath'], 100 * r['path_mdd_p10'], 100 * r['ndx'], 100 * r['ndx_mdd'],
            100 * r['spx29_mdd'], 100 * r['wd'], 'IN ' if r['in_tier'] else 'OUT', 100 * r['gap_vs_frontier']), flush=True)
    # joint random neighbours: every knob drawn at once inside the same ranges (seed 7, 100 draws)
    rng = np.random.default_rng(7); J = []
    for j in range(100):
        e = dict(sl=int(rng.integers(150, 251)), bd=float(rng.uniform(0.01, 0.03)), vc=float(rng.uniform(0.35, 0.45)),
                 vwin=int(rng.integers(10, 61)))
        k = dict(ks=float(rng.uniform(0.8, 1.2)), kfl=float(rng.uniform(0.0, 0.5)), step_lo=float(rng.uniform(0.05, 0.15)))
        ds = float(rng.uniform(-0.025, 0.025))
        cfg = dict(cfg0); cfg['sig'] = cfg0['sig'] + ds
        M3c.clear(); r = NL.flat(NL.run3(cfg, M3(**e), NL.eng_kw(cfg, **k)))
        r.update(env=e, eng=k, dsig=ds, in_tier=bool(r['wd'] >= bud), dpath=r['path'] - b['path'], gap_vs_frontier=r['path'] - F(r['wd']))
        J.append(r)
    M3c.clear()
    core = [r for r in rows if r['group'] == 'core']
    def sh(L, f): return float(np.mean([f(r) for r in L])) if L else float('nan')
    summ = dict(
        n_core=len(core), share_core_in_tier=sh(core, lambda r: r['in_tier']), share_core_within_1pp=sh(core, lambda r: abs(r['dpath']) <= 0.01),
        share_core_in_tier_and_1pp=sh(core, lambda r: r['in_tier'] and abs(r['dpath']) <= 0.01),
        core_path_min=min(r['path'] for r in core), core_path_max=max(r['path'] for r in core), core_path_median=float(np.median([r['path'] for r in core])),
        core_wd_min=min(r['wd'] for r in core), core_wd_max=max(r['wd'] for r in core),
        core_in_tier_better_path=[r['name'] for r in core if r['in_tier'] and r['dpath'] > 0.0005],
        core_gap_vs_frontier_median=float(np.median([r['gap_vs_frontier'] for r in core])),
        n_all=len(rows), share_all_in_tier=sh(rows, lambda r: r['in_tier']), share_all_within_1pp=sh(rows, lambda r: abs(r['dpath']) <= 0.01),
        joint_n=len(J), joint_share_in_tier=sh(J, lambda r: r['in_tier']), joint_share_within_1pp=sh(J, lambda r: abs(r['dpath']) <= 0.01),
        joint_share_in_tier_and_1pp=sh(J, lambda r: r['in_tier'] and abs(r['dpath']) <= 0.01),
        joint_path_p10=float(np.percentile([r['path'] for r in J], 10)), joint_path_median=float(np.median([r['path'] for r in J])),
        joint_path_p90=float(np.percentile([r['path'] for r in J], 90)),
        joint_wd_p10=float(np.percentile([r['wd'] for r in J], 10)), joint_wd_median=float(np.median([r['wd'] for r in J])),
        joint_wd_p90=float(np.percentile([r['wd'] for r in J], 90)),
        joint_gap_vs_frontier_median=float(np.median([r['gap_vs_frontier'] for r in J])),
        joint_in_tier_path_median=float(np.median([r['path'] for r in J if r['in_tier']])) if any(r['in_tier'] for r in J) else None)
    OUT['picks'][p] = dict(id=cid, budget=bud, base=b, rows=rows, joint=J, summary=summ)
    print(p, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in summ.items()}), '%.0fs' % (time.time() - t0), flush=True)
json.dump(OUT, open('/mnt/project-files/research/df1/checks/neigh/local.json', 'w'), indent=1)
print('done %.0fs' % (time.time() - t0))
