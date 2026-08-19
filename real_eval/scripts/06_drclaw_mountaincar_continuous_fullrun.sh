#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
FRAMEWORK_MODEL_RAW="${REAL_EVAL_FRAMEWORK_MODEL:-${REAL_EVAL_MODEL:-gpt-5.4}}"
export FRAMEWORK_NAME="Dr. Claw"
export FRAMEWORK_SLUG="06_drclaw_mountaincar_continuous_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 06)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
dr-claw/research_brief.json
dr-claw/tasks.json
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="dr-claw:runtime-ready"
export FRAMEWORK_DISABLE_GPU="1"
export FRAMEWORK_NATIVE_ENTRYPOINT="node server/cli.js chat --model gpt-5.4"
export FRAMEWORK_KIMI_INJECTION="OPENAI_BASE_URL, OPENAI_API_KEY, and OPENAI_MODEL resolve to the isolated provider"
export FRAMEWORK_NATIVE_LOG_MARKER="DRCLAW_NATIVE_CHAT"
export FRAMEWORK_EXECUTOR_KIND="framework_cli"
export FRAMEWORK_COMMAND_LABEL="node server/cli.js chat --model gpt-5.4"
# NOTE: refine this per-framework native launch command during smoke testing.
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
echo "DRCLAW_NATIVE_CHAT"
# Run Dr. Claw with memory-efficient Node.js settings
export NODE_OPTIONS="--max-old-space-size=8192"
# Run the chat-based research workflow
cd /workspace && node server/cli.js chat --model "$OPENAI_MODEL" \
  --prompt "Read research_brief.json and tasks.json, then execute the Topic 2 research workflow" 2>&1
EOF
)
exec "$ROOT/real_eval/scripts/mountaincar_framework_fullrun.sh"
