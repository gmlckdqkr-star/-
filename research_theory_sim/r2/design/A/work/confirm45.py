import grid
grid.SEEDS = (4, 5); grid.BASE_FILE = 'base_s45.json'; grid.W.clear()
from grid import *
b = dict(p0=0.02, th_c=1.25, hl_m=40, L_r=0.0)
print(json.dumps(grid.base()))
for name, kw in [('A exit p0=.02 th=1.25 hm=40', b), ('B A+th_r=0.9', dict(b, th_r=0.9)), ('C A+L_r=1.5 d_r=.2', dict(b, L_r=1.5, d_r=0.2)),
                 ('D th=1.2', dict(b, th_c=1.2)), ('E p0=0.015', dict(b, p0=0.015)), ('F th=1.3', dict(b, th_c=1.3))]:
    grid.run_variant('[s4,5] ' + name, kw)
