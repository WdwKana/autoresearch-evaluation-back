#!/usr/bin/env bash
# 顺序跑某一档的 N 发;任何时刻只有一个容器。用法: run_tier.sh <档> <发数>
SP=/tmp/claude-0/-root-researchclaweval-public/51dbc20a-062b-4219-ba2a-1b69cde17c93/scratchpad
TIER=$1; N=$2
for rep in $(seq 1 $N); do
  if docker ps --format '{{.Names}}' | grep -qE "control_tier|control_native02"; then echo "ABORT: a control container is already running"; exit 1; fi
  prev=$(cat $SP/current_tier 2>/dev/null)
  nohup bash $SP/tier/launch_tier.sh $TIER $rep > $SP/launch_tier${TIER}_rep${rep}.nohup 2>&1 &
  lp=$!
  for i in $(seq 1 90); do [ "$(cat $SP/current_tier 2>/dev/null)" != "$prev" ] && break; sleep 2; done
  sleep 30
  echo "################ TIER $TIER REP $rep"
  bash $SP/tier/watch_tier.sh
  wait $lp 2>/dev/null; sleep 5
done
echo "TIER_${TIER}_DONE; containers of ours still up: $(docker ps --format '{{.Names}}' | grep -c control_tier)"
