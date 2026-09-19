#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
export FRAMEWORK_NAME="AI-Scientist-v2"
export FRAMEWORK_SLUG="02_ai_scientist_v2_psydefdetect_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 02)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
AI-Scientist-v2/ai_scientist/ideas/psydefdetect_topic.md
docs/psydefdetect_literature_catalog.md
automation/psydefdetect_contract.md
automation/psydefdetect_execution_budget.md
real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py
real_eval/adapters/ai_scientist_v2/patch_semantic_scholar_bounded.py
real_eval/adapters/ai_scientist_v2/patch_ideation_action_format.py
real_eval/adapters/ai_scientist_v2/exit_delivery_check.py
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="ai-scientist-v2:runtime-ready"
export FRAMEWORK_DOCKER_ARGS=$(cat <<'EOF'
-e
AI_SCIENTIST_LOCAL_LITERATURE_CATALOG=/workspace/docs/psydefdetect_literature_catalog.md
-e
AI_SCIENTIST_PSYDEFDETECT_TWO_EXPERIMENTS=1
EOF
)
export FRAMEWORK_NATIVE_ENTRYPOINT="perform_ideation_temp_free.py -> launch_scientist_bfts.py"
export FRAMEWORK_PROVIDER_INJECTION="ai_scientist.llm OpenAI client configured from OPENAI_BASE_URL, OPENAI_API_KEY, and OPENAI_MODEL"
export FRAMEWORK_NATIVE_LOG_MARKER="AI_SCIENTIST_V2_NATIVE_BFTS"
export FRAMEWORK_EXECUTOR_KIND="framework_cli"
export FRAMEWORK_COMMAND_LABEL="python ai_scientist/perform_ideation_temp_free.py; python launch_scientist_bfts.py"
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
echo "AI_SCIENTIST_V2_NATIVE_BFTS"
python3 real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py
python3 real_eval/adapters/ai_scientist_v2/patch_semantic_scholar_bounded.py
# Ideation parser: accept markdown-decorated ACTION/ARGUMENTS labels (run
# fullrun_psydef_02_ds_r5_20260919_212250 lost a complete idea to "**Action**:").
python3 real_eval/adapters/ai_scientist_v2/patch_ideation_action_format.py
echo "[psydef-wrapper] shared adapter applied"
# Ideation output cap: upstream llm.py hardcodes MAX_NUM_TOKENS = 4096. A model
# that reasons before answering spends part of that on reasoning, and its
# FinalizeIdea JSON is cut mid-string ("Unterminated string", 0 ideas: run
# fullrun_psydef_02_ds_r5_20260919_212837). Same remedy the maintainers' BabyLM
# wrapper already applies.
python3 - <<'PYTOK'
from pathlib import Path
llm = Path("ai_scientist/llm.py")
text = llm.read_text(encoding="utf-8")
if "MAX_NUM_TOKENS = 4096" not in text and "MAX_NUM_TOKENS = 16384" not in text:
    raise SystemExit("MAX_NUM_TOKENS anchor not found in ai_scientist/llm.py")
llm.write_text(text.replace("MAX_NUM_TOKENS = 4096", "MAX_NUM_TOKENS = 16384"), encoding="utf-8")
print("[psydef-wrapper] ideation MAX_NUM_TOKENS = 16384")
PYTOK
python3 - ai_scientist/llm.py "$OPENAI_MODEL" ai_scientist/utils/token_tracker.py ai_scientist/perform_ideation_temp_free.py ai_scientist/tools/semantic_scholar.py ai_scientist/treesearch/agent_manager.py ai_scientist/treesearch/parallel_agent.py launch_scientist_bfts.py ai_scientist/treesearch/backend/backend_openai.py ai_scientist/treesearch/interpreter.py <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
model = sys.argv[2]
text = path.read_text(encoding="utf-8")
if f'"{model}"' not in text:
    text = text.replace("AVAILABLE_LLMS = [", f'AVAILABLE_LLMS = [\n    "{model}",', 1)
text = text.replace('elif "gpt" in model:', 'elif "gpt" in model or model == "' + model + '":')
text = text.replace(
    "return openai.OpenAI(), model",
    'return openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url=os.environ["OPENAI_BASE_URL"]), model',
)
path.write_text(text, encoding="utf-8")

