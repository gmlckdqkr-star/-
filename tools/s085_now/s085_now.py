#!/usr/bin/env python3
"""s0.85 지금 상태 점검기 (C3 신호 부분). 2026-11-04, 스레드 '적중 확률 높일 도구와 방법 만들기'.

연구 규칙과의 관계: 이 도구는 '현재 상태'만 계산한다(성과 수치 없음). 2015년 이후 시장 자료를 읽으므로
연구 설계 스레드는 이 폴더의 out/ 을 열지 않는다. 코드 자체는 연구 정의를 그대로 옮긴 것이다:
  C3sig = crash_overlay strat.fam4(c, L_on=3.0, vcap=0.40, vlev=1.0, keys=('inv','shock6m'), caution=('shock6m',), Lc=1.0, sl=200, band=0.02)
  flags = crash_overlay ov.flags_hist: inv = 최근 378거래일 안에 (10년 − 3개월) < 0 이 한 번이라도, shock6m = 10년 금리 126거래일 변화 > 1.0%p
  vol(20) = 20일 로그수익 표준편차 × √252, 추세 관문 = 200일 SMA ±2% 히스테리시스(경보가 켜져 있을 때만 꺼짐)
  s0.85 = C3sig + AV23s 계좌 낙폭 브레이크(s=0.85). 브레이크는 '내 계좌'의 고점 대비 낙폭에 달려 있어 여기서는 계산하지 않는다
  (새로 시작하는 계좌 = 낙폭 0 = 브레이크가 C3 목표를 그대로 둠). 실제 체결은 연구 가정상 신호 2거래일 뒤.

쓰는 법:
  python3 s085_now.py --prices qqq.csv            # date,close (QQQ 또는 NDX 종가, 최소 230거래일)
  [--rates-dir DIR]  미국 재무부 일별 수익률 CSV 캐시 폴더(없으면 home.treasury.gov에서 최근 3년을 받음; robots 허용)
  [--out out/]       보고서 저장 폴더 (기본: 이 파일 옆 out/)
"""
import argparse, os, sys, datetime as dt, urllib.request, numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TSY = ('https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{y}/all'
       '?type=daily_treasury_yield_curve&field_tdr_date_value={y}&page&_format=csv')

def rates(rdir, years):
    os.makedirs(rdir, exist_ok=True); fr = []
    for y in years:
        p = os.path.join(rdir, f'tsy_{y}.csv')
        stale = (not os.path.exists(p)) or (y == dt.date.today().year and
                 (dt.datetime.now().timestamp() - os.path.getmtime(p)) > 6 * 3600)
        if stale:
            req = urllib.request.Request(TSY.format(y=y), headers={'User-Agent': 'Mozilla/5.0 (research tool)'})
            with urllib.request.urlopen(req, timeout=60) as r, open(p, 'wb') as f: f.write(r.read())
        d = pd.read_csv(p); d['Date'] = pd.to_datetime(d['Date'], format='%m/%d/%Y')
        fr.append(d.set_index('Date')[['3 Mo', '10 Yr']].rename(columns={'3 Mo': 'y3m', '10 Yr': 'y10'}))
    return pd.concat(fr).sort_index().astype(float)

def compute(px, Y):
    # 금리 경보는 금리 자료 자체의 거래일 행으로 계산한 뒤 가격 날짜에 붙인다 (가격 이력이 짧아도 378일 창이 온전함)
    Y = Y.dropna().copy(); inv_y = (Y['y10'] - Y['y3m']) < 0
    Y['inv'] = inv_y.astype(float).rolling(378, min_periods=1).max() > 0; Y['d6'] = Y['y10'] - Y['y10'].shift(126)
    X = px.join(Y, how='left'); X[['y3m', 'y10', 'inv', 'd6']] = X[['y3m', 'y10', 'inv', 'd6']].ffill()
    lvl = X['close']; lr = np.log(lvl).diff()
    m = lr.rolling(20).mean(); vol = np.sqrt(np.maximum((lr * lr).rolling(20).mean() - m * m, 0) * 252)
    sma = lvl.rolling(200).mean()
    inv_raw = inv_y; inv = X['inv'].astype(bool); d6 = X['d6']; shock6m = d6 > 1.0
    cond = inv | shock6m
    lo = lvl < sma * 0.98; hi = lvl > sma * 1.02
    off = np.zeros(len(X), bool); st = False
    for i in range(len(X)):
        on_c = bool(hi.iloc[i]) or not bool(cond.iloc[i]); off_c = bool(lo.iloc[i]) and bool(cond.iloc[i])
        st = (not on_c) if st else off_c; off[i] = st
    v = sma.notna().values; reset = ((hi | ~cond).values & v)
    settled = bool(reset.any())   # 이 날 이후 관문 상태는 시작 상태와 무관하게 확정
    B = np.where(vol > 0.40, 1.0, 3.0); B = np.where(shock6m, np.minimum(B, 1.0), B); B = np.where(off, 0.0, B)
    out = pd.DataFrame(dict(close=lvl, sma200=sma, ratio=lvl / sma - 1, vol20=vol, y10=X['y10'], y3m=X['y3m'],
                            spread=X['y10'] - X['y3m'], d10_126=d6, inv=inv, shock6m=shock6m, off=off, B=B))
    out.attrs['settled'] = settled
    return out, inv_raw

