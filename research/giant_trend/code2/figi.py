"""CUSIP -> ticker via OpenFIGI public mapping API (no key: 25 req/min, 10 ids/req). Resumable."""
import json, time, os, urllib.request, urllib.error
R = '/mnt/project-files/research/giant_trend/results2/'
cus = json.load(open(R + 'cusips.json')); fn = R + 'figi_map.json'
mp = json.load(open(fn)) if os.path.exists(fn) else {}
todo = [c for c in cus if c not in mp]
for i in range(0, len(todo), 10):
    batch = todo[i:i + 10]; body = json.dumps([{'idType': 'ID_CUSIP', 'idValue': c} for c in batch]).encode(); res = None
    for k in range(6):
        t0 = time.time()
        try:
            req = urllib.request.Request('https://api.openfigi.com/v3/mapping', data=body, headers={'Content-Type': 'application/json'})
            resp = urllib.request.urlopen(req, timeout=30); res = json.loads(resp.read())
            rem = int(resp.headers.get('ratelimit-remaining', 5)); rst = int(resp.headers.get('ratelimit-reset', 5))
            if rem <= 1: time.sleep(rst + 1)
            break
        except urllib.error.HTTPError as e:
            print('http', e.code, flush=True); time.sleep(int(e.headers.get('ratelimit-reset', 20) or 20) + 1)
        except Exception as e:
            print('err', repr(e)[:80], round(time.time() - t0, 1), flush=True); time.sleep(5)
    if res is None: continue
    for c, r in zip(batch, res):
        d = r.get('data') or []; us = [x for x in d if x.get('exchCode') == 'US'] or d
        mp[c] = [us[0].get('ticker'), us[0].get('name'), us[0].get('securityType')] if us else None
    if (i // 10) % 20 == 0: json.dump(mp, open(fn, 'w')); print(i, len(mp), time.strftime('%H:%M:%S'), flush=True)
json.dump(mp, open(fn, 'w')); print('done', len(mp), sum(1 for v in mp.values() if v))
