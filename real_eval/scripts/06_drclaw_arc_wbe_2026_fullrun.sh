#!/usr/bin/env bash
set -euo pipefail

ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
export FRAMEWORK_NAME="Dr. Claw"
export FRAMEWORK_SLUG="06_drclaw_arc_wbe_2026_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 06)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
dr-claw/research_brief.json
dr-claw/tasks.json
docs/arc_wbe_2026_summary.md
automation/arc_wbe_2026_contract.md
automation/arc_wbe_2026_execution_budget.md
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="dr-claw:runtime-ready"
export FRAMEWORK_ENTRYPOINT="bash"
export FRAMEWORK_DOCKER_ARGS=$(cat <<'EOF'
--user
0:0
-e
NODE_PATH=/opt/dr-claw/node_modules
EOF
)
export FRAMEWORK_NATIVE_ENTRYPOINT="node server/cli.js chat"
export FRAMEWORK_KIMI_INJECTION="Dr. Claw OpenRouter-compatible client reads injected OPENAI_BASE_URL and OPENAI_API_KEY"
export FRAMEWORK_NATIVE_LOG_MARKER="DRCLAW_NATIVE_CHAT"
export FRAMEWORK_EXECUTOR_KIND="framework_cli"
export FRAMEWORK_COMMAND_LABEL="node server/cli.js chat --model kimi-k2.6"
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
echo "DRCLAW_NATIVE_CHAT"
prompt='Read dr-claw/research_brief.json, dr-claw/tasks.json, docs/arc_wbe_2026_summary.md, automation/arc_wbe_2026_contract.md, and automation/arc_wbe_2026_execution_budget.md. Execute the task with your native planning and tool loop. Use only the injected Kimi relay. Run two bounded ARC estimator experiments, select one, and write root-level estimator.py, submission.json, score.json, experiment_trace.json, and final_report.md. Do not access data outside /data/arc_wbe_2026 or write outside /workspace.'
echo "DRCLAW_STDIN_EOF_AFTER_ACTIVE_TURN"
printf '%s\n' "$prompt" | timeout "${ARC_WBE_2026_FRAMEWORK_TIMEOUT_SECONDS:-1800}s" node server/cli.js chat --model "$OPENAI_MODEL"
EOF
)
exec "$ROOT/real_eval/scripts/arc_framework_fullrun.sh"
