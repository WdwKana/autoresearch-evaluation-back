#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
export FRAMEWORK_NAME="AutoResearchClaw"
export FRAMEWORK_SLUG="04_autoresearchclaw_arc_wbe_2026_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 04)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
AutoResearchClaw/config.arc.yaml
AutoResearchClaw/topic.txt
real_eval/scripts/lib_autoresearchclaw_handoff.sh
docs/arc_wbe_2026_summary.md
automation/arc_wbe_2026_contract.md
automation/arc_wbe_2026_execution_budget.md
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="autoresearchclaw:runtime-ready"
export FRAMEWORK_ENTRYPOINT="bash"
export FRAMEWORK_NATIVE_ENTRYPOINT="python -m researchclaw.cli run"
export FRAMEWORK_KIMI_INJECTION="config.arc.yaml OpenAI-compatible client uses OPENAI_BASE_URL, OPENAI_API_KEY, and OPENAI_MODEL"
export FRAMEWORK_NATIVE_LOG_MARKER="AUTORESEARCHCLAW_NATIVE_RUN"
export FRAMEWORK_EXECUTOR_KIND="framework_cli"
export FRAMEWORK_COMMAND_LABEL="python3 -m researchclaw.cli run --config config.arc.yaml"
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
ROOT="${ROOT:-/workspace}"
echo "AUTORESEARCHCLAW_NATIVE_RUN"
topic="$(tr '\n' ' ' < topic.txt)"
source real_eval/scripts/lib_autoresearchclaw_handoff.sh
autoresearchclaw_validate_run_id "${REAL_EVAL_RUN_ID:?REAL_EVAL_RUN_ID is required}"
apply_autoresearchclaw_stage8_idea_lock_adapter "/workspace"
idea_provenance_contract="Before the first experiment, have the native Stage 8 synthesis write the framework-authored research_idea.json and research_idea_lock_event.json. The lock event must identify AutoResearchClaw as the framework writer, bind the finalized artifact SHA256, and carry a timezone-aware timestamp. Record research_idea.json, idea_locked_before_experiments=true, and first_experiment_started_at in experiment_trace.json."
artifact_root="/workspace/artifacts/arc-wbe-2026-${REAL_EVAL_RUN_ID}"
set +e
timeout "${ARC_WBE_2026_FRAMEWORK_TIMEOUT_SECONDS:-28800}s" python3 -m researchclaw.cli run \
  --config config.arc.yaml \
  --topic "$topic $idea_provenance_contract" \
  --output "$artifact_root" \
  --auto-approve
native_rc=$?
set -e
if [[ "$native_rc" -ne 0 ]]; then
  exit "$native_rc"
fi
autoresearchclaw_handoff arc_wbe_2026 /workspace "$artifact_root"
verify_framework_research_idea_json "/workspace"
EOF
)
exec "$ROOT"/real_eval/scripts/arc_framework_fullrun.sh
