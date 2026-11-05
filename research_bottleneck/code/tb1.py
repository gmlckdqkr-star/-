"""TB1 (PRECOMMIT_TB1.md sha 0e057f32). <=2014. v1 (s0.85) + tech-wave / bottleneck industry partner under MS1 (el._comb). Engine = DV2."""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/c3_create/lanes/I_INTEGRATE/code')
sys.path.insert(0, '/mnt/project-files/research/diversifier/code')
sys.path.insert(0, '/mnt/project-files/research/data/ken_french')
import ii, el, sl, kf_parse
import dv1
OUT = '/mnt/project-files/research/bottleneck/results/'
CUT = pd.Timestamp('2014-12-31')
POOL = ['Oil', 'Coal', 'Util', 'Trans', 'Telcm', 'Steel', 'Mines', 'Chips', 'ElcEq', 'Mach', 'LabEq']
MAP = {'Autos': ['Oil', 'Steel'], 'Aero': ['Oil', 'Mach'], 'Hardw': ['Chips', 'LabEq'], 'Softw': ['Chips'], 'Chips': ['LabEq', 'Mach'],
       'Telcm': ['Chips', 'ElcEq'], 'Drugs': ['LabEq']}
RULES = ['B1', 'B2', 'B3', 'K0']
LS = (1, 2, 3)
ST = [(r, L) for r in RULES for L in LS]
NM = ['%s_L%d' % x for x in ST]
_TW = {}

def kf49():
    S = kf_parse.sections('/mnt/project-files/research/broad_etf/data/raw/kf/49_Industry_Portfolios_daily_CSV.zip')
    vw = [v for k, v in S.items() if k.startswith('The')][0]
    vw = vw[vw.index <= CUT].where(lambda x: x > -99) / 100.0
    assert vw.index[-1] <= CUT
    return vw

def build():
    if _TW: return _TW
    S = sl.src(); idx = pd.DatetimeIndex(S['dates']); n = len(idx)
    vw = kf49().reindex(idx)
    for k in set(POOL) | set(MAP):
        S['K_' + k] = vw[k].fillna(0.0).values
    me = S['ME'] > 0.5; mpos = np.where(me)[0]
    lv = {k: np.cumsum(np.log1p(S['K_' + k])) for k in set(POOL) | set(MAP)}
    lm = np.cumsum(np.log1p(S['SPX']))
    np_ = len(POOL); pi = {k: i for i, k in enumerate(POOL)}
    ew = np.full(np_, 1.0 / np_)
    TW = {r: np.tile(ew, (n, 1)) for r in RULES}
    # B2: 12-1 momentum top-3 at month ends (value held until next decision; simw only reads TW at dec days)
    for t in mpos:
        if t >= 252:
            sc = np.array([lv[k][t - 21] - lv[k][t - 252] for k in POOL])
            w = np.zeros(np_); w[np.argsort(-sc)[:3]] = 1 / 3.0; TW['B2'][t] = w
    # B3: wave on if leader 36m (756d) log return minus market > 0.26
    act_log = []
    for t in mpos:
        if t < 756: continue
        on = [L for L in MAP if (lv[L][t] - lv[L][t - 756]) - (lm[t] - lm[t - 756]) > 0.26]
        tg = sorted({b for L in on for b in MAP[L]})
        if tg:
            w = np.zeros(np_)
            for b in tg: w[pi[b]] = 1.0 / len(tg)
            TW['B3'][t] = w
        act_log.append((str(idx[t].date()), on))
    # K0 hindsight ceiling: 5y block winner (diagnostic only)
    blocks = [('1986-01-01', '1990-12-31'), ('1991-01-01', '1995-12-31'), ('1996-01-01', '2000-12-31'), ('2001-01-01', '2005-12-31'),
              ('2006-01-01', '2010-12-31'), ('2011-01-01', '2014-12-31')]
    win = []
    for a, b in blocks:
        m = (idx >= pd.Timestamp(a)) & (idx <= pd.Timestamp(b)); ix = np.where(m)[0]
        tot = [lv[k][ix[-1]] - lv[k][ix[0] - 1] for k in POOL]; j = int(np.argmax(tot)); win.append((a, POOL[j]))
        w = np.zeros(np_); w[j] = 1.0
        lo = max(ix[0] - 3, 0)                   # decided so that the 2-day delayed trade lands at block start
        TW['K0'][lo:ix[-1] - 2] = w
    dK0 = me.copy().astype(np.float64)
    for a, b in blocks:
        i0 = int(np.searchsorted(S['dates'], np.datetime64(pd.Timestamp(a)))); dK0[max(i0 - 3, 0)] = 1.0
    S['DEC_K0'] = dK0
    _TW.update(TW); _TW['_act'] = act_log; _TW['_win'] = win
    return _TW

