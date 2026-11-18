import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, px1lib as PX
for bn in DC.SEL:
    m=DC.market(bn); c=m['ctx']
    for vc in (.35,.45):
        mm=dict(m); mm['st_v1']=PX.signal(c,('F1',3,vc,'alarm','shock6m',200,.02))
        a=DC.target(m,'v1',0.1,1.0); b=DC.target(mm,'v1',0.1,1.0)
        print(bn, vc, 'state cells changed', int((mm['st_v1']!=m['st_v1']).sum()), 'target max |diff|', float(np.abs(a-b).max()))
