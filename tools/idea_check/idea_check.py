#!/usr/bin/env python3
"""연구 아이디어 사전 점검기 (죽은 축 자동 거절). 2026-11-04, 스레드 '적중 확률 높일 도구와 방법 만들기'.

쓰는 법:
  python3 idea_check.py check "옵션 만기 주간에 나스닥 팔기"      # 닫힌 축과 맞는지, 근거 파일, 다시 열 조건
  python3 idea_check.py list                                       # 등록된 축 전부
  python3 idea_check.py add --id T20 --area 시점 --name "..." --kw "a,b" --verdict CLOSED --result "..." --evidence "..." --reopen "..."
판정:
  자동 거절   = 닫힌 축(CLOSED)과 강하게 일치. 새 정보 종류가 아니면 시작하지 않는다.
  막힘        = 자료가 사용자 문(가입·로그인·유료) 뒤에 있음.
  전진 기록만 = 과거 검증이 불가능해 이미 전진 기록 중.
  진행 중     = 다른 스레드가 하고 있음.
  새 축 후보  = 등록된 축과 약하게만 겹침 → G1 관문부터 (아래 점검표).
"""
import sys, os, json, re, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, 'closed_axes.json')
LABEL = {'CLOSED': '자동 거절', 'BLOCKED': '막힘 (사용자 문 필요)', 'FORWARD': '전진 기록만', 'OPEN': '진행 중 (다른 스레드)'}
CHECKLIST = """[새 축이면 시작 전 점검표]
 1. 자료가 2014-12-31까지 실제로 있나 (발표 지연 반영, 빈티지 필요 여부)
 2. 무료·합법인가 (robots.txt/약관 확인, 유료는 제안만, Financial Datasets 금지, 사용자 개인정보 외부 입력 금지)
 3. 금지 파일을 열지 않는가 (memory forbidden-files 목록)
 4. 사전 등록(PRECOMMIT) 먼저: 변수·변환·시도 수 N 고정
 5. 시점 신호 → research/breakthrough/code/gate.py (보정 적중 ≥65% 보류, ≥70% 설계, 항상 보유 55.5%를 넘어야 정보)
    종목·수익원 → 비용 후 단독 Sharpe ≈1.1 (같은 기준 0.55) 또는 종목 IC ≥ .05 + 지속성 (IS12 기준)
 6. 가격 패널로 표현되면 lab 먼저 (research/lab/USAGE_FOR_THREADS_KO.md), 보고에 'lab 사용: 예/아니오(이유)'
 7. 숫자는 MS1 대표값(dev250_path, 세후·청산세)만, 보수 점검을 끝낸 뒤 한 번만 보고
 8. 끝나면 이 등록부에 add로 한 줄 추가 (닫힘이든 아니든)"""

def norm(s): return re.sub(r'[\s·,./()\-_+]', '', s.lower())
def grams(s):
    s = norm(s); return {s[i:i + 2] for i in range(len(s) - 1)}

def load():
    with open(REG, encoding='utf-8') as f: return json.load(f)

def score(idea, ax):
    n = norm(idea); hits = [k for k in ax['kw'] if norm(k) and norm(k) in n]
    g1, g2 = grams(idea), grams(ax['name'] + ' ' + ' '.join(ax['kw']))
    jac = len(g1 & g2) / max(1, len(g1)) if g1 else 0.0
    return 3.0 * len(hits) + 4.0 * jac, hits

def check(idea, top=3):
    d = load(); rs = sorted(((score(idea, a), a) for a in d['axes']), key=lambda x: -x[0][0])
    print(f'아이디어: {idea}\n')
    best = None
    for (s, hits), a in rs[:top]:
        if s < 1.0: continue
        best = best or (s, a)
        print(f"[{a['id']}] {a['name']}  (점수 {s:.1f}, 겹친 낱말: {', '.join(hits) or '-'})")
        print(f"   상태: {LABEL.get(a['verdict'], a['verdict'])} | 결과: {a['result']}")
        print(f"   근거: {a['evidence']} | 다시 열 조건: {a['reopen']}\n")
    if best and best[0] >= 3.0:
        a = best[1]; v = LABEL.get(a['verdict'], a['verdict'])
        print(f"판정: {v} — [{a['id']}]와 일치. " + ('새 정보 종류가 아니면 시작하지 않는다.' if a['verdict'] == 'CLOSED' else ''))
        if a['verdict'] == 'CLOSED': print("    (같은 축이라도 '다시 열 조건'을 충족하는 새 자료가 있으면 그 근거를 적고 점검표로 진행)")
    else:
        print('판정: 새 축 후보 — 등록된 닫힌 축과 강하게 겹치지 않음. 아래 점검표부터.')
    print('\n' + CHECKLIST)

def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd')
    c = sp.add_parser('check'); c.add_argument('idea', nargs='+'); c.add_argument('--top', type=int, default=3)
    sp.add_parser('list')
    a = sp.add_parser('add')
    for k in ('id', 'area', 'name', 'kw', 'verdict', 'result', 'evidence', 'reopen'): a.add_argument('--' + k, required=True)
    x = ap.parse_args()
    if x.cmd == 'check': check(' '.join(x.idea), x.top)
    elif x.cmd == 'list':
        for ax in load()['axes']: print(f"{ax['id']:4} {LABEL.get(ax['verdict'], ax['verdict']):14} {ax['area']:6} {ax['name']}")
    elif x.cmd == 'add':
        d = load()
        if any(ax['id'] == x.id for ax in d['axes']): sys.exit(f'이미 있는 id: {x.id}')
        if x.verdict not in LABEL: sys.exit('verdict는 CLOSED/BLOCKED/FORWARD/OPEN 중 하나')
        d['axes'].append(dict(id=x.id, area=x.area, name=x.name, kw=[k.strip() for k in x.kw.split(',') if k.strip()],
                              verdict=x.verdict, result=x.result, evidence=x.evidence, reopen=x.reopen))
        tmp = REG + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, REG); print('추가됨:', x.id)
    else: ap.print_help()

if __name__ == '__main__': main()
