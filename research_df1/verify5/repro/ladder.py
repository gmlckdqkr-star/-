"""My own A5 ladder (from PRECOMMIT_DF5 sec 3 A5 text): assets [QQQ, QLD, TQQQ, D]. Start QQQ 1-d0, D d0.
Profit ladder (optional): each +g of NDX level since last reference (outside a crisis) move f of the QQQ weight into D.
Down ladder: crisis steps at NDX drawdown from running peak <= -th1/-th2/-th3; at each step move 1/3 of the D weight held at
crisis start into QQQ (step1), QLD (step2), TQQQ (step3); 'T200' confirmation = execute armed steps only while NDX > 200d SMA.
When NDX regains the crisis-start peak, QLD+TQQQ are folded into QQQ. Trades only at events (weights drift otherwise)."""
import numpy as np
WARM = 300

def ladder(lv, on200, RQ, R2, R3, RD, up=None, dn=None, conf=0, d0=0.3):
    P, T = lv.shape
    W = np.zeros((P, T, 4)); EV = np.zeros((P, T), bool)
    w = np.zeros((P, 4)); w[:, 0] = 1 - d0; w[:, 3] = d0
    W[:, WARM - 1] = w; EV[:, WARM - 1] = True
    H = lv[:, WARM - 1].copy(); Rup = H.copy()
    s = np.zeros(P, int); armed = np.zeros((P, 3), bool); epi = np.zeros(P, bool); Hep = np.zeros(P); D0 = np.zeros(P)
    th = dn if dn else None
    for t in range(WARM, T):
        g = w * (1 + np.stack([RQ[:, t], R2[:, t], R3[:, t], RD[:, t]], 1))
        w = g / np.maximum(g.sum(1, keepdims=True), 1e-300)
        x = lv[:, t]; H = np.maximum(H, x); ev = np.zeros(P, bool)
        if up:
            c = (~epi) & (x >= Rup * (1 + up[0]))
            mv = np.where(c, up[1] * w[:, 0], 0.0); w[:, 0] -= mv; w[:, 3] += mv
            Rup = np.where(c, x, Rup); ev |= c & (mv > 0)
        if th:
            dd = x / H - 1
            for j in range(3):
                armed[:, j] |= (j >= s) & (dd <= -th[j])
            new = armed[:, 0] & ~epi
            Hep = np.where(new, H, Hep); D0 = np.where(new, w[:, 3], D0); epi |= new
            go = epi & ((conf == 0) | on200[:, t])
            for st in range(3):
                c = go & (s == st) & armed[:, st]
                mv = np.where(c, np.minimum(D0 / 3.0, w[:, 3]), 0.0)
                w[:, 3] -= mv; w[:, st] += mv; ev |= c & (mv > 0); s = s + c.astype(int)
            rec = epi & (x >= Hep)
            ev |= rec & ((w[:, 1] > 0) | (w[:, 2] > 0))
            w[:, 0] = np.where(rec, w[:, 0] + w[:, 1] + w[:, 2], w[:, 0])
            w[:, 1] = np.where(rec, 0.0, w[:, 1]); w[:, 2] = np.where(rec, 0.0, w[:, 2])
            s = np.where(rec, 0, s); armed[rec] = False; epi = np.where(rec, False, epi); Rup = np.where(rec, x, Rup)
        EV[:, t] = ev; W[:, t] = w
    return W, EV
