#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
export FRAMEWORK_NAME="DeepScientist"
export FRAMEWORK_SLUG="05_deepscientist_topic2_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 05)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
DeepScientist/DEEPSCIENTIST_BRIEF.md
docs/topic2_summary.md
automation/topic2_contract.md
automation/topic2_execution_budget.md
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="deepscientist:runtime-ready"
export FRAMEWORK_DOCKER_ARGS=$(cat <<'EOF'
--user
0:0
-v
/home/jianbiao/.nvm/versions/node/v24.16.0:/opt/researchclaweval-node:ro
EOF
)
export FRAMEWORK_NEEDS_HOST_CODEX="1"
export FRAMEWORK_NATIVE_ENTRYPOINT="ds init; ds new; ds run experiment --runner codex"
export FRAMEWORK_KIMI_INJECTION="DeepScientist official CodexRunner reads the injected /codex-home/config.toml provider"
export FRAMEWORK_NATIVE_LOG_MARKER="DEEPSCIENTIST_NATIVE_CODEX_RUNNER"
export FRAMEWORK_EXECUTOR_KIND="framework_cli"
export FRAMEWORK_COMMAND_LABEL="ds --home /workspace/.deepscientist run experiment --runner codex"
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
export PATH="/opt/researchclaweval-node/bin:$PATH"
export NODE_PATH="/opt/researchclaweval-node/lib/node_modules"
export DEEPSCIENTIST_CODEX_BINARY="/opt/researchclaweval-node/bin/codex"
DS_HOME=/workspace/.deepscientist
QUEST_ID=mountaincar-continuous
echo "DEEPSCIENTIST_NATIVE_CODEX_RUNNER"
ds --home "$DS_HOME" init
git config --global user.name "DeepScientist"
git config --global user.email "deepscientist@localhost"
sed -i 's#config_dir: ~/.codex#config_dir: /codex-home#' "$DS_HOME/config/runners.yaml"
grep -Fq 'config_dir: /codex-home' "$DS_HOME/config/runners.yaml"
python3 - "$DS_HOME/config/runners.yaml" <<'PY'
import sys
from pathlib import Path
import yaml
p = Path(sys.argv[1])
d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
d.setdefault("codex", {})["tool_call_budget"] = 120
p.write_text(yaml.safe_dump(d, default_flow_style=False), encoding="utf-8")
print("codex tool_call_budget set to 120")
PY
python3 - <<'PY'
from pathlib import Path
p = Path('/codex-home/config.toml')
s = p.read_text(encoding='utf-8')
if 'background_terminal_max_timeout' not in s:
    p.write_text(s + '\nbackground_terminal_max_timeout = 3600\n')
    print('codex background_terminal_max_timeout set to 3600')
PY
ds --home "$DS_HOME" new "Execute the MountainCar-Continuous contract in /workspace through DeepScientist and produce the complete framework-owned handoff." --quest-id "$QUEST_ID"
QUEST_YAML="$DS_HOME/quests/$QUEST_ID/quest.yaml"
if [[ -f "$QUEST_YAML" ]]; then
  python3 -c "
import yaml, sys
p = sys.argv[1]
d = yaml.safe_load(open(p)) or {}
d['baseline_gate'] = 'waived'
open(p, 'w').write(yaml.dump(d, default_flow_style=False))
print('baseline_gate set to waived')
" "$QUEST_YAML"
fi
set +e
cat > /workspace/DEEPSCIENTIST_TASK_BRIEF.md <<BRIEF
Follow the Topic 2 contract exactly:
- Read DEEPSCIENTIST_BRIEF.md, docs/topic2_summary.md, automation/topic2_contract.md, and automation/topic2_execution_budget.md.
- Use the injected evaluation provider only.
- Write /workspace/research_idea.json before the first experiment (hypothesis, method_rationale, expected_failure_modes, comparison_logic).
- Run real training experiments using the starter code at /workspace/src. Save exactly five checkpoints directly at /workspace/checkpoints/config-42-0.pkl ... /workspace/checkpoints/config-42-4.pkl.
- Write /workspace/experiment_trace.json and /workspace/final_report.md at root. experiment_trace.json must set:
  framework_native_execution=true, consumed_topic_input=true, workspace_trace_root="/workspace",
  framework_internal_model=$OPENAI_MODEL, framework_internal_api_base_url=$OPENAI_BASE_URL,
  experiments as a JSON array of one or more objects each with string "experiment_id", selected_experiment_id matching one of them,
  idea_artifact="research_idea.json", idea_locked_before_experiments=true.
The host creates score.json after exit.
BRIEF

cat > /workspace/DEEPSCIENTIST_CONTINUE_BRIEF.md <<BRIEF
Continue the same MountainCar-Continuous quest from the current workspace. Do not restart from scratch. Finish or repair experiments if needed, promote the best result to exactly five checkpoints directly at /workspace/checkpoints/config-42-0.pkl ... /workspace/checkpoints/config-42-4.pkl, delete other checkpoint sets, and write any missing root files: experiment_trace.json and final_report.md. experiment_trace.json must set framework_native_execution=true, consumed_topic_input=true, workspace_trace_root="/workspace", framework_internal_model=$OPENAI_MODEL, framework_internal_api_base_url=$OPENAI_BASE_URL, experiments as an array where each item has a string "experiment_id", selected_experiment_id matching one of them, idea_artifact="research_idea.json", idea_locked_before_experiments=true.
BRIEF

# Run the native DeepScientist codex experiment runner until the handoff is complete.
attempt=0
max_attempts=5
missing=1
while [[ $attempt -lt $max_attempts ]]; do
  attempt=$((attempt+1))
  message_file=/workspace/DEEPSCIENTIST_TASK_BRIEF.md
  if [[ -f /workspace/research_idea.json ]]; then
    message_file=/workspace/DEEPSCIENTIST_CONTINUE_BRIEF.md
  fi
  echo "DeepScientist native run attempt ${attempt}/${max_attempts}"
  set +e
  timeout "${TOPIC2_FRAMEWORK_TIMEOUT:-7200}s" ds --home "$DS_HOME" run experiment \
    --quest-id "$QUEST_ID" --runner codex --model "$OPENAI_MODEL" \
    --message "Read $message_file and execute it fully. Use only the injected evaluation provider."
  ds_rc=$?
  set -e
  missing=0
  [[ -f /workspace/research_idea.json ]] || missing=1
  [[ -f /workspace/experiment_trace.json ]] || missing=1
  [[ -f /workspace/final_report.md ]] || missing=1
  count=$(find /workspace/checkpoints -maxdepth 1 -name 'config-42-*.pkl' 2>/dev/null | wc -l)
  [[ "$count" -eq 5 ]] || missing=1
  if [[ "$missing" -eq 0 ]]; then
    echo "DeepScientist native handoff complete (attempt ${attempt})"
    ds_rc=0
    break
  fi
  if [[ "$ds_rc" -ne 0 ]]; then
    echo "DeepScientist runner exited nonzero (${ds_rc}); retrying with a fresh codex turn"
  else
    echo "DeepScientist handoff incomplete (attempt ${attempt}); continuing native experiment run"
  fi
done

if [[ "$missing" -ne 0 ]]; then
  echo "DeepScientist did not produce a complete Topic2 handoff after ${max_attempts} native attempts."
  exit 42
fi
find /workspace/checkpoints -maxdepth 1 -name '*.pkl' ! -name 'config-42-*.pkl' -delete
EOF
)
exec "$ROOT"/real_eval/scripts/topic2_framework_fullrun.sh