import numpy as np
INPUTS = ('close', 'rf'); PARAMS = {}
def target_levels(close, rf, y10=None, params=PARAMS): return np.full(close.shape, 3.0)