tracker_path = Path(sys.argv[3])
# Shared adapter (patch_ai_scientist_v2_common.py) already handles:
# - token tracker None safety (or 0)
# - hasattr/getattr usage field check
# Skip the inline patch to avoid conflict.
tracker_path.write_text(tracker_path.read_text(encoding="utf-8"), encoding="utf-8")

idea_path = Path(sys.argv[4])
text = idea_path.read_text(encoding="utf-8")
# Shared adapter (patch_ai_scientist_v2_common.py) already handles:
# - robust parser (action blocks + lenient JSON)
# - unclosed JSON fence
# - mandatory ACTION/ARGUMENTS format enforcement
# - literature search optional/offline
# Only inject the PsyDef-specific contract
marker = "# Define the initial idea generation prompt"
mandatory = '''system_prompt += """

PsyDefDetect method-free ideation contract: propose exactly two materially different experiments and no others. Choose the hypothesis, method families, representations, architectures, and configuration details yourself from installed resources. Write a framework-authored research_idea.json before the first experiment with the rationale, expected failure modes, and comparison logic. Use only the fixed split and official local scorer. Do not use downloads, package installation, external datasets, or remote calls from experiment code. The generated program must execute both framework-selected experiments synchronously, select by observed macro-F1, and write predictions.jsonl, score.json, experiment_trace.json, and final_report.md at /workspace. Do not copy a host-prescribed algorithm into the idea.
"""

# Define the initial idea generation prompt'''
if marker not in text:
    raise SystemExit("AI-Scientist-v2 ideation system-prompt insertion point not found")
text = text.replace(marker, mandatory, 1)
idea_path.write_text(text, encoding="utf-8")

semantic_path = Path(sys.argv[5])
text = semantic_path.read_text(encoding="utf-8")
if "from pathlib import Path\n" not in text:
    text = "from pathlib import Path\n" + text
# Shared adapter (patch_ai_scientist_v2_common.py) already handles:
# - semantic_scholar offline bypass and local catalog
# Skip the inline patch to avoid conflict.
semantic_path.write_text(text, encoding="utf-8")

manager_path = Path(sys.argv[6])
text = manager_path.read_text(encoding="utf-8")
if "import os\n" not in text:
    text = "import os\n" + text
# The MANDATORY PSYDEFDETECT EXECUTION CONTRACT block that used to be appended
# to task_desc here was REMOVED (2026-09-17). task_desc is the one input the
# native judge (parse_exec_result) sees, and every one of its facts is already
# in the coder-only implementation guideline below, so the block added nothing
# for the coder while handing the judge a compliance checklist: across runs
# 112949/115325 the judge flagged 16/16 executed-and-delivered nodes on
# contract hunting, including invented requirements. Contract compliance is
# the host validator's job (psydefdetect_framework_fullrun.sh); the judge
# returns to its native scope (bugs visible in the execution output).
old = '''        journal = self.journals[stage.name]
        # Terminate if max iterations reached'''
new = '''        journal = self.journals[stage.name]
        if (
            os.getenv("AI_SCIENTIST_PSYDEFDETECT_TWO_EXPERIMENTS") == "1"
            and stage.stage_number == 1
        ):
            handoff_complete = all(
                Path("/workspace", name).is_file()
                for name in ("score.json", "experiment_trace.json", "final_report.md")
            ) and any(
                Path("/workspace", name).is_file()
                for name in ("predictions.jsonl", "submission.csv")
            )
            if handoff_complete and len(journal.good_nodes) > 0:
                return True, "Completed PsyDefDetect BFTS with a native root handoff"
            if len(journal.nodes) < stage.max_iterations:
                return False, "PsyDefDetect implementation still requires a valid root handoff"
            self.current_stage = None
            return True, "No valid implementation within the PsyDefDetect recovery budget"
        # Terminate if max iterations reached'''
if old not in text:
    raise SystemExit("AI-Scientist-v2 two-attempt completion insertion point not found")
text = text.replace(old, new, 1)
old = '''        ) = self.parse_stage_names(current_substage.name)
        if main_stage_num == 4:'''
