from grid import *
for p0, th, hm in itertools.product((0.02, 0.03), (1.15, 1.2, 1.25), (40, 60)):
    run_variant('exit p0=%.2f th=%.2f hl_m=%d' % (p0, th, hm), dict(p0=p0, th_c=th, hl_m=hm, L_r=0.0))
