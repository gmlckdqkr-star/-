# NI1-A audit: re-fetch 15 random sampled filings' document.xml and re-parse with an INDEPENDENT header-based parser.
# Does not import A/code. Raw documents stay in memory only; no names are printed or saved.
# Key: env OPENDART_API_KEY, never printed/logged/saved (masked in any error text).
import os, sys, json, re, io, zipfile, time, random, collections, urllib.request

KEY = os.environ['OPENDART_API_KEY']
UA = {'User-Agent': 'research-client/1.0'}
DOCS, OUT = sys.argv[1], sys.argv[2]
SEED = 5150
N = 15


def mask(s):
    return str(s).replace(KEY, '***')


def fetch(rno):
    u = 'https://opendart.fss.or.kr/api/document.xml?crtfc_key=' + KEY + '&rcept_no=' + rno
    for i in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()
        except Exception as e:
            print('retry', i, mask(e), flush=True); time.sleep(3 * (i + 1))
    return None


def text_of(b):
    # NOTE: the XML prolog says utf-8 but the bytes are cp949 in the files seen; choose the decoding that yields
    # the Korean section label, strict, utf-8 first (independent of the A/code order cp949-first).
    z = zipfile.ZipFile(io.BytesIO(b))
    raw = b''.join(z.read(n) for n in z.namelist())
    for enc in ('utf-8', 'cp949'):
        try:
            t = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        if '보고사유' in t or '세부변동' in t:
            return t, enc
    return raw.decode('cp949', errors='replace'), 'cp949-replace'


def strip(s):
    return re.sub(r'\s+', '', re.sub(r'<[^>]+>', '', s)).replace('&nbsp;', '')


def to_int(s):
    s = strip(s).replace(',', '')
    m = re.fullmatch(r'\(?([-+△▲▽]?)\s*(\d+)\)?', s)
    if not m:
        return None
    v = int(m.group(2))
    return -v if m.group(1) in ('-', '△', '▽') else v


def grid_rows(tbl):
    """expand a table into a list of rows of (text) cells with COLSPAN/ROWSPAN honoured."""
    rows = re.findall(r'<TR\b[^>]*>(.*?)</TR>', tbl, re.S)
    carry = {}  # col -> (remaining rows, text)
    out = []
    for tr in rows:
        cells = re.findall(r'<(T[DHEU])\b([^>]*)>(.*?)</\1>', tr, re.S)
        row = {}; col = 0; q = list(cells)
        while q or any(c >= col for c in carry):
            while col in carry:
                n, txt = carry[col]; row[col] = txt
                if n - 1 > 0: carry[col] = (n - 1, txt)
                else: del carry[col]
                col += 1
            if not q:
                break
            tag, at, inner = q.pop(0)
            cs = int((re.search(r'COLSPAN="(\d+)"', at) or [0, 1])[1]); rs = int((re.search(r'ROWSPAN="(\d+)"', at) or [0, 1])[1])
            txt = strip(inner)
            for c in range(col, col + cs):
                row[c] = txt
                if rs > 1: carry[c] = (rs - 1, txt)
            col += cs
        out.append([row[c] for c in sorted(row)])
    return out


def parse_header_based(t):
    """Locate tables after the 세부변동내역 label; build a header->column map from the header rows by TEXT
    (보고사유 / 변동전 / 증감 / 변동후); no ACODE/AUNIT attributes used. net1 uses the 증감 column with the sign from
    the reason; net2 uses (변동후 - 변동전) of the same rows (independent of the 증감 cell)."""
    i = t.find('세부변동내역')
    if i < 0:
        return dict(ok=False, why='no section')
    reg = t[i:]
    buy = sell = 0; buy2 = sell2 = 0; nrow = 0; labels = {}; hdrs = []
    for tbl in re.findall(r'<TABLE\b.*?</TABLE>', reg, re.S)[:3]:
        g = grid_rows(tbl)
        if not g or not any('보고사유' in c for c in g[0]):
            continue
        h = g[0]; h2 = g[1] if len(g) > 1 else []
        lab = [(h[k] + '|' + (h2[k] if k < len(h2) else '')) for k in range(len(h))]
        hdrs.append(lab)
        cr = next(k for k, c in enumerate(lab) if '보고사유' in c)
        cd = [k for k, c in enumerate(lab) if '증감' in c]
        cb = [k for k, c in enumerate(lab) if '변동전' in c]
        ca = [k for k, c in enumerate(lab) if '변동후' in c]
        if not cd:
            continue
        cd = cd[0]; cb = cb[0] if cb else None; ca = ca[0] if ca else None
        for row in g[2:]:
            if len(row) <= cd:
                continue
            rsn = row[cr]; v = to_int(row[cd])
            if v is None or not rsn or '보고사유' in rsn:
                continue
            nrow += 1
            key = '장내매수' if '장내매수' in rsn else ('장내매도' if '장내매도' in rsn else re.sub(r'[\d\s]', '', rsn)[:16])
            labels[key] = labels.get(key, 0) + 1
            dv = None
            if cb is not None and ca is not None:
                b0, a0 = to_int(row[cb]), to_int(row[ca])
                if b0 is not None and a0 is not None:
                    dv = a0 - b0
            if '장내매수' in rsn:
                buy += abs(v); buy2 += (dv if dv is not None else abs(v))
            elif '장내매도' in rsn:
                sell -= abs(v); sell2 += (dv if dv is not None else -abs(v))
        break  # the first detail table only (a document has one 세부변동내역 table)
    return dict(ok=nrow > 0, n_rows=nrow, buy=buy, sell=sell, net=buy + sell, net_afr_minus_bfr=buy2 + sell2,
                labels=labels, headers=hdrs)


