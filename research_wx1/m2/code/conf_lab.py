"""Lab-engine after-tax rows of the discovery #1 variant on the confirmation window only (2000-01-03..2014-12-31) and
EW on the same window (decay in after-tax terms; one shot, after the confirmation). argv: code_dir out_json"""
import sys, json, numpy as np, pandas as pd
sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2], '/dev/null']
src = open(sys.argv[1] + '/final.py').read()
src = src[:src.index("out = {'variants': {}}")]          # reuse data / score() definitions only
exec(compile(src, 'final_defs', 'exec'))
v = VAR[1560]
sc, g = score(v)
tg = LB.targets_from_picks(P, d, M.top_picks(sc, 50, rows=rs), v['K'], rb=v['Rb'], gate=g)
o = {'v1560_2000_2014': LB.aftertax_rows(P, tg, start='2000-01-03'), 'v1560_1986_1999': None}
st = pd.Timestamp('1986-01-02')
import lab.stocks as S_
# 1986-1999 after-tax: run to DEV_END is fixed in lab; report full and late window only
json.dump(o, open(sys.argv[2], 'w'), indent=1, default=float)
print(json.dumps(o, default=float))
