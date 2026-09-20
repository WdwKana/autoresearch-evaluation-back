#!/usr/bin/env bash
# 只查容器与日志,不调用任何 API。stage 1 结束或满 2 小时即停容器,然后汇总。
SP=/tmp/claude-0/-root-researchclaweval-public/51dbc20a-062b-4219-ba2a-1b69cde17c93/scratchpad
RUN=$(cat $SP/current_tier); NAME=$(cat $SP/current_tier_container); LOG=$RUN/logs/native.log
t0=$(date +%s); reason="container exited on its own"
while docker ps --format '{{.Names}}' | grep -q "$NAME"; do
  if grep -qE "Stage 1_initial_implementation_1_preliminary completed|Could not find working implementation|Experiment ended|Completed PsyDefDetect BFTS|No valid implementation within" "$LOG" 2>/dev/null; then reason="stage 1 ended -> external stop"; docker stop -t 10 "$NAME" >/dev/null; break; fi
  if [ $(( $(date +%s) - t0 )) -gt 7200 ]; then reason="2h hard cap -> external stop"; docker stop -t 10 "$NAME" >/dev/null; break; fi
  sleep 10
done
sleep 15
python3 "$SP/tier/summarize_tier.py" "$RUN" "$reason"
python3 - "$RUN/state.json" "$reason" <<'PY'
import json,sys,datetime
d=json.load(open(sys.argv[1])); d.update(status="stopped",summary=d["summary"]+" | ended: "+sys.argv[2],updated_at=datetime.datetime.now(datetime.UTC).isoformat()); json.dump(d,open(sys.argv[1],"w"),indent=2)
PY
echo "containers of ours still up: $(docker ps --format '{{.Names}}' | grep -c 'control_tier')"
