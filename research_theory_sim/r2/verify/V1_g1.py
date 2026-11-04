"""V1 check 4: G1 (research/breakthrough/code/gate.py, gate.test(sig, trials=7)) with each era fed its own market's
target: NDX frame 1984-01-03..2014-12-31 -> era ndx_86_14 only; SPX frame 1928-01-03..1985-12-31 -> era spx_55_85 only.
sig = (target >= 1.5) and (target > 0). Also the always-in base rate and trials=1 for reference. <=2014 only."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/verify'); import V1_common as V  # noqa
jp, ov = V.jp, V.ov
sys.path.insert(0, '/mnt/project-files/research/breakthrough/code'); import gate  # noqa


def verdict(low): return '60%-CANDIDATE' if low >= .77 else 'BUILD' if low >= .70 else 'HOLD' if low >= .65 else 'CLOSE'


def main(names):
    fr = {}
    for nm, a, b, s in (('ndx', '1984-01-03', '2014-12-31', 'NDX'), ('spx', '1928-01-03', '1985-12-31', 'SPX')):
        X = jp.mkX(*jp.calendar(a, b), s); assert X.index[-1] <= V.END
        fr[nm] = (X, ov.Ctx(X, ov.flags_hist(X), np.arange(len(X))[None, :]))
    out = {}
    lab = gate.labels()
    out['always_up'] = {e: float(l.mean()) for e, l in lab.items()}
    for L in names:
        rule = V.load_rule(L); S = {}
        for nm, (X, c) in fr.items():
            S[nm] = pd.Series(V.targets(rule, c.lvl, c.rf)[0], index=X.index).fillna(0.0)
        o = {}
        for sn, f in (('ge1.5', lambda s: s >= 1.5), ('gt0', lambda s: s > 0)):
            gn = gate.test(f(S['ndx']), trials=7, verbose=False); gs = gate.test(f(S['spx']), trials=7, verbose=False)
            e = dict(ndx_86_14={k: float(v) for k, v in gn['ndx_86_14'].items()}, spx_55_85={k: float(v) for k, v in gs['spx_55_85'].items()})
            low = min(e['ndx_86_14']['hit_deflated'], e['spx_55_85']['hit_deflated'])
            e['low_deflated'] = low; e['verdict'] = verdict(low)
            g1n = gate.test(f(S['ndx']), trials=1, verbose=False); g1s = gate.test(f(S['spx']), trials=1, verbose=False)
            e['low_deflated_trials1'] = min(g1n['ndx_86_14']['hit_deflated'], g1s['spx_55_85']['hit_deflated'])
            e['share_true_ndx_blocks'] = float(f(S['ndx']).reindex(lab['ndx_86_14'].index, method='ffill').mean())
            e['share_true_spx_blocks'] = float(f(S['spx']).reindex(lab['spx_55_85'].index, method='ffill').mean())
            o[sn] = e
            print('%-3s %-6s ndx hit %.4f (n %d, defl %.4f) spx hit %.4f (n %d, defl %.4f) low %.4f %s | true-share ndx %.3f spx %.3f' % (
                L, sn, e['ndx_86_14']['hit'], e['ndx_86_14']['n'], e['ndx_86_14']['hit_deflated'], e['spx_55_85']['hit'],
                e['spx_55_85']['n'], e['spx_55_85']['hit_deflated'], low, e['verdict'], e['share_true_ndx_blocks'], e['share_true_spx_blocks']), flush=True)
        try:
            R = json.load(open(V.R2 + 'test/out/real_%s.json' % L))['g1']
            o['compare'] = {sn: dict(mine=(o[sn]['ndx_86_14']['hit'], o[sn]['spx_55_85']['hit'], o[sn]['low_deflated'], o[sn]['verdict']),
                                     reported=(R[sn]['ndx_86_14']['hit'], R[sn]['spx_55_85']['hit'], R[sn]['low_deflated'], R[sn]['verdict']))
                            for sn in ('ge1.5', 'gt0')}
            print(L, 'compare', o['compare'], flush=True)
        except FileNotFoundError:
            pass
        out[L] = o
    print('always-up base rates', out['always_up'])
    return out


if __name__ == '__main__':
    names = sys.argv[1:] or ['D', 'A', 'B', 'C', 'L1']
    p = V.dump(main(names), 'V1_g1.json'); print('wrote', p)
