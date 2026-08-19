#!/usr/bin/env bash
set -euo pipefail

ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
export FRAMEWORK_NAME="DeepScientist"
export FRAMEWORK_SLUG="05_deepscientist_tdc_admet_tox_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 05)"
export FRAMEWORK_ENTRY_PREFIX="DeepScientist"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
DeepScientist/TDC_ADMET_TOX_BRIEF.md
automation/tdc_admet_tox_contract.md
automation/tdc_admet_tox_execution_budget.md
EOF
)
export FRAMEWORK_RUNTIME_IMAGE="${DEEPSCIENTIST_RUNTIME_IMAGE:-deepscientist:tdc-runtime-ready}"
export FRAMEWORK_DOCKER_ARGS=$(cat <<'EOF'
--user
0:0
EOF
)
export FRAMEWORK_NEEDS_HOST_CODEX="1"
export FRAMEWORK_NATIVE_ENTRYPOINT="ds init -> ds new -> ds run run-experiment --runner codex"
export FRAMEWORK_NATIVE_ENTRYPOINT_FILE="src/deepscientist/cli.py"
export FRAMEWORK_NATIVE_ENTRYPOINT_SOURCE="README.md"
export FRAMEWORK_PROVIDER_INJECTION="DeepScientist official CodexRunner reads the minimal isolated /codex-home/config.toml"
export FRAMEWORK_NATIVE_LOG_MARKER="DEEPSCIENTIST_NATIVE_CODEX_RUNNER_TDC"
export FRAMEWORK_NATIVE_PROCESS_MARKERS=$(cat <<'EOF'
NATIVE_CMD> ds --home /workspace/.deepscientist init
NATIVE_CMD> ds --home /workspace/.deepscientist new
NATIVE_CMD> timeout 7000s ds --home /workspace/.deepscientist run run-experiment
EOF
)
export FRAMEWORK_EXECUTOR_KIND="framework_internal_codex_runner"
export FRAMEWORK_COMMAND_LABEL="ds --home /workspace/.deepscientist run run-experiment --runner codex"
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
export PATH="/opt/researchclaweval-node/bin:$PATH"
export DEEPSCIENTIST_CODEX_BINARY="/opt/researchclaweval-node/bin/codex"
DS_HOME=/workspace/.deepscientist
QUEST_ID="tdc-admet-tox-${TDC_ADMET_TOX_EVAL_VARIANT:-gpt}-native"
echo "DEEPSCIENTIST_NATIVE_CODEX_RUNNER_TDC"
test -s /opt/deepscientist-tdc-home.tar
tar -xpf /opt/deepscientist-tdc-home.tar -C /workspace
export UV_OFFLINE=1
mkdir -p /workspace/logs
printf 'DeepScientist native handoff started\n' > /workspace/logs/native_execution.log
PS4='NATIVE_CMD> '
set -x
ds --home "$DS_HOME" init
sed -i 's#config_dir: ~/.codex#config_dir: /codex-home#' "$DS_HOME/config/runners.yaml"
grep -Fq 'config_dir: /codex-home' "$DS_HOME/config/runners.yaml"
ds --home "$DS_HOME" new \
  "Execute the mounted TDC-ADMET-Tox contract through DeepScientist's native research workflow." \
  --quest-id "$QUEST_ID"
timeout 7000s ds --home "$DS_HOME" run run-experiment \
  --quest-id "$QUEST_ID" \
  --runner codex \
  --model "$OPENAI_MODEL" \
  --message "Read these exact mounted files before doing anything else: /workspace/TDC_ADMET_TOX_BRIEF.md, /workspace/automation/tdc_admet_tox_contract.md, /workspace/automation/tdc_admet_tox_execution_budget.md, and every /workspace/docs/tdc_admet_tox_*.md file. The files exist under /workspace as absolute paths; use Read or Bash with absolute paths. DeepScientist must own hypothesis generation, 2 to 4 bounded foreground experiments, validation comparison, selection, runnable final prediction generation, traceable paper writing, and framework-stage self-audit. Use only visible SMILES and installed libraries. Never create score.json, access another Topic, install packages, call public internet, or start a fifth configuration. Record framework_internal_model as $OPENAI_MODEL and framework_internal_api_base_url as $OPENAI_BASE_URL."
QUEST_DIR="$DS_HOME/quests/$QUEST_ID"
if [[ -f "$QUEST_DIR/predictions.csv" ]]; then
  cp -a "$QUEST_DIR/predictions.csv" "$QUEST_DIR/experiment_trace.json" "$QUEST_DIR/paper.md" /workspace/
  for handoff in research_idea.json final_report.md environment.json; do
    if [[ -f "$QUEST_DIR/$handoff" ]]; then
      cp -a "$QUEST_DIR/$handoff" /workspace/
    fi
  done
  if [[ -d "$QUEST_DIR/runs" ]]; then
    cp -a "$QUEST_DIR/runs" /workspace/
  fi
  if [[ -d "$QUEST_DIR/logs" ]]; then
    cp -a "$QUEST_DIR/logs" /workspace/
  fi
  if [[ -d "$QUEST_DIR/experiments" ]]; then
    cp -a "$QUEST_DIR/experiments" /workspace/
  fi
fi
test -s /workspace/predictions.csv
test -s /workspace/experiment_trace.json
test -s /workspace/paper.md
if [[ -f /workspace/experiments/main/tdc_admet_tox_runner.py && -L /workspace/experiments/main/tdc_admet_tox_runner.py ]]; then
  rm -f /workspace/experiments/main/tdc_admet_tox_runner.py
  cp -aL "$QUEST_DIR/experiments/main/tdc_admet_tox_runner.py" /workspace/experiments/main/tdc_admet_tox_runner.py
fi
find /workspace -maxdepth 4 -type l -name "*.py" -delete || true
printf 'DeepScientist native handoff promoted\n' >> /workspace/logs/native_execution.log
echo "DEEPSCIENTIST_QUEST_HANDOFF_PROMOTED_TDC"
EOF
)
exec "$ROOT/real_eval/scripts/tdc_admet_tox_framework_fullrun.sh"
