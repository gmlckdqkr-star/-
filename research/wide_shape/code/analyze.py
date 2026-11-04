"""WS1 analysis: required accuracy per shape (A) and effective accuracy of real signals (B). Writes results/map_summary.json"""
import json, glob, numpy as np
RD = '/mnt/project-files/research/wide_shape/results/'
TG = {'30%': 0.30, '60%': 0.60, '200%': 2.00}


def need(xs, ys, target):
    """smallest x where interpolated y crosses target (ys increasing-ish). None if never."""
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    ys = np.where(np.isfinite(ys), ys, 1e12)
    if ys[0] >= target:
        return float(xs[0])
    for i in range(1, len(xs)):
        if ys[i] >= target:
            return float(xs[i - 1] + (xs[i] - xs[i - 1]) * (target - ys[i - 1]) / (ys[i] - ys[i - 1]))
    return None


def inv(xs, ys, y):
    """x at which the oracle curve reaches y (for IC_eq). below ys[0] -> negative marker"""
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    if y <= ys[0]:
        return float('-inf') if y < ys[0] - 1e-9 else 0.0
    for i in range(1, len(xs)):
        if ys[i] >= y:
            return float(xs[i - 1] + (xs[i] - xs[i - 1]) * (y - ys[i - 1]) / (ys[i] - ys[i - 1]))
    return float(xs[-1])


S = {'A1': {}, 'A2': {}, 'A3': {}, 'A4': {}, 'B': {}}
# A1 index
a1 = json.load(open(RD + 'a1_index.json')); pg = a1['p_grid']
for shape in ('L3_I3', 'L3_cash'):
    for h in (1, 5, 21):
        k = '%s_h%d' % (shape, h)
        row = {}
        for tn, tv in TG.items():
            vals = {bn: need(pg, a1[bn]['cells'][k], tv) for bn in ('real_ndx_86_14', 'real_spx_55_85', 'dev250_path')}
            low = None if (vals['real_ndx_86_14'] is None or vals['real_spx_55_85'] is None) else max(vals['real_ndx_86_14'], vals['real_spx_55_85'])
            row[tn] = dict(low_era=low, **vals)
        row['perfect'] = {bn: a1[bn]['cells'][k][-1] for bn in ('real_ndx_86_14', 'real_spx_55_85', 'dev250_path')}
        S['A1'][k] = row
# A2 stocks
for fn in sorted(glob.glob(RD + 'a2_*_h*.json')):
    a = json.load(open(fn)); key = '%s_h%d' % (a['univ'], a['h'])
    rhos = sorted(a['O1'].keys(), key=float)
    ics = [a['O1'][r]['ic'] for r in rhos]
    S['A2'][key] = {'O1': {}, 'O2': {}, 'curves': {}}
    for K in ('1', '3', '5', '10', '20'):
        y = [min(a['O1'][r]['K'][K]['real'], a['O1'][r]['K'][K]['res']) for r in rhos]
        yr = [a['O1'][r]['K'][K]['real'] for r in rhos]
        S['A2'][key]['curves'][K] = {'ic': ics, 'cagr_min': y, 'cagr_real': yr}
        S['A2'][key]['O1'][K] = {tn: need(ics, y, tv) for tn, tv in TG.items()}
        S['A2'][key]['O1'][K]['random'] = y[0]; S['A2'][key]['O1'][K]['perfect'] = y[-1]
        for q in ('0.1', '0.01'):
            ps = sorted([float(k.split('_')[1]) for k in a['O2'] if k.startswith(q + '_')])
            yy = [min(a['O2']['%s_%g' % (q, p)][K]['real'], a['O2']['%s_%g' % (q, p)][K]['res']) for p in ps]
            S['A2'][key]['O2'].setdefault(q, {})[K] = {tn: need(ps, yy, tv) for tn, tv in TG.items()}
# A4 sectors
a4 = json.load(open(RD + 'a4_sector.json'))
for k, v in a4.items():
    ps = sorted(v['O2_hit_best'].keys(), key=float); rs = sorted(v['O1_rho'].keys(), key=float)
    S['A4'][k] = {'N': v['N'], 'hit': {tn: need([float(p) for p in ps], [v['O2_hit_best'][p] for p in ps], tv) for tn, tv in TG.items()},
                  'rho': {tn: need([float(r) for r in rs], [v['O1_rho'][r] for r in rs], tv) for tn, tv in TG.items()},
                  'random': v['O2_hit_best'][ps[0]], 'perfect': v['O2_hit_best'][ps[-1]]}
# A3 combos
for fn in sorted(glob.glob(RD + 'a3_*.json')):
    a = json.load(open(fn)); S['A3'][a['univ']] = a['cells']
