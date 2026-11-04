"""WS1 addendum 2: OpenDART disclosure events (sibling raw files, read-only) in this study's map metric.
KRALL (ADV20 >= 1e8 KRW), h = 21 and 5, conservative KR execution (wsstk). Stage 1 descriptive per type, stage 2 registered
strategy for types selected on 2001-2008 (net excess > 0, block-clustered t > 2). Join on stock_code only. <= 2014."""
import sys, json, glob, re, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/wide_shape/code')
import wsdata as D, wsstk as S
RAW = '/mnt/project-files/research/open_data/raw/'
RD = '/mnt/project-files/research/wide_shape/results/'
SPLIT = np.datetime64('2009-01-01')
MODE = sys.argv[1] if len(sys.argv) > 1 else 'counts'      # counts | full
FMODE = sys.argv[2] if len(sys.argv) > 2 else 'conservative'   # delisting classification (lenient = sensitivity only)


def clean(nm):
    nm = (nm or '').strip()
    if nm.startswith('['):
        return None
    nm = nm.replace('ㆍ', '').replace('·', '').replace(' ', '')
    while True:
        m = re.search(r'\([^()]*\)$', nm)
        if not m:
            break
        nm = nm[:m.start()]
    if nm in ('단일판매계약체결', '공급계약체결'):
        nm = '단일판매공급계약체결'
    return nm or None


def load_events():
    rows, months = [], {'B': set(), 'I': set()}
    for fn in sorted(glob.glob(RAW + 'dart_[BI]_*.jsonl')):
        src = fn.split('dart_')[1][0]
        for ln in open(fn, encoding='utf-8'):
            try:
                d = json.loads(ln)
            except Exception:
                continue
            months[src].add(d.get('_win', ''))
            sc = (d.get('stock_code') or '').strip(); nm = clean(d.get('report_nm'))
            if len(sc) != 6 or not sc.isdigit() or nm is None or not d.get('rcept_dt'):
                continue
            if d['rcept_dt'] > '20141231':
                continue
            rows.append((sc, d['rcept_dt'], nm, src))
    ev = pd.DataFrame(rows, columns=['code', 'dt', 'typ', 'src']).drop_duplicates(['code', 'dt', 'typ'])
    return ev, months


ev, months = load_events()
need = {'%04d%02d' % (y, m) for y in range(2001, 2015) for m in range(1, 13)}
miss = {k: sorted(need - v) for k, v in months.items()}
print('events', len(ev), '| missing months B', len(miss['B']), (miss['B'][:3], miss['B'][-3:]) if miss['B'] else '', '| I', len(miss['I']),
      (miss['I'][:3], miss['I'][-3:]) if miss['I'] else '', flush=True)
