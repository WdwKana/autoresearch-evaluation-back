#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
export FRAMEWORK_NAME="AI-Scientist-v2"
export FRAMEWORK_SLUG="02_ai_scientist_v2_babylm_gpt_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 02)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
automation/babylm_method_free_contract.md
real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py
real_eval/adapters/ai_scientist_v2/patch_semantic_scholar_bounded.py
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="ai-scientist-v2:runtime-ready"
export FRAMEWORK_NATIVE_ENTRYPOINT="perform_ideation_temp_free.py -> launch_scientist_bfts.py"
export FRAMEWORK_PROVIDER_INJECTION="ai_scientist.llm OpenAI client configured from OPENAI_BASE_URL, OPENAI_API_KEY, and OPENAI_MODEL. GPU visibility: the cards declared in REAL_EVAL_ALLOWED_GPUS (device-level docker confinement in the runner), renumbered from 0 inside the container."
export FRAMEWORK_NATIVE_LOG_MARKER="AI_SCIENTIST_V2_BABYLM_GPT_NATIVE"
export FRAMEWORK_EXECUTOR_KIND="framework_cli"
export FRAMEWORK_COMMAND_LABEL="python ai_scientist/perform_ideation_temp_free.py; python launch_scientist_bfts.py"
# CUDA_VISIBLE_DEVICES used to be hardcoded to 0,1,2,3 -- other tenants' cards on
# this host. The runner now confines the container at the docker device level
# (opt-in via REAL_EVAL_ALLOWED_GPUS), and inside a confined container the
# allowed card is index 0.
export FRAMEWORK_DOCKER_ARGS=$(cat <<'EOF'
-e
AI_SCIENTIST_BABYLM_METHOD_FREE=1
-e
CUDA_VISIBLE_DEVICES=0
EOF
)
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
echo "AI_SCIENTIST_V2_BABYLM_GPT_NATIVE"
python3 real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py
echo "[baby-gpt-wrapper] shared adapter applied"
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
# Only inject the BabyLM-specific contract
marker = "# Define the initial idea generation prompt"
mandatory = '''system_prompt += """

BabyLM method-free ideation contract: propose 2-4 materially different experiments of your own design and no others. Choose the hypothesis, method families, representations, architectures, and configuration details yourself from installed resources. Write a framework-authored research_idea.json before the first experiment with the rationale, expected failure modes, and comparison logic. Use only the fixed split. The primary metric is WORD-LEVEL validation perplexity; character-level or subword-level is not accepted. Do not use downloads, package installation, external datasets, or remote calls from experiment code. The generated program must execute all framework-selected experiments synchronously, select by best word-level validation perplexity, and write research_idea.json, experiment_trace.json, and final_report.md at /workspace. Do not copy a host-prescribed algorithm into the idea.
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
# The MANDATORY BABYLM EXECUTION CONTRACT block that used to be appended to
# task_desc here was REMOVED (2026-09-18). task_desc is the one input the native
# judge (parse_exec_result) sees; psydef runs 112949/115325 vs 122907 showed a
# judge-visible contract checklist turns every executed node into a
# "compliance bug" (0/16 -> first draft accepted once removed), while the
# coder-only implementation guideline below already carries every fact.
#
# This wrapper's design is "2-4 configurations in ONE program" (the same
# two-experiments design the psydef wrapper carries upstream), so stage 1 is
# the whole experiment: stop after it and skip the multi-seed replay exactly
# as the psydef wrapper does. Stage 2's native goal (add HuggingFace datasets)
# would contradict the fixed-dataset contract anyway.
old = '''        ) = self.parse_stage_names(current_substage.name)
        if main_stage_num == 4:'''
new = '''        ) = self.parse_stage_names(current_substage.name)
        if os.getenv("AI_SCIENTIST_BABYLM_METHOD_FREE") == "1":
            return None
        if main_stage_num == 4:'''
if old not in text:
    raise SystemExit("AI-Scientist-v2 final-stage insertion point not found")
text = text.replace(old, new, 1)
old = '                            if current_substage.stage_number in [1, 2, 3, 4]:'
new = '''                            if (
                                current_substage.stage_number in [1, 2, 3, 4]
                                and os.getenv("AI_SCIENTIST_BABYLM_METHOD_FREE") != "1"
                            ):'''
if old not in text:
    raise SystemExit("AI-Scientist-v2 multi-seed skip insertion point not found")
text = text.replace(old, new, 1)
manager_path.write_text(text, encoding="utf-8")

parallel_path = Path(sys.argv[7])
text = parallel_path.read_text(encoding="utf-8")
old = '''    def _prompt_environment(self):
        pkgs = ['''
new = '''    def _prompt_environment(self):
        if os.getenv("AI_SCIENTIST_BABYLM_METHOD_FREE") == "1":
            return {
                "Installed Packages": (
                    "PyTorch, HuggingFace Transformers, numpy, and standard library. "
                    "Do not use downloads, package installation, external datasets, or remote calls from experiment code."
                )
            }
        pkgs = ['''
if old not in text:
    raise SystemExit("AI-Scientist-v2 environment-prompt insertion point not found")
text = text.replace(old, new, 1)
old = '''    def _prompt_impl_guideline(self):
        impl_guideline = ['''
new = '''    def _prompt_impl_guideline(self):
        if os.getenv("AI_SCIENTIST_BABYLM_METHOD_FREE") == "1":
            return {
                "Implementation guideline": [
                    "Write one self-contained Python program to train a language model on the BabyLM dataset.",
                    "Load only /data/BabyLM-2026-Strict-Small and the contract. Dataset facts: the directory contains ONLY .txt files (training files end with .train.txt); there is NO separate validation directory. Read every .txt file (filter by extension), split the loaded text into train/validation yourself (for example hold out 10% of lines), never catch file-reading exceptions silently (print and raise), and after loading verify the data is non-empty and print the train/validation token counts.",
                    "Do not use downloads, package installation, pretrained models, external datasets, or remote calls from the experiment code.",
                    "Run exactly 2-4 materially different configurations selected by the framework's research idea; do not use a host-prescribed algorithm.",
                    "The primary metric is WORD-LEVEL validation perplexity (character-level or subword-level perplexity is not accepted); print it for each configuration and select the best configuration by it.",
                    "Have the program itself write /workspace/research_idea.json BEFORE running the experiments (a JSON object with non-empty string fields hypothesis, method_rationale, expected_failure_modes, comparison_logic), then /workspace/experiment_trace.json and /workspace/final_report.md after the experiments.",
                    "experiment_trace.json schema (host-validated, format facts): a JSON object whose experiments field is a JSON ARRAY (a list, not a dict) of 2-4 objects, each with experiment_id (string), name, and validation_perplexity (number); selected_experiment_id must equal one of those experiment_id values; the object must also set framework_native_execution=true, consumed_topic_input=true, workspace_trace_root='/workspace', idea_artifact='research_idea.json', idea_locked_before_experiments=true, and framework_internal_model / framework_internal_api_base_url copied from the OPENAI_MODEL / OPENAI_BASE_URL environment variables. All JSON must be strict (no NaN or Infinity; use null).",
                    "Important code structure requirements: do NOT place execution code behind an if __name__ == '__main__': guard -- the native interpreter runs the file via exec, where that condition is false and nothing would execute. All code must run at global scope or from functions called at global scope, so the script executes immediately when run without any special entry point.",
                    "Data saving requirements: the code should start with import os; working_dir = os.path.join(os.getcwd(), 'working'); os.makedirs(working_dir, exist_ok=True). Save the metrics you compute (at least per-configuration validation perplexity per epoch plus training losses) as numpy arrays with np.save(os.path.join(working_dir, 'experiment_data.npy'), experiment_data), using the structure experiment_data = {'<config_name>': {'metrics': {'train': [], 'val': []}, 'losses': {'train': [], 'val': []}}}; the native metric parser and plotting step read this file.",
                    "At the end of the program print a verification block: each experiment_id with its word-level validation perplexity, the selected_experiment_id, and the byte size of each of the three root files you wrote, so the execution log itself evidences what was produced.",
                    "Be aware of the running time: the whole program must finish within 60 minutes on a single GPU; size the models and epochs accordingly.",
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
    if os.getenv("AI_SCIENTIST_BABYLM_METHOD_FREE") == "1":
        required = (
            "/workspace/research_idea.json",
            "/workspace/experiment_trace.json",
            "/workspace/final_report.md",
        )
        missing = [path for path in required if not os.path.isfile(path)]
        if missing:
            raise RuntimeError(
                "Native BabyLM BFTS exited without its complete root handoff: "
                + ", ".join(missing)
            )
        # No host-side repair here. The NaN->null rewriting and the trace-field
        # backfill that used to run at this point were removed (2026-09-18):
        # they edited framework-authored artifacts after the fact, which the
        # contract boundary forbids (same reasoning as the removed ARC/psydef
        # exit_delivery_check). The host validator judges the files exactly as
        # the framework left them.
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
# Bound Semantic Scholar 429 backoff (same adapter ARC/psydef/TDC wrappers use);
# without it run 20260918_045654 sat in 400-500s backoffs and would have
# exhausted the 1800s ideation budget.
python3 real_eval/adapters/ai_scientist_v2/patch_semantic_scholar_bounded.py
rm -f ai_scientist/ideas/babylm_topic.json
# Increase max_tokens to avoid truncation of long GPT responses
python3 -c "
from pathlib import Path
llm = Path('ai_scientist/llm.py')
text = llm.read_text()
text = text.replace('MAX_NUM_TOKENS = 4096', 'MAX_NUM_TOKENS = 16384')
llm.write_text(text)
print('Increased MAX_NUM_TOKENS to 16384')
"
mkdir -p ai_scientist/ideas
cat > ai_scientist/ideas/babylm_topic.md <<'MARKDOWN'
# Title: Language Model Optimization for BabyLM Strict-Small

## Keywords
language model, autoregressive, BabyLM, perplexity, multi-domain

## TL;DR
Train language models on BabyLM Strict-Small. Compare 2-4 configurations, measure word-level perplexity.

## Abstract
This project trains language models on the BabyLM 2026 Strict-Small dataset (10M words, 6 domains). The framework selects the algorithm family, architecture, hyperparameters, and training procedure. The evaluation metric is word-level validation perplexity on a held-out split. The framework must compare 2-4 materially different configurations. The host does not prescribe an algorithm, architecture, hyperparameter, baseline, or experiment order. Use the dataset at /data/BabyLM-2026-Strict-Small. Write and lock research_idea.json before the first experiment. Write experiment_trace.json with word-level validation_perplexity for each experiment, and final_report.md.
MARKDOWN
timeout "${AI_SCIENTIST_V2_BABYLM_IDEATION_TIMEOUT_SECONDS:-1800}s" \
  python ai_scientist/perform_ideation_temp_free.py \
  --workshop-file ai_scientist/ideas/babylm_topic.md \
  --model "$OPENAI_MODEL" \
  --max-num-generations 1 \
  --num-reflections 2
test -s ai_scientist/ideas/babylm_topic.json
echo "AI_SCIENTIST_V2_BABYLM_IDEA_OK"
python3 - bfts_config.yaml "$OPENAI_MODEL" <<'PY'
from pathlib import Path
import sys
import yaml

path = Path(sys.argv[1])
model = sys.argv[2]
config = yaml.safe_load(path.read_text(encoding="utf-8"))
config["exp_name"] = "babylm"
config["generate_report"] = False
config["agent"]["num_workers"] = 1
config["agent"]["steps"] = 3
config["agent"]["stages"]["stage1_max_iters"] = 20
config["agent"]["search"]["num_drafts"] = 3
config["agent"]["search"]["debug_prob"] = 0.5
config["agent"]["search"]["max_debug_depth"] = 3
config["agent"]["multi_seed_eval"]["num_seeds"] = 1
config["agent"]["code"]["max_tokens"] = 16000
config["exec"]["timeout"] = 3600
for section in ("code", "feedback", "vlm_feedback"):
    config["agent"][section]["model"] = model
config["report"]["model"] = model
path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
PY
timeout "${AI_SCIENTIST_V2_BABYLM_TIMEOUT_SECONDS:-14400}s" python launch_scientist_bfts.py \
  --load_ideas ai_scientist/ideas/babylm_topic.json \
  --idea_idx 0 \
  --skip_writeup \
  --skip_review \
  --model_agg_plots "$OPENAI_MODEL"
EOF
)
exec "$ROOT"/real_eval/scripts/babylm_framework_fullrun.sh