"""OV1-E step 4: v1-combined rule through ov1lib.measure2 (run ONLY if early AND unseen type-A tests passed).
dev250_path (HEADLINE): TED* path-rebuilt with L.path_series on the dev250 calendar, then x / q90 / ON along each path row.
dev250_glued (upper bound only): ON of each source date (master-calendar ON) gathered onto the path.
real bases: master-calendar ON (identical to the kill test); SPX before 1976-03-31 undefined -> v1 ('not covered')."""
import sys, os, json, hashlib, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/lanes/OV1-E/code'); sys.path.insert(0, '/mnt/project-files/research/ov1/code')
import ov1lib as L, sig_e  # noqa
LANE = '/mnt/project-files/research/ov1/lanes/OV1-E/'
SHA = hashlib.sha256(open(LANE + 'PRECOMMIT.md', 'rb').read()).hexdigest()
assert SHA.startswith('e2a080f6ce9b1dd4'), SHA
assert hashlib.sha256(open(LANE + 'code/sig_e.py', 'rb').read()).hexdigest().startswith('39a9d9aa52d0eadf')
e = json.load(open(LANE + 'results/killA_early.json')); u = json.load(open(LANE + 'results/killA_unseen.json'))
assert e['early_pass'] is True and u['unseen_pass'] is True, 'kill test not passed in both windows'
FAM = 2; DEFL = (1 + np.log(FAM)) ** .5
MCAL = sig_e.master_cal(); TED = sig_e.ted_star(MCAL); ON_M = sig_e.on_series(TED)[0]
INFO = {}

def make2(c, bn):
    B = L.v1_B(c); bfn, bp, fs = L.v1_parts(c)
    if bn == 'dev250_path':
        A = L.path_series(TED, bn); on = sig_e.on_rows(A)[0]
    else:
        on = L.gather(ON_M.astype(float), bn) > 0.5
    Bn = sig_e.overlay(B, on)
    W = L.ov.WARM
    INFO[bn] = dict(on_share_days=float(on[:, W:].mean()), cut_share_days=float(((B == 3) & on)[:, W:].mean()),
                    v1_3x_share=float((B == 3)[:, W:].mean()), undefined_share=None)
    if bn == 'dev250_path':
        q = sig_e.on_rows(A[:1])[2]; INFO[bn]['first_defined_pos_row0'] = int(np.argmax(~np.isnan(q[0])))
    return Bn, bfn, bp, fs

T = L.measure2('OV1-E_ted_cut', make2)
H, R = T['HEADLINE_MS1'], T['REAL_NDX']
spx = T['real_spx_55_85']
final = bool(H > 0.1616 and R > 0.3108 and T['dev250_path']['pw_vs_s085'] >= 0.55 and spx['cagr'] >= spx['ref_s085'] - 0.01)
out = dict(precommit_sha256=SHA, rows={k: v for k, v in T.items() if isinstance(v, dict)}, HEADLINE_MS1=H, REAL_NDX=R,
           BEATS_V1_BOTH=T['BEATS_V1_BOTH'], FINAL_PASS=final, info=INFO,
           deflation=dict(family_N=FAM, factor=DEFL, headline_deflated=0.1616 + (H - 0.1616) / DEFL, real_deflated=0.3108 + (R - 0.3108) / DEFL),
           glued_note='dev250_glued is an upper bound only')
print(json.dumps({k: v for k, v in out.items() if k != 'rows'}, indent=1))
json.dump(out, open(LANE + 'results/measure2.json', 'w'), indent=1)
with open(LANE + 'ledger.csv', 'a') as f:
    for bn, r in out['rows'].items():
        for k in ('cagr', 'd_vs_s085', 'pw_vs_s085'):
            f.write('OV1-E,ted63_p90_1260,ms1:%s,%s,%s\n' % (bn, k, r[k]))
    f.write('OV1-E,ted63_p90_1260,ms1,FINAL_PASS,%s\n' % final)
