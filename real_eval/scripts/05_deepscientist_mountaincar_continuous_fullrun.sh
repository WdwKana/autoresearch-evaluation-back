#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
FRAMEWORK_MODEL_RAW="${REAL_EVAL_FRAMEWORK_MODEL:-${REAL_EVAL_MODEL:-gpt-5.4}}"
export FRAMEWORK_NAME="DeepScientist"
export FRAMEWORK_SLUG="05_deepscientist_mountaincar_continuous_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 05)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
DeepScientist/DEEPSCIENTIST_BRIEF.md
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="deepscientist:runtime-ready"
export FRAMEWORK_DISABLE_GPU="1"
export FRAMEWORK_NATIVE_ENTRYPOINT="ds init; ds new; ds run run-experiment --runner codex"
export FRAMEWORK_KIMI_INJECTION="OPENAI_BASE_URL, OPENAI_API_KEY, and OPENAI_MODEL resolve to the isolated provider"
export FRAMEWORK_NATIVE_LOG_MARKER="DEEPSCIENTIST_NATIVE_CODEX_RUNNER"
export FRAMEWORK_EXECUTOR_KIND="framework_cli"
export FRAMEWORK_COMMAND_LABEL="ds init; ds new; ds run run-experiment --runner codex"
# NOTE: refine this per-framework native launch command during smoke testing.
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
echo "DEEPSCIENTIST_NATIVE_CODEX_RUNNER"
# Ensure ds CLI is available
export PATH="${PATH}:$(npm bin -g 2>/dev/null || echo /usr/local/bin)"
# Run DeepScientist experiment workflow
ds --home /workspace/.deepscientist init 2>&1
ds --home /workspace/.deepscientist new 2>&1
ds --home /workspace/.deepscientist run experiment --runner codex 2>&1
EOF
)
exec "$ROOT/real_eval/scripts/mountaincar_framework_fullrun.sh"