def report(o, inv_raw, src):
    t = o.index[-1]; r = o.iloc[-1]; age = (pd.Timestamp(dt.date.today()) - t).days
    name = {3.0: '3배 (TQQQ 100%)', 1.0: '1배 (QQQ 100% 또는 TQQQ 1/3 + 현금)', 0.0: '현금 (달러 예금)'}[float(r.B)]
    why = []
    if r.off: why.append('추세 관문 꺼짐: 200일선 −2% 아래 + 금리 경보 켜짐')
    else:
        if r.vol20 > 0.40: why.append('20일 변동성 40% 초과 → 1배')
        if r.shock6m: why.append('10년 금리 6개월 +1%p 넘게 급등(주의 단계) → 1배 상한')
        if not why: why.append('추세 위 또는 금리 경보 없음, 변동성 정상 → 3배')
    last_inv = inv_raw[inv_raw].index.max() if inv_raw.any() else None
    chg = o['B'].ne(o['B'].shift()); chg.iloc[0] = False; recent = o.loc[chg & (o.index >= t - pd.Timedelta(days=400)), 'B']
    L = [f'# s0.85 지금 상태 ({t:%Y-%m-%d} 종가 기준)', '',
         f'**C3 목표 레버리지: {name}**  ← 연구 가정상 2거래일 뒤 체결', '',
         '이유: ' + '; '.join(why), '',
         (f"경계까지 여유: 지수가 200일선 −2% 선까지 {r.ratio + 0.02:.1%} 더 빠지면 현금 전환 (금리 역전 경보가 켜져 있어서)" if (r.inv or r.shock6m) and not r.off else
          f"경계까지 여유: 금리 경보가 꺼져 있어 추세만으로는 현금이 되지 않음" if not r.off else
          f"복귀 조건: 200일선 +2% 위 ({0.02 - r.ratio:.1%} 상승) 또는 금리 경보 해제"), '',
         '| 항목 | 지금 값 | 바뀌는 경계 |', '|---|---|---|',
         f"| 지수 / 200일선 | {r.ratio:+.1%} | 경보 켜진 상태에서 −2% 아래면 현금, 꺼진 상태에서 +2% 위면 복귀 |",
         f"| 20일 변동성(연) | {r.vol20:.1%} | 40% 초과면 1배 |",
         f"| 10년 − 3개월 금리 | {r.spread:+.2f}%p | 0 미만(역전)이 한 번 나오면 378거래일 동안 경보 |",
         f"| 금리 역전 경보(inv) | {'켜짐' if r.inv else '꺼짐'} | 마지막 역전일 {last_inv:%Y-%m-%d} |" if last_inv is not None else
         f"| 금리 역전 경보(inv) | {'켜짐' if r.inv else '꺼짐'} | 자료 구간에 역전 없음 |",
         f"| 10년 금리 126일 변화 | {r.d10_126:+.2f}%p | +1.00%p 초과면 급등 경보(shock6m) |",
         f"| 급등 경보(shock6m) | {'켜짐' if r.shock6m else '꺼짐'} | |",
         f"| 추세 관문 | {'꺼짐(현금)' if r.off else '열림'} | |", '',
         '최근 400일 목표 변경: ' + (', '.join(f'{d:%Y-%m-%d}→{b:g}배' for d, b in recent.items()) or '없음'), '',
         '## 주의', ('- 추세 관문 상태: 확정 (자료 구간 안에 200일선 +2% 위 또는 경보 해제일이 있음).' if o.attrs.get('settled') else
                    '- ⚠ 추세 관문 상태 미확정: 자료 구간에 복귀 조건이 한 번도 없었다. 가격을 더 길게(500거래일 이상) 넣어 다시 돌릴 것.'),
         f'- 가격 자료: {src}, 마지막 날짜 {t:%Y-%m-%d} (오늘과 {age}일 차이){" ⚠ 자료가 오래됨" if age > 5 else ""}.',
         '- QQQ 종가는 분배금만큼 NDX와 조금 다르다(200일선 비율 차이 0.1~0.3%p 수준, 경계 근처면 NDX로 다시 확인).',
         '- 브레이크(AV23s, s=0.85)는 내 계좌의 고점 대비 낙폭으로 레버리지를 더 낮춘다. 새 계좌(낙폭 0)는 위 목표 그대로. 이미 운용 중이면 프로그램의 브레이크 값을 따른다.',
         '- 성과 수치는 넣지 않는다. s0.85 MS1 대표값은 연구 문서(research/measure_std) 기준 16.2%(2014년 이하 개발 구간).']
    return '\n'.join(L)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--prices', required=True)
    ap.add_argument('--rates-dir', default=os.path.join(HERE, 'cache')); ap.add_argument('--out', default=os.path.join(HERE, 'out'))
    a = ap.parse_args()
    px = pd.read_csv(a.prices, parse_dates=['date']).set_index('date').sort_index()[['close']].astype(float)
    if len(px) < 230: sys.exit('가격이 230거래일보다 적다 (200일선 + 20일 변동성 필요)')
    y = px.index[-1].year; Y = rates(a.rates_dir, [y - 2, y - 1, y])
    o, inv_raw = compute(px, Y)
    st = o.attrs.get('settled'); o = o.dropna(subset=['sma200']); o.attrs['settled'] = st
    txt = report(o, inv_raw, os.path.basename(a.prices))
    os.makedirs(a.out, exist_ok=True); p = os.path.join(a.out, f's085_now_{o.index[-1]:%Y%m%d}.md')
    open(p, 'w', encoding='utf-8').write(txt + '\n'); print(txt); print('\n저장:', p)

if __name__ == '__main__': main()
