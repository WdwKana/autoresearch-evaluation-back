#!/usr/bin/env bash
set -euo pipefail

ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
RUN_ID="${REAL_EVAL_RUN_ID:-systemd-gave2-fullrun-finalizer-$(date +%Y%m%d-%H%M%S)}"
LOG_ROOT="${REAL_EVAL_SYSTEMD_LOG_ROOT:-$ROOT/real_eval/systemd_runs/$RUN_ID}"
LOG_FILE="$LOG_ROOT/run.log"
STATE_FILE="$LOG_ROOT/state.json"
SUMMARY_FILE="$LOG_ROOT/summary.txt"
PROMPT_FILE="${REAL_EVAL_PROMPT_FILE:-$ROOT/real_eval/prompts/gave2_fullrun_finalizer_systemd_prompt.md}"
CHILD_SUMMARY="$LOG_ROOT/child_summary.md"
HERMES_BIN="${HERMES_BIN:-/home/guanghao/.hermes/hermes-agent/venv/bin/hermes}"

mkdir -p "$LOG_ROOT"

write_state() {
  local status="$1"
  local exit_code="$2"
  cat > "$STATE_FILE" <<EOF
{"run_id":"$RUN_ID","status":"$status","exit_code":$exit_code,"log":"$LOG_FILE","summary":"$SUMMARY_FILE","child_summary":"$CHILD_SUMMARY","prompt_file":"$PROMPT_FILE"}
EOF
}

on_exit() {
  local rc="$?"
  if [[ "$rc" -eq 0 ]]; then
    write_state "finished" "$rc"
    printf 'FINALIZER_FINISH run_id=%s rc=%s time=%s\n' "$RUN_ID" "$rc" "$(date -Is)" | tee -a "$SUMMARY_FILE"
  else
    write_state "failed" "$rc"
    printf 'FINALIZER_FAIL run_id=%s rc=%s time=%s\n' "$RUN_ID" "$rc" "$(date -Is)" | tee -a "$SUMMARY_FILE"
  fi
}
trap on_exit EXIT

exec > >(tee -a "$LOG_FILE") 2>&1

write_state "running" 0
printf 'FINALIZER_START run_id=%s time=%s\n' "$RUN_ID" "$(date -Is)" | tee -a "$SUMMARY_FILE"
printf 'ROOT=%s\nLOG_ROOT=%s\nPROMPT_FILE=%s\nHERMES_BIN=%s\n' "$ROOT" "$LOG_ROOT" "$PROMPT_FILE" "$HERMES_BIN" | tee -a "$SUMMARY_FILE"

cd "$ROOT"
export PATH="$(dirname "$HERMES_BIN"):$PATH"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"
export HERMES_ACCEPT_HOOKS=1

hermes --oneshot "$(cat "$PROMPT_FILE")" \
  --worktree \
  --skills hermes-agent,systematic-debugging,test-driven-development \
  --toolsets terminal,file,skills,session_search,todo,web \
  --yolo | tee -a "$LOG_FILE"

if [[ ! -f "$CHILD_SUMMARY" ]]; then
  cat > "$CHILD_SUMMARY" <<EOF
# Child Summary

Hermes finalizer run completed without creating the expected child summary file.
See run log: $LOG_FILE
EOF
fi