new = '''        ) = self.parse_stage_names(current_substage.name)
        if os.getenv("AI_SCIENTIST_PSYDEFDETECT_TWO_EXPERIMENTS") == "1":
            return None
        if main_stage_num == 4:'''
if old not in text:
    raise SystemExit("AI-Scientist-v2 final-stage insertion point not found")
text = text.replace(old, new, 1)
old = '                            if current_substage.stage_number in [1, 2, 3, 4]:'
new = '''                            if (
                                current_substage.stage_number in [1, 2, 3, 4]
                                and os.getenv("AI_SCIENTIST_PSYDEFDETECT_TWO_EXPERIMENTS") != "1"
                            ):'''
if old not in text:
    raise SystemExit("AI-Scientist-v2 multi-seed skip insertion point not found")
manager_path.write_text(text.replace(old, new, 1), encoding="utf-8")

parallel_path = Path(sys.argv[7])
text = parallel_path.read_text(encoding="utf-8")
old = '''    def _prompt_environment(self):
        pkgs = ['''
new = '''    def _prompt_environment(self):
        if os.getenv("AI_SCIENTIST_PSYDEFDETECT_TWO_EXPERIMENTS") == "1":
            return {
                "Installed Packages": (
                    "Use only Python standard library, numpy, pandas, scipy, and scikit-learn. "
                    "Do not import torch or use CUDA, pretrained models, downloads, package installation, "
                    "external datasets, or remote calls from experiment code."
                )
            }
        pkgs = ['''
if old not in text:
    raise SystemExit("AI-Scientist-v2 environment-prompt insertion point not found")
text = text.replace(old, new, 1)
old = '''    def _prompt_impl_guideline(self):
        impl_guideline = ['''
new = '''    def _prompt_impl_guideline(self):
        if os.getenv("AI_SCIENTIST_PSYDEFDETECT_TWO_EXPERIMENTS") == "1":
            return {
                "Implementation guideline": [
                    "Write one self-contained CPU-only Python program using standard library, numpy, pandas, scipy, and scikit-learn only.",
                    "Never import torch, sentence_transformers, transformers, or any package outside that allowlist.",
                    "Do not use pretrained models, embeddings, external datasets, downloads, package installation, or remote calls from the experiment code.",
                    "Load only /data/psydefdetect/PsyDefConv.json and /workspace/automation/psydefdetect_split.json.",
                    "PsyDefConv.json is a top-level list with row keys id, dialogue_id, dialogue, current_text, and integer label; select rows by matching split train_record_ids/eval_record_ids to row['id'].",
                    "Use current_text as the target text, optionally prepend dialogue turn text, and do not assume conversation_id/defense_mechanism fields.",
                    "Run exactly two materially different configurations selected by the framework's research idea; do not use a host-prescribed algorithm.",
                    "Invoke the official scorer for each prediction file exactly as: python /workspace/automation/scripts/run_psydefdetect_local_score.py --dataset-root /data/psydefdetect --split-manifest /workspace/automation/psydefdetect_split.json --predictions <that prediction file> --output-score <a per-experiment score json path>. All four arguments are required.",
                    "Run the scorer via subprocess with captured output, check its return code, and print its stdout and stderr so any scorer failure is visible in the execution log.",
                    "Select the higher observed psydefdetect_score and have the program itself write /workspace/predictions.jsonl, /workspace/score.json, /workspace/experiment_trace.json, and /workspace/final_report.md.",
                    "experiment_trace.json schema (host-validated, format facts): a JSON object whose experiments field is a JSON ARRAY (a list, not a dict) of 2-4 objects, each carrying a string experiment_id and its official psydefdetect_score; selected_experiment_id must equal one of those experiment_id values; the object must also set framework_native_execution=true, consumed_topic_input=true, workspace_trace_root='/workspace', and framework_internal_model / framework_internal_api_base_url copied from the OPENAI_MODEL / OPENAI_BASE_URL environment variables. Do not rewrite /workspace/research_idea.json.",
                    "At the end of the program print a verification block: the return code of each official scorer invocation, each experiment_id with its psydefdetect_score, the selected_experiment_id, and the byte size of each of the four root files you wrote, so the execution log itself evidences what was produced.",
                    "Print `psydefdetect_score: <selected numeric score>` after the four root artifacts are written so the native metric parser can evaluate the implementation.",
                    "Important code structure requirements: do NOT place execution code behind an if __name__ == '__main__': guard -- the native interpreter runs the file via exec, where that condition is false and nothing would execute. All code must run at global scope or from functions called at global scope, so the script executes immediately when run without any special entry point.",
                    "Data saving requirements: the code should start with import os; working_dir = os.path.join(os.getcwd(), 'working'); os.makedirs(working_dir, exist_ok=True). Save the metrics you compute (at least the official psydefdetect_score of each configuration, plus any per-class or validation metrics) as numpy arrays with np.save(os.path.join(working_dir, 'experiment_data.npy'), experiment_data), using the structure experiment_data = {'<config_name>': {'metrics': {...}, 'predictions': [...], 'ground_truth': [...]}}; the native metric parser and plotting step read this file.",
                    "Do not create plots yourself (the native pipeline plots from experiment_data.npy), and do not create synthetic datasets, background jobs, or runtime installations.",
                ]
            }
        impl_guideline = ['''
