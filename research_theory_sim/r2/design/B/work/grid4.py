from grid1 import *
for k in (0.5, 0.6):
    for bf in (0.0, 0.03, 0.06):
        for bh in (0.0, 0.1, 0.2):
            if bf == 0 and bh == 0: continue
            ev('fh', k=k, hfwd=20, hf=20, hmid=80, bf=bf, bh=bh, hy=1)
