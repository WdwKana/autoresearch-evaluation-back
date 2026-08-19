#!/usr/bin/env bash
set -euo pipefail

ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
RUN_ID="${REAL_EVAL_RUN_ID:-systemd-gave2-fullrun-finalizer-$(date +%Y%m%d-%H%M%S)}"
UNIT_SAFE_RUN_ID="$(printf '%s' "$RUN_ID" | tr -c 'A-Za-z0-9_.-' '-')"
UNIT="${REAL_EVAL_SYSTEMD_UNIT:-researchclaweval-gave2-fullrun-finalizer-$UNIT_SAFE_RUN_ID}"
LOG_ROOT="${REAL_EVAL_SYSTEMD_LOG_ROOT:-$ROOT/real_eval/systemd_runs/$RUN_ID}"
JOB="$ROOT/real_eval/scripts/run_gave2_fullrun_finalizer_systemd_job.sh"
USER_UID="$(id -u)"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$USER_UID}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"

if [[ "$RUN_ID" == *babylm* ]] || [[ "$LOG_ROOT" == *babylm* ]]; then
  echo "refusing BabyLM-overlapping finalizer identifiers or paths" >&2
  exit 9
fi
if ! test -S "$XDG_RUNTIME_DIR/bus"; then
  echo "systemd user bus missing: $XDG_RUNTIME_DIR/bus" >&2
  exit 2
fi
if ! systemctl --user list-units >/dev/null 2>&1; then
  echo "systemd --user is not running or not reachable" >&2
  exit 3
fi
if [[ ! -x "$JOB" ]]; then
  echo "Job wrapper is not executable: $JOB" >&2
  exit 4
fi
if [[ ! -x "/home/guanghao/.hermes/hermes-agent/venv/bin/hermes" ]]; then
  echo "Hermes binary missing: /home/guanghao/.hermes/hermes-agent/venv/bin/hermes" >&2
  exit 5
fi

mkdir -p "$LOG_ROOT"
cat > "$LOG_ROOT/submission.json" <<EOF
{"run_id":"$RUN_ID","unit":"$UNIT.service","kind":"gave2_fullrun_finalizer","log_root":"$LOG_ROOT","submitted_at":"$(date -Is)"}
EOF

systemd-run --user \
  --unit "$UNIT" \
  --collect \
  --description "ResearchClawEval GAVE2 full-run finalizer $RUN_ID" \
  --property=WorkingDirectory="$ROOT" \
  --property=KillMode=control-group \
  --property=TimeoutStopSec=120 \
  --setenv=RESEARCHCLAWEVAL_ROOT="$ROOT" \
  --setenv=REAL_EVAL_RUN_ID="$RUN_ID" \
  --setenv=REAL_EVAL_SYSTEMD_LOG_ROOT="$LOG_ROOT" \
  --setenv=XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" \
  --setenv=DBUS_SESSION_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS" \
  "$JOB"

cat <<EOF
UNIT=$UNIT.service
RUN_ID=$RUN_ID
LOG_ROOT=$LOG_ROOT
LOG_FILE=$LOG_ROOT/run.log
STATE_FILE=$LOG_ROOT/state.json

Status:
  XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS systemctl --user status $UNIT.service --no-pager

Journal:
  XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS journalctl --user -u $UNIT.service -f

File log:
  tail -f $LOG_ROOT/run.log
EOF
