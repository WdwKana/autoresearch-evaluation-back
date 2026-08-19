#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
EVOSCIENTIST_MODEL="${REAL_EVAL_FRAMEWORK_MODEL:-${REAL_EVAL_MODEL:-kimi-k2.6}}"
export FRAMEWORK_NAME="EvoScientist"
export FRAMEWORK_SLUG="07_evoscientist_arc_wbe_2026_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 07)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
EvoScientist/EVOSCIENTIST_BRIEF.md
EvoScientist/arc_wbe_2026_start_message.txt
docs/arc_wbe_2026_summary.md
automation/arc_wbe_2026_contract.md
automation/arc_wbe_2026_execution_budget.md
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="evoscientist:runtime-ready"
export FRAMEWORK_ENTRYPOINT="bash"
export FRAMEWORK_NATIVE_ENTRYPOINT="evoscientist --use-cwd --auto-mode"
export FRAMEWORK_KIMI_INJECTION="custom-openai provider reads CUSTOM_OPENAI_BASE_URL and CUSTOM_OPENAI_API_KEY"
export FRAMEWORK_NATIVE_LOG_MARKER="EVOSCIENTIST_NATIVE_CLI"
export FRAMEWORK_EXECUTOR_KIND="framework_cli"
export FRAMEWORK_DOCKER_ARGS=$(cat <<EOF
--user
$(id -u):$(id -g)
-e
HOME=/workspace
-e
XDG_CONFIG_HOME=/workspace/.config
-e
EVOSCIENTIST_DATA_DIR=/workspace/.evoscientist
-e
EVOSCIENTIST_USE_RESPONSES_API=false
-e
MPLCONFIGDIR=/tmp
-e
EVOSCIENTIST_LOG_LEVEL=info
-e
EVOSCIENTIST_MODEL=$EVOSCIENTIST_MODEL
EOF
)
export FRAMEWORK_COMMAND_LABEL="/opt/venv/bin/evoscientist --use-cwd -p @arc_wbe_2026_start_message.txt"
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
echo "EVOSCIENTIST_NATIVE_CLI"
rm -rf /workspace/workspace /workspace/verify_workspace
mkdir -p /workspace/.config/evoscientist
cat > /workspace/.config/evoscientist/config.yaml <<YAML
provider: custom-openai
model: ${EVOSCIENTIST_MODEL}
openai_auth_mode: api_key
default_mode: run
default_workdir: /workspace
show_thinking: false
enable_async_subagents: false
YAML
prompt="$(cat arc_wbe_2026_start_message.txt)
This is a bounded Kimi evaluation. Do not inspect data or metadata, open parquet, install packages, access unmapped paths, or inspect scorer source. Execute weight-only experiment 1, weight-only experiment 2, then finalize; do not inspect the same file twice or make a third experiment. Official predict receives only injected mlp.weights. All internal API calls must use OPENAI_BASE_URL, OPENAI_API_KEY, and OPENAI_MODEL. Before exit, write root-level estimator.py, submission.json, experiment_trace.json, final_report.md, and a provisional score.json. The host evaluator will replace score.json by officially scoring your estimator after exit."
timeout "${EVOSCIENTIST_ARC_TIMEOUT_SECONDS:-1800}s" /opt/venv/bin/evoscientist --use-cwd -p "$prompt" --auto-mode --auto-approve --ui cli --no-thinking
EOF
)
exec "$ROOT"/real_eval/scripts/arc_framework_fullrun.sh
