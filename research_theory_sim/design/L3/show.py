import sys, json, glob
pat = sys.argv[1] if len(sys.argv) > 1 else 'runs_stage1_*.jsonl'
n = int(sys.argv[2]) if len(sys.argv) > 2 else 25
rows = []
for f in glob.glob('/mnt/project-files/research/theory_sim/design/L3/' + pat):
    rows += [json.loads(l) for l in open(f)]
rows.sort(key=lambda r: -r['J'])
print('N rows', len(rows))
for r in rows[:n]:
    print({k: v for k, v in r.items() if k not in ('on_dd80', 'off_dd80', 'on_p10', 'off_p10')})
