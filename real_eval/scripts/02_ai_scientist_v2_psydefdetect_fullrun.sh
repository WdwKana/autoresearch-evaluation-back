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
text = tracker_path.read_text(encoding="utf-8")
old = '''        self.token_counts[model]["prompt"] += prompt_tokens
        self.token_counts[model]["completion"] += completion_tokens
        self.token_counts[model]["reasoning"] += reasoning_tokens
        self.token_counts[model]["cached"] += cached_tokens'''
new = '''        self.token_counts[model]["prompt"] += prompt_tokens or 0
        self.token_counts[model]["completion"] += completion_tokens or 0
        self.token_counts[model]["reasoning"] += reasoning_tokens or 0
        self.token_counts[model]["cached"] += cached_tokens or 0'''
if old not in text:
    raise SystemExit("AI-Scientist-v2 token accounting insertion point not found")
text = text.replace(old, new, 1)
text = text.replace(
    'if hasattr(result.usage, "prompt_tokens_details")',
    'if getattr(result.usage, "prompt_tokens_details", None) is not None',
)
tracker_path.write_text(text, encoding="utf-8")

idea_path = Path(sys.argv[4])
text = idea_path.read_text(encoding="utf-8")
old = "arguments_json = json.loads(arguments_text)"
if text.count(old) != 2:
    raise SystemExit("AI-Scientist-v2 idea action parser shape changed")
