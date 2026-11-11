import json
F = '/home/user/-/research_xv1/cand/cross.py'; out = []
def add(fam, name, func, params, names, t0=None): out.append(dict(family=fam, name=name, file=F, func=func, params=params, names=list(names), t0=t0))
CH = ['semis']
add('SBC-CAP', 'SBC_P1', 'sbc_cap', dict(N=252, Lr=3.0), [])
add('SBC-CAP', 'SBC_P2', 'sbc_cap', dict(N=252, Lr=2.0), [])
add('SBC-CAP', 'SBC_P3', 'sbc_cap', dict(N=504, Lr=3.0), [])
add('SBC-CAP', 'SBC_P4', 'sbc_cap', dict(N=126, Lr=3.0), [])
add('SBC-CAP', 'SBC_P5', 'sbc_cap', dict(N=252, Lr=3.0, chip=True), CH)
add('SBC-CAP', 'SBC_P6', 'sbc_cap', dict(N=252, Lr=3.0, always=True), [])
CL = ['ret:SOXL', 'semis']
for i, (D, a, H, lead) in enumerate([(0.40, 1/3, 252, True), (0.40, 1/2, 252, True), (0.30, 1/3, 252, True), (0.50, 1/3, 252, True), (0.40, 1/3, 504, True), (0.40, 1/3, 252, False)], 1):
    add('CHIP-LEAD-12M', 'CHIP_P%d' % i, 'chip_lead', dict(D=D, a=a, H=H, lead=lead), CL)
T0H = '1986-10-31'   # first row on which kappa(252 valid days) exists
add('Gated TMF fill', 'TMF_P1', 'tmf_fill', dict(veh='TMF', cap=1.0), ['ret:TMF', 'ret:TLT'], T0H)
add('Gated TMF fill', 'TMF_P2', 'tmf_fill', dict(veh='TMF', cap=0.5), ['ret:TMF', 'ret:TLT'], T0H)
add('Gated TMF fill', 'TMF_P3', 'tmf_fill', dict(veh='TLT', cap=1.0), ['ret:TLT'], T0H)
add('Gated TMF fill', 'TMF_P4', 'tmf_fill', dict(veh='TMF', cap=1.0, useH=False), ['ret:TMF', 'ret:TLT'])
add('Gated TMF fill', 'TMF_P5', 'tmf_fill', dict(veh='TMF', cap=1.0, useE=True), ['ret:TMF', 'ret:TLT'], T0H)
add('Gated TMF fill', 'TMF_P6', 'tmf_fill', dict(veh='TLT', cap=1.0, useH=False), ['ret:TLT'])
for nm, (D, c, m, w) in dict(S1=(0.35, True, 0, .15), S2=(0.50, True, 0, .15), S3=(0.35, False, 0, .15), S4=(0.50, False, 0, .15), S5=(0.35, True, 1, .10), S6=(0.50, True, 1, .10)).items():
    add('SOXL crash-rebound sleeve', 'SOXLSL_' + nm, 'soxl_sleeve', dict(D=D, confirm=c, mode=m, w=w), CL)
CAL = ['cal:month', 'cal:dom', 'cal:dow', 'cal:ymod4']
add('MIDTERM-ADD', 'MID_P1', 'midterm_add', dict(), CAL + ['ret:TQQQ'])
add('MIDTERM-ADD', 'MID_P2', 'midterm_add', dict(vcap=False), CAL + ['ret:TQQQ'])
add('MIDTERM-ADD', 'MID_P3', 'midterm_add', dict(start='election'), CAL + ['ret:TQQQ'])
add('MIDTERM-ADD', 'MID_P4', 'midterm_add', dict(phi=0.5), CAL + ['ret:TQQQ'])
add('MIDTERM-ADD', 'MID_P5', 'midterm_add', dict(end='apr'), CAL + ['ret:TQQQ'])
add('MIDTERM-ADD', 'MID_P6', 'midterm_add', dict(veh='QLD'), CAL + ['ret:QLD'])
json.dump(out, open('/home/user/-/research_xv1/cand/cross.configs.json', 'w'), indent=1); print(len(out))
