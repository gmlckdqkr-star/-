"""Dummy candidates for the synthetic-world test of the gates (no market idea in them)."""
import numpy as np
import xv1


def sleeve(v, name='good', w=0.1, band=0.25):
    """v1 next to a constant-weight sleeve in the registered synthetic instrument `name`; the sleeve has priority and is
    re-set to its weight whenever it leaves the band (profit skim into v1, refill from v1)"""
    o = xv1.ref(v)
    o.update(G=v.x[name][:, None], Wt=np.full((v.T, 1), w), mode=1, inc=0, up=np.array([band]), dn=np.array([band])); return o
