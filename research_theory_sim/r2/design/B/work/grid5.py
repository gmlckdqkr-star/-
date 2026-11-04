from grid1 import *
for bh in (0.1, 0.2):
    ev('yard', k=0.6, hfwd=20, bh=bh, hy='y1')
for bh in (0.1, 0.2):
    ev('hope3', k=0.6, hfwd=20, bh=bh, hy=3)
for sm in (5, 10):
    ev('smooth', k=0.6, hfwd=20, bh=0.1, hy=1, smooth=sm)