text = text.replace(
    old,
    "arguments_json = json.JSONDecoder().raw_decode(arguments_text.lstrip())[0]",
)
text = text.replace(
    "Ensure the JSON is properly formatted for automatic parsing.",
    "Ensure the JSON is properly formatted for automatic parsing. Emit exactly one ACTION/ARGUMENTS block per response.",
    1,
)
marker = "# Define the initial idea generation prompt"
mandatory = '''system_prompt += """

PsyDefDetect mandatory runtime contract: propose exactly two local experiments and no others. Experiment 1 is word TF-IDF with class-balanced LogisticRegression. Experiment 2 is character TF-IDF with class-balanced LinearSVC or SGDClassifier using hinge loss. Use only installed numpy, pandas, scipy, and scikit-learn. Do not use or import sentence-transformers, transformers, torch, Hugging Face, pretrained models, embeddings, external datasets, prompt/API classification, package installation, or remote calls in the generated experiment code. Describe the implementation as installed local libraries only; do not enumerate prohibited alternatives in the idea prose. The program itself must run both experiments on the fixed split with the official local scorer, select the higher observed macro-F1, and write predictions.jsonl, score.json, experiment_trace.json, and final_report.md at /workspace. Include the positive experiment requirements in the Title, Abstract, Short Hypothesis, and Experiments fields so the downstream native BFTS code agent receives them.
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
old = '''    def use_tool(self, query: str) -> Optional[str]:
        papers = self.search_for_papers(query)'''
new = '''    def use_tool(self, query: str) -> Optional[str]:
        local_catalog = os.getenv("AI_SCIENTIST_LOCAL_LITERATURE_CATALOG")
        if local_catalog and Path(local_catalog).is_file():
            return Path(local_catalog).read_text(encoding="utf-8")
        papers = self.search_for_papers(query)'''
if old not in text:
    raise SystemExit("AI-Scientist-v2 Semantic Scholar projection insertion point not found")
semantic_path.write_text(text.replace(old, new, 1), encoding="utf-8")

manager_path = Path(sys.argv[6])
text = manager_path.read_text(encoding="utf-8")
if "import os\n" not in text:
    text = "import os\n" + text
old = '''        return task_desc

    def _create_initial_stage(self):'''
new = '''        if os.getenv("AI_SCIENTIST_PSYDEFDETECT_TWO_EXPERIMENTS") == "1":
            task_desc += f"""

MANDATORY PSYDEFDETECT EXECUTION CONTRACT:
- Generate one self-contained program that synchronously runs exactly two configurations: word TF-IDF plus class-balanced LogisticRegression, and character TF-IDF plus class-balanced LinearSVC or SGDClassifier(loss='hinge').
- Use only the fixed /data/psydefdetect/PsyDefConv.json dataset, /workspace/automation/psydefdetect_split.json, standard library, numpy, pandas, scipy, and scikit-learn.
- PsyDefConv.json is a top-level list whose rows use id, dialogue_id, dialogue, current_text, and integer label. Join train_record_ids/eval_record_ids from the split manifest to row['id']; use current_text as the target text and never assume conversation_id, defense_mechanism, or pre-split top-level objects.
- Do not remove English stop words; short dialogue utterances and function words are valid signal.
- Never import or use sentence_transformers, transformers, torch, Hugging Face, pretrained models, embeddings, external datasets, downloads, package installation, or remote calls.
- Score both configurations with /workspace/automation/scripts/run_psydefdetect_local_score.py, select the higher observed macro-F1, and have the generated program itself write /workspace/predictions.jsonl, /workspace/score.json, /workspace/experiment_trace.json, and /workspace/final_report.md.
- experiment_trace.json must contain exactly two unique experiment ids, the correct selected_experiment_id, framework_native_execution=true, consumed_topic_input=true, workspace_trace_root='/workspace', framework_internal_model='{os.getenv("OPENAI_MODEL", "")}', and framework_internal_api_base_url='{os.getenv("OPENAI_BASE_URL", "")}'.
"""
        return task_desc

    def _create_initial_stage(self):'''
if old not in text:
    raise SystemExit("AI-Scientist-v2 BFTS task-contract insertion point not found")
text = text.replace(old, new, 1)
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
                    "Load only /data/psydefdetect/PsyDefConv.json and /workspace/automation/psydefdetect_split.json.",
                    "PsyDefConv.json is a top-level list with row keys id, dialogue_id, dialogue, current_text, and integer label; select rows by matching split train_record_ids/eval_record_ids to row['id'].",
                    "Use current_text as the target text, optionally prepend dialogue turn text, and do not use stop_words='english' or assume conversation_id/defense_mechanism fields.",
                    "Run exactly two configurations synchronously: word TF-IDF with balanced LogisticRegression, then character TF-IDF with balanced LinearSVC or SGDClassifier(loss='hinge').",
                    "Invoke /workspace/automation/scripts/run_psydefdetect_local_score.py for each prediction file with complete CLI arguments.",
                    "Select the higher observed psydefdetect_score and have the program itself write /workspace/predictions.jsonl, /workspace/score.json, /workspace/experiment_trace.json, and /workspace/final_report.md.",
                    "Print `psydefdetect_score: <selected numeric score>` after the four root artifacts are written so the native metric parser can evaluate the implementation.",
                    "Do not create plots, neural models, synthetic datasets, background jobs, or runtime installations.",
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
text = interpreter_path.read_text(encoding="utf-8")
old = "        global_scope: dict = {}"
new = '''        global_scope: dict = {
            "__name__": "__main__",
            "__file__": str(self.working_dir / self.agent_file_name),
        }'''
if old not in text:
    raise SystemExit("AI-Scientist-v2 interpreter main-module insertion point not found")
interpreter_path.write_text(text.replace(old, new, 1), encoding="utf-8")
PY
rm -f ai_scientist/ideas/psydefdetect_topic.json
timeout "${AI_SCIENTIST_V2_PSYDEFDETECT_IDEATION_TIMEOUT_SECONDS:-1800}s" \
  python ai_scientist/perform_ideation_temp_free.py \
  --workshop-file ai_scientist/ideas/psydefdetect_topic.md \
  --model "$OPENAI_MODEL" \
  --max-num-generations 1 \
  --num-reflections 4
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
experiment_numbers = set(re.findall(r"\bexperiment\s+([1-9][0-9]*)\b", experiment_scope))
required_groups = (
    ("tf-idf", "tfidf"),
    ("word",),
    ("character", "char"),
    ("logistic",),
    ("linearsvc", "linear svm", "sgdclassifier", "hinge"),
)
missing = [group for group in required_groups if not any(term in scope for term in group)]
if found or missing or experiment_numbers != {"1", "2"}:
    raise SystemExit(
        "AI-Scientist-v2 idea violates local two-experiment contract: "
        f"prohibited={found}, missing={missing}, experiment_numbers={sorted(experiment_numbers)}"
    )
print("AI_SCIENTIST_V2_IDEA_CONTRACT_OK")
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
config["agent"]["steps"] = 3
config["agent"]["stages"]["stage1_max_iters"] = 3
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
EOF
)
exec "$ROOT"/real_eval/scripts/psydefdetect_framework_fullrun.sh
