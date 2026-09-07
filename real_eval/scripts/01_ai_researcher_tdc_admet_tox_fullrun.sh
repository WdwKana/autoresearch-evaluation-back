#!/usr/bin/env bash
set -euo pipefail

ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
MODEL="${TDC_ADMET_TOX_EVAL_MODEL:-${REAL_EVAL_FRAMEWORK_MODEL:-${REAL_EVAL_MODEL:-gpt-5.4}}}"
export FRAMEWORK_NAME="AI-Researcher"
export FRAMEWORK_SLUG="01_ai_researcher_tdc_admet_tox_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 01)"
export FRAMEWORK_ENTRY_PREFIX="AI-Researcher"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
AI-Researcher/benchmark/final/tdc_admet_tox/tdc_admet_tox.json
AI-Researcher/benchmark/process/dataset_candidate/tdc_admet_tox/metaprompt.py
real_eval/adapters/tdc_admet_tox/patch_ai_researcher.py
real_eval/adapters/ai_researcher/patch_idea_loop_fixes.py
real_eval/adapters/ai_researcher/patch_prepare_bypass.py
real_eval/adapters/ai_researcher/patch_empty_input_truth.py
real_eval/adapters/ai_researcher/patch_loop_guard.py
real_eval/adapters/ai_researcher/patch_file_browser_text.py
real_eval/adapters/ai_researcher/patch_ml_delivery_validation.py
real_eval/adapters/ai_researcher/patch_request_probe.py
real_eval/adapters/ai_researcher/patch_response_probe.py
real_eval/adapters/ai_researcher/patch_budget_clock.py
real_eval/adapters/ai_researcher/patch_wire_tap.py
real_eval/adapters/ai_researcher/patch_browser_tool_timeout.py
real_eval/adapters/ai_researcher/patch_resource_visibility.py
real_eval/adapters/ai_researcher/patch_logger_resilience.py
automation/tdc_admet_tox_contract.md
automation/tdc_admet_tox_execution_budget.md
EOF
)
export FRAMEWORK_RUNTIME_IMAGE="${AI_RESEARCHER_RUNTIME_IMAGE:-ai-researcher:runtime-ready}"
export FRAMEWORK_NATIVE_ENTRYPOINT="python research_agent/run_infer_idea.py"
export FRAMEWORK_NATIVE_ENTRYPOINT_FILE="research_agent/run_infer_idea.py"
export FRAMEWORK_NATIVE_ENTRYPOINT_SOURCE="README.md"
export FRAMEWORK_PROVIDER_INJECTION="MetaChain COMPLETION_MODEL/CHEEP_MODEL/API_BASE_URL use the isolated GPT relay; experiments execute inside the framework container without a host Docker socket"
export FRAMEWORK_NATIVE_LOG_MARKER="AI_RESEARCHER_NATIVE_INFER_IDEA_TDC"
export FRAMEWORK_NATIVE_PROCESS_MARKERS="NATIVE_CMD> timeout 7000s python3 research_agent/run_infer_idea.py"
export FRAMEWORK_EXECUTOR_KIND="framework_cli"
export FRAMEWORK_COMMAND_LABEL="python research_agent/run_infer_idea.py --category tdc_admet_tox"
export FRAMEWORK_DOCKER_ARGS=$(cat <<EOF
-e
COMPLETION_MODEL=openai/$MODEL
-e
CHEEP_MODEL=openai/$MODEL
-e
PYTHONPATH=/workspace:/workspace/research_agent
-e
HF_HOME=/root/.cache/huggingface
-e
HF_HUB_OFFLINE=1
-e
TRANSFORMERS_OFFLINE=1
-e
TDC_ADMET_TOX_NATIVE_RUN=1
-e
GPUS=
-e
AI_RESEARCHER_MAX_TURNS=300
-e
AI_RESEARCHER_LOOP_GUARD_LIMIT=8
-e
AI_RESEARCHER_PREPARE_BYPASS=1
-e
AI_RESEARCHER_ML_DELIVERY_GLOBS=*.py
-e
AI_RESEARCHER_TOTAL_BUDGET_SECONDS=7000
-e
AI_RESEARCHER_REQUEST_PROBE=1
-e
AI_RESEARCHER_PROBE_LOG=/workspace/request_probe.jsonl
-e
AI_RESEARCHER_RESPONSE_PROBE_LOG=/workspace/response_probe.jsonl
-e
AI_RESEARCHER_WIRE_TAP_LOG=/workspace/wire_tap.jsonl
-e
AI_RESEARCHER_EXEC_CPUS=4
-e
AI_RESEARCHER_ML_DELIVERY_VALIDATOR=python3 /workspace/automation/scripts/validate_tdc_admet_tox_run.py --workspace /workspace --stage framework --public-dataset-root /workspace/data/tdc_admet_tox
EOF
)
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
echo "AI_RESEARCHER_NATIVE_INFER_IDEA_TDC"
python3 real_eval/adapters/tdc_admet_tox/patch_ai_researcher.py
# General fix stack (10/11, conflict-verified 2026-09-07; exec_env_provision
# skipped: TDC runs experiments locally, no nested exec container -- dead code).
python3 real_eval/adapters/ai_researcher/patch_idea_loop_fixes.py
python3 real_eval/adapters/ai_researcher/patch_prepare_bypass.py
python3 real_eval/adapters/ai_researcher/patch_empty_input_truth.py
python3 real_eval/adapters/ai_researcher/patch_loop_guard.py
python3 real_eval/adapters/ai_researcher/patch_file_browser_text.py
python3 real_eval/adapters/ai_researcher/patch_ml_delivery_validation.py
python3 real_eval/adapters/ai_researcher/patch_request_probe.py
python3 real_eval/adapters/ai_researcher/patch_response_probe.py
python3 real_eval/adapters/ai_researcher/patch_budget_clock.py
python3 real_eval/adapters/ai_researcher/patch_wire_tap.py
python3 real_eval/adapters/ai_researcher/patch_browser_tool_timeout.py
python3 real_eval/adapters/ai_researcher/patch_resource_visibility.py
python3 real_eval/adapters/ai_researcher/patch_logger_resilience.py
python3 - <<'PY'
from research_agent.inno.tools import (
    execute_command,
    gen_code_tree_structure,
    plan_dataset,
    plan_testing,
    plan_training,
    read_file,
    run_python,
)
import research_agent.inno.agents.inno_agent.judge_agent
import research_agent.inno.agents.inno_agent.ml_agent
import research_agent.inno.agents.inno_agent.plan_agent
import research_agent.run_infer_idea

required_tools = (
    execute_command,
    gen_code_tree_structure,
    plan_dataset,
    plan_testing,
    plan_training,
    read_file,
    run_python,
)
assert all(callable(tool) for tool in required_tools)
print("AI_RESEARCHER_TDC_IMPORT_GATE_OK")
PY
PS4='NATIVE_CMD> '
set -x
timeout 7000s python3 research_agent/run_infer_idea.py \
  --instance_path benchmark/final/tdc_admet_tox/tdc_admet_tox.json \
  --container_name tdc_ai_researcher \
  --model "$OPENAI_MODEL" \
  --workplace_name . \
  --cache_path cache_tdc_admet_tox \
  --port 12372 \
  --max_iter_times 1 \
  --category tdc_admet_tox
EOF
)
exec "$ROOT/real_eval/scripts/tdc_admet_tox_framework_fullrun.sh"
