"""DF7 POST-HOC (not pre-registered, report only): how many of the 198 DF7-B rules pass G1-G5 if the trend premium is larger than PRIM's 50%.
Conventions: neutral panel + trend fraction f in {0.6..1.0} (gold & bonds zero excess, as in f*), and RAW (raw panel + trend 100% = 1986-2014 as it happened).
python df7post.py scan -> results/df7_post.json. Run from /tmp/df7w. <=2014 only."""
import sys, json, time
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df7 as D
def scan():
    t0 = time.time(); C = D.configs(); out = {'meta': dict(note='post-hoc, report only; selection not changed'), 'conv': {}}
    M = json.load(open(D.RES + 'df7_main.json'))
    out['conv']['0.5'] = dict(npass={i: g['npass'] for i, g in M['gates'].items()}, ddm={i: g['ddm'] for i, g in M['gates'].items()},
                              score={i: g['score'] for i, g in M['gates'].items()})
    for cv in (0.6, 0.7, 0.8, 0.9, 1.0, 'RAW'):
        rows, Q = D.run_set(C, cv); G = D.gates(rows, Q)
        out['conv'][str(cv)] = dict(npass={i: g['npass'] for i, g in G.items()}, ddm={i: g['ddm'] for i, g in G.items()},
                                    score={i: g['score'] for i, g in G.items()}, rows=rows, qqq=Q)
        json.dump(out, open(D.RES + 'df7_post.json', 'w'), indent=1)
        D.log('post', cv, 'pass', sum(g['npass'] == 5 for g in G.values()))
    D.log('post done %.0fs' % (time.time() - t0))
if __name__ == '__main__' and (len(sys.argv) == 1 or sys.argv[1] == 'scan'):
    scan()

PICKS = ['F2|q0.2|r0.4|g0.1|m0.3', 'F2|q0.2|r0.5|g0.1|m0.2']   # most defensive passers at trend 100%/RAW and at 80% (post-hoc picks)
def picks():
    t0 = time.time(); C = {c['id']: c for c in D.configs()}; cf = [C[i] for i in PICKS]
    P = json.load(open(D.RES + 'df7_post.json')); P['picks'] = dict(ids=PICKS, fstar=D.fstar(cf), report={})
    json.dump(P, open(D.RES + 'df7_post.json', 'w'), indent=1)
    for cv in ('PRIM', 'RAW', 'ZERO'):
        rr, qq = D.run_set(cf, cv, keys=D.RKEYS); P['picks']['report'][cv] = dict(rows=rr, qqq=qq)
        json.dump(P, open(D.RES + 'df7_post.json', 'w'), indent=1)
    D.log('picks done %.0fs' % (time.time() - t0))
if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'picks':
    picks()
