"""NDX era: index returns are zero-filled from 1984-10-23 until NDX data start (1985-10-02) inside the 300-day warm-up; those zeros
enter the expanding vol / efficiency-ratio percentiles. Re-evaluate VOL80 and CHOP with the pre-data days excluded."""
import io, contextlib, numpy as np
with contextlib.redirect_stdout(io.StringIO()):
    import s3_flags as F
bn = 'real_ndx_86_14'
z = np.load(F.D + 'data_%s.npz' % bn); WARM = int(z['WARM']); T = len(z['TQ'])
r = z['rfull'].copy(); first = int(np.nonzero(np.abs(r) > 0)[0][0]); r2 = r.copy(); r2[:first] = np.nan
ks = np.arange(252, T - 3, 21)
f0 = F.my_flags(r, z['y10'], z['cape_ok'], WARM, T); f1 = F.my_flags(r2, z['y10'], z['cape_ok'], WARM, T)
R = np.stack([F.sleeve_formula(z['TQ'], z['DEP'], z['CU'])] + [z['S_' + X] for X in F.PARTNERS], 1)
a = F.rules_eval(R, f0, ks); b = F.rules_eval(R, f1, ks)
for fl in ('vol_hi', 'chop'):
    d = f0[fl][ks] != f1[fl][ks]
    print('%s: flags differ at %d of %d block starts (first differing block %s, last %s)' % (fl, d.sum(), len(ks), ks[d][:1], ks[d][-1:]))
for key in a:
    if key.endswith(('VOL80', 'CHOP')):
        print('%-20s stored-style: hit %.4f gain %+.5f t %+.2f | zeros excluded: hit %.4f gain %+.5f t %+.2f' % (
            key, a[key]['hit'], a[key]['gain'], a[key]['t'], b[key]['hit'], b[key]['gain'], b[key]['t']))
