#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
EVOSCIENTIST_MODEL="${REAL_EVAL_FRAMEWORK_MODEL:-${REAL_EVAL_MODEL:-deepseek-v4-flash}}"
export FRAMEWORK_NAME="EvoScientist"
export FRAMEWORK_SLUG="07_evoscientist_topic2_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 07)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
EvoScientist/EVOSCIENTIST_BRIEF.md
EvoScientist/topic2_start_message.txt
docs/topic2_summary.md
automation/topic2_contract.md
automation/topic2_execution_budget.md
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="evoscientist:runtime-ready"
export FRAMEWORK_ENTRYPOINT="bash"
export FRAMEWORK_NATIVE_ENTRYPOINT="evoscientist --use-cwd --auto-mode"
export FRAMEWORK_KIMI_INJECTION="custom-openai provider reads CUSTOM_OPENAI_BASE_URL, CUSTOM_OPENAI_API_KEY, and EVOSCIENTIST_MODEL"
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
EVOSCIENTIST_USE_RESPONSES_API=true
-e
MPLCONFIGDIR=/tmp
-e
EVOSCIENTIST_LOG_LEVEL=info
-e
EVOSCIENTIST_MODEL=$EVOSCIENTIST_MODEL
EOF
)
export FRAMEWORK_COMMAND_LABEL="/opt/venv/bin/evoscientist --use-cwd -p @topic2_start_message.txt"
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
show_thinking: true
enable_async_subagents: false
YAML
prompt='# MountainCar-Continuous Native Evaluation Brief

This is a framework-capability evaluation. The framework'\''s documented native entrypoint must own hypothesis generation, experiment design, implementation, execution, comparison, selection, and the final report.

## Visible inputs

- `/workspace/src/`: Frozen starter code (train.py, policy.py, networks.py, helpers.py, config.yaml, __init__.py) — you may modify
- `/workspace/evaluate.py`: Read-only frozen evaluator (do not modify)
- `/workspace/automation/topic2_contract.md`
- `/workspace/automation/topic2_execution_budget.md`
- `/workspace/docs/topic2_summary.md`

## Task description

Improve the official Average Reward of MountainCarContinuous-v0, a reinforcement-learning task where a car must build momentum to reach a flag at the top of a hill. A runnable PPO Actor-Critic baseline is provided in src/. You may modify the training code, model architecture, hyperparameters, and add new research code. The environment has JAX, gymnax, flax, optax, and tensorflow_probability installed.

## Required deliverables

1. Exactly 5 valid trained checkpoints under /workspace/checkpoints/ (named config-42-0.pkl through config-42-4.pkl).
2. The corresponding config.yaml and all code under src/ that the evaluator needs to reconstruct the model.
3. Root-level research_idea.json, experiment_trace.json, and final_report.md.

## Constraints

- Do not modify evaluate.py or the Model class name in networks.py.
- The frozen evaluator asserts len(checkpoint_files) == 5.
- The host runs the frozen evaluator to produce the final score (Reward Mean, higher is better).
- Use only the injected evaluation provider for all internal API calls.
- Use the available tools directly (Read, Write, Bash). Never describe tool calls in prose; make the actual tool call.
- Do not install packages, access unmapped paths, or perform downloads.
- The framework owns the method choice; the host prescribes no algorithm family, feature representation, architecture, hyperparameters, or experiment sequence.

## Required native workflow

1. Propose a hypothesis using only the visible inputs.
2. Complete one or more materially distinct framework-chosen experimental configurations.
3. Immediately after the final experiment, select the best result and promote the selected artifacts.
4. Before exit, write root-level: /workspace/research_idea.json, /workspace/experiment_trace.json, /workspace/final_report.md.
5. In experiment_trace.json, record framework_internal_model and framework_internal_api_base_url. The host creates score.json after native exit.'
prompt+="
## TRACE ENV RULE
- framework_internal_model must equal the injected model: $OPENAI_MODEL
- framework_internal_api_base_url must equal the injected base URL: $OPENAI_BASE_URL
"
prompt+='

## FINAL ACTIONS REQUIRED
- After the last experiment, select the single best configuration. Delete every other checkpoint file. Keep exactly five files named /workspace/checkpoints/config-42-0.pkl through /workspace/checkpoints/config-42-4.pkl.
- Write /workspace/final_report.md before exiting. Do not stop until research_idea.json, experiment_trace.json, and final_report.md all exist at /workspace and exactly five config-42-*.pkl checkpoints are present.
'

set +e
timeout "${EVOSCIENTIST_MC_TIMEOUT:-7200}s" /opt/venv/bin/evoscientist --use-cwd -p "$prompt" --auto-mode --auto-approve --ui cli
ev_rc=$?
set -e
if [[ "$ev_rc" -ne 0 ]]; then exit "$ev_rc"; fi
find /workspace/checkpoints -maxdepth 1 -name '*.pkl' ! -name 'config-42-*.pkl' -delete
EOF
)
exec "$ROOT"/real_eval/scripts/topic2_framework_fullrun.sh