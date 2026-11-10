"""Markdown tables for the ONF1 reports, straight from the result files (no hand-copied numbers).
  python -B code/make_tables.py ms1      -> corrected MS1 table (<=2014)
  python -B code/make_tables.py sens     -> sensitivities outside the registration (<=2014, 30 seeds)
  python -B code/make_tables.py dev      -> real-night windows inside <=2014
  python -B code/make_tables.py devx     -> extra window checks inside <=2014 (sub-periods, fees, t-statistics)
  python -B code/make_tables.py holdout  -> post-2014 windows            (holdout folder only)
  python -B code/make_tables.py holdx    -> post-2014 extra window checks (holdout folder only)"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
R = paths.RES; which = sys.argv[1] if len(sys.argv) > 1 else ''
if which not in ('ms1', 'sens', 'dev', 'devx', 'holdout', 'holdx'): sys.exit('usage: make_tables.py ms1 | sens | dev | devx | holdout | holdx')
if which in ('holdout', 'holdx') and os.environ.get('ONF1_ALLOW_HOLDOUT') != '1': sys.exit('post-2014 tables: run with ONF1_ALLOW_HOLDOUT=1 (holdout folder only)')
NAME = {'P1 v9-US': 'P1 v9 미국만', 'P2 v10-US': 'P2 v10 미국만', 'P3 A-US': 'P3 PRESET_A 미국만', 'P3 A-US bd2': 'P3 (브레이크 2일 지연)',
        'P1 v9-US bd2': 'P1 (브레이크 2일 지연)', 'P2 v10-US bd2': 'P2 (브레이크 2일 지연)',
        'T1': 'T1 밤 1.0배 항상', 'T2': 'T2 밤 0.5배 항상', 'T3': 'T3 밤 2.0배 항상', 'T4': 'T4 v1 현금일 때만', 'T5': 'T5 v1 보유 중에만', 'T6': 'T6 변동성 높으면 축소',
        'F1': 'F1 선물 v1 + 밤 1.0배', 'F2': 'F2 선물 v1 + 밤 2.0배', 'F3': 'F3 선물 v1 + 현금일 때만'}
ALL = ('P1 v9-US', 'P1 v9-US bd2', 'P2 v10-US', 'P2 v10-US bd2', 'P3 A-US', 'P3 A-US bd2', 'T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'F1', 'F2', 'F3')
def p(x): return '%.1f' % (x * 100)
def s(x): return '%+.1f' % (x * 100)
def dd2(x, a='dev250_path', b='real_ndx_86_14'): return '%s / %s' % (s(x[a]['d']), s(x[b]['d']))

if which == 'ms1':
    pre = {}; fix = {}
    for g in 'PTF':
        pre.update(json.load(open(R + 'pre_%s_le2014.json' % g))); fix.update(json.load(open(R + 'fix_%s_le2014.json' % g)))
    v = fix['v1']; print('v1: 대표 %.2f%%, 실제 %.2f%%\n' % (v['dev250_path'] * 100, v['real_ndx_86_14'] * 100))
    print('| 후보 | 등록 당시 측정 C (대표 / 실제) | 보정 측정 C 대표 (v1 대비) | 보정 측정 C 실제 (v1 대비) | 규칙 1 충족 난수 | 수수료 2배 C (v1 대비) | 규칙 1+2 충족 난수 | M (v1 대비) | H (v1 대비) | Z (v1 대비) |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    for k in ALL:
        c = fix[k + '|C|base']; a, b = c['dev250_path'], c['real_ndx_86_14']
        pr = pre[k + '|C|base'] if ' bd2' not in k else None
        prs = '%s / %s' % (p(pr['dev250_path']['cagr']), p(pr['real_ndx_86_14']['cagr'])) if pr else '-'
        def dd(m, t='base'): return dd2(fix['%s|%s|%s' % (k, m, t)])
        print('| %s | %s | %s (%s) | %s (%s) | %d/30 | %s | %d/30 | %s | %s | %s |' % (NAME[k], prs, p(a['cagr']), s(a['d']), p(b['cagr']), s(b['d']), c['seeds_pass_both'],
              dd('C', 'fee2'), fix[k + '|rule1and2_C'], dd('M'), dd('H'), dd('Z')))
    print('\nM 가정에서 (v1 대비 대표 / 실제, 규칙 1 충족 난수 → 수수료 2배 v1 대비, 규칙 1+2 충족 난수):')
    for k in ('P3 A-US', 'P3 A-US bd2', 'T1', 'T2', 'T5', 'T6', 'F1'):
        x = fix[k + '|M|base']; y = fix[k + '|M|fee2']
        print('- %s: %s, %d/30 → %s, %d/30' % (NAME[k], dd2(x), x['seeds_pass_both'], dd2(y), fix[k + '|rule1and2_M']))
    sv = json.load(open(R + 'sens_V_le2014.json'))
    print('\n대표 기준 MDD 중앙값 / −80%% 이하로 떨어진 경로 비율 (보정 측정 C): v1 %s%% / %.0f%%, ' % (p(sv['v1']['dev250_path']['mdd']), sv['v1']['dev250_path']['dd80'] * 100)
          + ', '.join('%s %s%% / %.0f%%' % (NAME[k], p(fix[k + '|C|base']['dev250_path']['mdd']), fix[k + '|C|base']['dev250_path']['dd80'] * 100) for k in ('P1 v9-US', 'P2 v10-US', 'P3 A-US', 'T5', 'T6', 'F1')))

elif which == 'sens':
    S = {}
    for sec in 'ABCDEFG': S[sec] = json.load(open(R + 'sens_%s_le2014.json' % sec))
    fix = {}
    for g in 'PTF': fix.update(json.load(open(R + 'fix_%s_le2014.json' % g)))
    A, B, C, D, E, F, G = (S[x] for x in 'ABCDEFG')
    MAIN = ('P1 v9-US', 'P2 v10-US', 'P3 A-US', 'T5', 'F1')
    print('수수료 민감도 (v1 대비 %p, 대표 / 실제, 난수 30개 평균. 0.83bp 가 등록 값, 1.66bp 가 등록 스트레스):\n')
    print('| 후보 | C 0.30bp | C 0.60bp | C 0.83bp | C 1.66bp | M 0.30bp | M 0.60bp | M 0.83bp | M 1.66bp |'); print('|---|---|---|---|---|---|---|---|---|')
    for k in MAIN:
        print('| %s | ' % NAME[k] + ' | '.join(dd2(x) for x in (A[k + '|C|fee030'], A[k + '|C|fee060'], fix[k + '|C|base'], fix[k + '|C|fee2'],
                                                             A[k + '|M|fee030'], A[k + '|M|fee060'], fix[k + '|M|base'], fix[k + '|M|fee2'])) + ' |')
    print('| %s | %s | - | %s | %s | %s | - | %s | %s |' % (NAME['P3 A-US bd2'], dd2(A['P3 A-US bd2|C|fee030']), dd2(fix['P3 A-US bd2|C|base']), dd2(fix['P3 A-US bd2|C|fee2']),
                                                     dd2(A['P3 A-US bd2|M|fee030']), dd2(fix['P3 A-US bd2|M|base']), dd2(fix['P3 A-US bd2|M|fee2'])))
    print('\n가정 민감도 (v1 대비 %p, 대표 / 실제, 난수 30개 평균. 왼쪽 값이 수수료 0.83bp, 오른쪽 값이 수수료 2배):\n')
    print('| 후보 | 등록 C | 등록 M (1993년부터) | 프리미엄 1996년부터 | C + 밤 금리 몫 | C + 계좌 현금 이자 | C + 둘 다 |'); print('|---|---|---|---|---|---|---|')
    def two(d, k, tag): return ('%s → %s' % (dd2(d[k + '|%s|base' % tag]), dd2(d[k + '|%s|fee2' % tag]))) if (k + '|%s|base' % tag) in d else '-'
    for k in MAIN + ('T6',):
        print('| %s | %s | %s | %s | %s | %s | %s |' % (NAME[k], two(fix, k, 'C'), two(fix, k, 'M'), two(B, k, 'M96'), two(C, k, 'Ccarry'), two(D, k, 'Ccash'), two(D, k, 'Ccarry+cash')))
    print('| %s | %s | %s | - | - | - | %s → - |' % (NAME['P3 A-US bd2'], two(fix, 'P3 A-US bd2', 'C'), two(fix, 'P3 A-US bd2', 'M'), dd2(D['P3 A-US bd2|Ccarry+cash|base'])))
    def cd(x): return '%s / %s (%s)' % (p(x['dev250_path']['cagr']), p(x['real_ndx_86_14']['cagr']), dd2(x))
    print('\nPRESET_A 미국만: 브레이크가 늦을 때와 유리한 가정을 모두 겹칠 때 (연 수익률 %, 괄호는 v1 대비 %p, 대표 / 실제, 난수 30개 평균):\n')
    print('| 조건 | 브레이크 당일 반응 | 하루 늦음 | 이틀 늦음 |'); print('|---|---|---|---|')
    print('| 등록 조건 (C, 0.83bp) | %s | %s | %s |' % (cd(fix['P3 A-US|C|base']), cd(G['P3 A-US bd1|C|base']), cd(fix['P3 A-US bd2|C|base'])))
    print('| M, 0.83bp | %s | %s | %s |' % (cd(fix['P3 A-US|M|base']), cd(G['P3 A-US bd1|M|base']), cd(fix['P3 A-US bd2|M|base'])))
    print('| C, 0.30bp | %s | %s | %s |' % (cd(A['P3 A-US|C|fee030']), cd(G['P3 A-US bd1|C|fee030']), cd(A['P3 A-US bd2|C|fee030'])))
    print('| M + 계좌 현금 이자 + 0.30bp (유리한 가정을 모두 겹침) | %s | %s | %s |' % (cd(G['P3 A-US|M+cash|fee030']), cd(G['P3 A-US bd1|M+cash|fee030']), cd(G['P3 A-US bd2|M+cash|fee030'])))
    print('\n같은 겹침(M + 계좌 현금 이자 + 0.30bp)에서 F1: %s. T5 는 M + 0.30bp 에서 %s (T5 의 선물 계좌 이자는 재지 않음).' % (cd(G['F1|M+cash|fee030']), cd(A['T5|M|fee030'])))
    def be(k, m):
        """break-even one-way fee (bp): where the 30-seed mean d crosses 0, piecewise linear between the measured fees; the lower of the two bases."""
        pts = [(f, src[k + '|%s|%s' % (m, tag)]) for f, src, tag in ((0.30, A, 'fee030'), (0.60, A, 'fee060'), (0.83, fix, 'base'), (1.66, fix, 'fee2')) if (k + '|%s|%s' % (m, tag)) in src]
        out = []
        for bn in ('dev250_path', 'real_ndx_86_14'):
            x = [(f, c[bn]['d']) for f, c in pts]
            if x[0][1] <= 0: out.append((-1, '%.2f 미만' % x[0][0])); continue
            for (f0, d0), (f1, d1) in zip(x[:-1], x[1:]):
                if d0 > 0 >= d1: out.append((f0 + (f1 - f0) * d0 / (d0 - d1), None)); break
            else: out.append((99, '%.2f 초과' % x[-1][0]))
        lo = min(out); return lo[1] if lo[1] else '%.2f' % lo[0]
    print('\n손익분기 수수료 (편도 bp, 두 기준 모두 v1 대비 플러스가 되는 한계, 난수 30개 평균을 수수료 사이에서 직선 보간): '
          + ', '.join('%s C %s · M %s' % (NAME[k], be(k, 'C'), be(k, 'M')) for k in MAIN + ('P3 A-US bd2',)))
    v = E['v1']; print('\nS&P 시대 기준 (밤 자료가 전혀 없어 전부 합성, 프리미엄 0. v1: 1955~85 %.1f%%, 1970~85 %.1f%%). v1 대비 %%p (1955~85 / 1970~85, 난수 30개 평균):' % (v['real_spx_55_85'] * 100, v['real_spx_70_85'] * 100))
    print(', '.join('%s %s' % (NAME[k].split(' ')[0] if k not in ('P1 v9-US', 'P2 v10-US', 'P3 A-US') else NAME[k], dd2(E[k + '|C|base'], 'real_spx_55_85', 'real_spx_70_85'))
                    for k in ('P1 v9-US', 'P2 v10-US', 'P3 A-US', 'T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'F1', 'F2', 'F3')))
    print('\n8천만 원에서 정수 계약만 쓸 때 (v1 대비 %p, 대표 / 실제, 난수 30개 평균. MNQ 1계약 = 8,355만 원은 2026-10-07 지수, 7,490만 원은 2026-11-09 지수 기준):')
    for k in ('T5', 'T1'):
        print('- %s: 1계약 8,355만 원이면 C %s, M %s. 1계약 7,490만 원이면 C %s, M %s. 계약 단위 없이 같은 자본이면 C %s, M %s.' % (
            NAME[k], dd2(F[k + '|C|unit80M']), dd2(F[k + '|M|unit80M']), dd2(G[k + '|C|unit80M_n749']), dd2(G[k + '|M|unit80M_n749']), dd2(F[k + '|C|frac80M']), dd2(F[k + '|M|frac80M'])))

elif which in ('dev', 'holdout'):
    d = json.load(open(R + 'hist_dev.json' if which == 'dev' else paths.HOLD + 'hist_holdout.json'))
    W = list(d.keys())
    ROW = [('v1', 'v1'), ('hold 1x', '나스닥100 1배 보유'), ('hold 3x', '나스닥100 3배 보유'), ('v1 via futures (MF1)', 'v1 을 선물로 구현'),
           ('T1', NAME['T1']), ('T2', NAME['T2']), ('T3', NAME['T3']), ('T4', NAME['T4']), ('T5', NAME['T5']), ('T6', NAME['T6']), ('F1', NAME['F1']), ('F2', NAME['F2']), ('F3', NAME['F3']),
           ('P1 v9-US d2', 'v9 미국만'), ('P1 v9-US d2 bd2', 'v9 미국만 (브레이크 2일 지연)'), ('P1 v9-US d2 fee x2', 'v9 미국만 (수수료 2배)'),
           ('P2 v10-US d2', 'v10 미국만'), ('P2 v10-US d2 bd2', 'v10 미국만 (브레이크 2일 지연)'), ('P2 v10-US d2 fee x2', 'v10 미국만 (수수료 2배)'),
           ('P3 A-US d2', 'PRESET_A 미국만'), ('P3 A-US d2 bd2', 'PRESET_A 미국만 (브레이크 2일 지연)'), ('P3 A-US d2 fee x2', 'PRESET_A 미국만 (수수료 2배)'),
           ('P3 A-US d2 pkg-assump', 'PRESET_A 미국만 (업로드 가정)')]
    print('| 전략 | ' + ' | '.join('%s~%s' % (d[w]['window'][0][:7], d[w]['window'][1][:7]) for w in W) + ' |'); print('|---|' + '---|' * len(W))
    for k, lab in ROW: print('| %s | ' % lab + ' | '.join('%s%% / %s%%' % (p(d[w][k]['cagr']), '%.0f' % (d[w][k]['mdd'] * 100)) for w in W) + ' |')

else:
    d = json.load(open(R + 'hist_extra_dev.json' if which == 'devx' else paths.HOLD + 'hist_extra_holdout.json'))
    W = list(d.keys()); hdr = ' | '.join('%s~%s' % (d[w]['window'][0][:7], d[w]['window'][1][:7]) for w in W)
    print('T5 − v1 (연 %p), 수수료별, 그리고 일별 차이의 t 값:\n')
    print('| | ' + hdr + ' |'); print('|---|' + '---|' * len(W))
    print('| v1 (CAGR / MDD) | ' + ' | '.join('%s%% / %.0f%%' % (p(d[w]['v1']['cagr']), d[w]['v1']['mdd'] * 100) for w in W) + ' |')
    for lab, nm in (('0.83bp', '수수료 0.83bp (등록)'), ('1.66bp', '수수료 2배'), ('0.60bp', '수수료 0.60bp'), ('0.30bp', '수수료 0.30bp')):
        print('| T5 − v1, %s | ' % nm + ' | '.join(s(d[w]['T5 ' + lab]['d']) for w in W) + ' |')
    print('| t 값 (0.83bp, 단순 / 자기상관 보정) | ' + ' | '.join('%.1f / %.1f' % (d[w]['T5 0.83bp']['t'], d[w]['T5 0.83bp']['t_nw']) for w in W) + ' |')
    print('| 밤 포지션을 든 날의 비율 / 평균 크기 | ' + ' | '.join('%.0f%% / %.2f배' % (d[w]['T5 0.83bp']['tilt_on'] * 100, d[w]['T5 0.83bp']['avg_tilt']) for w in W) + ' |')
    print('\n업로드 프리셋(미국만) − v1 (연 %p), 수수료별:\n')
    print('| | ' + hdr + ' |'); print('|---|' + '---|' * len(W))
    for cn, nm in (('P1 v9-US', 'v9'), ('P2 v10-US', 'v10'), ('P3 A-US', 'PRESET_A')):
        for lab, fn in (('0.83bp', '0.83bp (등록)'), ('1.66bp', '2배'), ('0.60bp', '0.60bp'), ('0.30bp', '0.30bp'), ('0.30bp bd2', '0.30bp + 브레이크 2일 지연')):
            print('| %s, %s | ' % (nm, fn) + ' | '.join('%s (MDD %.0f%%)' % (s(d[w]['%s %s' % (cn, lab)]['d']), d[w]['%s %s' % (cn, lab)]['mdd'] * 100) for w in W) + ' |')
