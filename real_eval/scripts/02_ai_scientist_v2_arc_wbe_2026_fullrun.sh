#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
AI_SCIENTIST_MODEL="${REAL_EVAL_FRAMEWORK_MODEL:-${REAL_EVAL_MODEL:-kimi-k2.6}}"
export FRAMEWORK_NAME="AI-Scientist-v2"
export FRAMEWORK_SLUG="02_ai_scientist_v2_arc_wbe_2026_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 02)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
AI-Scientist-v2/ai_scientist/ideas/arc_wbe_2026_topic.md
docs/arc_wbe_2026_summary.md
automation/arc_wbe_2026_contract.md
automation/arc_wbe_2026_execution_budget.md
real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py
real_eval/adapters/ai_scientist_v2/patch_semantic_scholar_bounded.py
real_eval/adapters/ai_scientist_v2/exit_delivery_check.py
real_eval/adapters/ai_scientist_v2/patch_ideation_task_framing.py
real_eval/adapters/ai_scientist_v2/patch_bfts_delivery_contract.py
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="ai-scientist-v2:runtime-ready"
export FRAMEWORK_NATIVE_ENTRYPOINT="perform_ideation_temp_free.py; launch_scientist_bfts.py"
export FRAMEWORK_KIMI_INJECTION="ai_scientist.llm OpenAI-compatible client reads OPENAI_BASE_URL, OPENAI_API_KEY, and OPENAI_MODEL"
export FRAMEWORK_NATIVE_LOG_MARKER="AI_SCIENTIST_V2_NATIVE_BFTS"
export FRAMEWORK_EXECUTOR_KIND="framework_cli"
export FRAMEWORK_COMMAND_LABEL="python ai_scientist/perform_ideation_temp_free.py; python launch_scientist_bfts.py"
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
echo "AI_SCIENTIST_V2_NATIVE_BFTS"
python3 real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py
echo "[arc-wrapper] shared adapter applied"
python3 real_eval/adapters/ai_scientist_v2/patch_semantic_scholar_bounded.py
python3 real_eval/adapters/ai_scientist_v2/patch_bfts_delivery_contract.py
python3 - ai_scientist/llm.py "$OPENAI_MODEL" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
model = sys.argv[2]
text = path.read_text(encoding="utf-8")
if f'"{model}"' not in text:
    text = text.replace("AVAILABLE_LLMS = [", f"AVAILABLE_LLMS = [\n    \"{model}\",", 1)
text = text.replace('elif "gpt" in model:', 'elif "gpt" in model or model == "' + model + '":')
text = text.replace(
    'return openai.OpenAI(), model',
    'return openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url=os.environ["OPENAI_BASE_URL"]), model',
)
path.write_text(text, encoding="utf-8")
PY
python3 - ai_scientist/llm.py ai_scientist/treesearch/backend/backend_openai.py <<'PY'
from pathlib import Path
import sys

for raw in sys.argv[1:]:
    path = Path(raw)
    text = path.read_text(encoding="utf-8")
    if "from ai_scientist.gpt_responses_compat import chat_create" not in text:
        text = "from ai_scientist.gpt_responses_compat import chat_create\n" + text
    text = text.replace("client.chat.completions.create(", "chat_create(client,")
    path.write_text(text, encoding="utf-8")
PY
python3 - ai_scientist/utils/token_tracker.py <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
text = text.replace(
    "result.usage.completion_tokens_details.reasoning_tokens,",
    "result.usage.completion_tokens_details.reasoning_tokens or 0,",
)
text = text.replace(
    "result.usage.prompt_tokens_details.cached_tokens\n",
    "result.usage.prompt_tokens_details.cached_tokens or 0\n",
)
path.write_text(text, encoding="utf-8")
PY
python3 - ai_scientist/perform_ideation_temp_free.py <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
marker = "# Define the initial idea generation prompt"
addition = '''system_prompt += """

ARC-WBE-2026 native handoff contract: choose 2-4 materially different experiments from the framework-authored hypothesis, compare them using framework-visible evidence, and select one. Before experiment execution, the native idea will be locked as /workspace/research_idea.json. The implementation must write /workspace/estimator.py, /workspace/submission.json, /workspace/experiment_trace.json, and /workspace/final_report.md. The trace must include framework_native_execution=true, consumed_topic_input=true, workspace_trace_root='/workspace', the 2-4 experiments, selected_experiment_id, framework_internal_model from OPENAI_MODEL, framework_internal_api_base_url from OPENAI_BASE_URL, idea_artifact='research_idea.json', and idea_locked_before_experiments=true. The host does not prescribe an algorithm family, representation, architecture, hyperparameters, baseline, experiment order, or selected method.
"""

# Define the initial idea generation prompt'''
if marker not in text:
    raise SystemExit("AI-Scientist-v2 ARC handoff prompt insertion point not found")
path.write_text(text.replace(marker, addition, 1), encoding="utf-8")
PY
python3 - launch_scientist_bfts.py <<'PY'
from pathlib import Path
import sys

