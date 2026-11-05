import sys, json; sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
out = {}
for nm, kw in (('K1a_delay1', dict(delay=1)), ('K1b_cspr1', dict(cspr=0.01)), ('K1c_delay3', dict(delay=3))):
    def make(c, kw=kw):
        B, f, p, fs = std.s085(c); return B, f, p, fs, kw
    T = std.measure(nm, make); out[nm] = T
json.dump(out, open('/mnt/project-files/research/nx1/results/k1.json', 'w'), indent=1)
