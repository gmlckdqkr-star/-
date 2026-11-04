"""N1 FOMC pre-announcement drift: F1/F2 x standalone/overlay under MS1 + placebo + correlation."""
import numpy as np, pandas as pd, json
from common import *

def flags_for(dates_mat, ev, win):
    evs = set(np.array(ev, dtype='datetime64[ns]').astype('datetime64[D]'))
    D = dates_mat.astype('datetime64[D]')
    F = np.isin(D, list(evs))
    if win == 2:   # also the trading day before the event (in the path's own previous day of the source calendar)
        G = np.zeros_like(F); G[:, :-1] = F[:, 1:]; F = F | G
    return F.astype(float)

def main():
    C, DM = ctx_dates(); ev = fomc_days(); print('events 1994-2014:', len(ev))
    out = {}
    for win in (1, 2):
        for use in ('S', 'O'):
            name = 'F%d%s' % (win, use)
            def make(c, win=win, use=use):
                key = [k for k, v in C.items() if v is c][0]
                F = flags_for(DM[key], ev, win); E3 = 3 * shift_left(F, 3)
                if use == 'S': return E3, std.ident, np.zeros(1), 0.5
                B, bfn, bp, fs = std.s085(c); return np.maximum(B, E3), bfn, bp, fs
            out[name] = std.measure(name, make)
    json.dump(out, open(RES + '/n1_fomc_ms1.json', 'w'), indent=1)

if __name__ == '__main__': main()
