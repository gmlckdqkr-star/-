#!/bin/bash
# PRECOMMIT_SL1 sec.3: shards until 150 done or 2026-11-04 21:00Z (ADDENDUM_SL1_B)
cd /tmp/claude-0/-home-user--/e60ac389-f078-575c-af9f-bad532fab64a/scratchpad/bt1/code
DL=$(date -d '2026-11-04 21:00:00Z' +%s)
for s in $(seq 0 149); do
  [ $(date +%s) -ge $DL ] && { echo "deadline reached before shard $s"; break; }
  [ -f /tmp/claude-0/-home-user--/e60ac389-f078-575c-af9f-bad532fab64a/scratchpad/bt1/out/sl1_shards/s$(printf %04d $s).npz ] && continue
  /root/.cache/lab/ms1-venv/bin/python -B sl1_mega.py $s $((s+1)) || echo "shard $s failed"
done
echo ALLDONE $(date -u +%H:%M:%SZ)