# Upstream copies experiment_results only "if os.path.exists(...)" but then
# removes it unconditionally, so a run whose stages produced no aggregated
# results directory crashes at the very end -- after all BFTS work is done
# (observed in runs fullrun_arc_02_bounded_20260827_{081051,082742_b,084434}).
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
old = '    shutil.rmtree(osp.join(idea_dir, "experiment_results"))'
new = (
    '    _arc_results_dir = osp.join(idea_dir, "experiment_results")\n'
    '    if osp.exists(_arc_results_dir):\n'
    '        shutil.rmtree(_arc_results_dir)'
)
if old in text:
    text = text.replace(old, new, 1)
else:
    print("SKIP: experiment_results cleanup insertion point not found")
old_kw = 'keywords = ["python", "torch", "mp", "bfts", "experiment"]'
new_kw = ('keywords = ["python", "torch", "mp", "bfts", "experiment"]\n'
          '    _arc_self_pids = {current_process.pid, current_process.ppid()}')
if old_kw in text and "_arc_self_pids" not in text:
    text = text.replace(old_kw, new_kw, 1)
old_sig = """            if any(keyword in cmdline for keyword in keywords):
                proc.send_signal(signal.SIGTERM)"""
new_sig = """            if any(keyword in cmdline for keyword in keywords) and proc.pid not in _arc_self_pids:
                proc.send_signal(signal.SIGTERM)"""
if old_sig in text:
    text = text.replace(old_sig, new_sig, 1)
else:
    print("SKIP: orphan-cleanup insertion point not found")
path.write_text(text, encoding="utf-8")
PY
python3 real_eval/adapters/ai_scientist_v2/patch_ideation_task_framing.py
rm -f ai_scientist/ideas/arc_wbe_2026_topic.json
timeout "${AI_SCIENTIST_V2_ARC_IDEATION_TIMEOUT_SECONDS:-1800}s" python ai_scientist/perform_ideation_temp_free.py \
  --workshop-file ai_scientist/ideas/arc_wbe_2026_topic.md \
  --model "$OPENAI_MODEL" \
  --max-num-generations 1 \
  --num-reflections 5
test -s ai_scientist/ideas/arc_wbe_2026_topic.json
python3 - ai_scientist/ideas/arc_wbe_2026_topic.json <<'PY'
from pathlib import Path
import json
import sys

ideas = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if not isinstance(ideas, list) or not ideas or not isinstance(ideas[0], dict):
    raise SystemExit("AI-Scientist-v2 did not finalize a native ARC research idea")
idea = ideas[0]
if not idea.get("Experiments"):
    raise SystemExit("AI-Scientist-v2 native idea does not define experiments")
if not (idea.get("Risk Factors and Limitations") or idea.get("Expected Failure Modes")):
    raise SystemExit("AI-Scientist-v2 native idea does not define failure modes")
print("AI_SCIENTIST_V2_ARC_IDEA_OK")
PY
python3 - ai_scientist/ideas/arc_wbe_2026_topic.json "$OPENAI_MODEL" "$OPENAI_BASE_URL" <<'PYSPEC'
from pathlib import Path
import json
import sys

# The delivery contract is injected only into the ideation system prompt, so the
# BFTS coding agent -- which loads this idea JSON and never sees that prompt --
# has no way to learn where artifacts must land (run
# fullrun_arc_02_bounded_20260828_054050 finished all stages and delivered
# nothing to /workspace). Carry the same requirements into the idea record the
# BFTS stages actually read. Host defines the output schema only; the method,
# experiments and results stay entirely framework-authored.
path = Path(sys.argv[1])
model, base_url = sys.argv[2], sys.argv[3]
ideas = json.loads(path.read_text(encoding="utf-8"))
spec = (
    "\n\nARC delivery contract (host output schema; the method remains yours). "
    "ALL FIVE files below are mandatory; a run missing ANY of them is scored as a "
    "total failure, so write submission.json and final_report.md even if brief:\n"
    "- write these five files at the workspace root /workspace: research_idea.json, "
    "estimator.py, submission.json, experiment_trace.json, final_report.md;\n"
    "- estimator.py must define `class Estimator` with `predict(self, mlp)` returning "
    "a (32, 256) numpy array; numpy and the standard library only (the official "
    "scorer provides nothing else); ship learned parameters beside it as .npz;\n"
    "- CRITICAL interface fact: the mlp argument is an OBJECT, not an array. "
    "np.asarray(mlp) raises 'float() argument must be ... not MLP' and forfeits the "
    "run (a prior attempt failed on all 100 evaluation MLPs exactly this way). Read "
    "mlp.weights -- an ordered list of per-layer (width, width) numpy weight "
    "matrices -- plus mlp.width, mlp.depth, and mlp.seed for any randomness. "
    "Design and test every experiment against this interface;\n"
    "- never return zeros/ones/full/empty constants and never use the words "
    "placeholder or fallback prediction (the scorer rejects them);\n"
    "- experiment_trace.json must contain framework_native_execution=true, "
    "consumed_topic_input=true, workspace_trace_root='/workspace', a list of 2-4 "
    "experiments each with a unique string experiment_id, selected_experiment_id "
    "matching one of them, framework_internal_model='" + model + "', "
    "framework_internal_api_base_url='" + base_url + "', "
    "idea_artifact='research_idea.json', idea_locked_before_experiments=true;\n"
    "- research_idea.json needs non-empty hypothesis, method_rationale, "
    "expected_failure_modes and comparison_logic."
)
changed = False
for idea in ideas if isinstance(ideas, list) else []:
    if isinstance(idea, dict) and "ARC delivery contract" not in str(idea.get("Experiments", "")):
        idea["Experiments"] = str(idea.get("Experiments", "")) + spec
        changed = True
