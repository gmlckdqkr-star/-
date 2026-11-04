import gridrun as G, json, harness as H
cfg=[]
for a1 in (0.2,0.25):
    cfg.append(dict(hv=140,H=1.5,a0=0.03,a1=a1,a2=1.0,a3=1.0,Hr=5.0,use_y10=1))
    cfg.append(dict(hv=140,H=1.5,a0=0.03,a1=a1,a2=0.0,a3=1.0,Hr=5.0,use_y10=0))
rows=G.run_grid(cfg,'select_seeds123',seeds=(1,2,3))
print('N =',len(cfg)); G.show(rows,10)
json.dump(rows,open('select_rows.json','w'))
print('holds ON seeds123',H.holds((1,2,3),1000,True)); print('holds OFF seeds123',H.holds((1,2,3),1000,False))
