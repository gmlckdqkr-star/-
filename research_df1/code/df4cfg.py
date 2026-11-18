"""DF4 helpers: config lookup for all 1,367 DF1-3 ids and one runner (vmode from cfg['M'] for DF3 configs)."""
import json, sys
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2
RES = '/mnt/project-files/research/df1/results/'
OLD = dict(json.load(open(RES + 'grid.json'))['configs']); OLD.update(json.load(open(RES + 'grid_df2.json'))['configs'])
def cfg_of(i):
    if i in OLD: return OLD[i]['cfg']
    _, fam, Mm, k, s, L, kn, ro = i.split('|')
    return dict(id=i, fam='df3', M=Mm, k=k, sig=None if s == 'snone' else float(s[1:]), Lmax=float(L[1:]), knee=kn, roff=ro)
def run_any(cfg, m, **extra):
    if cfg.get('fam') == 'df3':
        L = DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax']); kw = dict(RG.KNEES[cfg['knee']]); kw.update(vmode=0 if cfg['M'] == 'M0' else 2); kw.update(extra)
        return dfe.run(m, L, roff=RG.ROFF[cfg['roff']], **kw)[0]
    if cfg.get('fam') == 'df2': return R2.run_cfg(cfg, m, **extra)
    return RG.run_cfg(cfg, m, **extra)
