import os, sys, io, zipfile, urllib.request, urllib.parse, re, json, time
K = os.environ['OPENDART_API_KEY']
def get(path, **q):
    q['crtfc_key'] = K
    u = 'https://opendart.fss.or.kr/api/' + path + '?' + urllib.parse.urlencode(q)
    try:
        return urllib.request.urlopen(u, timeout=120).read()
    except Exception as e:
        return ('ERR ' + type(e).__name__ + ' ' + str(e).replace(K, '***')).encode()
def flat_of(b):
    for enc in ('utf-8', 'euc-kr', 'cp949'):
        try:
            t = b.decode(enc); break
        except Exception:
            t = None
    if t is None: t = b.decode('cp949', 'replace'); enc = 'cp949?'
    f = re.sub(r'&nbsp;|&#160;', '', t)
    f = re.sub(r'<[^>]+>', '|', f)
    f = re.sub(r'[ \t\r\n　\xa0]+', '', f)
    return enc, t, re.sub(r'\|+', '|', f)
def num_after(f, kw, n=3):
    out = []
    for m in re.finditer(kw, f):
        seg = f[m.end(): m.end() + 120]
        nums = re.findall(r'\|\(?-?[0-9][0-9,]{3,}\)?', seg)
        if nums: out.append([x.strip('|') for x in nums[:n]])
        if len(out) >= 2: break
    return out
def doc(rc, tag):
    b = get('document.xml', rcept_no=rc)
    if b[:2] != b'PK':
        print(tag, rc, 'not zip', b[:160].decode('utf-8', 'replace')); return
    z = zipfile.ZipFile(io.BytesIO(b))
    print(tag, rc, 'zip', len(b), 'files', [(n, z.getinfo(n).file_size) for n in z.namelist()][:6])
    for n in z.namelist()[:4]:
        enc, t, f = flat_of(z.read(n))
        closed = t.rstrip().endswith('</DOCUMENT>') or '</DOCUMENT>' in t[-200:] or '</html>' in t[-200:].lower()
        print('    ', n, 'enc', enc, 'flat', len(f), 'complete', closed)
        for kw in ['자산총계', '부채총계', '자본총계', '매출액', '영업이익', '당기순이익']:
            print('        ', kw, len(re.findall(kw, f)), num_after(f, kw))
if sys.argv[1] == 'docs':
    for a in sys.argv[2:]:
        tag, rc = a.split(':'); doc(rc, tag); time.sleep(0.5)
else:
    # list periodic filings for a corp over a window
    code, b, e = sys.argv[2:5]
    j = json.loads(get('list.json', corp_code=code, bgn_de=b, end_de=e, pblntf_ty='A', page_count=100))
    print(j.get('status'), j.get('message'), j.get('total_count'))
    for x in (j.get('list') or []):
        print('  ', x['rcept_dt'], x['rcept_no'], x['corp_name'], x['report_nm'])
