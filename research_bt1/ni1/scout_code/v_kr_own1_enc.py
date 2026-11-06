import os,json,urllib.request,urllib.parse,zipfile,io,re,sys
key=os.environ['OPENDART_API_KEY']
H={'User-Agent':'research-client/1.0'}
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=30).read()
out=[]
for ym in ['200106','200112','200206','200212','200306','200406','200506','200606']:
    q=dict(crtfc_key=key,bgn_de=ym+'01',end_de=ym+'28',pblntf_ty='D',corp_cls='Y',page_no=1,page_count=100)
    d=json.loads(get('https://opendart.fss.or.kr/api/list.json?'+urllib.parse.urlencode(q)))
    rows=[r for r in d.get('list',[]) if '임원' in r['report_nm'] and '정정' not in r['report_nm']][:3]
    res=[]
    for r in rows:
        b=get('https://opendart.fss.or.kr/api/document.xml?crtfc_key=%s&rcept_no=%s'%(key,r['rcept_no']))
        z=zipfile.ZipFile(io.BytesIO(b)); raw=z.read(z.namelist()[0])
        bad=raw.count('占쏙옙'.encode('utf-8'))+raw.count(b'\xef\xbf\xbd')
        try: t=raw.decode('cp949'); enc='cp949'
        except: t=raw.decode('utf-8','replace'); enc='utf8'
        ok='장내매수' in t or '장내매도' in t or '보고사유' in t or '변동사유' in t
        ver=re.search(r'(\d\.\d)\s', re.sub('<[^>]+>',' ',t)[:300])
        res.append(dict(rn=r['rcept_no'],enc=enc,mojibake=bad,readable_kw=ok,buy='장내매수' in t,sell='장내매도' in t))
    print(ym,'total',d.get('total_count'),res)
    out.append(dict(ym=ym,total=d.get('total_count'),docs=res))
json.dump(out,open(sys.argv[1],'w'),ensure_ascii=False,indent=1)