if old not in text:
    raise SystemExit("AI-Scientist-v2 implementation-prompt insertion point not found")
parallel_path.write_text(text.replace(old, new, 1), encoding="utf-8")

launch_path = Path(sys.argv[8])
text = launch_path.read_text(encoding="utf-8")
old = '''    perform_experiments_bfts(idea_config_path)
    experiment_results_dir = osp.join(idea_dir, "logs/0-run/experiment_results")'''
new = '''    perform_experiments_bfts(idea_config_path)
    if os.getenv("AI_SCIENTIST_PSYDEFDETECT_TWO_EXPERIMENTS") == "1":
        required = (
            "/workspace/score.json",
            "/workspace/experiment_trace.json",
            "/workspace/final_report.md",
        )
        prediction_ok = any(
            os.path.isfile(path)
            for path in ("/workspace/predictions.jsonl", "/workspace/submission.csv")
        )
        missing = [path for path in required if not os.path.isfile(path)]
        if missing or not prediction_ok:
            raise RuntimeError(
                "Native PsyDefDetect BFTS exited without its complete root handoff: "
                + ", ".join(missing or ["predictions.jsonl or submission.csv"])
            )
        save_token_tracker(idea_dir)
        raise SystemExit(0)
    experiment_results_dir = osp.join(idea_dir, "logs/0-run/experiment_results")'''
if old not in text:
    raise SystemExit("AI-Scientist-v2 post-BFTS insertion point not found")
launch_path.write_text(text.replace(old, new, 1), encoding="utf-8")

backend_path = Path(sys.argv[9])
text = backend_path.read_text(encoding="utf-8")
if "import os\n" not in text:
    text = text.replace("import logging\n", "import logging\nimport os\n", 1)
old = '''    client = get_ai_client(model_kwargs.get("model"), max_retries=0)
    filtered_kwargs: dict = select_values(notnone, model_kwargs)  # type: ignore'''
new = '''    injected_model = os.getenv("OPENAI_MODEL")
    if injected_model:
        model_kwargs["model"] = injected_model
    client = get_ai_client(model_kwargs.get("model"), max_retries=0)
    filtered_kwargs: dict = select_values(notnone, model_kwargs)  # type: ignore'''
if old not in text:
    raise SystemExit("AI-Scientist-v2 injected-model routing insertion point not found")
text = text.replace(old, new, 1)
old = '''    messages = opt_messages_to_list(system_message, user_message)

    if func_spec is not None:'''
new = '''    messages = opt_messages_to_list(system_message, user_message)
    # The GPT Chat-to-Responses provider maps a system message to instructions.
    # A system-only BFTS prompt would therefore have no Responses input.
    if system_message and user_message is None:
        messages = [{"role": "user", "content": system_message}]

    if func_spec is not None:'''
if old not in text:
    raise SystemExit("AI-Scientist-v2 system-only message projection insertion point not found")
backend_path.write_text(text.replace(old, new, 1), encoding="utf-8")

