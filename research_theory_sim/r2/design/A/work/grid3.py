from grid import *
b = dict(p0=0.02, th_c=1.25, hl_m=40, L_r=0.0)
for name, kw in [('hl_f=3', dict(hl_f=3)), ('hl_f=8', dict(hl_f=8)), ('hl_tr=10', dict(hl_tr=10)), ('hl_tr=40', dict(hl_tr=40)),
                 ('no trend cond', dict(use_trend=False)), ('th_r=0.9', dict(th_r=0.9)), ('th_r=1.1', dict(th_r=1.1)),
                 ('L_r=1.5 d_r=0.2', dict(L_r=1.5, d_r=0.2)), ('L_r=2.0 d_r=0.3', dict(L_r=2.0, d_r=0.3)),
                 ('base on meter vol', dict(base_vol='meter'))]:
    kk = dict(b); kk.update(kw)
    run_variant('base(p0=.02,th=1.25,hm=40) + ' + name, kk)
