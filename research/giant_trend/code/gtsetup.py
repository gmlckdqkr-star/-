"""Shared GT setup: data, product returns, strategy table."""
import sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/giant_trend/code')
import gtdata, gteng as E, gtstrat as S

D = gtdata.load(); c = S.Ctx(D); E.set_calendar(c.idx)
cal = json.load(open('/mnt/project-files/research/giant_trend/results/calib.json'))
E.EXTRA[2] = max(0, max(v['gap'] for v in cal['2'].values())); E.EXTRA[3] = max(0, max(v['gap'] for v in cal['3'].values()))
# amendment A1 (before any run): internal turnover cost of monthly-resorted KF portfolios, annual
INTERNAL = {'BIG_LoREV': 0.06, 'BIG_HiPRIOR': 0.025, 'BIG_HiOP': 0.0015, 'BIG_LoBETA': 0.003, 'BIG_HiBM': 0.0015, 'BIG_LoBM': 0.0015}
R = {n: D['ind'][n].values for n in c.names}
for f in D['fac'].columns: R[f] = D['fac'][f].values - INTERNAL.get(f, 0) / 12
R['MKT'] = D['mkt'].values; R['BOND10'] = D['bond'].values
P = E.product_returns(R, c.rf, D['dy'].values, D['sh']['GS10'].values)

STRATS = {
 'BUF_B': (lambda: S.hold_mix(c, {'BIG_HiOP': .5, 'BIG_LoBETA': .5}, start='1963-07'), 'op'),
 'BUF_T1': (lambda: S.buf_t(c), 'long'),
 'BUF_T2': (lambda: S.buf_t(c, score='rs60/vol'), 'long'),
 'MUN_T': (lambda: S.buf_t(c, review='every', every=60), 'long'),
 'GRA_B': (lambda: S.hold_mix(c, {'BIG_HiBM': 1.0}), 'long'),
 'GRA_T': (lambda: S.gra_t(c), 'long'),
 'GRA_C': (lambda: S.gra_c(c), 'long'),
 'FIS_T': (lambda: S.hold_mix(c, {'BIG_HiOP': .5, 'BIG_HiPRIOR': .5}, start='1963-07'), 'op'),
 'ONE_T': (lambda: S.one_t(c), 'long'),
 'DRU_T': (lambda: S.dru_t(c), 'long'),
 'SOR_T': (lambda: S.sor_t(c), 'long'),
 'DAL_QX': (lambda: S.dal_q(c), 'long'),
 'DAL_QF': (lambda: S.dal_q(c, frozen_end='1969-12'), 'long'),
 'DAL_RP': (lambda: S.dal_rp(c), 'long'),
 'TEM_B': (lambda: S.tem(c), 'long'),
 'TEM_T': (lambda: S.tem(c, need_secular=True), 'long'),
 'MAR_T': (lambda: S.mar_t(c), 'long'),
 'THO_B': (lambda: S.hold_mix(c, {'BIG_LoREV': 1.0}), 'long'),
 'TUD_B': (lambda: S.tud_b(c), 'long'),
 'MKT_H': (lambda: S.hold_mix(c, {'MKT': 1.0}), 'base'),
}
