"""ETX1 candidate configs (PRECOMMIT_ETX1.md, sha d8ca5d31). build(b, L, cfg) -> (prods, sleeves, ws, reb)."""
import etxeng as G

ALL31 = ['SHY', 'IEF', 'TLT', 'EDV', 'UST', 'TYD', 'UBT', 'TMF', 'GLD', 'GDX', 'DBMF', 'KMLM', 'NTSX', 'GDE', 'RSST', 'RSBT', 'RSSB',
         'XLU', 'XLP', 'XLV', 'IWN', 'IWD', 'MTUM', 'QUAL', 'IYR', 'VTI', 'SSO', 'UPRO', 'HFEA', 'DEF3', 'TRIO']
FILL22 = ['SHY', 'IEF', 'TLT', 'EDV', 'UST', 'TYD', 'UBT', 'TMF', 'GLD', 'GDX', 'DBMF', 'KMLM', 'NTSX', 'GDE', 'RSST', 'RSBT', 'RSSB',
          'XLU', 'XLP', 'XLV', 'DEF3', 'TRIO']
BUNDLE = {'HFEA': ({'UPRO': 0.55, 'TMF': 0.45}, 63), 'DEF3': ({'TLT': 1 / 3, 'GLD': 1 / 3, 'DBMF': 1 / 3}, 252),
          'TRIO': ({'TMF': 1 / 3, 'GDE': 1 / 3, 'RSST': 1 / 3}, 252)}
GROUP = {**{k: 'bond' for k in ['SHY', 'IEF', 'TLT', 'EDV']}, **{k: 'levbond' for k in ['UST', 'TYD', 'UBT', 'TMF']},
         'GLD': 'gold', 'GDX': 'gold', 'DBMF': 'trend', 'KMLM': 'trend', **{k: 'stacked' for k in ['NTSX', 'GDE', 'RSST', 'RSBT', 'RSSB']},
         **{k: 'equity' for k in ['XLU', 'XLP', 'XLV', 'IWN', 'IWD', 'MTUM', 'QUAL', 'IYR', 'VTI']}, 'SSO': 'levequity', 'UPRO': 'levequity',
         'HFEA': 'bundle', 'DEF3': 'bundle', 'TRIO': 'bundle'}


def mix_of(name):
    if name in BUNDLE: return BUNDLE[name]
    return {name: 1.0}, 0


def configs():
    out = []
    for n in ALL31:
        for w in (0.15, 0.30): out.append(('S1_%s_w%02d' % (n, int(w * 100)), ('S1', n, w)))
    for n in FILL22: out.append(('S2_%s' % n, ('S2', n)))
    for n in FILL22: out.append(('S3_%s' % n, ('S3', n)))
    return out


def build(b, L, cfg):
    kind = cfg[0]
    if kind == 'S1':
        mix, rd = mix_of(cfg[1]); w = cfg[2]
        prods = ['TQQQ', 'CASH'] + sorted(mix)
        return prods, G.bind(b, [G.sl_s085(L), G.sl_static(mix, rd)]), [1 - w, w]
    if kind in ('S2', 'S3'):
        mix, _ = mix_of(cfg[1])
        prods = ['TQQQ', 'CASH'] + sorted(mix)
        return prods, [G.sl_s085(L, mix, mode='all' if kind == 'S2' else 'deep')], [1.0]
    raise KeyError(cfg)


def products_of(cfg):
    mix, _ = mix_of(cfg[1]); return sorted(mix)
