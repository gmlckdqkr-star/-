import json,os,sys,urllib.request,urllib.parse,collections,re
key=os.environ['OPENDART_API_KEY']
out=sys.argv[1]
res=[]
for bg,en,cls,page in [('20010301','20010331','Y',1),('20030301','20030331','Y',1),('20080301','20080331','Y',1),('20121101','20121130','Y',1),('20141201','20141231','Y',1),('20141201','20141231','Y',2)]:
    q=dict(crtfc_key=key,bgn_de=bg,end_de=en,pblntf_ty='D',corp_cls=cls,page_no=page,page_count=100)
    u='https://opendart.fss.or.kr/api/list.json?'+urllib.parse.urlencode(q)
    req=urllib.request.Request(u,headers={'User-Agent':'research-client/1.0'})
    r=urllib.request.urlopen(req,timeout=30); b=r.read(); d=json.loads(b)
    rows=d.get('list',[])
    kinds=collections.Counter(re.sub(r'\[.*?\]','',x['report_nm']).strip() for x in rows)
    dts=sorted(x['rcept_dt'] for x in rows)
    blank=sum(1 for x in rows if not x.get('stock_code','').strip())
    print(bg,en,cls,'p',page,'http',r.status,'bytes',len(b),'status',d.get('status'),'total',d.get('total_count'),'rows',len(rows),'dt',dts[:1],dts[-1:],'blank_stock',blank)
    print('  ',dict(kinds.most_common(8)))
    for x in rows: res.append({k:x[k] for k in ('rcept_no','rcept_dt','stock_code','report_nm','corp_cls')})
json.dump(res,open(out,'w'),ensure_ascii=False)
