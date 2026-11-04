import itertools, gridrun as G
cfg=[dict(hv=hv,H=Hh,a0=a0,a1=a1) for hv in (20,40,80) for Hh in (0.5,1.0,2.0) for a0 in (0.0,0.02,0.04) for a1 in (0.0,0.1,0.2,0.4)]
rows=G.run_grid(cfg,'grid1_price_ledger',seeds=(1,))
print('N =',len(cfg)); G.show(rows,20)
import json; json.dump(rows,open('grid1_rows.json','w'))
