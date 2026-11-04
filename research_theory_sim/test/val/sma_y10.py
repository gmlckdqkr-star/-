"""validation only: 200-day trend 3x/cash, halved when y10 rose >1pp over 126 days (exercises the y10 input)."""
import numpy as np
INPUTS = ('close', 'rf', 'y10'); PARAMS = {'n': 200}
def target_levels(close, rf, y10=None, params=PARAMS):
    n = params['n']; P, T = close.shape; c = np.cumsum(np.c_[np.zeros(P), close], axis=1)
    m = np.full((P, T), np.nan); m[:, n - 1:] = (c[:, n:] - c[:, :-n]) / n
    B = np.where(close > m, 3.0, 0.0)
    dy = np.full((P, T), 0.0); dy[:, 126:] = y10[:, 126:] - y10[:, :-126]
    return np.where(dy > 1.0, B / 2, B)
