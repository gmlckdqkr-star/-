import numpy as np, harness as H
seeds=(1,2)
for mech in (True,False):
    print('mech',mech,'holds',H.holds(seeds,1000,mech))
for L in (0.5,1.0,1.5,2.0,2.5,3.0):
    o=H.evaluate(lambda d,L=L: np.full(d['r'].shape,L), seeds=seeds, name='const', prm={'L':L})
    print('const %.1f  ON %.4f (p10 %.4f dd80 %.3f)  OFF %.4f'%(L,o['on']['cagr_med'],o['on']['cagr_p10'],o['on']['p_dd80'],o['off']['cagr_med']))
