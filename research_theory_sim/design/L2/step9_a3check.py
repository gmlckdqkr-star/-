# pre-stated decision (written before running): drop a3 if J(a3=0) >= J(a3=1) - 0.0005 on seeds 1-3
import gridrun as G, json
cfg=[dict(hv=140,H=1.5,a0=0.03,a1=0.2,a2=0.0,a3=0.0,Hr=5.0,use_y10=0)]
rows=G.run_grid(cfg,'select_a3_check_seeds123',seeds=(1,2,3))
G.show(rows)
json.dump(rows,open('select_a3_rows.json','w'))