if not changed:
    print("SKIP: no idea record to annotate")
path.write_text(json.dumps(ideas, indent=2), encoding="utf-8")
PYSPEC
python3 - bfts_config.yaml "$OPENAI_MODEL" <<'PY'
from pathlib import Path
import os
import sys
import yaml

path = Path(sys.argv[1])
model = sys.argv[2]
config = yaml.safe_load(path.read_text(encoding="utf-8"))
config["exp_name"] = "arc_wbe_2026"
config["generate_report"] = False
config["agent"]["num_workers"] = 1
config["agent"]["steps"] = 2
config["agent"]["expose_prediction"] = True
# `steps` alone does not bound the run: the four BFTS stages carry their own
# stage*_max_iters (upstream 20/12/12/18 = 62 iterations) and ignore `steps`
# when set. Two runs died at the wrapper timeout mid-stage-2/3 with nothing
# delivered. Bound every stage so the tree search converges and finalizes
# inside the topic's execution budget.
stages = dict(config["agent"].get("stages") or {})
for key, value in (
    # Stage 1 must be generous enough to reach a working implementation --
    # agent_manager aborts the whole run when it does not ("did not find a
    # working implementation after N iterations"); later stages only refine.
    # Upstream default is 20; 12 proved too tight: run 20260914_051027 burned
    # all 12 stage-1 iters (judge kept rejecting the permutation-consistency
    # methodology) and the whole run aborted before stage 2. 18 rebalances
    # toward upstream while still bounding the stage (fits the 9000s budget:
    # ~4min/iter + ~40min stages 2-4).
    # NOTE: the generic ARC wrapper forwards only whitelisted env vars into
    # the container, so these defaults are what actually apply unless that
    # whitelist is extended.
    ("stage1_max_iters", int(os.environ.get("ARC_WBE_2026_BFTS_STAGE1_ITERS", "18"))),
    ("stage2_max_iters", int(os.environ.get("ARC_WBE_2026_BFTS_STAGE2_ITERS", "4"))),
    ("stage3_max_iters", int(os.environ.get("ARC_WBE_2026_BFTS_STAGE3_ITERS", "3"))),
    ("stage4_max_iters", int(os.environ.get("ARC_WBE_2026_BFTS_STAGE4_ITERS", "3"))),
):
    stages[key] = value
config["agent"]["stages"] = stages
for section in ("code", "feedback", "vlm_feedback"):
    config["agent"][section]["model"] = model
config["report"]["model"] = model
# treesearch/journal.py falls back to a hardcoded "gpt-4o" whenever
# agent.summary / agent.select_node are absent (they are commented out in the
# upstream bfts_config.yaml), so materialize them, then force every remaining
# "model" key in the config onto the injected model.
for section in ("summary", "select_node"):
    entry = dict(config["agent"].get(section) or {})
    entry["model"] = model
    entry.setdefault("temp", 0.3)
    config["agent"][section] = entry

def set_all_models(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "model" and isinstance(value, str):
                node[key] = model
            else:
                set_all_models(value)
    elif isinstance(node, list):
        for item in node:
            set_all_models(item)

set_all_models(config)
path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
PY
timeout "${ARC_WBE_2026_FRAMEWORK_TIMEOUT_SECONDS:-3600}s" python launch_scientist_bfts.py \
  --load_ideas ai_scientist/ideas/arc_wbe_2026_topic.json \
  --idea_idx 0 \
  --skip_writeup \
  --skip_review \
  --model_agg_plots "$OPENAI_MODEL"
# The delivery bridge that stood here was removed. Its relocation records show
# the only paths it ever exercised were renaming idea.json to research_idea.json
# (schema still rejected: runs _075822/_131435/_143755) and promoting an
# alphabetically-last best_solution_*.py to estimator.py -- a host-side
# selection the contract reserves for the framework, biased toward stage-4
# ablation variants. The location-only relocation a bridge is legitimate for
# never occurred in any 02 run. Delivery is owned by the framework itself
# (spec in the idea record) with the exit delivery check as the backstop.
# Exit delivery check REMOVED (2026-09-07): it backfills framework artifacts
# via the framework model, which the contract forbids (arc_wbe_2026_contract.md
# line 43: "The host must not generate, repair, promote, or backfill
# framework-authored research artifacts"). Delivery is now owned entirely by
# the framework: the BFTS delivery-contract patch makes the agent produce the
# files itself in-run; anything it fails to produce is left honestly missing.

EOF
)
exec "$ROOT"/real_eval/scripts/arc_framework_fullrun.sh
