import lzma, io, numpy as np
d = np.load(io.BytesIO(lzma.open('/mnt/project-files/research/data/panel_f32.npz.xz').read()), allow_pickle=True)
ks = d.files; print(len(ks))
want = [k for k in ks if k.split('|')[0] in ('QQQ', 'QLD', 'TQQQ', '_NDX', 'SSO', 'UPRO', 'SPY', '_IRX', 'BIL', '_cols', 'cols')]
print(want)
print([k for k in ks if 'col' in k.lower()][:10])
