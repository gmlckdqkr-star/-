#!/bin/bash
# TS1 freeze: hash every design file + protocol, copy to the repo, commit + push BEFORE any real-data run of the rules.
set -e
TS=/mnt/project-files/research/theory_sim; REPO=/home/user/-; DST=$REPO/research_theory_sim
NOW=$(date -u +%Y-%m-%dT%H:%MZ)
cd $TS
find design common -type f ! -name '*.pyc' ! -path '*/__pycache__/*' | sort > /tmp/ts1_files.txt
{ echo "TS1 FREEZE $NOW (before any real-data run of the lane rules)"; echo "primary: $1";
  sha256sum DESIGN_BRIEF.md TEST_PROTOCOL.md; xargs -a /tmp/ts1_files.txt sha256sum; } > FREEZE_TS1.txt
mkdir -p $DST; tar --exclude="__pycache__" --exclude="*.pyc" -cf - design common | (cd $DST && tar -xf -)
cp FREEZE_TS1.txt DESIGN_BRIEF.md TEST_PROTOCOL.md $DST/
cp test/harness.py test/post2014.py test/freeze.sh $DST/test/ 2>/dev/null || { mkdir -p $DST/test; cp test/harness.py test/post2014.py test/freeze.sh $DST/test/; }
cd $REPO && git add research_theory_sim && git commit -q -m "TS1 freeze: blind lane rules + tournament choice ($1) hashed before the real-history test

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014mak2FNrX83Uuj2xt9J62F" && git push -q origin claude/project-thread-hhwozh && git log --oneline | head -1
echo "frozen at $NOW"; wc -l $TS/FREEZE_TS1.txt
