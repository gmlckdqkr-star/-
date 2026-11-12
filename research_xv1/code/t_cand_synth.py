"""Dummy candidates for the synthetic-world test of the gates (no market idea in them). One function per family: the
evaluator treats one source function as one family."""
import numpy as np
import xv1


def sleeve(v, name='drift', w=0.1, band=0.25):
    """v1 next to a constant-weight sleeve in the registered synthetic instrument `name`; the sleeve has priority and is
    re-set to its weight whenever it leaves the band (profit skim into v1, refill from v1)"""
    o = xv1.ref(v)
    o.update(G=v.x[name][:, None], Wt=np.full((v.T, 1), w), mode=1, inc=0, up=np.array([band]), dn=np.array([band])); return o


def timed(v, name, w=0.1):
    """v1 next to a sleeve in the registered synthetic instrument `name`, held only while the registered synthetic signal
    'sig_' + name is on (the sleeve has priority; no rebalancing while it is held)"""
    o = xv1.ref(v); on = np.nan_to_num(v.x['sig_' + name]) > 0
    o.update(G=v.x[name][:, None], Wt=np.where(on, w, 0.0)[:, None], mode=1, inc=0); return o


def good(v, w=0.1): return timed(v, 'good', w)
def rev(v, w=0.1): return timed(v, 'rev', w)
def flat(v, w=0.1): return timed(v, 'flat', w)
def bad(v, w=0.1): return timed(v, 'bad', w)
def good2(v, w=0.1): return timed(v, 'good2', w)
def good3(v, w=0.1): return timed(v, 'good3', w)


def static0(v, name='drift', w=1.0):
    """no v1 level, a constant weight in `name`, a re-set every 252 rows: its holdings depend on no input (may not be opened)"""
    o = xv1.ref(v); RB = np.zeros((v.T, 1)); RB[::252] = 1.0
    o.update(B=np.zeros(v.T), G=v.x[name][:, None], Wt=np.full((v.T, 1), w), mode=1, inc=0, RB=RB); return o
