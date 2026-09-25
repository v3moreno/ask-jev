#!/usr/bin/env bash
# Smoke suite: opencode headless enforcing jev via AGENTS.md.
#   ./run.sh [model]          # default: configured default (gpt-6-luna)
# Writes /tmp/jev-smoke-<test>.out and prints a per-test summary.
set -uo pipefail
cd "$(dirname "$0")"
MODEL="${1:-}"

declare -A TESTS=(
  [t1-filter]="Which files in ./docs/ are relevant to: what did my ISP say about the charge? List filenames only."
  [t2-summarize]="Summarize my ISP email in two sentences."
  [t3-draft]="Draft a short reply to my ISP confirming I received their message about the refund."
  [t4-lookup]="Do I have a flight coming up? Give me the dates and booking ref."
  [t5-triage]="Triage ./docs/*.txt: for each file, one line saying what kind of message it is."
  [t6-nodoc]="Is Pluto a planet? One sentence."
)

printf "%-14s %7s %6s  %s\n" test wall jev-calls answer
for t in t1-filter t2-summarize t3-draft t4-lookup t5-triage t6-nodoc; do
  f=/tmp/jev-smoke-$t.out
  t0=$EPOCHSECONDS
  timeout 300 opencode run ${MODEL:+--model "$MODEL"} "${TESTS[$t]}" >"$f" 2>&1
  t1=$EPOCHSECONDS
  calls=$(grep -o 'ask-jev\|jev_' "$f" | sort | uniq -c | tr '\n' ' ')
  tail=$(tail -c 400 "$f" | tr '\n' ' ')
  printf "%-14s %6ds %6s  %s\n" "$t" "$((t1 - t0))" "$calls" "${tail:0:120}"
done
