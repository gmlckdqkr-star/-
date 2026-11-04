"""Parity: lab example stk_lowvol_top50 through w3lib.evaluate (lab compile_targets -> same engine calls) vs the lab
README example numbers (MS1 9.2%). Not a hypothesis (N not counted)."""
import sys, json, yaml
sys.path.insert(0, '/mnt/project-files/research/multi_cand/w3_stock_new/code')
import w3lib as w
from lab import stocks, dsl
spec = dsl.check_spec(yaml.safe_load(open('/mnt/project-files/research/lab/specs/examples/stk_lowvol_top50.yaml')))
P = w.panel(); tg = stocks.compile_targets(spec, P)
ev, S, sh = w.evaluate(P, tg, 'parity_lowvol50', null=False)
out = dict(cons=ev['cons_cagr_at'], sharpe=ev['sharpe_pretax'], ms1_path=ev['ms1']['dev250_path']['cagr'])
lab = stocks.evaluate(spec, P, null=False, pit=False)['windows']['w86']
out.update(lab_cons=lab['cons']['cagr_at'], lab_sharpe=lab['sharpe'])
json.dump(out, open(f'{w.W3}/results/parity_lowvol50.json', 'w'), indent=1); print(out)
