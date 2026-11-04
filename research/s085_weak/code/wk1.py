"""WK1 fixes (PRECOMMIT_WK1.md): G1 incremental test + MS1 for W1..W8."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/s085_weak/code'); import wk
std = wk.std; bk = wk.bk; jp = wk.jp; ov = wk.ov

def feats(c):
    lv = c.lvl; P, T = lv.shape
    rfa = c.rf * 252
    v20 = c.vol(20); v60 = c.vol(60); s200 = c.sma(200)
    m252 = np.full((P, T), np.nan); m252[:, 252:] = lv[:, 252:] / lv[:, :-252] - 1
    d = np.abs(np.diff(lv, axis=1, prepend=lv[:, :1])); cs = np.cumsum(d, axis=1)
    er = np.full((P, T), np.nan); er[:, 63:] = np.abs(lv[:, 63:] - lv[:, :-63]) / np.maximum(cs[:, 63:] - cs[:, :-63], 1e-12)
    tr = lv / s200
    with np.errstate(invalid='ignore'):
        W = dict(W1=rfa < 0.04, W2=v20 < 0.20, W3=tr > 1.05, W4=er > 0.30, W5=m252 > 0.15,
                 W6=2 * m252 > 4 * v60 ** 2 + 2 * rfa + 0.0245, W7=(er > 0.30) | (tr > 1.10), W8=(v60 < 0.25) & (m252 > 0.10))
    return W

def make_fix(k):
    def make(c):
        B, bfn, bp, fs = std.s085(c); W = feats(c)[k]
        return np.where((B > 1.0) & ~W, 1.0, B), bfn, bp, fs
    return make

def g1_incr():
    C = std.contexts(); import gate
    out = {}
    for era, (bn, a, b, st, cal) in {'ndx_86_14': ('real_ndx_86_14', '1984-01-03', '2014-12-31', '1986-01-02', 'NDX'),
                                     'spx_55_85': ('real_spx_55_85', '1928-01-03', '1985-12-31', '1955-01-03', 'SPX')}.items():
        c = C[bn]; R, M = jp.calendar(a, b); X = jp.mkX(R, M, cal); dts = X.index[c.ii[0]]
        B = std.s085(c)[0][0]; W = feats(c)
        lab = gate.labels()[era]
        # secondary label: 3x beats 1x over t+3..t+23
        ex = np.log1p(3 * X['r'] - 2 * X['rf'] - 0.0245 / 252) - np.log1p(X['r'] - 0.002 / 252); cs = np.r_[0, np.cumsum(ex.values)]
        pos = {d: i for i, d in enumerate(X.index)}
        lab2 = pd.Series({d: cs[pos[d] + 24] - cs[pos[d] + 3] > 0 for d in lab.index})
        on = pd.Series(B >= 2.5, dts).reindex(lab.index, method='ffill')
        base_hit = float(((pd.Series(B > 0, dts).reindex(lab.index, method='ffill')) == lab).mean())
        out.setdefault('C3_base_hit', {})[era] = base_hit
        for k, w in W.items():
            s = pd.Series(w[0], dts).reindex(lab.index, method='ffill')
            sel = on & ~s.astype(bool)
            n = int(sel.sum()); h = float((~lab[sel]).mean()) if n else np.nan; h2 = float((~lab2[sel]).mean()) if n else np.nan
            se = (h * (1 - h) / n) ** .5 if n else np.nan
            out.setdefault(k, {})[era] = dict(n=n, hit_3x_lt_cash=h, deflated=h - 2 * se * (1 + np.log(8)) ** .5 if n else np.nan,
                                             hit_3x_lt_1x=h2, base_rate_3x_lt_cash_when_on=float((~lab[on.astype(bool)]).mean()))
    for k in [x for x in out if x.startswith('W')]:
        low = min(v['deflated'] for v in out[k].values() if v['n'] > 0) if all(v['n'] > 5 for v in out[k].values()) else -1
        out[k]['G1_incr'] = 'PASS' if low >= 0.65 else 'CLOSE'; out[k]['low_deflated'] = low
    return out

if __name__ == '__main__':
    sys.path.insert(0, '/mnt/project-files/research/breakthrough/code')
    G = g1_incr(); print(json.dumps(G, indent=1), flush=True)
    M = {}
    for k in ['W%d' % i for i in range(1, 9)]:
        T = std.measure(k, make_fix(k), verbose=False)
        M[k] = {bn: dict(cagr=T[bn]['cagr'], d=T[bn]['d_vs_s085'], pw=T[bn]['pw_vs_s085'], dd80=T[bn].get('dd80')) for bn in T if isinstance(T[bn], dict)}
        print(k, json.dumps(M[k]), flush=True)
    json.dump(dict(G1=G, MS1=M), open('/mnt/project-files/research/s085_weak/results/wk1.json', 'w'), indent=1)
