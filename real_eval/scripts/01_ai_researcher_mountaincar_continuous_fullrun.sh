#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
FRAMEWORK_MODEL_RAW="${REAL_EVAL_FRAMEWORK_MODEL:-${REAL_EVAL_MODEL:-gpt-5.4}}"
export FRAMEWORK_NAME="AI-Researcher"
export FRAMEWORK_SLUG="01_ai_researcher_mountaincar_continuous_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 01)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
AI-Researcher/benchmark/final/mountaincar_continuous/mountaincar_continuous.json
AI-Researcher/benchmark/process/dataset_candidate/mountaincar_continuous/metaprompt.py
real_eval/adapters/mountaincar_continuous/patch_ai_researcher.py
real_eval/adapters/mountaincar_continuous/patch_model_fact_ai_researcher.py
real_eval/adapters/mountaincar_continuous/relocate_handoff_ai_researcher.py
real_eval/adapters/ai_researcher/patch_idea_loop_fixes.py
real_eval/adapters/ai_researcher/patch_prepare_bypass.py
real_eval/adapters/ai_researcher/patch_empty_input_truth.py
real_eval/adapters/ai_researcher/patch_loop_guard.py
real_eval/adapters/ai_researcher/patch_browser_tool_timeout.py
real_eval/adapters/ai_researcher/patch_run_command_idle_timeout.py
real_eval/adapters/ai_researcher/patch_run_command_keepalive.py
real_eval/adapters/ai_researcher/patch_refine_report_fallback.py
real_eval/adapters/ai_researcher/patch_nested_gpu_isolation.py
real_eval/adapters/ai_researcher/patch_nested_cpu_isolation.py
real_eval/adapters/ai_researcher/patch_resource_visibility.py
real_eval/adapters/ai_researcher/patch_logger_resilience.py
real_eval/adapters/ai_researcher/patch_tool_args_resilience.py
real_eval/adapters/ai_researcher/patch_file_browser_text.py
real_eval/adapters/ai_researcher/patch_file_browser_paging.py
real_eval/adapters/ai_researcher/patch_exec_env_provision.py
real_eval/adapters/ai_researcher/patch_ml_delivery_validation.py
real_eval/adapters/ai_researcher/patch_request_probe.py
real_eval/adapters/ai_researcher/patch_response_probe.py
real_eval/adapters/ai_researcher/patch_reasoning_effort_fallback.py
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="ai-researcher:runtime-ready"
export FRAMEWORK_DISABLE_GPU="1"
export FRAMEWORK_NATIVE_ENTRYPOINT="python research_agent/run_infer_idea.py"
export FRAMEWORK_KIMI_INJECTION="OPENAI_BASE_URL, OPENAI_API_KEY, and OPENAI_MODEL resolve to the isolated provider"
export FRAMEWORK_NATIVE_LOG_MARKER="AI_RESEARCHER_NATIVE_INFER_IDEA"
export FRAMEWORK_EXECUTOR_KIND="framework_cli"
export FRAMEWORK_COMMAND_LABEL="python research_agent/run_infer_idea.py"
# NOTE: refine this per-framework native launch command during smoke testing.
# The image caches the sentence-transformers model the tools package loads at
# import time, but under HOME=/workspace huggingface_hub looks in
# /workspace/.cache and fails closed with HF_HUB_OFFLINE=1 -- run
# fullrun_mcar_01_20260828_142007 (retained) died there before reaching any
# research work. Point HF at the cache the image actually ships, exactly as the
# TDC wrapper does.
MC_MODEL="${MOUNTAINCAR_CONTINUOUS_MODEL:-${REAL_EVAL_FRAMEWORK_MODEL:-${REAL_EVAL_MODEL:-}}}"
export FRAMEWORK_DOCKER_ARGS=$(cat <<EOF
-e
HF_HOME=/root/.cache/huggingface
-e
HF_HUB_OFFLINE=1
-e
TRANSFORMERS_OFFLINE=1
-e
AI_RESEARCHER_EXEC_CPUS=32
-e
OPENAI_MODEL=$MC_MODEL
-e
COMPLETION_MODEL=openai/$MC_MODEL
-e
CHEEP_MODEL=openai/$MC_MODEL
-e
AI_RESEARCHER_PREPARE_BYPASS=1
-e
AI_RESEARCHER_ML_DELIVERY_GLOBS=networks.py,config-*.pkl,*.py
-e
AI_RESEARCHER_MAX_TURNS=300
-e
AI_RESEARCHER_LOOP_GUARD_LIMIT=8
-e
AI_RESEARCHER_EXEC_PIP=
-e
AI_RESEARCHER_REQUEST_PROBE=1
-e
AI_RESEARCHER_PROBE_LOG=/workspace/request_probe.jsonl
-e
MOUNTAINCAR_CONTINUOUS_INFER_TIMEOUT_SECONDS=${MOUNTAINCAR_CONTINUOUS_INFER_TIMEOUT_SECONDS:-21600}
-e
AI_RESEARCHER_RESPONSE_PROBE_LOG=/workspace/response_probe.jsonl
EOF
)

