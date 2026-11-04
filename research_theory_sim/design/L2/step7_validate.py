import gridrun as G, json
b=dict(hv=140,H=1.5,a0=0.03,a1=0.25,a2=1.0,a3=1.0,use_y10=1,Hr=3.0)
def v(**k):
    q=dict(b); q.update(k); return q
cfg=[v(), v(Hr=5.0), v(lw_d=2.0), v(a0=0.04,a1=0.2), v(H=2.0,a0=0.04,a1=0.2), v(hv=100), v(a2=0.0,use_y10=0,Hr=5.0),
     dict(hv=140,H=1.5,a0=0.03,a1=0.25), v(a1=0.2,Hr=5.0), v(a1=0.3,Hr=5.0), v(H=1.0,Hr=5.0), v(a2=2.0,Hr=5.0)]
rows=G.run_grid(cfg,'validate1_seeds23',seeds=(2,3))
print('N =',len(cfg)); G.show(rows,20)
json.dump(rows,open('validate1_rows.json','w'))
