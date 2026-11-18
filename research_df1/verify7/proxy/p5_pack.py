"""verify7/proxy: merge the three intermediate JSONs (p1, p2, p3 in /tmp/df7v_proxy) into verify7/proxy/proxy.json. Run p1, p2, p3 first."""
import json
o = {}
for k, f in (('audit', 'proxy_audit.json'), ('sens', 'proxy_sens.json'), ('lag', 'proxy_lag.json')):
    o[k] = json.load(open('/tmp/df7v_proxy/' + f))
o['note'] = 'all numbers <=2014-12-31; AQR from tsmom_monthly_le2014.csv only; fee model = estimate (2% mgmt + 20% perf, monthly HWM, optional T-bill hurdle, optional 1%/yr trading cost)'
json.dump(o, open('/mnt/project-files/research/df1/verify7/proxy/proxy.json', 'w'), indent=1, default=str)
print('ok', list(o))
