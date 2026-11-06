# NI1-B step 3: Frazzini-Lamont expected-announcer signal on S&P 500 PIT members; monthly Spearman IC, gate, reference basket.
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/bt1/ni1/B/code'); import fl_common as F
oap_p, shift_json, out = sys.argv[1], sys.argv[2], sys.argv[3]
SHIFT = json.load(open(shift_json))['chosen_shift']
dates, adj, mem = F.load_panel()
ym, me, months = F.month_index(dates)
K = len(months)
oap = pd.read_parquet(oap_p); oap = oap[oap.yyyymm <= 201412]
I, R, pidx = F.announcement_matrix(oap, months)
if SHIFT == -1:
    Ip = np.zeros_like(I); Ip[:-1] = I[1:]
else:
    Ip = I
memME = mem[me]
L = F.link_by_month(memME, R, pidx)
T = len(dates)
lastvalid = np.array([np.where(np.isfinite(adj[:, c]))[0].max() if np.isfinite(adj[:, c]).any() else -1 for c in range(adj.shape[1])])
later_delisted = lastvalid < T - 1

def rank(x):
    return pd.Series(x).rank(method='average').to_numpy()

rows = []
k0 = F.ym_to_m(197412) - months[0]; k1 = F.ym_to_m(201411) - months[0]
cov = []
for k in range(k0, k1 + 1):
    t_me = me[k]; ent = t_me + 2; ex = me[k + 1]
    m_cols = np.where(memME[k])[0]
    lk = L[k, m_cols] >= 0
    cov.append((months[k], len(m_cols), int(lk.sum()), int(later_delisted[m_cols].sum()), int((lk & later_delisted[m_cols]).sum())))
    # forward returns for all members (benchmark) and linked members (IC)
    pe = adj[ent, m_cols]
    seg = adj[ent + 1:ex + 1, m_cols]
    fin = np.isfinite(seg)
    lastidx = np.where(fin.any(0), seg.shape[0] - 1 - np.argmax(fin[::-1], 0), -1)
    px = np.where(lastidx >= 0, seg[np.maximum(lastidx, 0), np.arange(len(m_cols))], np.nan)
    fr = px / pe - 1
    okb = np.isfinite(fr)
    bench = fr[okb].mean() if okb.any() else np.nan
    okc = okb & lk
    cols = m_cols[okc]; f = fr[okc]
    js = L[k, cols]
    if k - 11 < 0: continue
    sig = Ip[k - 11, js] & ~Ip[k, js] & (Ip[k - 11:k + 1, js].sum(0) == 4)
    n = len(f); ns = int(sig.sum())
    if n >= 20 and 0 < ns < n:
        ic = np.corrcoef(rank(sig.astype(float)), rank(f))[0, 1]
    else:
        ic = np.nan
    bk = f[sig].mean() if ns else np.nan
    rows.append(dict(hold=int(months[k + 1]), n=n, ns=ns, ic=ic, basket=bk, bench=bench))
df = pd.DataFrame(rows)
df['hy'] = 1970 + df.hold // 12
def st(x):
    x = x[np.isfinite(x)]
    return dict(mean=float(x.mean()), sd=float(x.std(ddof=1)), n=int(len(x)), t=float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))))
per = {'1975-2014': (1975, 2014), '1975-84': (1975, 1984), '1985-94': (1985, 1994), '1995-04': (1995, 2004),
       '2005-14': (2005, 2014), '1989-2014': (1989, 2014)}
ic = {p: st(df.ic[(df.hy >= a) & (df.hy <= b)].to_numpy()) for p, (a, b) in per.items()}
full = ic['1975-2014']['mean']
dec_pos = all(ic[p]['mean'] > 0 for p in ['1975-84', '1985-94', '1995-04', '2005-14'])
keep = (full >= 0.05) and dec_pos and ic['1989-2014']['mean'] > 0
# reference basket
b = df[np.isfinite(df.basket) & np.isfinite(df.bench) & (df.hy >= 1975)].copy()
b['net'] = b.basket - 0.002; b['ex'] = b.net - b.bench
def ann(x): return float(np.prod(1 + x) ** (12 / len(x)) - 1)
bas = {}
for p, (a, c) in per.items():
    s = b[(b.hy >= a) & (b.hy <= c)]
    bas[p] = dict(months=int(len(s)), basket_gross_mean_m=float(s.basket.mean()), basket_net_mean_m=float(s.net.mean()),
                  bench_mean_m=float(s.bench.mean()), excess_net_mean_m=float(s.ex.mean()),
                  excess_net_t=float(s.ex.mean() / s.ex.std(ddof=1) * np.sqrt(len(s))),
                  basket_net_ann=ann(s.net.to_numpy()), bench_ann=ann(s.bench.to_numpy()),
                  basket_net_sharpe_ann_rawret=float(s.net.mean() / s.net.std(ddof=1) * np.sqrt(12)),
                  excess_net_ir_ann=float(s.ex.mean() / s.ex.std(ddof=1) * np.sqrt(12)))
cv = pd.DataFrame(cov, columns=['m', 'members', 'linked', 'members_later_delisted', 'linked_later_delisted'])
cv['y'] = 1970 + cv.m // 12
covd = {}
for p, (a, c) in per.items():
    s = cv[(cv.y >= a - (1 if a == 1975 else 0)) & (cv.y <= c)]
    s = cv[(cv.y >= a) & (cv.y <= c)] if a != 1975 else cv[(cv.y <= c)]
    covd[p] = dict(members_mean=float(s.members.mean()), linked_mean=float(s.linked.mean()),
                   linked_share=float(s.linked.sum() / s.members.sum()),
                   later_delisted_linked_share=float(s.linked_later_delisted.sum() / max(s.members_later_delisted.sum(), 1)),
                   other_linked_share=float((s.linked - s.linked_later_delisted).sum() / (s.members - s.members_later_delisted).sum()),
                   later_delisted_members_mean=float(s.members_later_delisted.mean()))
diag = dict(months_total=int(len(df[df.hy >= 1975])), months_ic=int(np.isfinite(df.ic[df.hy >= 1975]).sum()),
            ic_cross_section_n_mean=float(df.n.mean()), signal_count_mean=float(df.ns.mean()),
            signal_share_mean=float((df.ns / df.n).mean()),
            ic_positive_share=float((df.ic[np.isfinite(df.ic)] > 0).mean()),
            signal_share_by_decade={p: float((df.ns / df.n)[(df.hy >= a) & (df.hy <= c)].mean()) for p, (a, c) in per.items()},
            min_linked_month=int(cv.linked.min()), max_linked_month=int(cv.linked.max()))
res = dict(test='NI1-B Frazzini-Lamont expected-announcer premium, S&P 500 PIT', shift=SHIFT, ic=ic,
           gate=dict(full_mean_ge_005=bool(full >= 0.05), four_decades_positive=bool(dec_pos),
                     mean_1989_2014_positive=bool(ic['1989-2014']['mean'] > 0), verdict='KEEP' if keep else 'CLOSE'),
           basket_reference=bas, coverage=covd, diagnostics=diag)
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps(res, indent=1))