def parse_attr_based(t):
    """Second independent read using the DART XML attributes: AUNIT RPT_RSN for reason, ACODE MDF_STK_CNT for change.
    Also reports the set of ACODE/AUNIT names that appear in rows with a reason cell."""
    buy = sell = 0; n = 0; codes = collections.Counter()
    for tr in re.findall(r'<TR\b[^>]*>(.*?)</TR>', t, re.S):
        if 'RPT_RSN' not in tr:
            continue
        attrs = re.findall(r'(?:ACODE|AUNIT)="([^"]+)"', tr)
        codes.update(set(attrs))
        rs = re.search(r'<T[DEU]\b[^>]*AUNIT="RPT_RSN"[^>]*>(.*?)</T[DEU]>', tr, re.S)
        cc = re.search(r'<T[DEU]\b[^>]*ACODE="MDF_STK_CNT"[^>]*>(.*?)</T[DEU]>', tr, re.S)
        if not rs or not cc:
            continue
        v = to_int(cc.group(1))
        if v is None:
            continue
        n += 1
        r = strip(rs.group(1))
        if '장내매수' in r:
            buy += abs(v)
        elif '장내매도' in r:
            sell -= abs(v)
    return dict(n_rows=n, net=buy + sell, buy=buy, sell=sell, attr_names=sorted(codes))


docs = [json.loads(l) for l in open(DOCS)]
rnd = random.Random(SEED)
pick = rnd.sample(range(len(docs)), N)
res = []
for k in pick:
    d = docs[k]
    b = fetch(d['rcept_no'])
    time.sleep(0.5)
    if b is None:
        res.append(dict(rcept_no=d['rcept_no'], fetch='fail')); continue
    try:
        t, enc = text_of(b)
    except Exception as e:
        res.append(dict(rcept_no=d['rcept_no'], fetch='not_zip', err=mask(e)[:80])); continue
    h = parse_header_based(t)
    a = parse_attr_based(t)
    # raw-document numbers that may matter: does a 장내매수 string occur anywhere outside detail rows?
    n_buy_str = t.count('장내매수'); n_sell_str = t.count('장내매도')
    rec = dict(rcept_no=d['rcept_no'], rcept_dt=d['rcept_dt'], enc=enc, their_parsed=d.get('parsed'), their_net=d.get('net'),
               their_buy=d.get('buy'), their_sell=d.get('sell'), their_rows=d.get('n_rows'),
               hdr_ok=h.get('ok'), hdr_net=h.get('net'), hdr_net_afr_minus_bfr=h.get('net_afr_minus_bfr'), hdr_rows=h.get('n_rows'), hdr_labels=h.get('labels'),
               attr_net=a['net'], attr_rows=a['n_rows'], attr_names=a['attr_names'],
               n_str_jangnae_buy=n_buy_str, n_str_jangnae_sell=n_sell_str)
    rec['match_hdr'] = (rec['hdr_net'] == rec['their_net'])
    rec['match_attr'] = (rec['attr_net'] == rec['their_net'])
    res.append(rec)
    print(json.dumps(rec, ensure_ascii=False), '| header labels:', h.get('headers'), flush=True)
    del t, b
summary = dict(seed=SEED, n=len(res), match_hdr=sum(1 for r in res if r.get('match_hdr')),
               match_attr=sum(1 for r in res if r.get('match_attr')),
               match_afr_minus_bfr=sum(1 for r in res if r.get('hdr_net_afr_minus_bfr') == r.get('their_net')),
               sign_match_hdr=sum(1 for r in res if r.get('hdr_net') is not None and r.get('their_net') is not None
                                  and (r['hdr_net'] > 0) - (r['hdr_net'] < 0) == (r['their_net'] > 0) - (r['their_net'] < 0)))
print(json.dumps(summary))
json.dump(dict(summary=summary, rows=res), open(OUT, 'w'), ensure_ascii=False, indent=1)
