#!/bin/bash
# XV1 self-tests on a frozen read-only copy of research_xv1, under the registered environment.
# Test worlds only: nothing after 2014 is read. Never run the tests from files that are being edited.
# usage:   selftest.sh <frozen copy of research_xv1> <log folder> <scratch folder under /tmp, not yet existing>
# example: cp -r research_xv1 /tmp/xv1_frozen && chmod -R a-w /tmp/xv1_frozen && bash research_xv1/tools/selftest.sh /tmp/xv1_frozen /tmp/xv1_logs /tmp/xv1_scratch
# pass:    every line of <log folder>/summary.txt ends in "exit 0", and the logs show EXPECTED VERDICTS OK, GUARDS OK, DRY RUN ... PASS
set -u
C="$1/code"; L="$2"; S="$3"; mkdir -p "$L" /home/claude/pyc_xv1_reg /home/claude/nbcache_xv1_reg
cd /home/user
PY="$HOME/.cache/lab/ms1-venv/bin/python -B"
export NUMBA_CACHE_DIR=/home/claude/nbcache_xv1_reg PYTHONHASHSEED=0 NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR" OPENBLAS_CORETYPE=HASWELL OPENBLAS_NUM_THREADS=1 PYTHONPYCACHEPREFIX=/home/claude/pyc_xv1_reg
run() { n=$(echo "$1" | cut -d' ' -f1 | sed 's/\.py//'); s=$(date +%s); $PY $C/$1 > "$L/$n.log" 2>&1; echo "$n exit $? $(( $(date +%s) - s ))s" >> "$L/summary.txt"; }
( run "t_g3_synth.py ${S}_g3" ) &
run "t_xeng_parity.py"; run "t_design_acct.py"; run "m_checks.py --dry2014"; run "t_batch_dry.py ${S}_dry"; run "t_old_end.py"
wait
cat "$L/summary.txt"; grep -h "EXPECTED VERDICTS\|GUARDS \|DRY RUN" "$L"/*.log
