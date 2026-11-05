import sys,collections
d=sys.argv[1]
cmh="CMTE_ID,CMTE_NM,TRES_NM,CMTE_ST1,CMTE_ST2,CMTE_CITY,CMTE_ST,CMTE_ZIP,CMTE_DSGN,CMTE_TP,CMTE_PTY_AFFILIATION,CMTE_FILING_FREQ,ORG_TP,CONNECTED_ORG_NM,CAND_ID".split(',')
ph="CMTE_ID,AMNDT_IND,RPT_TP,TRANSACTION_PGI,IMAGE_NUM,TRANSACTION_TP,ENTITY_TP,NAME,CITY,STATE,ZIP_CODE,EMPLOYER,OCCUPATION,TRANSACTION_DT,TRANSACTION_AMT,OTHER_ID,CAND_ID,TRAN_ID,FILE_NUM,MEMO_CD,MEMO_TEXT,SUB_ID".split(',')
cm={}
for l in open(d+'/cm.txt',encoding='latin-1'):
    f=l.rstrip('\n').split('|'); r=dict(zip(cmh,f)); r.pop('TRES_NM',None); cm[r['CMTE_ID']]=r
corp={k:v for k,v in cm.items() if v['ORG_TP'] in ('C','W')}
print('cm',len(cm),'corp',len(corp),'corp w/ connected org',sum(1 for v in corp.values() if v['CONNECTED_ORG_NM'].strip()))
n=0;nc=0;dates=[];am=collections.Counter();tt=collections.Counter();rpt=collections.Counter();img=collections.Counter();cands=collections.defaultdict(set);lagd=[]
import datetime
for l in open(d+'/itpas2.txt',encoding='latin-1'):
    f=l.rstrip('\n').split('|'); r=dict(zip(ph,f)); n+=1
    if r['CMTE_ID'] not in corp: continue
    nc+=1; am[r['AMNDT_IND']]+=1; tt[r['TRANSACTION_TP']]+=1; rpt[r['RPT_TP']]+=1
    dt=r['TRANSACTION_DT']
    if len(dt)==8:
        try:
            t=datetime.date(int(dt[4:]),int(dt[:2]),int(dt[2:4])); dates.append(t)
            im=r['IMAGE_NUM']
            if len(im)>=6:
                s=datetime.date(1900+int(im[:2]) if int(im[:2])>50 else 2000+int(im[:2]),int(im[2:4]),int(im[4:6]))
                lagd.append((s-t).days)
        except Exception: img['bad']+=1
    cands[r['CMTE_ID']].add(r['CAND_ID'])
print('rows',n,'corp rows',nc); print('amnd',am.most_common()); print('tp',tt.most_common(6)); print('rpt',rpt.most_common(12))
dates.sort(); print('date min/max',dates[0],dates[-1],'p1/p99',dates[len(dates)//100],dates[-len(dates)//100])
lagd.sort(); L=len(lagd); print('imgdate-txdate lag days n',L,'p5,p50,p90,p99',[lagd[int(L*q)] for q in (.05,.5,.9,.99)],'neg share',sum(x<0 for x in lagd)/L, img)
b=sorted(len(s) for s in cands.values()); print('pacs giving',len(b),'breadth median',b[len(b)//2],'p90',b[int(len(b)*.9)],'max',b[-1])
top=sorted(cands.items(),key=lambda x:-len(x[1]))[:15]
for k,s in top: print(len(s),cm[k]['CMTE_NM'],'|',cm[k]['CONNECTED_ORG_NM'])
