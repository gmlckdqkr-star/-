"""KL1 selection screen for S2-KR / S2-US (index timing by aggregate loser-intensity atoms), M1 engine copy.
KR: KR200 proxy products on the KR panel calendar, selection days 1999-01-04..2008-12-31, cost 0.15%.
US: S&P (<1986-01-02) / NDX (>=) MS1 products on the jp calendar, atoms from the S&P panel (last panel date <= day),
selection days 1971-01-04..1999-12-31, cost 0.3%. The engine runs only up to the last selection day."""
import os, sys, json, time, hashlib, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/claude-0/-home-user--/e60ac389-f078-575c-af9f-bad532fab64a/scratchpad/kl/nb')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wsdata as WD, kl_engine as EN
CACHE = WD.CACHE
SEL = {'KR': ('1999-01-04', '2008-12-31'), 'US': ('1971-01-04', '1999-12-31')}


def month_slots(dates, a, b):
    m = np.full(len(dates), -1, np.int64)
    w = (dates >= pd.Timestamp(a)) & (dates <= pd.Timestamp(b)); a0 = pd.Timestamp(a)
    m[w] = (dates.year[w] - a0.year) * 12 + (dates.month[w] - a0.month)
    return m, int(np.flatnonzero(w)[0]), int(np.flatnonzero(w)[-1]) + 1


def inputs(panel):
    if panel == 'KR':
        z = np.load(CACHE + 'kr_idx.npz'); dates = pd.to_datetime(z['dates'])
        A = np.load(CACHE + 'kr_atoms.npy')
        return dict(dates=dates, X=np.ascontiguousarray(z['X']), A=np.ascontiguousarray(A), cost=0.0015)
    sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std, jp  # noqa
    R, M = jp.calendar('1968-01-02', '2014-12-31')
    d = R.index
    r = R['SPX'].where(d < pd.Timestamp('1986-01-02'), R['NDX']).fillna(0.0).values
    rf = M['rf'].reindex(d).ffill().fillna(0.0).values
    X = EN.products(r, rf)
    pd_ = pd.to_datetime(np.load(CACHE + 'us_dates.npy'))
    pos = np.searchsorted(pd_.values, d.values, side='right') - 1
    A0 = np.load(CACHE + 'us_atoms.npy')
    A = np.where(pos[None, :] >= 0, A0[:, np.maximum(pos, 0)], -1).astype(np.int8)
    return dict(dates=d, X=X, A=np.ascontiguousarray(A), cost=0.003, r=r, rf=rf)


def run(panel):
    t0 = time.time()
    I = inputs(panel); dates = I['dates']
    rules = np.load(CACHE + 'gen_S2%s.npy' % panel)
    mon, w0, w1 = month_slots(dates, *SEL[panel]); nmon = int(mon.max()) + 1
    t1 = w1                                    # engine stops at the last selection day
    A = np.ascontiguousarray(I['A'][:, :t1]); X = np.ascontiguousarray(I['X'][:, :t1])
    N = len(rules)
    D = np.zeros((N, nmon), np.float32); S = np.zeros((N, 4))
    ch = 20000
    for i in range(0, N, ch):
        rr = np.ascontiguousarray(rules[i:i + ch])
        om = np.zeros((len(rr), nmon), np.float32); os_ = np.zeros((len(rr), 4))
        EN.screen(A, X, rr, t1, mon, nmon, w0, w1, om, os_, I['cost'])
        D[i:i + ch] = om; S[i:i + ch] = os_
        print('  S2', panel, i + len(rr), '%.0fs' % (time.time() - t0), flush=True)
    np.save(CACHE + 'D_S2%s.npy' % panel, D); np.save(CACHE + 'stat_S2%s.npy' % panel, S)
    print('done S2', panel, D.shape, 'months', nmon, '%.0fs' % (time.time() - t0), flush=True)


if __name__ == '__main__':
    run(sys.argv[1])
