# NI1-A: parse 세부변동내역 of an insider ownership report (document.xml). No names are returned.
import re, zipfile, io

TR = re.compile(r'<TR\b[^>]*>(.*?)</TR>', re.S)
CELL = re.compile(r'<(T[DUEH])\b([^>]*)>(.*?)</\1>', re.S)
TAG = re.compile(r'<[^>]+>')


def decode(raw):
    for enc in ('cp949', 'utf-8'):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return raw.decode('cp949', errors='replace'), 'cp949-replace'


def unzip(b):
    z = zipfile.ZipFile(io.BytesIO(b))
    names = z.namelist()
    return z.read(names[0]), len(names)


def num(s):
    s = TAG.sub('', s).replace(',', '').replace(' ', '').replace('\xa0', '')
    m = re.search(r'[-+]?\d+', s)
    return int(m.group(0)) if m else None


def parse(text):
    """returns dict(parsed, n_rows, buy, sell, net, reasons) with buy>=0, sell<=0."""
    out = dict(parsed=False, n_rows=0, buy=0, sell=0, net=0, reasons={}, has_section='세부변동내역' in text)
    for tr in TR.findall(text):
        if 'RPT_RSN' not in tr:
            continue
        rsn = None; cnt = None
        for tag, attrs, inner in CELL.findall(tr):
            if 'AUNIT="RPT_RSN"' in attrs and rsn is None:
                rsn = re.sub(r'\s+', '', TAG.sub('', inner))
            if 'ACODE="MDF_STK_CNT"' in attrs and cnt is None:
                cnt = num(inner)
        if rsn is None or cnt is None:
            continue
        out['n_rows'] += 1
        key = '장내매수' if '장내매수' in rsn else ('장내매도' if '장내매도' in rsn else 'other')
        out['reasons'][key] = out['reasons'].get(key, 0) + 1
        if key == '장내매수':
            out['buy'] += abs(cnt)
        elif key == '장내매도':
            out['sell'] -= abs(cnt)
    out['parsed'] = out['n_rows'] > 0
    out['net'] = out['buy'] + out['sell']
    return out
