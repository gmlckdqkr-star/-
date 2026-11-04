"""All 29 rules with the engine-faithful DRIFTING s0.85 sleeve (TQ/cash split reset only when the level changes), vs stored (formula)."""
import sys, io, contextlib, numpy as np
with contextlib.redirect_stdout(io.StringIO()):
    import s3_flags as F          # runs its own checks silently
import s2_info as V
out = {}
for bn in ['real_ndx_86_14', 'real_spx_55_85']:
    z = np.load(F.D + 'data_%s.npz' % bn); WARM = int(z['WARM']); T = len(z['TQ'])
    fm = F.my_flags(z['rfull'], z['y10'], z['cape_ok'], WARM, T); ks = np.arange(252, T - 3, 21)
    for lab, sl in (('formula', F.sleeve_formula(z['TQ'], z['DEP'], z['CU'])), ('drift', V.s085_sleeve(z['TQ'], z['DEP'], z['CU'])),
                    ('drift+cost', V.s085_sleeve(z['TQ'], z['DEP'], z['CU'], 0.003))):
        R = np.stack([sl] + [z['S_' + X] for X in F.PARTNERS], 1)
        for key, v in F.rules_eval(R, fm, ks).items(): out[(bn, key, lab)] = v
keys = sorted({k[1] for k in out})
for lab in ('formula', 'drift', 'drift+cost'):
    nd = [out[('real_ndx_86_14', k, lab)]['gain'] for k in keys]
    low = {k: min(out[('real_ndx_86_14', k, lab)]['hit_defl'], out[('real_spx_55_85', k, lab)]['hit_defl']) for k in keys}
    best = max(low, key=low.get)
    tmin = {k: min(out[('real_ndx_86_14', k, lab)]['t'], out[('real_spx_55_85', k, lab)]['t']) for k in keys}
    both_pos = [k for k in keys if out[('real_ndx_86_14', k, lab)]['gain'] > 0 and out[('real_spx_55_85', k, lab)]['gain'] > 0]
    print('%-10s NDX gains: max %+.5f (all negative: %s) | best lower-era deflated hit %.4f (%s) | rules with gain > 0 in both eras: %s | max lower-era t %.2f'
          % (lab, max(nd), all(g < 0 for g in nd), low[best], best, both_pos, max(tmin.values())))
