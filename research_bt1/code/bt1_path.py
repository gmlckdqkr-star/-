"""daily detail of one BT1 rule row (any form): dec (decided product at close t), act, g (log growth vs 1x after cost).
Same logic as bt1_mega.screen / m1_engine.one_path."""
import os, sys, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt1_mega as BM, m1_engine as EN
from numba import njit


@njit(cache=True)
def _one(A, LX, r, t1, CC):
    dec = np.empty(t1, np.int64); act = np.zeros(t1, np.int8); g = np.zeros(t1)
    hold = r[14]; held = 2; age = 1 << 30; prev = 0
    for t in range(t1):
        v = BM.rcode(A, r, t)
        if v < 0:
            act[t] = 0
            if held != 2:
                held = 2; age = 0
            else:
                age += 1
            prev = 0
        else:
            act[t] = 1
            if v != held:
                if prev == 0 or age + 1 >= hold:
                    held = v; age = 0
                else:
                    age += 1
            else:
                age += 1
            prev = 1
        dec[t] = held
    for t in range(t1):
        p = dec[t - 3] if t >= 3 else 2
        pn = dec[t - 2] if t >= 2 else 2
        lg = LX[p, t]
        if t + 1 < t1 and pn != p:
            lg += CC[p, pn]
        g[t] = lg
    return dec, act, g


def one_path(A, X, row, t1=None):
    t1 = A.shape[1] if t1 is None else t1
    LX = BM.logx(np.ascontiguousarray(X[:, :t1]))
    return _one(np.ascontiguousarray(A[:, :t1]), LX, np.asarray(row, np.int32), t1, BM.COSTC)


def codes(row):
    f = int(row[0])
    return [int(row[11]), int(row[12])] if f in (0, 1, 2) else [int(row[11]), int(row[12]), int(row[13])]
