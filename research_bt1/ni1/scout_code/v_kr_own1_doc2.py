import os,urllib.request,zipfile,io,re
key=os.environ['OPENDART_API_KEY']
for rn in ['20010331000214','20010330001214']:
    b=urllib.request.urlopen(urllib.request.Request('https://opendart.fss.or.kr/api/document.xml?crtfc_key=%s&rcept_no=%s'%(key,rn),headers={'User-Agent':'research-client/1.0'}),timeout=30).read()
    z=zipfile.ZipFile(io.BytesIO(b)); print(z.namelist()); raw=z.read(z.namelist()[0])
    t=raw.decode('cp949',errors='replace'); txt=re.sub(r'<[^>]+>',' ',t); txt=re.sub(r'\s+',' ',txt)
    print(len(txt)); 
    # mask hangul names: print only section headers and digits pattern
    print(re.findall(r'(변동|취득|처분|매수|매도|사유|일자|소유|주식수|비율|장내|장외)',txt)[:40])
    print(re.sub(r'[가-힣]{2,4}(?= )', lambda m: m.group(0) if m.group(0) in ('변동','취득','처분','사유','주식','보통주','합계','변동일','증감','장내매수','장내매도') else '#', txt)[:900])