# B effective accuracy
for fn in sorted(glob.glob(RD + 'b_*_h*.json')):
    b = json.load(open(fn)); key = '%s_h%d' % (b['univ'], b['h'])
    if key not in S['A2']:
        continue
    cur = S['A2'][key]['curves']
    out = {}
    for nm, d in b['signals'].items():
        e = {'ic_all': d['ic_all'], 'ic_A': d['ic_A'], 'ic_B': d['ic_B'], 'prec10_K5': d['prec10_K5'], 'prec1_K5': d['prec1_K5']}
        for K in ('5', '20'):
            c = cur[K]
            real = d['K' + K]['real']
            e['K' + K] = dict(real=real, real_A=d['K' + K]['real_A'], real_B=d['K' + K]['real_B'], res=d['K' + K]['res'],
                              ic_eq=inv(c['ic'], c['cagr_real'], real), ic_req30=S['A2'][key]['O1'][K]['30%'])
        out[nm] = e
    S['B'][key] = out
json.dump(S, open(RD + 'map_summary.json', 'w'), indent=1, default=lambda x: None)


def f(x, pct=False):
    if x is None:
        return '불가'
    if x == float('-inf'):
        return '<0'
    return ('%.0f%%' % (100 * x)) if pct else ('%.3f' % x)


L = []
L.append('## A1 지수 방향 (3배 롱/3배 인버스, 대칭 적중률 p, 낮은 시대 = max(실제 NDX 86~14, 실제 SPX 55~85))')
L.append('| 모양 | 30% | 60% | 200% | p=1 상한 (NDX / SPX / dev250) |')
L.append('|---|---|---|---|---|')
for k, r in S['A1'].items():
    L.append('| %s | %s | %s | %s | %s / %s / %s |' % (k, f(r['30%']['low_era']), f(r['60%']['low_era']), f(r['200%']['low_era']),
                                                     f(r['perfect']['real_ndx_86_14'], 1), f(r['perfect']['real_spx_55_85'], 1), f(r['perfect']['dev250_path'], 1)))
L.append('\n## A2 종목 선택 (롱 1배, 필요 실현 IC; 실제 경로·재표본 중 낮은 값 기준)')
L.append('| 유니버스_기간 | K | 무작위 | 30% | 60% | 200% | 완전정보 | 상위10% 적중 필요 (30/60/200) | 상위1% 적중 필요 (30/60/200) |')
L.append('|---|---|---|---|---|---|---|---|---|')
for key, v in S['A2'].items():
    for K in ('1', '3', '5', '10', '20'):
        o = v['O1'][K]; q1 = v['O2']['0.1'][K]; q2 = v['O2']['0.01'][K]
        L.append('| %s | %s | %s | %s | %s | %s | %s | %s/%s/%s | %s/%s/%s |' % (key, K, f(o['random'], 1), f(o['30%']), f(o['60%']), f(o['200%']), f(o['perfect'], 1),
                                                                          f(q1['30%']), f(q1['60%']), f(q1['200%']), f(q2['30%']), f(q2['60%']), f(q2['200%'])))
L.append('\n## A4 업종 선택 (상위 1개)')
L.append('| 모양 | N | 무작위 | 최고 업종 적중 필요 (30/60/200) | 필요 rho (30/60/200) | 완전정보 |')
L.append('|---|---|---|---|---|---|')
for k, v in S['A4'].items():
    L.append('| %s | %d | %s | %s/%s/%s | %s/%s/%s | %s |' % (k, v['N'], f(v['random'], 1), f(v['hit']['30%']), f(v['hit']['60%']), f(v['hit']['200%']),
                                                    f(v['rho']['30%']), f(v['rho']['60%']), f(v['rho']['200%']), f(v['perfect'], 1)))
L.append('\n## B 실제 신호 (평균 IC vs 실효 IC_eq = 같은 K·h 오라클에서 같은 세후 수익을 내는 IC)')
L.append('| 모양 | 신호 | IC 전체 (앞/뒤) | 상위10% 적중 K5 | K5 세후 (앞/뒤) | K5 IC_eq / 30% 필요 | K20 세후 | K20 IC_eq / 30% 필요 |')
L.append('|---|---|---|---|---|---|---|---|')
for key, v in S['B'].items():
    for nm, e in v.items():
        L.append('| %s | %s | %.3f (%.3f/%.3f) | %.3f | %s (%s/%s) | %s / %s | %s | %s / %s |' % (
            key, nm, e['ic_all'], e['ic_A'], e['ic_B'], e['prec10_K5'], f(e['K5']['real'], 1), f(e['K5']['real_A'], 1), f(e['K5']['real_B'], 1),
            f(e['K5']['ic_eq']), f(e['K5']['ic_req30']), f(e['K20']['real'], 1), f(e['K20']['ic_eq']), f(e['K20']['ic_req30'])))