interpreter_path = Path(sys.argv[10])
# Shared adapter (patch_ai_scientist_v2_common.py) already handles:
# - interpreter global_scope (__name__, __file__)
# Skip the inline patch to avoid conflict.
interpreter_path.write_text(interpreter_path.read_text(encoding="utf-8"), encoding="utf-8")
PY
# Upstream ideation aborts the whole reflection loop on ANY unparsable reply
# (one malformed JSON -> "Stored 0 ideas": run fullrun_psydef_02_ds_r5_20260919_213122,
# where the model dropped a closing quote in a search query). The host does not
# repair the reply; like the maintainers' TDC wrapper it lets the framework's own
# ideation start over, at most 3 times. A stored idea list of "[]" counts as empty.
for ideation_attempt in 1 2 3; do
  rm -f ai_scientist/ideas/psydefdetect_topic.json
  timeout "${AI_SCIENTIST_V2_PSYDEFDETECT_IDEATION_TIMEOUT_SECONDS:-1800}s" \
    python ai_scientist/perform_ideation_temp_free.py \
    --workshop-file ai_scientist/ideas/psydefdetect_topic.md \
    --model "$OPENAI_MODEL" \
    --max-num-generations 1 \
    --num-reflections 2
  if python3 -c "import json,sys; d=json.load(open('ai_scientist/ideas/psydefdetect_topic.json')); sys.exit(0 if isinstance(d, list) and d else 1)" 2>/dev/null; then
    echo "[psydef-wrapper] ideation produced an idea on attempt $ideation_attempt"
    break
  fi
  echo "[psydef-wrapper] ideation produced 0 ideas on attempt $ideation_attempt"
done
test -s ai_scientist/ideas/psydefdetect_topic.json
python3 - ai_scientist/ideas/psydefdetect_topic.json <<'PY'
import json
import re
import sys

ideas = json.load(open(sys.argv[1], encoding="utf-8"))
if not isinstance(ideas, list) or len(ideas) != 1 or not isinstance(ideas[0], dict):
    raise SystemExit("AI-Scientist-v2 must finalize exactly one PsyDefDetect idea")
idea = ideas[0]
scope = "\n".join(str(idea.get(key, "")) for key in ("Title", "Abstract", "Short Hypothesis", "Experiments")).lower()
experiment_scope = str(idea.get("Experiments", "")).lower()
prohibited = (
    "sentence-transform",
    "minilm",
    "hugging face",
    "huggingface",
    "pretrained",
    "embedding",
    "torch",
    "download",
    "prompt-based",
    "openai api",
)
# Policy sentences often repeat the forbidden dependency names while explicitly
# prohibiting them. Only affirmative experiment sentences participate in this gate.
experiment_sentences = re.split(r"(?<=[.!?])\s+", experiment_scope)
found = []
for sentence in experiment_sentences:
    for term in prohibited:
        start = sentence.find(term)
        while start >= 0:
            prefix = sentence[:start]
            # A prohibition can mention the forbidden name without using it.
            if not re.search(
                r"\b(?:no|not|without|avoid|exclude|forbid|prohibit|never|do not|don't)\b[^.!?]{0,100}$",
                prefix,
            ):
                found.append(term)
                break
            start = sentence.find(term, start + len(term))
experiment_tokens = re.findall(r"\bexperiment\s+([1-9][0-9]*|[a-z])\b", experiment_scope)
experiment_numbers = set(experiment_tokens)
numbered_items = set(
    re.findall(r"(?m)^\s*([1-9][0-9]*)\s*[).:-]\s+", experiment_scope)
)
inline_items = set(
    re.findall(r"(?<![A-Za-z0-9])([1-9][0-9]*)\s*[).:-]\s+", experiment_scope)
)
structured_experiments = idea.get("Experiments")
structured_two_experiments = (
    isinstance(structured_experiments, list)
    and len(structured_experiments) == 2
)
two_experiments_declared = (
    len(experiment_numbers) == 2
    or numbered_items == {"1", "2"}
    or inline_items == {"1", "2"}
    or structured_two_experiments
)
if found or not two_experiments_declared:
    raise SystemExit(
        "AI-Scientist-v2 idea violates method-free two-experiment contract: "
        f"prohibited={found}, experiment_numbers={sorted(experiment_numbers)}"
    )