_A = {}
def arrays(bn, chunk=100):
    if bn in _A: return _A[bn]
    TW = build(); ii.ext(); c = ii.ctx(bn); I0 = c['ii']; off = c['off']; P, T = I0.shape
    S = np.zeros((P, T - ii.WARM, len(ST)), np.float32); SO = np.zeros_like(S); hi = off + int(I0.max()) + 1
    for a in range(0, P, chunk):
        sub = I0[a:a + chunk]; I = sl.inputs(sub, off, hi=hi); p, t = I['P'], I['T']; g = I.g
        R = np.stack([I['K_' + k] for k in POOL], axis=2); R[:, 0, :] = 0.0
        for j, (rule, L) in enumerate(ST):
            A = np.stack([sl.asset(I, 'eq', R[:, :, i], L) for i in range(len(POOL))], axis=2)
            tw = TW[rule][g]; dec = (I['DEC_K0'] if rule == 'K0' else I['ME']).copy()
            s, so = sl.simw(np.ascontiguousarray(A), I['dep'], np.ascontiguousarray(tw.astype(np.float64)), dec, 2, 0.003)
            S[a:a + chunk, :, j] = s[:, ii.WARM:]; SO[a:a + chunk, :, j] = so[:, ii.WARM:]
    _A.clear(); _A[bn] = (S, SO); return S, SO

def run(bn, j, w, cost=0.003):
    TQ, DEP, CU, IDL = ii.ref_in(bn); S, SO = arrays(bn)
    if w == 0:
        Sa = np.zeros((S.shape[0], S.shape[1], 1), S.dtype); SOa = Sa.copy(); wv = np.zeros(1)
    else:
        Sa = np.ascontiguousarray(S[:, :, j:j + 1]); SOa = np.ascontiguousarray(SO[:, :, j:j + 1]); wv = np.array([w])
    return el._comb(np.ascontiguousarray(TQ), np.ascontiguousarray(DEP), np.ascontiguousarray(CU), np.ascontiguousarray(IDL), Sa, SOa,
                    1 - w, wv, 0, cost, ii._PP['tax'], ii._D, int(ii._PP['harvest']), ii._PP['hthr'], 21, 0.05, 0.25)

W = (0.1, 0.2, 0.3)

def full(bn, j, w, f0, E0, s0, fc0, D=None, b00=None, gn=None):
    """confirm-style row for one stream/weight"""
    r = {}; T = E0.shape[1]
    f, E = run('dev250_path', j, w); st = ii.stats('dev250_path', f, E); dd = np.log(f / f0) / (T / 252) * 100
    r['path'] = dict(cagr=float(st['cagr']) * 100, mdd=float(st['mdd']), dd80=float(st['dd80']), dmed=float(np.median(dd)), win=float(np.mean(dd > 0)))
    fc, _ = run('dev250_path', j, w, cost=0.006); r['cost2x_dmed'] = float(np.median(np.log(fc / fc0) / (T / 252) * 100))
    return r

def standalone(bn, j):
    """partner alone at w=1 (sleeve's own CAGR on this basis, MS1 tax)"""
    f, E = run(bn, j, 1.0); return float(ii.stats(bn, f, E)['cagr']) * 100

if __name__ == '__main__':
    t0 = time.time(); TW = build(); res = {'win_K0': TW['_win']}
    on = [x for x in TW['_act'] if x[1]]
    res['b3_active_share'] = len(on) / max(len(TW['_act']), 1)
    res['b3_on_examples'] = {y: [x for x in TW['_act'] if x[0].startswith(y)][:1] for y in ('1960', '1970', '1980', '1990', '1998', '2005', '2012')}
    print('K0 winners', TW['_win'], '\nB3 active share', round(res['b3_active_share'], 3), flush=True)
    # ---- kill test 1: hindsight ceiling K0 on confirm bases
    out = {}
    f0, E0 = run('dev250_path', 0, 0); s0 = ii.stats('dev250_path', f0, E0); fc0, _ = run('dev250_path', 0, 0, cost=0.006)
    fn, En = run('real_ndx_86_14', 0, 0); gn = ii.stats('real_ndx_86_14', fn, En)['cagr']
    D = dv1.dates('real_ndx_86_14'); b00 = dv1.seg(En[0], D, '2000-01-01', '2014-12-31')
    out['_v1'] = dict(path=float(s0['cagr']) * 100, dd80=float(s0['dd80']), mdd=float(s0['mdd']), ndx=float(gn) * 100, nd00=float(b00) * 100)
    print('v1', out['_v1'], flush=True)
    for L in LS:
        j = NM.index('K0_L%d' % L)
        for w in W:
            f, E = run('dev250_path', j, w); st = ii.stats('dev250_path', f, E); dd = np.log(f / f0) / (E0.shape[1] / 252) * 100
            fN, EN = run('real_ndx_86_14', j, w); g = ii.stats('real_ndx_86_14', fN, EN)['cagr']
            out['K0_L%d|%.1f' % (L, w)] = dict(path=float(st['cagr']) * 100, dmed=float(np.median(dd)), win=float(np.mean(dd > 0)),
                                               dd80=float(st['dd80']), ndx=float(g) * 100, d_ndx=float(g - gn) * 100)
            print('K0_L%d|%.1f' % (L, w), {k: round(v, 3) for k, v in out['K0_L%d|%.1f' % (L, w)].items()}, flush=True)
    res['K0'] = out
    json.dump(res, open(OUT + 'k0_ceiling.json', 'w'), indent=1, default=str)
    print('sec', round(time.time() - t0))
