#!/bin/bash
# TS2 freeze: hash every round-2 design file + brief + protocol + engine + test code, copy to the repo, commit + push
# BEFORE any real-data run of the round-2 rules. Usage: freeze_r2.sh <PRIMARY lane id>
set -e
TS=/mnt/project-files/research/theory_sim; R2=$TS/r2; REPO=/home/user/-; DST=$REPO/research_theory_sim/r2
NOW=$(date -u +%Y-%m-%dT%H:%MZ); LIST=/root/.cache/ts2_files.txt; BIG=/root/.cache/ts2_big.txt
cd $R2
find design -type f ! -name '*.pyc' ! -path '*/__pycache__/*' | sort > $LIST
find design -type f ! -name '*.pyc' ! -path '*/__pycache__/*' -size +5M | sort > $BIG
{ echo "TS2 FREEZE $NOW (before any real-data run of the round-2 lane rules)"; echo "primary: $1";
  sha256sum DESIGN_BRIEF_R2.md TEST_PROTOCOL_R2.md test/harness_r2.py test/post2014_r2.py test/freeze_r2.sh;
  (cd $TS && sha256sum common/exec_engine.py design/L1/rule.py);
  xargs -a $LIST sha256sum;
  echo "not copied to git (over 5 MB, hashed above):"; cat $BIG; } > FREEZE_TS2.txt
mkdir -p $DST/test
tar --exclude="__pycache__" --exclude="*.pyc" -X $BIG -cf - design | (cd $DST && tar -xf -)
cp FREEZE_TS2.txt DESIGN_BRIEF_R2.md TEST_PROTOCOL_R2.md $DST/
cp test/harness_r2.py test/post2014_r2.py test/freeze_r2.sh $DST/test/
cd $REPO && git add research_theory_sim/r2 && git commit -q -F - <<EOF
TS2 freeze: round-2 blind lane rules + tournament choice ($1) hashed before the real-history test

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014mak2FNrX83Uuj2xt9J62F
EOF
for i in 1 2 3 4; do git push -q origin claude/project-thread-hhwozh && break || sleep $((2**i)); done
git log --oneline | head -1
echo "frozen at $NOW"; wc -l $R2/FREEZE_TS2.txt