print("AI_SCIENTIST_V2_IDEA_CONTRACT_OK")
from pathlib import Path
native_idea = {
    "framework": "AI-Scientist-v2",
    "source_artifact": "ai_scientist/ideas/psydefdetect_topic.json",
    "hypothesis": idea.get("Short Hypothesis") or idea.get("Hypothesis") or idea.get("Abstract", ""),
    "method_rationale": idea.get("Experiments", ""),
    "expected_failure_modes": idea.get("Expected Failure Modes") or idea.get("Failure Modes") or "",
    "comparison_logic": idea.get("Comparison") or idea.get("Experiments", ""),
    "native_idea": idea,
}
Path("/workspace/research_idea.json").write_text(
    json.dumps(native_idea, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print("AI_SCIENTIST_V2_RESEARCH_IDEA_LOCKED")
PY
python3 - bfts_config.yaml "$OPENAI_MODEL" <<'PY'
from pathlib import Path
import sys
import yaml

path = Path(sys.argv[1])
model = sys.argv[2]
config = yaml.safe_load(path.read_text(encoding="utf-8"))
config["exp_name"] = "psydefdetect"
config["generate_report"] = False
config["agent"]["num_workers"] = 1
import os
# Two identical runs (fullrun_psydef_02_20260828_070449_p / _071419_p2) ended
# with the framework completing its 3 stage-1 iterations and never reaching a
# complete root handoff -- the budget the author tuned (presumably for
# kimi-k2.6) is too tight for the injected model. Same remedy as 02xARC
# (stage1 4 -> 12): give stage 1 room, overridable via env.
config["agent"]["steps"] = int(os.environ.get("PSYDEFDETECT_BFTS_STEPS", "3"))
config["agent"]["stages"]["stage1_max_iters"] = int(os.environ.get("PSYDEFDETECT_BFTS_STAGE1_ITERS", "8"))
# Bound stages 2-4 as the ARC wrapper does: `steps` is ignored whenever the
# upstream config carries stage*_max_iters (12/12/18), which would run past the
# 7200s wall clock and turn a delivered run into a timeout failure.
config["agent"]["stages"]["stage2_max_iters"] = int(os.environ.get("PSYDEFDETECT_BFTS_STAGE2_ITERS", "3"))
config["agent"]["stages"]["stage3_max_iters"] = int(os.environ.get("PSYDEFDETECT_BFTS_STAGE3_ITERS", "3"))
config["agent"]["stages"]["stage4_max_iters"] = int(os.environ.get("PSYDEFDETECT_BFTS_STAGE4_ITERS", "3"))
config["agent"]["search"]["num_drafts"] = 1
config["agent"]["search"]["debug_prob"] = 1.0
config["agent"]["search"]["max_debug_depth"] = 2
config["agent"]["multi_seed_eval"]["num_seeds"] = 1
config["agent"]["expose_prediction"] = True
config["exec"]["timeout"] = 900
for section in ("code", "feedback", "vlm_feedback"):
    config["agent"][section]["model"] = model
config["report"]["model"] = model
path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
PY
timeout "${AI_SCIENTIST_V2_PSYDEFDETECT_TIMEOUT_SECONDS:-7200}s" python launch_scientist_bfts.py \
  --load_ideas ai_scientist/ideas/psydefdetect_topic.json \
  --idea_idx 0 \
  --skip_writeup \
  --skip_review \
  --model_agg_plots "$OPENAI_MODEL"
# exit_delivery_check DISABLED (2026-09-17): it backfills framework artifacts via
# the framework model after the native run ends, which the contract boundary
# forbids (same reasoning as the ARC wrapper's removal). Left out so the psydef
# control run measures native delivery only. Team decision on final disposition
# is pending; re-enable by restoring the line below.
# python3 real_eval/adapters/ai_scientist_v2/exit_delivery_check.py --workspace /workspace --topic psydefdetect || true

EOF
)
exec "$ROOT"/real_eval/scripts/psydefdetect_framework_fullrun.sh
