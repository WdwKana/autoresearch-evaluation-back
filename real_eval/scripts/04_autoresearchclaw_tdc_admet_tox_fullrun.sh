#!/usr/bin/env bash
set -euo pipefail

ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
export FRAMEWORK_NAME="AutoResearchClaw"
export FRAMEWORK_SLUG="04_autoresearchclaw_tdc_admet_tox_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 04)"
export FRAMEWORK_ENTRY_PREFIX="AutoResearchClaw"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
AutoResearchClaw/config.tdc_admet_tox.yaml
AutoResearchClaw/topic.tdc_admet_tox.txt
real_eval/scripts/lib_autoresearchclaw_handoff.sh
AutoResearchClaw/TDC_ADMET_TOX_BRIEF.md
real_eval/adapters/tdc_admet_tox/patch_autoresearchclaw.py
automation/tdc_admet_tox_contract.md
automation/tdc_admet_tox_execution_budget.md
EOF
)
export FRAMEWORK_RUNTIME_IMAGE="${AUTORESEARCHCLAW_RUNTIME_IMAGE:-autoresearchclaw:runtime-ready}"
export FRAMEWORK_NATIVE_ENTRYPOINT="python -m researchclaw.cli run"
export FRAMEWORK_NATIVE_ENTRYPOINT_FILE="researchclaw/cli.py"
export FRAMEWORK_NATIVE_ENTRYPOINT_SOURCE="README.md"
export FRAMEWORK_PROVIDER_INJECTION="AutoResearchClaw openai-compatible config reads the isolated OPENAI_BASE_URL, OPENAI_API_KEY, and OPENAI_MODEL"
export FRAMEWORK_NATIVE_LOG_MARKER="AUTORESEARCHCLAW_NATIVE_RUN_TDC"
export FRAMEWORK_NATIVE_PROCESS_MARKERS="NATIVE_CMD> timeout 7000s python3 -m researchclaw.cli run"
export FRAMEWORK_EXECUTOR_KIND="framework_cli"
export FRAMEWORK_COMMAND_LABEL="python -m researchclaw.cli run --config config.tdc_admet_tox.yaml --auto-approve"
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
ROOT="${ROOT:-/workspace}"
echo "AUTORESEARCHCLAW_NATIVE_RUN_TDC"
python3 real_eval/adapters/tdc_admet_tox/patch_autoresearchclaw.py
topic="$(cat topic.tdc_admet_tox.txt)"
source real_eval/scripts/lib_autoresearchclaw_handoff.sh
autoresearchclaw_validate_run_id "${REAL_EVAL_RUN_ID:?REAL_EVAL_RUN_ID is required}"
apply_autoresearchclaw_stage8_idea_lock_adapter "/workspace"
idea_provenance_contract="Before the first experiment, have the native Stage 8 synthesis write the framework-authored research_idea.json and research_idea_lock_event.json. The lock event must identify AutoResearchClaw as the framework writer, bind the finalized artifact SHA256, and carry a timezone-aware timestamp. Record research_idea.json, idea_locked_before_experiments=true, and first_experiment_started_at in experiment_trace.json."
artifact_root="/workspace/artifacts/tdc-admet-tox-${REAL_EVAL_RUN_ID}"
export AUTORESEARCHCLAW_ARTIFACT_ROOT="${artifact_root}/deliverables"
PS4='NATIVE_CMD> '
set -x
set +e
timeout 7000s python3 -m researchclaw.cli run \
  --config config.tdc_admet_tox.yaml \
  --topic "$topic $idea_provenance_contract" \
  --output "$artifact_root" \
  --auto-approve \
  --skip-noncritical-stage
native_rc=$?
set -e
if [[ "$native_rc" -ne 0 ]]; then
  exit "$native_rc"
fi
autoresearchclaw_handoff tdc_admet_tox /workspace "$artifact_root"
WORKSPACE=/workspace python3 real_eval/adapters/tdc_admet_tox/patch_autoresearchclaw.py --handoff
verify_framework_research_idea_json "/workspace"
EOF
)
exec "$ROOT/real_eval/scripts/tdc_admet_tox_framework_fullrun.sh"
