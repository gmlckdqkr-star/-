import gridrun as G, json
base=dict(hv=140,H=1.5,a0=0.03,a1=0.25,a2=1.0,a3=1.0,use_y10=1)
cfg=[]
for lw_c in (0.0,1.0,3.0):
    for lw_d in (0.0,2.0,5.0):
        if lw_c==0 and lw_d==0: continue
        q=dict(base); q.update(lw_c=lw_c,lw_d=lw_d); cfg.append(q)
for hv in (200,300):
    q=dict(base); q.update(hv=hv); cfg.append(q)
q=dict(base); q.update(demean=1); cfg.append(q)
q=dict(base); q.update(demean=1,a0=0.04); cfg.append(q)
for Hr in (1.5,6.0):
    q=dict(base); q.update(Hr=Hr); cfg.append(q)
for a3 in (2.0,):
    q=dict(base); q.update(a3=a3); cfg.append(q)
for vf in (0.0025,0.01):
    q=dict(base); q.update(vfloor=vf); cfg.append(q)
rows=G.run_grid(cfg,'grid4_ledger_weights_misc',seeds=(1,))
print('N =',len(cfg)); G.show(rows,25)
json.dump(rows,open('grid4_rows.json','w'))
