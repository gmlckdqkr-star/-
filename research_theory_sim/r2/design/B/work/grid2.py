from grid1 import *
for bf in (0.05, 0.15):
    for hmid in (80, 160):
        ev('fear', k=0.5, hfwd=20, hf=20, hmid=hmid, bf=bf)
for bl in (0.05, 0.15):
    ev('fearL', k=0.5, hfwd=20, hmid=80, hl=640, bl=bl)
for bh in (0.1, 0.3):
    ev('hope', k=0.5, hfwd=20, bh=bh, hy=1)
