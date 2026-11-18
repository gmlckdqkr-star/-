import json
D=json.load(open('/mnt/project-files/research/df1/results/df6_main.json')); F=json.load(open('/mnt/project-files/research/df1/results/df6_final.json'))
C=D['configs']; G=D['gates']; idx={c['id']:c for c in C}
P={(c['V'],c['R'],c['ei'],c['ci']):(G[c['id']]['npass']==5) for c in C if c['role']=='main'}
# sensitivity (NOT pre-registered): radius 1, and 'other R' dropped
for rad in (1,2):
  for needR in (True,False):
    ok=[]
    for i in F['gpass']:
        c=idx[i]; nb=[P[(c['V'],c['R'],c['ei']+de,c['ci']+dc)] for de in range(-rad,rad+1) for dc in range(-rad,rad+1) if (de or dc) and (c['V'],c['R'],c['ei']+de,c['ci']+dc) in P]
        oth=P[(c['V'],252 if c['R']==63 else 63,c['ei'],c['ci'])]
        if len(nb)>=4 and sum(nb)>=0.75*len(nb) and (oth or not needR): ok.append((i,sum(nb),len(nb)))
    print('radius',rad,'need other R',needR,'H4-pass',len(ok), ok[:10])
# which of those also pass H1,H2,H3,H5
for i,h in F['H'].items():
    if all(h['H1'].values()) and all(h['H2'].values()) and h['H3'] and h['H5']: print('H1-3,H5 ok:', i, 'H4', h['H4'])