K_ = D.load_kr(); X_ = D.kr_derived(K_)
codes = pd.Index(K_['codes']); dates = pd.to_datetime(K_['dates'])
ev['ci'] = codes.get_indexer(ev['code'])
ev = ev[ev['ci'] >= 0].copy()
ev['t_use'] = np.searchsorted(dates.values, pd.to_datetime(ev['dt'], format='%Y%m%d').values, side='right')   # first trading day after filing
ev = ev[ev['t_use'] < len(dates)]
out = {'n_events_joined': int(len(ev)), 'missing_months': miss, 'h': {}}
for h in (21, 5):
    B = S.build_kr(K_, X_, h, start='2001-01-01', fail_mode=FMODE)
    nb = len(B.t_dec)
    b_of = np.searchsorted(B.t_dec, ev['t_use'].values, side='left')       # first decision at or after t_use = 'new' block
    e = ev.assign(b=b_of)
    e = e[e['b'] < nb]
    e = e[B.elig[e['b'].values, e['ci'].values]]
    isA = B.dates.values[e['b'].values] < SPLIT
    cntA = e[isA].groupby('typ').size()
    types = sorted(cntA[cntA >= 200].index)
    res = {'n_blocks': nb, 'split_block': int(np.searchsorted(B.dates.values, SPLIT)), 'types': {}, 'counts_A': {t: int(cntA[t]) for t in types}}
    print('h', h, 'types with >=200 eligible events 2001-2008:', len(types), flush=True)
    if MODE == 'counts':
        for t in types:
            print('  %-24s A %5d  all %5d' % (t, cntA[t], int((e['typ'] == t).sum())))
        out['h']['h%d' % h] = res
        continue
    q = B.seed_krw / 5
    cb = 0.00015 + B.hs + 0.7 * B.s20 * np.sqrt(q / B.adv)
    netpair = np.where(B.entry, B.R - (2 * cb + 0.003), 0.0)                 # failed entry = cash
    ew = np.array([np.nanmean(np.where(B.elig[b], B.R[b], np.nan)) for b in range(nb)])
    m10 = np.ceil(0.10 * B.n).astype(int); m1 = np.ceil(0.01 * B.n).astype(int)
    top10 = B.rk >= (B.n - m10)[:, None]; top1 = B.rk >= (B.n - m1)[:, None]; bot10 = (B.rk >= 0) & (B.rk < m10[:, None])
    split = res['split_block']
    for t in types:
        et = e[e['typ'] == t].drop_duplicates(['b', 'ci'])
        bb, ii = et['b'].values, et['ci'].values
        d = {}
        for part, sel in (('A', bb < split), ('B', bb >= split)):
            b_, i_ = bb[sel], ii[sel]
            if len(b_) == 0:
                d[part] = None; continue
            x = netpair[b_, i_] - ew[b_]
            blk = pd.Series(x).groupby(b_).mean()
            tt = float(blk.mean() / (blk.std(ddof=1) / np.sqrt(len(blk)))) if len(blk) > 2 else 0.0
            d[part] = dict(n=int(len(b_)), nblk=int(len(blk)), top1=float(top1[b_, i_].mean()), top10=float(top10[b_, i_].mean()),
                           bot10=float(bot10[b_, i_].mean()), entry_ok=float(B.entry[b_, i_].mean()), ex_net=float(blk.mean()), t=tt)
        res['types'][t] = d
        a, b2 = d['A'], d['B']
        print('  %-24s A n%5d top1 %.3f top10 %.3f bot10 %.3f ex %+.4f t %+.1f | B %s' % (
            t, a['n'], a['top1'], a['top10'], a['bot10'], a['ex_net'], a['t'],
            ('n%5d top1 %.3f top10 %.3f bot10 %.3f ex %+.4f t %+.1f' % (b2['n'], b2['top1'], b2['top10'], b2['bot10'], b2['ex_net'], b2['t'])) if b2 else '-'), flush=True)
    sel = [t for t in types if res['types'][t]['A'] and res['types'][t]['A']['ex_net'] > 0 and res['types'][t]['A']['t'] > 2]
    res['selected'] = sel
    ewB = float(np.prod(1 + ew[split:]) ** (252.0 / ((nb - split) * h)) - 1)
    res['ew_B'] = ewB
    if sel:
        es = e[e['typ'].isin(sel)]
        rng = np.random.default_rng(5)
        es = es.assign(u=rng.random(len(es))).sort_values(['b', 't_use', 'u'], ascending=[True, False, True]).drop_duplicates(['b', 'ci'])
        for K in (5, 20):
            pk = np.full((nb, K), -1, np.int64)
            for b, g in es.groupby('b'):
                c = g['ci'].values[:K]; pk[b, :len(c)] = c
            r, gr, cs = S.run_picks(B, pk)
            re_, rs, p10 = S.perf(B, r)
            BA = S.Blocks(); BA.h = h; BA.years = B.years[:split]; BA.tax = False
            BB = S.Blocks(); BB.h = h; BB.years = B.years[split:]; BB.tax = False
            fill = float((pk >= 0).sum(1).mean() / K)
            res['K%d' % K] = dict(real=re_, res_med=rs, res_p10=p10, real_A=S.perf(BA, r[:split])[0], real_B=S.perf(BB, r[split:])[0],
                                  gross_yr=float(gr.mean() * 252 / h), cost_yr=float(cs.mean() * 252 / h), slot_fill=fill)
        k = res['K5']
        res['pass'] = bool(k['real_B'] > 0 and k['real_B'] > ewB and k['res_med'] > 0.242 and
                           all(res['types'][t]['B'] and res['types'][t]['B']['ex_net'] > 0 for t in sel))
        print('h', h, 'selected', sel, 'K5', json.dumps(res['K5']), 'K20', json.dumps(res['K20']), 'EW_B %.3f' % ewB, 'pass', res['pass'], flush=True)
    else:
        res['pass'] = False
        print('h', h, 'no type selected', flush=True)
    out['h']['h%d' % h] = res
if MODE == 'full':
    out['trials_added'] = sum(len(v['types']) for v in out['h'].values()) + 4
    out['fail_mode'] = FMODE
    json.dump(out, open(RD + ('dart_map.json' if FMODE == 'conservative' else 'dart_map_%s.json' % FMODE), 'w'), indent=1, ensure_ascii=False)
