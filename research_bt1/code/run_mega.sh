#!/bin/bash
# runs shards until 150 done or deadline 2026-11-05 02:00Z (ADDENDUM_BT1_1 sec.2)
cd /tmp/claude-0/-home-user--/e60ac389-f078-575c-af9f-bad532fab64a/scratchpad/bt1/code
DL=$(date -d '2026-11-05 02:00:00Z' +%s)
for s in $(seq 0 149); do
  [ $(date +%s) -ge $DL ] && { echo "deadline reached before shard $s"; break; }
  [ -f /tmp/claude-0/-home-user--/e60ac389-f078-575c-af9f-bad532fab64a/scratchpad/bt1/out/shards/s$(printf %04d $s).npz ] && continue
  /root/.cache/lab/ms1-venv/bin/python -B bt1_mega.py $s $((s+1)) || echo "shard $s failed"
done
echo ALLDONE $(date -u +%H:%M:%SZ)
