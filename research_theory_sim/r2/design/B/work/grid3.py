from grid1 import *
for learn in (0, 1):
    for k in (0.4, 0.5, 0.6):
        for hfwd in (10, 20, 40):
            ev('kelly', k=k, hfwd=hfwd, learn=learn)
