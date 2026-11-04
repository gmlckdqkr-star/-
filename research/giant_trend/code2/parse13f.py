"""Parse original 13F-HR filings into holdings: (giant, filed, period, cusip, value, title). CUSIP check digit validated."""
import os, re, json, sys
RAW = os.environ.get('GT2_RAW', '/tmp/gt2raw')
OUT = '/mnt/project-files/research/giant_trend/results2/holdings.json'
def cusip_ok(c):
    if not re.fullmatch(r'[0-9A-Z]{8}[0-9]', c) or not re.search(r'\d', c[:6]) and False: return False
    s = 0
    for i, ch in enumerate(c[:8]):
        v = int(ch) if ch.isdigit() else ord(ch) - 55
        if i % 2 == 1: v *= 2
        s += v // 10 + v % 10
    return (10 - s % 10) % 10 == int(c[8])
BAD = re.compile(r'\b(PUT|CALL|PUTS|CALLS|NOTE|NOTES|DEB|DEBT|BOND|BONDS|PFD|PREF|WARRANT|WARRANTS|WTS?|RIGHTS?|CONV|CV)\b', re.I)
NUM = re.compile(r'^\$?[\d,]+(\.\d+)?$')
SPL = re.compile(r'(?<![0-9A-Z])([0-9A-Z]{6})[ -]([0-9A-Z]{2})[ -]([0-9])(?![0-9A-Z])')
def parse_text(txt):
    rows = []; last = None
    for line in txt.splitlines():
        toks = line.split(); hit = None
        for j, t in enumerate(toks):
            t2 = t.strip(',;|').upper()
            if len(t2) == 9 and cusip_ok(t2): hit = (t2, j); break
        if hit is None:
            m = SPL.search(line.upper())
            if m and cusip_ok(''.join(m.groups())):
                c = ''.join(m.groups()); pre = line[:m.start()].split(); rest = line[m.end():].split()
                toks = pre + [c] + rest; hit = (c, len(pre))
        if hit is not None:
            c, j = hit
            nums = [x.replace(',', '').replace('$', '') for x in toks[j + 1:j + 4] if NUM.match(x)]
            if nums:
                bad = bool(BAD.search(line)); rows.append((c, float(nums[0]), bad, ' '.join(toks[:j])[:60], float(nums[1]) if len(nums) > 1 else 0.0)); last = (c, bad)
            continue
        # continuation line: starts with spaces, first two tokens numeric, then SH/PRN
        cont = last and line[:20].strip() == '' and len(toks) >= 2 and NUM.match(toks[0]) and NUM.match(toks[1])
        if cont and (',' in toks[0] + toks[1] or (len(toks) >= 3 and toks[2].upper() in ('SH', 'PRN'))):
            rows.append((last[0], float(toks[0].replace(',', '')), last[1] or bool(BAD.search(line)), 'cont', float(toks[1].replace(',', ''))))
    return rows
def parse_xml(txt):
    rows = []
    for m in re.finditer(r'<(?:\w+:)?infoTable>(.*?)</(?:\w+:)?infoTable>', txt, re.S | re.I):
        b = m.group(1); g = lambda k: (re.search(rf'<(?:\w+:)?{k}>(.*?)</(?:\w+:)?{k}>', b, re.S | re.I) or [None, ''])[1].strip()
        c = g('cusip').upper(); v = g('value'); pc = g('putCall'); title = g('titleOfClass'); typ = g('sshPrnamtType')
        if not c or not v: continue
        bad = bool(pc) or typ.upper() == 'PRN' or bool(BAD.search(title))
        sh = g('sshPrnamt').replace(',', ''); rows.append((c, float(v.replace(',', '')), bad, g('nameOfIssuer')[:60], float(sh) if sh else 0.0))
    return rows
idx = json.load(open(f'{RAW}/index.json')); out = []; qa = []
for g, fl in idx.items():
    for f in fl:
        if not os.path.exists(f['file']): continue
        txt = open(f['file'], errors='ignore').read()
        rows = parse_xml(txt) if re.search(r'<(?:\w+:)?infoTable>', txt, re.I) else parse_text(txt)
        tot = re.search(r'Value\s+Total:?\s*\$?\s*([\d,]+)', txt, re.I)
        tv = float(tot.group(1).replace(',', '')) if tot else None
        agg = {}
        for c, v, bad, nm, sh in rows:
            if bad: continue
            a = agg.setdefault(c, [0.0, nm, 0.0]); a[0] += v; a[2] += sh
            if a[1] == 'cont' and nm != 'cont': a[1] = nm
        s_all = sum(r[1] for r in rows)
        qa.append((g, f['filed'], len(rows), round(s_all / tv, 3) if tv else None))
        out.append(dict(giant=g, filed=f['filed'], period=f['period'], hold={c: [round(v, 1), nm, sh] for c, (v, nm, sh) in agg.items()}))
os.makedirs(os.path.dirname(OUT), exist_ok=True); json.dump(out, open(OUT, 'w'))
import statistics
for g in idx:
    q = [x for x in qa if x[0] == g]; r = [x[3] for x in q if x[3]]
    print(g, len(q), 'rows med', statistics.median([x[2] for x in q]), 'parsed/total med', statistics.median(r) if r else None, 'min', min(r) if r else None, 'n<0.9', sum(1 for x in r if x < .9))
