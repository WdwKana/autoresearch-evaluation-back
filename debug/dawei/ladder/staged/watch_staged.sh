#!/usr/bin/env bash
# 只查容器与日志。stage 3 结束(或 stage 4 出现)或 4 小时上限即停容器,然后按阶段汇总。
SP=/tmp/claude-0/-root-researchclaweval-public/51dbc20a-062b-4219-ba2a-1b69cde17c93/scratchpad
RUN=$(cat $SP/current_staged); NAME=$(cat $SP/current_staged_container); LOG=$RUN/logs/native.log
t0=$(date +%s); reason="container exited on its own"
while docker ps --format '{{.Names}}' | grep -q "$NAME"; do
  if grep -qE "Stage 3_[a-z_0-9]* completed|Current Main Stage: ablation|stage_4_|Could not find working implementation" "$LOG" 2>/dev/null; then reason="stage 3 ended / stage 4 reached -> external stop"; docker stop -t 10 "$NAME" >/dev/null; break; fi
  if [ $(( $(date +%s) - t0 )) -gt 14400 ]; then reason="4h hard cap -> external stop"; docker stop -t 10 "$NAME" >/dev/null; break; fi
  sleep 15
done
sleep 15
python3 "$SP/staged/summarize_staged.py" "$RUN" "$reason"
python3 - "$RUN/state.json" "$reason" <<'PY'
import json,sys,datetime
d=json.load(open(sys.argv[1])); d.update(status="stopped",summary=d["summary"]+" | ended: "+sys.argv[2],updated_at=datetime.datetime.now(datetime.UTC).isoformat()); json.dump(d,open(sys.argv[1],"w"),indent=2)
PY
