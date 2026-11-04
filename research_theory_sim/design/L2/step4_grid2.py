import gridrun as G, json
bases=[dict(hv=80,H=2.0,a0=0.04,a1=0.2),dict(hv=80,H=1.0,a0=0.02,a1=0.2),dict(hv=80,H=1.0,a0=0.02,a1=0.3)]
cfg=[]
for b in bases:
    for a2 in (0.0,1.0,2.0,4.0):
        for a3 in (0.0,0.5,1.0):
            if a2==0 and a3==0: continue
            q=dict(b); q.update(a2=a2,a3=a3,use_y10=1); cfg.append(q)
rows=G.run_grid(cfg,'grid2_spread_rfgap',seeds=(1,))
print('N =',len(cfg)); G.show(rows,15)
json.dump(rows,open('grid2_rows.json','w'))
