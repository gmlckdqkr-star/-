"""Build the lab plugin with the FROZEN 1986 tables (PRECOMMIT_ML.md sec 3-4) and 3 specs (V1, V2, B0).
Tables come only from rows whose label ended before 1986-01-01. Output: research/mega_lattice/lab_specs/."""
import sys, json, numpy as np, os
sys.path.insert(0, '/mnt/project-files/research/mega_lattice/code')
import ml, feat
OUTD = '/mnt/project-files/research/mega_lattice/lab_specs/'
os.makedirs(OUTD + 'plugins', exist_ok=True)

rows, edges, subs, off, ncell = ml.build()
lat = ml.Lattice(rows, edges, subs, off, ncell)
dA, dB = lat.deltas(1986); d = ((dA + dB) / 2).astype(np.float32)
cal = lat.calib(1986)
np.save('/mnt/project-files/research/mega_lattice/results/frozen1986_delta.npy', d)
json.dump(dict(cal=cal, edges={k: (None if v is None else list(map(float, v))) for k, v in edges.items()}),
          open('/mnt/project-files/research/mega_lattice/results/frozen1986_meta.json', 'w'), indent=1)

src = open('/mnt/project-files/research/mega_lattice/code/feat.py').read()
body = '''

# ---- frozen tables (rows with label end < 1986-01-01 only) ----
EDGES = %s
SUBS = np.array(%s, dtype=np.int64)
OFF = np.array(%s, dtype=np.int64)
DELTA = np.frombuffer(bytes.fromhex(%r), dtype=np.float32).astype(np.float64)
CAL = %s


def _score(B):
    ok = B.min(1) >= 0
    c = OFF[None, :] + B[:, SUBS[:, 0]].astype(np.int64)
    m2 = SUBS[:, 1] >= 0; m3 = SUBS[:, 2] >= 0
    c[:, m2] += 5 * B[:, SUBS[m2, 1]].astype(np.int64)
    c[:, m3] += 25 * B[:, SUBS[m3, 2]].astype(np.int64)
    c[~ok] = 0
    s = DELTA[c].mean(1)
    s[~ok] = np.nan
    return s


def _ladder(L):
    q = np.zeros(len(L)); l2 = np.zeros(len(L)); l3 = np.zeros(len(L))
    a = L <= 1; q[a] = L[a]
    b = (L > 1) & (L <= 2); l2[b] = L[b] - 1; q[b] = 2 - L[b]
    c = L > 2; l3[c] = L[c] - 2; l2[c] = 3 - L[c]
    return q, l2, l3


def weights(F, sleeves, params):
    var = params.get('var', 'V1')
    px = F['QQQ'].astype(float)
    mo = F['month()'].values
    D = feats(px, mo)
    B = binize(D, EDGES)
    s = np.empty(len(B)); s[:] = np.nan
    step = 2000
    for i in range(0, len(B), step):
        s[i:i + step] = _score(B[i:i + step])
    mu = CAL['a'] + CAL['b'] * s
    P = 1 / (1 + np.exp(-(CAL['c0'] + CAL['c1'] * s)))
    r = np.log(px).diff().fillna(0.0)
    v21 = (r ** 2).ewm(halflife=21, adjust=False).mean().values * 21
    n = len(px); L = np.ones(n); cur = 1.0
    for t in range(n):
        if t %% 5 == 0 and not np.isnan(s[t]) and v21[t] > 0:
            if var == 'V1':
                tgt = min(max(0.5 * mu[t] / v21[t], 0.0), 3.0); tgt = round(tgt * 2) / 2
                if abs(tgt - cur) >= 0.75:
                    cur = tgt
            elif var == 'B0':
                tgt = min(max(0.5 * CAL['ybar'] / v21[t], 0.0), 3.0); tgt = round(tgt * 2) / 2
                if abs(tgt - cur) >= 0.75:
                    cur = tgt
            else:
                cur = 3.0 if P[t] >= CAL['pbar'] + 0.05 else (0.0 if P[t] <= CAL['pbar'] - 0.05 else 1.5)
        elif np.isnan(s[t]):
            cur = 1.0
        L[t] = cur
    q, l2, l3 = _ladder(L)
    out = pd.DataFrame({'QQQ': q, 'QLD': l2, 'TQQQ': l3}, index=F.index)
    return out[[c for c in sleeves]]
''' % (json.dumps({k: (None if v is None else list(map(float, v))) for k, v in edges.items()}).replace('null', 'None'),
       json.dumps(subs.tolist()), json.dumps(off.tolist()), d.tobytes().hex(),
       json.dumps({k: float(v) for k, v in cal.items()}))
open(OUTD + 'plugins/mega_lattice.py', 'w').write(src + body)
for var, idea in [('V1', '초거대 격자(1985년 이전 표 고정) 기대수익 -> 반켈리 0~3배 사다리, 주1회, 0.75 이상 차이일 때만'),
                  ('V2', '초거대 격자 확률 -> 3단 분할(0 / 1.5 / 3배), 주1회'),
                  ('B0', '대조: 같은 사다리, 기대수익 상수(변동성 맞춤만)')]:
    open(OUTD + 'ml_%s.yaml' % var, 'w').write(
        'name: mega_lattice_%s\nfamily: mega_lattice\nknown: 1\nidea: %s\nplugin: plugins/mega_lattice.py:weights\n'
        'sleeves: [QQQ, QLD, TQQQ]\ninputs: [QQQ, \'month()\']\nparams: {var: %s}\n' % (var, idea, var))
print('ok', cal)
