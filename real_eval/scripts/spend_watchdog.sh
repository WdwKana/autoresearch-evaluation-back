#!/usr/bin/env bash
# Spend watchdog: stop this side's runs once they have burned a stated budget.
#
# WHY
#   The wrappers bound wall-clock only (timeout 7000s/7200s). Wall-clock is not
#   a cost bound: fullrun_arc_01_ds2_20260901_122200 spent $12.30 inside its
#   two-hour limit because a single model emitted 124 prompts above 250k tokens.
#   An overnight run therefore has no ceiling on spend.
#
# WHAT IT DOES
#   Polls the provider's own per-call log (the same source used for post-hoc
#   accounting), sums the quota spent since the watchdog started, and when that
#   crosses --budget it stops OUR runs only: the rceval tmux windows and the
#   containers this harness creates. It never touches other users' containers,
#   and it never deletes run directories -- a stopped run is retained for
#   post-mortem exactly like any other failure.
#
# USAGE
#   real_eval/scripts/spend_watchdog.sh --budget 8 [--poll 120] [--dry-run]
set -uo pipefail

ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
BUDGET_USD=""; POLL=120; DRY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --budget) BUDGET_USD="$2"; shift 2;;
    --poll) POLL="$2"; shift 2;;
    --dry-run) DRY=1; shift;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
[[ -n "$BUDGET_USD" ]] || { echo "--budget <usd> is required" >&2; exit 2; }

set -a; source "$ROOT/.env"; set +a
BASE="${OPENAI_BASE_URL%/v1}"
START_TS=$(date +%s)
LOG="${SPEND_WATCHDOG_LOG:-$ROOT/real_eval/runs/spend_watchdog.log}"
mkdir -p "$(dirname "$LOG")"

say() { echo "[$(date -Is)] $*" | tee -a "$LOG"; }
say "watchdog armed: budget \$$BUDGET_USD, poll ${POLL}s, baseline $(date -d @$START_TS -Is)"

spent_since() {
  curl -s -m 60 "$BASE/api/log/token?key=$OPENAI_API_KEY&p=1&page_size=1000" \
       -H "Authorization: Bearer $OPENAI_API_KEY" 2>/dev/null \
  | python3 -c "
import json,sys
try: rows=json.load(sys.stdin)['data']
except Exception: print('ERR'); raise SystemExit
cut=$START_TS
q=sum(r.get('quota') or 0 for r in rows if r.get('type')==2 and r['created_at']>=cut)
print(f'{q/500000:.4f}')"
}

stop_ours() {
  say "STOPPING our runs (budget exceeded)"
  for w in $(tmux list-windows -t rceval -F '#{window_name}' 2>/dev/null); do
    case "$w" in babylm*|arc*|mcar*|tdc*|psydef*|ds-queue) tmux kill-window -t "rceval:$w" 2>/dev/null && say "  killed tmux window $w";; esac
  done
  docker ps --format '{{.Names}}' \
    | grep -E '^(ai_researcher|arc_wbe_2026_eval|tdc-fw|tdc-relay|01_ai_researcher|02_ai_scientist)' \
    | while read -r c; do docker rm -f "$c" >/dev/null 2>&1 && say "  removed container $c"; done
}

while true; do
  S=$(spent_since)
  if [[ "$S" == "ERR" || -z "$S" ]]; then
    say "billing query failed; will retry (watchdog stays armed)"
  else
    say "spent since start: \$$S / \$$BUDGET_USD"
    if awk "BEGIN{exit !($S >= $BUDGET_USD)}"; then
      if [[ "$DRY" == 1 ]]; then say "DRY-RUN: would stop our runs now"; else stop_ours; fi
      say "watchdog done"
      exit 0
    fi
  fi
  sleep "$POLL"
done
