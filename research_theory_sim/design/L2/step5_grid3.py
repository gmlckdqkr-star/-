import gridrun as G, json
cfg=[]
for hv in (60,100,140):
    for Hh in (1.5,2.0,3.0):
        for a0 in (0.03,0.04,0.05):
            for a1 in (0.15,0.2,0.25):
                cfg.append(dict(hv=hv,H=Hh,a0=a0,a1=a1,a2=1.0,a3=1.0,use_y10=1))
rows=G.run_grid(cfg,'grid3_refine',seeds=(1,))
print('N =',len(cfg)); G.show(rows,15)
json.dump(rows,open('grid3_rows.json','w'))
