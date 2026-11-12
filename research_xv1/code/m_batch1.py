"""XV1 batch 1: registers the configurations (once) and scores them on the design blocks (G1). Run only after the structure is
registered and m_checks.py and m_v1.py have passed.

  python m_batch1.py register     write BATCH_1.json and its ledger line; scores nothing
  python m_batch1.py run          score the registered batch on D7, apply G1, write results/batch_1.json, print the table
  python m_batch1.py show         print the table of the scored batch again

Batch 1 = the owner's barbell (16 configurations: semiconductor 3x sleeve of 5 / 10 / 20 / 30% always held with three
rebalancing rules, and 10 / 20% held only in an up-trend with two rules) and the four packages written from the eight
designers' rule texts (agree 12, bridge 18, states 20, cross 30). 96 configurations, family-wise level 0.05 / 2 = 0.025."""
import os
import sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xv1

CAND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cand', '')


def configs():
    out = []; nm = ('ret:SOXL', 'semis')
    for rule in ('skim', 'band', 'yearly'):
        for w in (0.05, 0.10, 0.20, 0.30):
            out.append(xv1.Config('barbell always-held', 'BB_A_%s_%02d' % (rule, round(100 * w)), CAND + 'barbell.py', 'always',
                                  dict(w=w, rule=rule, band=0.25), names=nm, calendar=(rule == 'yearly')))   # v7: a 252-row rebalance is a calendar slot in all but name
    for rule in ('skim', 'band'):
        for w in (0.10, 0.20):
            out.append(xv1.Config('barbell trend-held', 'BB_T_%s_%02d' % (rule, round(100 * w)), CAND + 'barbell.py', 'trend',
                                  dict(w=w, rule=rule, band=0.25), names=nm))
    for pkg in ('agree', 'bridge', 'states', 'cross'):
        out += [xv1.Config(**e) for e in json.load(open(CAND + pkg + '.configs.json'))]
    return out


def sub2(o):
    """v7: active 63-row sub-blocks in two design blocks (twice the median over the six full design blocks). The sealed set
    has two blocks; below 6 active sub-blocks there no verdict above INCONCLUSIVE is possible."""
    a = sorted(o['active_sub63'][:6]); return a[2] + a[3]


def table(out):
    pc = lambda x: '%+7.2f' % (100 * x)
    R = sorted(out['results'].values(), key=lambda o: (o.get('void') is not None, o.get('p_family', 9), -o.get('d', -9)))
    print('batch %d: %d configurations, family-wise level %.4f' % (out['batch'], out['n'], out['alpha']))
    print('%-30s %-16s %7s %7s %6s %8s %8s %4s %5s %4s %6s %6s  %-4s %-8s %-4s %s' % (
        'family', 'name', 'd', 'd*', 'te', 'p_fam', 'p*_fam', 'blk', 'span', 'sub2', 'skew', 'ac1', 'abcd', 'type', 'g0', 'advance'))
    for o in R:
        if 'void' in o: print('%-30s %-16s VOID: %s' % (o['family'][:30], o['name'][:16], o['void'])); continue
        print('%-30s %-16s %s %s %6.1f %8.5f %8.5f %4d %5d %4d %+6.2f %+6.2f  %-4s %-8s %-4s %s' % (
            o['family'][:30], o['name'][:16], pc(o['d']), pc(o['d_star']), 100 * o['te'], o['p_family'], o['p_star_family'], o['active_blocks'], o['n_span'],
            sub2(o), o['skew63'], o['ac1_63'], ''.join('Y' if x else 'n' for x in o['g1'].values()), o['kind'], 'req' if o['g0'] == 'required' else 'n/a',
            ('ADVANCE' if o['advance'] else '') + (' shape!' if (o['skew63'] < xv1.SHAPE_SKEW_MIN or o['ac1_63'] > xv1.SHAPE_AC1_MAX) else '')))
    ok = [o for o in R if o.get('g1_pass')]
    print('sub2 = active 63-row sub-blocks in two typical design blocks; with fewer than 6 in the sealed blocks an opening can only return FAIL or INCONCLUSIVE')
    print('shape! = d sub-block means with skewness below %.1f or lag-1 autocorrelation above %.1f: a G1 pass or a CONSISTENT verdict of such a '
          'configuration is reported with "error rate not controlled (skewed or autocorrelated differences)"' % (xv1.SHAPE_SKEW_MIN, xv1.SHAPE_AC1_MAX))
    print('G1 passed: %d of %d; void: %d; advancing: %s' % (len(ok), out['n'], sum('void' in o for o in R), [o['name'] for o in R if o.get('advance')]))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'register':
        c = configs(); k, sha = xv1.register_batch(c); print('configurations', len(c), '| batch', k, '| sha256', sha)
    elif cmd == 'run':
        table(xv1.run_batch(1))
    elif cmd == 'show':
        table(json.load(open(xv1.OUT + 'results/batch_1.json')))