export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
echo "AI_RESEARCHER_NATIVE_INFER_IDEA"
export PYTHONPATH=/workspace:/workspace/research_agent/inno/tools:${PYTHONPATH:-}
# The framework source is rsynced to /workspace itself; the staged inputs land
# under /workspace/AI-Researcher. Put the freshly generated instance record and
# metaprompt where the framework actually reads them.
if [ -d /workspace/AI-Researcher/benchmark ]; then
  cp -r /workspace/AI-Researcher/benchmark/. /workspace/benchmark/
fi
# PYMODELFACT inline block extracted to real_eval/adapters/mountaincar_continuous/patch_model_fact_ai_researcher.py (2026-10-16); body unchanged.
python3 real_eval/adapters/mountaincar_continuous/patch_model_fact_ai_researcher.py
python3 real_eval/adapters/mountaincar_continuous/patch_ai_researcher.py
# New framework-fix stack (same adapters as ARC; mcar delivery globs).
python3 real_eval/adapters/ai_researcher/patch_idea_loop_fixes.py
python3 real_eval/adapters/ai_researcher/patch_prepare_bypass.py
python3 real_eval/adapters/ai_researcher/patch_empty_input_truth.py
python3 real_eval/adapters/ai_researcher/patch_loop_guard.py
python3 real_eval/adapters/ai_researcher/patch_browser_tool_timeout.py
python3 real_eval/adapters/ai_researcher/patch_run_command_idle_timeout.py
python3 real_eval/adapters/ai_researcher/patch_run_command_keepalive.py
python3 real_eval/adapters/ai_researcher/patch_refine_report_fallback.py
python3 real_eval/adapters/ai_researcher/patch_nested_gpu_isolation.py
python3 real_eval/adapters/ai_researcher/patch_nested_cpu_isolation.py
python3 real_eval/adapters/ai_researcher/patch_resource_visibility.py
python3 real_eval/adapters/ai_researcher/patch_logger_resilience.py
python3 real_eval/adapters/ai_researcher/patch_tool_args_resilience.py
python3 real_eval/adapters/ai_researcher/patch_file_browser_text.py
python3 real_eval/adapters/ai_researcher/patch_file_browser_paging.py
python3 real_eval/adapters/ai_researcher/patch_exec_env_provision.py
python3 real_eval/adapters/ai_researcher/patch_ml_delivery_validation.py
python3 real_eval/adapters/ai_researcher/patch_request_probe.py
python3 real_eval/adapters/ai_researcher/patch_response_probe.py
python3 real_eval/adapters/ai_researcher/patch_reasoning_effort_fallback.py
PS4='NATIVE_CMD> '
set -x
timeout "${MOUNTAINCAR_CONTINUOUS_INFER_TIMEOUT_SECONDS:-21600}s" python3 research_agent/run_infer_idea.py \
  --instance_path benchmark/final/mountaincar_continuous/mountaincar_continuous.json \
  --container_name mountaincar_ai_researcher \
  --model "$OPENAI_MODEL" \
  --workplace_name workplace \
  --cache_path cache_mountaincar_continuous \
  --port 12374 \
  --max_iter_times 1 \
  --category mountaincar_continuous || echo "[mcar] native infer exited non-zero (rc=$?, e.g. timeout 124) -- proceeding to handoff+score"
set +x
# PYRELOC inline block extracted to real_eval/adapters/mountaincar_continuous/relocate_handoff_ai_researcher.py (2026-10-16); body unchanged.
python3 real_eval/adapters/mountaincar_continuous/relocate_handoff_ai_researcher.py
EOF
)
# [2026-10-02] The shared runner derives its own MC_MODEL (gate expectation) from
# the PROVIDER_CONFIG toml unless MOUNTAINCAR_CONTINUOUS_MODEL is set, while this
# wrapper injects $MC_MODEL (env-derived) into the container. A launch whose
# PROVIDER_CONFIG defaulted to the luna toml made the gate expect gpt-5.6-luna
# and reject a complete, truthful gpt-6-luna delivery (fullrun_mcar_01_g6luna_rep2
# _20260928_113815, exit 42). Pin the runner's expectation to the model this
# wrapper actually ran.
export MOUNTAINCAR_CONTINUOUS_MODEL="$MC_MODEL"
# [2026-10-04] Official scoring must run where JAX/gymnax exist. The shared runner
# scores with $MOUNTAINCAR_CONTINUOUS_PYTHON (default: host python, which has
# neither); point that existing hook at a 01-scoped in-image interpreter instead
# of editing the shared runner. Verified to reproduce -95.30374908447266 offline.
export MOUNTAINCAR_CONTINUOUS_PYTHON="${MOUNTAINCAR_CONTINUOUS_PYTHON:-$ROOT/real_eval/adapters/mountaincar_continuous/host_python_jax.sh}"
# The shared runner stays at upstream; 01's changes to it are applied to a copy
# (real_eval/adapters/ai_researcher/shared_layer_patches/, see real_eval/adapters/shared_layer_overlay.py).
# That copy is where the >=1 experiment gate mentioned in the runtime command above lives.
SHARED_RUNNER="$(python3 "$ROOT/real_eval/adapters/shared_layer_overlay.py" materialize ai_researcher real_eval/scripts/mountaincar_framework_fullrun.sh)"
export RESEARCHCLAWEVAL_ROOT="$ROOT"
exec "$SHARED_RUNNER"
