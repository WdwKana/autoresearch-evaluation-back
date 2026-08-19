#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
export FRAMEWORK_NAME="DeepScientist"
export FRAMEWORK_SLUG="05_deepscientist_psydefdetect_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 05)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
DeepScientist/PSYDEFDETECT_BRIEF.md
automation/psydefdetect_contract.md
automation/psydefdetect_execution_budget.md
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="deepscientist:runtime-ready"
export FRAMEWORK_DOCKER_ARGS=$(cat <<'EOF'
--user
0:0
EOF
)
export FRAMEWORK_NATIVE_ENTRYPOINT="ds init -> ds new -> ds run run-experiment --runner codex"
export FRAMEWORK_PROVIDER_INJECTION="DeepScientist's official CodexRunner uses the injected /codex-home/config.toml evaluation provider"
export FRAMEWORK_NATIVE_LOG_MARKER="DEEPSCIENTIST_NATIVE_CODEX_RUNNER"
export FRAMEWORK_EXECUTOR_KIND="framework_cli"
export FRAMEWORK_COMMAND_LABEL="ds --home /workspace/.deepscientist run run-experiment --runner codex"
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
export DEEPSCIENTIST_CODEX_BINARY="/opt/researchclaweval-node/bin/codex"
DS_HOME=/workspace/.deepscientist
QUEST_ID=psydefdetect-gpt-native
echo "DEEPSCIENTIST_NATIVE_CODEX_RUNNER"
ds --home "$DS_HOME" init
sed -i 's#config_dir: ~/.codex#config_dir: /codex-home#' "$DS_HOME/config/runners.yaml"
grep -Fq 'config_dir: /codex-home' "$DS_HOME/config/runners.yaml"
ds --home "$DS_HOME" new \
  "Execute the PsyDefDetect contract in /workspace through DeepScientist and produce the complete framework-owned handoff." \
  --quest-id "$QUEST_ID"
timeout "${DEEPSCIENTIST_PSYDEFDETECT_TIMEOUT_SECONDS:-7200}s" \
  ds --home "$DS_HOME" run run-experiment \
  --quest-id "$QUEST_ID" \
  --runner codex \
  --model "$OPENAI_MODEL" \
  --message "Read PSYDEFDETECT_BRIEF.md, automation/psydefdetect_contract.md, and automation/psydefdetect_execution_budget.md. DeepScientist must plan and execute exactly 2 materially different LOCAL fixed-split experiments: word-level TF-IDF with class-balanced LogisticRegression, and character-level TF-IDF with class-balanced LinearSVC or SGDClassifier(loss=hinge). Do not perform API classification, remote calls from experiment code, package installation, background jobs, sleep/poll loops, or parallel experiment commands. Run each experiment synchronously in the foreground, score both with the mounted official scorer, immediately select the higher macro-F1 over positive labels 1-8, and promote the selected result. DeepScientist itself must write /workspace/predictions.jsonl or /workspace/submission.csv, /workspace/score.json, /workspace/experiment_trace.json, and /workspace/final_report.md before the native command exits. In experiment_trace.json, record the planning provider exactly as this literal JSON fragment: \"framework_internal_model\": \"$OPENAI_MODEL\", \"framework_internal_api_base_url\": \"$OPENAI_BASE_URL\". These fields describe DeepScientist's injected LLM provider; never replace them with scikit-learn, a classifier name, or none. Use only the injected evaluation provider for planning/code generation and /data/psydefdetect for input."
EOF
)
exec "$ROOT"/real_eval/scripts/psydefdetect_framework_fullrun.sh
