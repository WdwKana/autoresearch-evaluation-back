#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
export FRAMEWORK_NAME="ARIS"
export FRAMEWORK_SLUG="03_aris_arc_wbe_2026_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 03)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
Auto-claude-code-research-in-sleep/ARC_WBE_2026_BRIEF.md
docs/arc_wbe_2026_summary.md
automation/arc_wbe_2026_contract.md
automation/arc_wbe_2026_execution_budget.md
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="aris:runtime-ready"
export FRAMEWORK_DOCKER_ARGS=$(cat <<'EOF'
--user
0:0
EOF
)
export FRAMEWORK_NATIVE_ENTRYPOINT="ARIS /experiment-bridge skill"
export FRAMEWORK_KIMI_INJECTION="Codex executor reads injected provider config at /codex-home/config.toml"
export FRAMEWORK_NATIVE_LOG_MARKER="ARIS_NATIVE_EXPERIMENT_BRIDGE"
export FRAMEWORK_EXECUTOR_KIND="framework_skill_executor"
export FRAMEWORK_COMMAND_LABEL='codex exec --yolo -C /workspace "/experiment-bridge ARC_WBE_2026_BRIEF.md"'
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
test -f skills/skills-codex/experiment-bridge/SKILL.md
echo "ARIS_NATIVE_EXPERIMENT_BRIDGE"
timeout "${ARC_WBE_2026_FRAMEWORK_TIMEOUT_SECONDS:-1800}s" \
  codex exec --yolo --skip-git-repo-check -C /workspace \
  "/experiment-bridge ARC_WBE_2026_BRIEF.md. This is the ARIS native skill workflow. Follow the injected ARC contract and execution budget. Use only injected Kimi configuration. Run two bounded estimators and let the workflow promote root-level estimator.py, submission.json, experiment_trace.json, final_report.md, and provisional score.json."
EOF
)
exec "$ROOT"/real_eval/scripts/arc_framework_fullrun.sh