# A3 combo table: required market-direction hit p_m per (h, L, K, rho)
L.append('\n## A3 종목 + 인버스 결합 (오르는 블록이라 본 때 상위 K 종목, 내리는 블록이라 본 때 인버스 지수; 필요 시장 방향 적중 p_m)')
L.append('| 유니버스 | h | 인버스 배수 | K | 종목 IC 오라클 rho | 30% | 60% | 200% | p_m=1 |')
L.append('|---|---|---|---|---|---|---|---|---|')
for univ, cells in S['A3'].items():
    keys = sorted({k.split('_pm')[0] for k in cells})
    for base in keys:
        pms = sorted(float(k.split('_pm')[1]) for k in cells if k.startswith(base + '_pm'))
        ys = [min(cells['%s_pm%g' % (base, pm)]['real'], cells['%s_pm%g' % (base, pm)]['res']) for pm in pms]
        h, Lv, K, rho = base.split('_')
        L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (univ, h[1:], Lv[1:], K[1:], rho[3:], f(need(pms, ys, .3)), f(need(pms, ys, .6)), f(need(pms, ys, 2.0)), f(ys[-1], 1)))
# micro-universe sensitivity (addendum 1)
import os
if os.path.exists(RD + 'micro_kr.json'):
    m = json.load(open(RD + 'micro_kr.json'))
    L.append('\n## 민감도: 한국 소액 전용 유니버스 (20일 평균 거래대금 >= 2천만 원; 지도용, 후보 아님)')
    L.append('| h | 평균 자격 종목 수 | K | 무작위 | 필요 IC 30% / 60% / 200% | COMBO13 IC / 세후 | LVOL IC / 세후 | MOM IC / 세후 |')
    L.append('|---|---|---|---|---|---|---|---|')
    for hk, o in m.items():
        rh = sorted(o['O1'].keys(), key=float); ics = [o['O1'][r]['ic'] for r in rh]
        for K in ('K5', 'K20'):
            ys = [o['O1'][r][K] for r in rh]
            sg = o['B']
            L.append('| %s | %.0f | %s | %s | %s / %s / %s | %.3f / %s | %.3f / %s | %.3f / %s |' % (hk[1:], o['elig_mean'], K[1:], f(ys[0], 1), f(need(ics, ys, .3)), f(need(ics, ys, .6)), f(need(ics, ys, 2.0)),
                     sg['COMBO13']['ic'], f(sg['COMBO13'][K], 1), sg['LVOL']['ic'], f(sg['LVOL'][K], 1), sg['MOM']['ic'], f(sg['MOM'][K], 1)))
if os.path.exists(RD + 'xcheck_lab.json'):
    x = json.load(open(RD + 'xcheck_lab.json'))
    L.append('\n## lab 교차 확인 (미국 S&P 500 월간, 1971~2014 세후)')
    L.append('| 명세 | lab 71~14 | lab 86~14 | lab MS1 경로 | 이 엔진 | 이 엔진 결정일 위상 11개 범위 |')
    L.append('|---|---|---|---|---|---|')
    for r in x['rows']:
        ph = ('%s ~ %s' % (f(r['mine_phase_min'], 1), f(r['mine_phase_max'], 1))) if r['mine_phase_min'] is not None else '-'
        L.append('| %s | %s | %s | %s | %s | %s |' % (r['spec'], f(r['lab_71_14'], 1), f(r['lab_86_14'], 1), f(r['lab_ms1'], 1), f(r['mine'], 1), ph))
if os.path.exists(RD + 'c_registered.json'):
    c = json.load(open(RD + 'c_registered.json'))
    L.append('\n## C 등록 검정 (한국 복합 신호; 통과 = 뒤 IC >= 앞 IC의 50%, 재표본 중앙 > 24.2%, 뒤 기간 실제 > 0)')
    L.append('| 모양 | 신호 수 | IC 앞 / 뒤 | K20 실제 / 재표본 중앙 / 뒤 기간 | K20 총수익 / 비용 (연) | K5 실제 | 통과 |')
    L.append('|---|---|---|---|---|---|---|')
    for k, v in c.items():
        a = v['K20']
        L.append('| %s | %d | %.3f / %.3f | %s / %s / %s | %s / %s | %s | %s |' % (k, len(v['signals']), v['ic_A'], v['ic_B'], f(a['real'], 1), f(a['res_med'], 1), f(a['real_B'], 1),
                 f(a['gross_yr'], 1), f(a['cost_yr'], 1), f(v['K5']['real'], 1), '통과' if v['pass'] else '탈락'))
open(RD + 'MAP_TABLES.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
