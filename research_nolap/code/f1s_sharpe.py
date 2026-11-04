import numpy as np, json
from common import *
import fomc
C, DM = ctx_dates(); c = C['real_ndx_86_14']; W = ov.WARM
o = {}
for win in (1, 2):
    F = fomc.flags_for(DM['real_ndx_86_14'], fomc_days(), win); B = 3 * shift_left(F, 3)
    # pre-tax after-cost: run engine with tax 0
    _, E = std.engine(c, B, std.ident, np.zeros(1), 0.5, tax=0.0)
    x = E[0, 1:] / E[0, :-1] - 1; rf = c.rf[0, W + 1:]; d = DM['real_ndx_86_14'][0, W + 1:]
    m = d >= np.datetime64('1994-02-01'); ex = (x - rf)[m]
    o['F%dS' % win] = float(ex.mean() / ex.std() * np.sqrt(252)); print(win, o['F%dS' % win])
json.dump(o, open(RES + '/n1_sharpe.json', 'w'))
