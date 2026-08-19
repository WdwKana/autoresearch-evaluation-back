#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
export FRAMEWORK_NAME="DeepScientist"
export FRAMEWORK_SLUG="05_deepscientist_arc_wbe_2026_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 05)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
DeepScientist/DEEPSCIENTIST_BRIEF.md
docs/arc_wbe_2026_summary.md
automation/arc_wbe_2026_contract.md
automation/arc_wbe_2026_execution_budget.md
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="deepscientist:runtime-ready"
export FRAMEWORK_DOCKER_ARGS=$(cat <<'EOF'
--user
0:0
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
export DEEPSCIENTIST_CODEX_BINARY="/opt/researchclaweval-node/bin/codex"
DS_HOME=/workspace/.deepscientist
QUEST_ID=arc-wbe-2026
echo "DEEPSCIENTIST_NATIVE_CODEX_RUNNER"
ds --home "$DS_HOME" init
sed -i 's#config_dir: ~/.codex#config_dir: /codex-home#' "$DS_HOME/config/runners.yaml"
grep -Fq 'config_dir: /codex-home' "$DS_HOME/config/runners.yaml"
ds --home "$DS_HOME" new "Execute the ARC-WBE-2026 contract in /workspace through DeepScientist and produce the complete framework-owned handoff." --quest-id "$QUEST_ID"
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
timeout "${ARC_WBE_2026_FRAMEWORK_TIMEOUT_SECONDS:-7200}s" \
  ds --home "$DS_HOME" run experiment --quest-id "$QUEST_ID" --runner codex --model "$OPENAI_MODEL" \
  --message "Read DEEPSCIENTIST_BRIEF.md, docs/arc_wbe_2026_summary.md, automation/arc_wbe_2026_contract.md, and automation/arc_wbe_2026_execution_budget.md. Use only the injected evaluation provider. Before the first experiment, write and lock research_idea.json. research_idea.json must be a top-level JSON object with non-empty hypothesis, method_rationale, expected_failure_modes, and comparison_logic fields. DeepScientist owns the hypothesis, method choice, experiment design, comparison, and final selection. Run 2-4 materially different experiments and write root-level research_idea.json, estimator.py, submission.json, experiment_trace.json, and final_report.md. experiment_trace.json must record framework_native_execution true, consumed_topic_input true as a boolean, workspace_trace_root \"/workspace\", framework_internal_model, framework_internal_api_base_url, experiments, selected_experiment_id, idea_artifact exactly \"research_idea.json\", and idea_locked_before_experiments true. mlp.weights is a list of 32 (256, 256) weight matrices. mlp.depth=32, mlp.width=256. The estimator.py predict(mlp) must return a fnp.ndarray of shape (32, 256) — predicted mean activation of each of the 256 hidden neurons in each of the 32 layers; a final-layer-only (256,) output is invalid. The scorer sandbox has only flopscope.numpy (import as fnp) — do NOT import numpy, scipy, or torch. flopscope arrays are immutable — do NOT use item assignment (arr[i] = ...) or indexed in-place updates. Build the result functionally using fnp.stack() or fnp.concatenate(). The host creates score.json after native exit."
EOF
)
exec "$ROOT"/real_eval/scripts/arc_framework_fullrun.sh
