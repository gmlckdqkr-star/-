import numpy as np
exec(open('r_oracle2.py').read().split('D = solve_diag')[0])
D = solve_diag(200, T, 11)
X = np.log1p(D['r']); EX = D['EX']; SD = D['SD']
print('mean X*252', np.mean(X[:, 300:]) * 252, 'mean EX*252', np.mean(EX[:, 300:]) * 252)
mu_ar = (EX + SD ** 2 / 2 - D['rf']) * 252
print('mean mu_ar', mu_ar[:, 300:].mean(), 'pct', np.percentile(mu_ar[:, 300:], [1, 5, 50, 95, 99, 99.9]))
print('mean SD*sqrt252', np.mean(SD[:, 300:]) * np.sqrt(252), 'realized', np.std(X[:, 300:]) * np.sqrt(252))
# lag-k autocorrelation of mu_ar (persistence)
m = mu_ar[:, 300:] - mu_ar[:, 300:].mean(1, keepdims=True)
for k in (1, 5, 21, 63):
    print('ac', k, (m[:, k:] * m[:, :-k]).sum() / (m ** 2).sum())
p = D['params']
i = np.argsort(p['B'])[-5:]
print('B', p['B'][i], 'A', p['A'][i], 'h_s', p['h_s'][i])
print('per-path median mu_ar for high B', np.median(mu_ar[i, 300:], axis=1), 'mean', mu_ar[i, 300:].mean(1), 'mu', p['mu'][i])
