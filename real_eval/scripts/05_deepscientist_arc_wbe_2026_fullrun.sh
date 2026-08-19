#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
export FRAMEWORK_NAME="DeepScientist"
export FRAMEWORK_SLUG="05_deepscientist_arc_wbe_2026_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 05)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
DeepScientist/DEEPSCIENTIST_BRIEF.md
docs/arc_wbe_2026_summary.md
automation/arc_wbe_2026_contract.md
automation/arc_wbe_2026_execution_budget.md
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="deepscientist:runtime-ready"
export FRAMEWORK_DOCKER_ARGS=$(cat <<'EOF'
--user
0:0
EOF
)
export FRAMEWORK_NATIVE_ENTRYPOINT="ds init; ds new; ds run --runner kimi"
export FRAMEWORK_KIMI_INJECTION="DeepScientist built-in KimiRunner with DEEPSCIENTIST_KIMI_MODEL=kimi-k2.6"
export FRAMEWORK_NATIVE_LOG_MARKER="DEEPSCIENTIST_NATIVE_KIMI_RUNNER"
export FRAMEWORK_EXECUTOR_KIND="framework_cli"
export FRAMEWORK_COMMAND_LABEL="ds --home /workspace/.deepscientist run run-experiment --runner kimi"
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
export DEEPSCIENTIST_KIMI_BINARY="${DEEPSCIENTIST_KIMI_BINARY:-kimi}"
export DEEPSCIENTIST_KIMI_MODEL="${OPENAI_MODEL:?OPENAI_MODEL is required}"
export DEEPSCIENTIST_KIMI_YOLO=1
DS_HOME=/workspace/.deepscientist
QUEST_ID=arc-wbe-2026
echo "DEEPSCIENTIST_NATIVE_KIMI_RUNNER"
ds --home "$DS_HOME" init
ds --home "$DS_HOME" new "Execute the ARC-WBE-2026 contract in /workspace and produce the required framework-native handoff artifacts." --quest-id "$QUEST_ID"
timeout "${ARC_WBE_2026_FRAMEWORK_TIMEOUT_SECONDS:-1800}s" \
  ds --home "$DS_HOME" run run-experiment --quest-id "$QUEST_ID" --runner kimi --model "$OPENAI_MODEL" \
  --message "Read DEEPSCIENTIST_BRIEF.md, docs/arc_wbe_2026_summary.md, automation/arc_wbe_2026_contract.md, and automation/arc_wbe_2026_execution_budget.md. Use the framework's Kimi runner and only injected API settings. Run two bounded white-box estimator experiments, select one, and write root-level estimator.py, submission.json, experiment_trace.json, final_report.md, and provisional score.json."
EOF
)
exec "$ROOT"/real_eval/scripts/arc_framework_fullrun.sh
