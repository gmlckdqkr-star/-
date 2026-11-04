from harness import *
for mech in (True, False):
    w = world(1, 1000, mech)
    t0 = time.time(); b = baselines(w)
    print('mech', mech, json.dumps(b), '%.0fs' % (time.time() - t0))
