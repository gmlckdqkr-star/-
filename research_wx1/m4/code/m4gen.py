"""WX1-M4 rule generator (locked before any search result; fixed seed). Writes results/rules.jsonl (one canonical rule per
line, duplicates removed by canonical hash) and prints the counts before / after dedup."""
import json, hashlib, random, sys
SEED = 20261104
S = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m4/'
GATES = ['ndx200', 'spx200', 'macro', 'ndxvol25', 'ndx12m', 'macro_ndx200']
RET_SC = [('ret', L, 0) for L in (21, 42, 63, 126, 189, 252)] + [('ret', L, 21) for L in (63, 126, 189, 252)] + \
         [('radj', L) for L in (63, 126, 252)] + [('comp',)]
ALLOC = dict(XSM=4500, MR=800, TSM=1500, VT=900, RP=1100, CORR=900, DISP=600, ACORR=700, CS=1000, PAIR=3000)


def gate_part(R, allow=True):
    if not allow or R.random() < 0.4:
        return dict(gate='none')
    return dict(gate=R.choice(GATES), gfreq=R.choice(['D', 'R']), goff=R.choice(['CASH', 'LTB1', 'DELEV']))


def draw(R, fam):
    c = R.choice
    if fam == 'XSM':
        r = dict(fam=fam, U=c(['SECT', 'SECT3', 'EQ', 'MULTI', 'CORE', 'FACT', 'GROW']), score=list(c(RET_SC)),
                 K=c([1, 2, 3, 5]), wt=c(['eq', 'iv']), lev=c([1, 2, 3]), filt=c(['none', 'dm', 'sma200', 'mkt200']),
                 fb=c(['CASH', 'LTB1', 'MTB1', 'GOLD1', 'DEF']), reb=c(['W', 'M', 'Q', 'M3T']))
    elif fam == 'MR':
        r = dict(fam=fam, U=c(['SECT', 'SECT3', 'EQ']), score=['rev', c([5, 10, 21])], K=c([1, 2, 3, 5]), wt=c(['eq', 'iv']),
                 lev=c([1, 2, 3]), filt=c(['none', 'sma200', 'mkt200']), fb=c(['CASH', 'LTB1']), reb=c(['W', 'M']))
    elif fam == 'TSM':
        r = dict(fam=fam, U=c(['CORE', 'SECT', 'EQ', 'MULTI', 'NLG', 'GROW', 'CLS', 'FACT']),
                 sig=c(['tsm3', 'tsm6', 'tsm12', 'sma50', 'sma100', 'sma200', 'x50200']), wt=c(['eq', 'iv']),
                 lev=c([1, 2, 3]), fb=c(['CASH', 'LTB1', 'MTB1']), reb=c(['W', 'M']))
    elif fam == 'VT':
        A = c(['NDX', 'SPX', 'SMALL', 'TECH', 'SEMI', 'HLTH', 'DISC'])
        r = dict(fam=fam, A=A, tv=c([0.15, 0.20, 0.25, 0.30, 0.40]), vn=c([21, 63]), lmax=c([2, 3]), ladder=c([True, False]),
                 filt=c(['none', 'sma200', 'tsm12']), fb='LTB1' if A == 'NDX' else c(['CASH', 'LTB1']), reb=c(['W', 'M']))
    elif fam == 'RP':
        r = dict(fam=fam, U=c(['NLG', 'NL', 'SL', 'NSL', 'CORE', 'CLS']), vn=c([21, 63, 126]), lev=c([1, 2, 3]),
                 tv=c([0, 0.10, 0.15, 0.20]), filt=c(['none', 'sma200', 'tsm12']), fb=c(['CASH', 'MTB1']), reb=c(['W', 'M', 'Q']))
    elif fam == 'CORR':
        r = dict(fam=fam, pair=c(['NDX-LTB', 'SPX-LTB', 'NDX-GOLD', 'SMALL-LTB', 'NDX-MTB']), n=c([63, 126]),
                 c=c([-0.2, 0.0, 0.2]), w=c([0.5, 0.6, 0.7]), lev=c([2, 3]), **{'else': c(['FULL', 'WCASH', 'CASH'])},
                 reb=c(['W', 'M']))
    elif fam == 'DISP':
        r = dict(fam=fam, U=c(['SECT', 'EQ']), score=['ret', c([21, 63, 126, 252]), 0], K=c([1, 2, 3]), lev=c([1, 2, 3]),
                 map=c(['hi_rot', 'lo_rot']), reb=c(['W', 'M']))
    elif fam == 'ACORR':
        r = dict(fam=fam, U=c(['SECT', 'EQ', 'MULTI']), score=['ret', c([21, 63, 126, 252]), 0], K=c([1, 2, 3, 5]),
                 lev=c([1, 2, 3]), **{'def': c(['CASH', 'LTB1', 'DEF'])}, reb=c(['W', 'M']))
    elif fam == 'CS':
        r = dict(fam=fam, cl=c([2, 3]), cshare=c([0.5, 0.7, 0.85]), cgate=c(['ndx200', 'macro_ndx200', 'ndx100']),
                 cfb=c(['CASH', 'LTB1']), U=c(['SECT', 'SECT3', 'MULTI', 'EQ']),
                 score=list(c([('ret', 63, 0), ('ret', 126, 0), ('ret', 252, 0), ('ret', 252, 21), ('ret', 126, 21), ('comp',)])),
                 K=c([1, 2, 3]), lev=c([1, 2, 3]), reb=c(['W', 'M']))
        return canon(dict(r, gate='none'))
    r.update(gate_part(R))
    return canon(r)


def canon(r):
    r = dict(r)
    if r.get('gate', 'none') == 'none':
        r.pop('gfreq', None); r.pop('goff', None); r['gate'] = 'none'
    if r.get('K') == 1 and 'wt' in r: r['wt'] = 'eq'
    if r['fam'] == 'RP' and r['U'] in ('NL', 'SL') and r.get('fb') == 'MTB1' and r['filt'] == 'none' and not r['tv']:
        r['fb'] = 'CASH'                                    # fallback never used
    if r['fam'] == 'CORR' and r['else'] == 'FULL' and False: pass
    return r


def h(r):
    return hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()[:16]


def main():
    R = random.Random(SEED)
    base, seen, raw = [], set(), 0
    for fam in ['XSM', 'MR', 'TSM', 'VT', 'RP', 'CORR', 'DISP', 'ACORR', 'CS']:
        for _ in range(ALLOC[fam]):
            r = draw(R, fam); raw += 1
            k = h(r)
            if k in seen: continue
            seen.add(k); base.append(r)
    pairs = []
    for _ in range(ALLOC['PAIR']):
        a, b = R.sample(base, 2); raw += 1
        r = dict(fam='PAIR', alpha=R.choice([0.5, 0.7]), r1=a, r2=b)
        k = h(r)
        if k in seen: continue
        seen.add(k); pairs.append(r)
    rules = base + pairs
    with open(S + 'results/rules.jsonl', 'w') as f:
        for i, r in enumerate(rules):
            f.write(json.dumps(dict(id=i, h=h(r), rule=r), sort_keys=True) + '\n')
    fams = {}
    for r in rules: fams[r['fam']] = fams.get(r['fam'], 0) + 1
    print(json.dumps(dict(seed=SEED, drawn=raw, unique=len(rules), by_family=fams)))


if __name__ == '__main__':
    main()
