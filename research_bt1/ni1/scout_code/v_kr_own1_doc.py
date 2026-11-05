import json,os,sys,urllib.request,zipfile,io,re,collections
key=os.environ['OPENDART_API_KEY']
rows=json.load(open(sys.argv[1]))
pick=[]
for pref in ('2001','2003','2008','2012','2014'):
    c=[r for r in rows if r['rcept_dt'].startswith(pref) and '임원' in r['report_nm'] and '정정' not in r['report_nm']]
    pick+=c[:2]
summ=[]
for r in pick:
    u='https://opendart.fss.or.kr/api/document.xml?crtfc_key=%s&rcept_no=%s'%(key,r['rcept_no'])
    resp=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'research-client/1.0'}),timeout=30)
    b=resp.read()
    try:
        z=zipfile.ZipFile(io.BytesIO(b)); raw=z.read(z.namelist()[0])
    except Exception as e:
        print(r['rcept_no'],'notzip',b[:200]); continue
    for enc in ('utf-8','cp949'):
        try: t=raw.decode(enc); break
        except: t=None
    txt=re.sub(r'<[^>]+>',' ',t); txt=re.sub(r'\s+',' ',txt)
    reasons=collections.Counter(re.findall(r'(장내매수|장내매도|신규보고|신규선임|증여|상속|유상신주취득|무상신주취득|시간외매매|장외매수|장외매도|주식매수선택권|전환|신규상장)',txt))
    dates=re.findall(r'(\d{4})[.년\-/ ]\s?(\d{1,2})[.월\-/ ]\s?(\d{1,2})',txt)
    # report obligation date vs rcept_dt lag: find 변동일 dates within the 세부변동내역 section
    sec=txt.split('세부변동내역')[1] if '세부변동내역' in txt else ''
    sdates=sorted(set('%s%02d%02d'%(a,int(b_),int(c)) for a,b_,c in re.findall(r'(\d{4})[.년\-/]\s?(\d{1,2})[.월\-/]\s?(\d{1,2})',sec[:4000])))
    s=dict(rcept_no=r['rcept_no'],rcept_dt=r['rcept_dt'],http=resp.status,zip_bytes=len(b),enc=enc,has_detail='세부변동내역' in txt,reasons=dict(reasons),detail_dates=sdates[:6])
    print(s); summ.append(s)
json.dump(summ,open(sys.argv[2],'w'),ensure_ascii=False,indent=1)
