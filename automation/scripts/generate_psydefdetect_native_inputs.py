#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED = 42
SPLIT_RATIO = 0.8
TOPIC_ID = "psydefdetect"
TOPIC_LABEL = "PsyDefDetect"

SUMMARY = """# PsyDefDetect Task Summary

## Goal
Run framework-native experimentation for PsyDefDetect rather than a single fast baseline.

## Standardized evaluation protocol
- Use the provided dialogue-level split manifest under `automation/psydefdetect_split.json`.
- Do not invent a new split.
- Treat macro-F1 over positive labels `1-8` as the primary score.

## Required research behavior
- Run at least 2 materially different experiments.
- Compare them and select one final approach.
- Use the framework's own orchestration flow for execution and finalization as much as possible.
- Record the experiment history in `experiment_trace.json`.
- Score the final predictions with `automation/scripts/run_psydefdetect_local_score.py`.
- Do not depend on downloading new Hugging Face models at runtime.
- Prefer API-based or already-available local methods for the second experiment.

## Required outputs
- `predictions.jsonl` or `submission.csv`
- `score.json`
- `experiment_trace.json`
- `final_report.md`
"""

METRIC_SPEC = """# PsyDefDetect Metric Spec

## Official local proxy metric
- Primary metric: macro-F1 over positive labels `1-8`
- Label `0` is excluded from the official macro average

## Standard local scoring command
```bash
python3 automation/scripts/run_psydefdetect_local_score.py \
  --dataset-root /data/psydefdetect \
  --split-manifest automation/psydefdetect_split.json \
  --predictions predictions.jsonl \
  --output-score score.json
```

If you emit `submission.csv` instead of `predictions.jsonl`, pass that file to the same scorer.
"""

SUBMISSION_SPEC = """# PsyDefDetect Submission Spec

## Prediction artifact
You may emit either:
- `predictions.jsonl`
- `submission.csv`

## Standardized label field
- JSONL: use `id` and either `predicted_label` or `label`
- CSV: use `id` and either `predicted_label` or `label`

## Hard requirement
Every eval record listed in `automation/psydefdetect_split.json` must have exactly one prediction.
"""

EXPERIMENT_REQUIREMENTS = """# PsyDefDetect Experiment Requirements

## Minimum bar
- At least 2 materially different experiments
- At least 1 selected final experiment
- A scored final prediction artifact

## Network / model policy
- Do not assume `huggingface.co` model downloads are available at runtime.
- Do not block the run waiting on new model downloads.
- Prefer one of:
  - API-based classification or reranking using the configured model provider
  - container-local libraries and already-installed resources
  - a non-neural comparative method that is materially different from the baseline

## Required trace file
Write `/workspace/experiment_trace.json` with at least:
- `framework_native_execution`: true
- `consumed_topic_input`: true
- `workspace_trace_root`
- `experiments`: array with length >= 2
- `selected_experiment_id`
- `prediction_artifact`
- `score_artifact`

Before exit, promote the selected final outputs to:
- `/workspace/predictions.jsonl` or `/workspace/submission.csv`
- `/workspace/score.json`
- `/workspace/experiment_trace.json`
- `/workspace/final_report.md`

Do not leave only per-experiment subfolders such as `exp*/` or `experiment_*/` without a framework-level final artifact set at `/workspace`.

Each experiment entry should include:
- `id`
- `description`
- `diff_vs_previous`
- `artifacts`
- `score_summary`
"""

RUNTIME_BRIEF = """# PsyDefDetect Runtime Brief

This run is for measuring framework capability, not just file production.

You must:
1. Read the shared contract and the standardized split manifest.
2. Use the framework's own orchestration flow, not a loose pile of unrelated scratch scripts, to run and compare experiments.
3. Run at least 2 experiments with materially different settings or methods.
4. Choose one final approach based on observed score evidence.
5. Promote the selected final outputs to `/workspace/predictions.jsonl` or `/workspace/submission.csv`, `/workspace/score.json`, `/workspace/experiment_trace.json`, and `/workspace/final_report.md` before exit.
6. Produce:
   - predictions.jsonl or submission.csv
   - score.json
   - experiment_trace.json
   - final_report.md

Using a single TF-IDF or single sklearn baseline and stopping immediately is insufficient.
Do not rely on downloading new Hugging Face models during runtime; prefer API-based or already-available local methods for the second experiment.
Do not leave only per-experiment subfolders such as `exp*/` or `experiment_*/` without a framework-level final artifact set at `/workspace`.
"""

AUTORESEARCHCLAW_SEARCH_GUIDANCE = """Generate at most 6 precise queries centered on psychological defense mechanisms, psychotherapy dialogue, and clinical NLP classification. Avoid broad generic mental-health queries and unrelated uses of the word defense.
"""

AUTORESEARCHCLAW_COLLECTION_GUIDANCE = """Keep the candidate set compact and directly relevant to psychological defense mechanisms, psychotherapy text, or clinical NLP classification. Do not expand broad generic mental-health queries.
"""

AUTORESEARCHCLAW_SCREEN_GUIDANCE = """The supplied candidates are a compact, relevance-ranked PsyDefDetect projection produced inside AutoResearchClaw. Select 15 to 25 papers from that projection and return them in the required shortlist JSON object. Keep PsyDefDetect shared-task papers, psychological defense-mechanism work, and directly applicable psychotherapy or clinical-NLP classification methods. Do not reject a relevant paper merely because it addresses an adjacent clinical-NLP classification task. Return an empty shortlist only when none of the supplied candidates qualifies; never fabricate or introduce a paper that is absent from the supplied candidates.
"""

AUTORESEARCHCLAW_EXPERIMENT_DESIGN_GUIDANCE = """PSYDEFDETECT FIXED EXPERIMENT CONTRACT

Design exactly two materially different, directly executable conditions and no ablations:
1. `word_tfidf_logistic_regression`: word-level TF-IDF with class-balanced LogisticRegression.
2. `char_tfidf_linear_svc`: character-level TF-IDF with class-balanced LinearSVC.

The dataset is `/data/psydefdetect/PsyDefConv.json`, a top-level JSON list. Each row has `id` (string), `dialogue_id` (string), `dialogue` (list of `{text, speaker}` objects), `current_text` (string), and `label` (integer 0-8). Load it with Python `json.load`, preserving each `row["id"]` exactly as a string including leading zeroes such as `"0001"`; do not use `pandas.read_json`, which may coerce those ids to integers. Join `/workspace/automation/psydefdetect_split.json` to rows by the unchanged `row["id"]`, using `train_record_ids` and `eval_record_ids`. Do not invent CSV files, positional indices, another split, distant supervision, synthetic labels, a validation subset, or a different class count.

The primary metric is macro-F1 over positive labels 1-8, direction `maximize`. The plan must explicitly state 9 classes (labels 0-8), the two artifact ids above, exactly two total runs, and the fixed split and filenames. `compute_budget.conditions` must contain exactly those two conditions. Keep `ablations` empty. Do not request repeated seeds, grid search, significance tests, bootstrap confidence intervals, SciPy, statsmodels, Torch, pretrained models, downloads, or remote calls from experiment code. Return only the framework's normal experiment-plan YAML.
"""

AUTORESEARCHCLAW_CODE_GENERATION_GUIDANCE = """PSYDEFDETECT COMPACT CODE CONTRACT

Implement only the two conditions in the validated experiment plan: word TF-IDF plus class-balanced LogisticRegression, and character TF-IDF plus class-balanced LinearSVC. Use the exact PsyDefConv JSON-list schema and fixed id-based split described in the plan. Read `PsyDefConv.json` with `json.load`, never `pandas.read_json`, and preserve every string id byte-for-byte including leading zeroes before joining the split. Use `current_text` as required input text; dialogue context may be joined from `turn["text"]` but must not replace `current_text`.

Keep the project compact: at most three Python files with one canonical definition for each helper. Use only Python standard library, numpy, pandas, and scikit-learn. No generated Python file may import or call `runpy`. Do not directly import scipy, statsmodels, torch, transformers, openai, or optional statistical packages. Do not install or download anything and do not make remote calls from experiment code. Use sklearn Pipelines so each vectorizer is fitted only on raw training text. Initialize every local variable before conditional use, include a real `if __name__ == "__main__":` entrypoint, and run both conditions synchronously exactly once.

Score each condition by invoking the mounted `/workspace/automation/scripts/run_psydefdetect_local_score.py` through `subprocess.run(..., check=True)` with all four CLI arguments: `--dataset-root /data/psydefdetect`, `--split-manifest /workspace/automation/psydefdetect_split.json`, `--predictions <condition prediction file>`, and `--output-score <condition score file>`. If the official scorer exits unsuccessfully, let `subprocess.CalledProcessError` propagate and abort the experiment immediately; do not catch it and continue. Never invoke the scorer in-process through `runpy`, generate or import another file named `run_psydefdetect_local_score.py`, write a null/placeholder score, or locally reimplement the scorer. You must never use a fallback summary. Select the higher observed `psydefdetect_score` from the two official score JSON files.

Before the native pipeline exits, the framework must deliver root-level `/workspace/predictions.jsonl`, `/workspace/score.json`, `/workspace/experiment_trace.json`, and `/workspace/final_report.md`. Copy the selected official score JSON to `/workspace/score.json`; it must retain numeric `psydefdetect_score` and `score_key: "psydefdetect_score"`. The trace must be one top-level JSON object containing exactly two `experiments`, each with a unique `experiment_id`, numeric `psydefdetect_score`, prediction/score paths, and the complete official `scorer_command`; `selected_experiment_id` must identify the higher-scoring record. It must also set `framework_native_execution: true`, `consumed_topic_input: true`, `workspace_trace_root: "/workspace"`, `framework_internal_model` from `OPENAI_MODEL`, and `framework_internal_api_base_url` from `OPENAI_BASE_URL`. Do not fabricate metrics or copy values from prompts.
"""

AUTORESEARCHCLAW_PSYDEF_BENCHMARK_KNOWLEDGE = """domains:
  psydefdetect:
    required_baselines:
      - Word TF-IDF Logistic Regression
      - Character TF-IDF Linear SVM
    keywords:
      - psydefdetect
      - psychological defense mechanism
      - defense mechanism classification
    standard_benchmarks:
      - name: PsyDefDetect
        tier: 1
        domain: text_classification
        size_mb: 5
        classes: 9
        metrics: [macro_f1_positive_1_8]
        api: "json.load(open('/data/psydefdetect/PsyDefConv.json', encoding='utf-8'))"
        note: "Use the fixed split at /workspace/automation/psydefdetect_split.json and the local scorer."
    common_baselines:
      - name: Word TF-IDF Logistic Regression
        source: "sklearn word n-gram TfidfVectorizer plus class-balanced LogisticRegression"
        paper: "Local reproducible sparse text baseline"
        pip: []
      - name: Character TF-IDF Linear SVM
        source: "sklearn character n-gram TfidfVectorizer plus class-balanced LinearSVC"
        paper: "Local complementary sparse text baseline"
        pip: []
"""

AI_SCIENTIST_LITERATURE_CATALOG = """# PsyDefDetect Offline Literature Candidate Context

This is a framework-visible input projection for environments where Semantic Scholar is rate-limited. It is not a selected idea, experiment plan, result, or framework output.

## Benchmark context
- PsyDefDetect is a nine-class psychological defense mechanism classification task over supportive-conversation dialogue context.
- The authoritative task definition, labels, split, and metric are the mounted local contract and dataset.
- Relevant methodological areas include dialogue-level text classification, class-imbalanced learning, prompt-based classification, contextual representation, and confusion analysis for semantically adjacent labels.

## Candidate implementation families
- Sparse lexical and character features with calibrated linear classifiers provide a reproducible local baseline.
- Context-aware prompting can compare the target utterance with its preceding supportive-conversation turns.
- Few-shot prompting, label-description prompting, reranking, and self-consistency are possible API-based comparisons when calls are batched.
- Any proposal must remain feasible with installed libraries and the injected model provider; do not require model downloads.

The framework should use this candidate context to formulate and select its own proposal.
"""


def render_framework_brief(dataset_root: Path, contract_file: Path) -> str:
    return f"""# PsyDefDetect Native Evaluation Brief

## Objective
Use the framework's own orchestration to plan, implement, execute, compare, and select 2-4 materially different PsyDefDetect experiments.

## Inputs
- dataset root inside the runtime: `/data/psydefdetect`
- source dataset: `{dataset_root}`
- contract: `{contract_file}`
- fixed split: `automation/psydefdetect_split.json`
- official local scorer: `automation/scripts/run_psydefdetect_local_score.py`

## Required framework-owned handoff
- `/workspace/predictions.jsonl` or `/workspace/submission.csv`
- `/workspace/score.json`
- `/workspace/experiment_trace.json`
- `/workspace/final_report.md`

The framework must create and promote these artifacts itself. The host will validate them but will not generate, modify, or backfill them. The trace must record the effective model and API base URL, 2-4 experiments, the selected experiment, topic-input consumption, and framework-native execution.
"""


def render_ai_researcher_metaprompt() -> str:
    return '''TASK = "PsyDefDetect psychological defense mechanism classification."
DATASET = """
Use only the real PsyDefDetect dataset mounted at /data/psydefdetect and exposed in the framework workplace. Use automation/psydefdetect_split.json without changing the split.
"""
BASELINE = "Implement and score one reproducible local classification baseline on the fixed split using only libraries already installed in the runtime. Do not use or download pretrained Hugging Face models."
COMPARISON = "Run exactly one second materially different local experiment with installed libraries, compare official local macro-F1 evidence, and immediately select the better valid result. Experiment code must not make remote API calls."
EVALUATION = "Use automation/scripts/run_psydefdetect_local_score.py. The framework must write predictions.jsonl or submission.csv, score.json, experiment_trace.json, and final_report.md at the workplace root so they map to /workspace in the evaluation handoff."
REF = "Do not use another topic, prior outputs, fabricated metrics, host-authored artifacts, runtime package installation, remote calls from experiment code, background jobs, or sleep/poll loops. The framework agent itself uses the injected evaluation provider for planning and code generation."
'''


def build_ai_researcher_payload() -> dict[str, object]:
    return {
        "instance_id": TOPIC_ID,
        "target": "PsyDefDetect psychological defense mechanism classification",
        "title": "Framework-native PsyDefDetect experimentation",
        "authors": ["ResearchClawEval local task"],
        "year": 2026,
        "url": "http://arxiv.org/abs/2402.02042v1",
        "abstract": "A local nine-class psychological defense mechanism classification task with a fixed dialogue-level split.",
        "venue": "Local Benchmark",
        "topic": "text_classification",
        "field": "natural_language_processing",
        "source_papers": [
            {
                "reference": "Defense Mechanism Classification in Supportive Conversations",
                "usage": "Use only as conceptual context; the mounted local dataset and contract are authoritative.",
            }
        ],
        "dataset_root": "/data/psydefdetect",
        "contract_file": "automation/psydefdetect_contract.md",
        "task1": "Run two materially different PsyDefDetect experiments through AI-Researcher, select by local score, and produce the complete root-level handoff.",
        "task2": "Preserve experiment evidence and effective provider metadata in experiment_trace.json.",
    }


def render_ai_scientist_topic(primary_model: str, provider_base_url: str) -> str:
    return f"""# Title
Local sparse classifiers for PsyDefDetect

# TL;DR
Run exactly two materially different local sparse classifiers on the fixed dialogue-level split: word TF-IDF with class-balanced LogisticRegression, and character TF-IDF with class-balanced LinearSVC or SGDClassifier(loss="hinge"). Compare official macro-F1 over positive labels 1-8 and select the higher observed score.

# Dataset
Use `/data/psydefdetect/PsyDefConv.json` and `automation/psydefdetect_split.json` only.

# Dataset schema
- `PsyDefConv.json` is a top-level JSON list. Every usable row has `id` (string), `dialogue_id` (string), `dialogue` (a list of `{{text, speaker}}` objects), `current_text` (string), and `label` (integer 0-8).
- Join the fixed split to rows by `row["id"]`: train ids are in `train_record_ids` and evaluation ids are in `eval_record_ids`. There are no `conversation_id`, `defense_mechanism`, train/val/test top-level objects, or pre-split data files.
- Use `current_text` as the required target text. Dialogue context may be formed by joining `turn["text"]` from `dialogue`, but do not discard `current_text`.
- Do not set `stop_words="english"`; short supportive-conversation utterances and function words are valid signal and must not produce an empty vocabulary.

# Mandatory implementation constraints
- Use only Python's standard library plus installed numpy, pandas, scipy, and scikit-learn.
- Do not import or use sentence_transformers, transformers, torch, Hugging Face, pretrained models, embeddings, external datasets, downloads, package installation, or remote calls from experiment code.
- Do not propose prompt-based or API classification experiments. The injected `{primary_model}` provider is used by AI-Scientist-v2 for planning and code generation only.
- The generated program must execute both experiments synchronously, invoke `automation/scripts/run_psydefdetect_local_score.py` with its complete CLI arguments, and select the higher observed score.
- The two experiments must have unique string ids. `selected_experiment_id` must identify the higher-scoring experiment.
- Before the native BFTS workflow exits, the generated program itself must write `/workspace/predictions.jsonl`, `/workspace/score.json`, `/workspace/experiment_trace.json`, and `/workspace/final_report.md`.
- `experiment_trace.json` must record exactly two experiments, `framework_native_execution: true`, `consumed_topic_input: true`, `workspace_trace_root: "/workspace"`, `framework_internal_model: "{primary_model}"`, and `framework_internal_api_base_url: "{provider_base_url}"`.
"""


def build_autoresearchclaw_config(provider_base_url: str, primary_model: str) -> str:
    return f"""project:
  name: "psydefdetect-native"
  mode: "full-auto"
  output_dir: "./artifacts/psydefdetect-${{REAL_EVAL_RUN_ID}}"

research:
  topic: "NLP classification of psychological defense mechanisms in supportive dialogue"
  domains:
    - "clinical natural language processing"
    - "computational psychology"
    - "psychotherapy dialogue classification"
  daily_paper_count: 12
  quality_threshold: 0.35

runtime:
  timezone: "Asia/Shanghai"
  max_parallel_tasks: 1
  retry_limit: 0

notifications:
  channel: "none"

knowledge_base:
  root: "./knowledge_base"

assets:
  dataset_root: "/data/psydefdetect"
  contract_file: "automation/psydefdetect_contract.md"

llm:
  provider: "openai-compatible"
  primary_model: "{primary_model}"
  fallback_models: []
  base_url: "{provider_base_url}"
  api_key_env: "OPENAI_API_KEY"

experiment:
  mode: "sandbox"
  time_budget_sec: 1800
  max_iterations: 2
  metric_key: "macro_f1_positive"
  metric_direction: "maximize"
  opencode:
    enabled: false
  benchmark_agent:
    enabled: false
  code_agent:
    enabled: true
    architecture_planning: true
    sequential_generation: true
    hard_validation: true
    hard_validation_max_repairs: 8
    exec_fix_max_iterations: 0
    exec_fix_timeout_sec: 90
    review_max_rounds: 0
  sandbox:
    python_path: "/usr/bin/python3"
    gpu_required: false
    allowed_imports: [json, csv, pathlib, collections, numpy, pandas, sklearn]

prompts:
  extra_prompts:
    search_strategy: "evaluation_prompts/psydefdetect_search_strategy.md"
    literature_collect: "evaluation_prompts/psydefdetect_literature_collect.md"
    literature_screen: "evaluation_prompts/psydefdetect_literature_screen.md"
    experiment_design: "evaluation_prompts/psydefdetect_experiment_design.md"
    code_generation: "evaluation_prompts/psydefdetect_code_generation.md"
"""


def build_split(dataset_root: Path) -> dict:
    rows = json.loads((dataset_root / "PsyDefConv.json").read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise SystemExit("PsyDefConv.json must contain a top-level list")
    dialogues: dict[str, list[dict]] = {}
    for item in rows:
        if not isinstance(item, dict):
            continue
        dialogue_id = item.get("dialogue_id")
        if not isinstance(dialogue_id, str):
            continue
        dialogues.setdefault(dialogue_id, []).append(item)

    dialogue_ids = sorted(dialogues)
    rng = random.Random(SEED)
    rng.shuffle(dialogue_ids)
    split_index = int(len(dialogue_ids) * SPLIT_RATIO)
    train_dialogue_ids = sorted(dialogue_ids[:split_index])
    eval_dialogue_ids = sorted(dialogue_ids[split_index:])
    train_set = set(train_dialogue_ids)
    eval_rows = [item for item in rows if isinstance(item, dict) and item.get("dialogue_id") not in train_set]
    train_rows = [item for item in rows if isinstance(item, dict) and item.get("dialogue_id") in train_set]
    return {
        "topic": "psydefdetect",
        "split_kind": "dialogue_level_fixed_seed",
        "seed": SEED,
        "train_ratio": SPLIT_RATIO,
        "train_dialogue_ids": train_dialogue_ids,
        "eval_dialogue_ids": eval_dialogue_ids,
        "train_record_ids": [item["id"] for item in train_rows if isinstance(item.get("id"), str)],
        "eval_record_ids": [item["id"] for item in eval_rows if isinstance(item.get("id"), str)],
        "train_record_count": len(train_rows),
        "eval_record_count": len(eval_rows),
    }


def write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate PsyDefDetect native input pack.")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--contract-file", required=True)
    parser.add_argument("--provider-base-url", default="https://api.openai.com/v1")
    parser.add_argument("--primary-model", default="gpt-5.4")
    args = parser.parse_args()

    output_root = Path(args.output_root).resolve()
    dataset_root = Path(args.dataset_root).resolve()
    contract_file = Path(args.contract_file).resolve()

    split_payload = build_split(dataset_root)
    write_file(output_root / "docs/psydefdetect_task_summary.md", SUMMARY)
    write_file(output_root / "docs/psydefdetect_metric_spec.md", METRIC_SPEC)
    write_file(output_root / "docs/psydefdetect_submission_spec.md", SUBMISSION_SPEC)
    write_file(output_root / "docs/psydefdetect_experiment_requirements.md", EXPERIMENT_REQUIREMENTS)
    write_file(output_root / "docs/psydefdetect_literature_catalog.md", AI_SCIENTIST_LITERATURE_CATALOG)
    write_file(output_root / "automation/psydefdetect_runtime_brief.md", RUNTIME_BRIEF)
    write_file(output_root / "automation/psydefdetect_split.json", json.dumps(split_payload, ensure_ascii=False, indent=2) + "\n")
    framework_brief = render_framework_brief(dataset_root, contract_file)
    framework_files = {
        "AI-Researcher/benchmark/process/dataset_candidate/psydefdetect/metaprompt.py": render_ai_researcher_metaprompt(),
        "AI-Scientist-v2/ai_scientist/ideas/psydefdetect_topic.md": render_ai_scientist_topic(
            args.primary_model, args.provider_base_url
        ),
        "Auto-claude-code-research-in-sleep/PSYDEFDETECT_BRIEF.md": framework_brief,
        "AutoResearchClaw/topic.psydefdetect.txt": "PsyDefDetect psychological defense mechanism classification\n",
        "AutoResearchClaw/config.psydefdetect.yaml": build_autoresearchclaw_config(
            args.provider_base_url, args.primary_model
        ),
        "AutoResearchClaw/evaluation_prompts/psydefdetect_search_strategy.md": AUTORESEARCHCLAW_SEARCH_GUIDANCE,
        "AutoResearchClaw/evaluation_prompts/psydefdetect_literature_collect.md": AUTORESEARCHCLAW_COLLECTION_GUIDANCE,
        "AutoResearchClaw/evaluation_prompts/psydefdetect_literature_screen.md": AUTORESEARCHCLAW_SCREEN_GUIDANCE,
        "AutoResearchClaw/evaluation_prompts/psydefdetect_experiment_design.md": AUTORESEARCHCLAW_EXPERIMENT_DESIGN_GUIDANCE,
        "AutoResearchClaw/evaluation_prompts/psydefdetect_code_generation.md": AUTORESEARCHCLAW_CODE_GENERATION_GUIDANCE,
        "AutoResearchClaw/psydefdetect_benchmark_knowledge.yaml": AUTORESEARCHCLAW_PSYDEF_BENCHMARK_KNOWLEDGE,
        "DeepScientist/PSYDEFDETECT_BRIEF.md": framework_brief,
        "EvoScientist/PSYDEFDETECT_BRIEF.md": framework_brief,
        "EvoScientist/psydefdetect_start_message.txt": (
            "Start PsyDefDetect. Read @PSYDEFDETECT_BRIEF.md, "
            "@automation/psydefdetect_contract.md, and "
            "@automation/psydefdetect_execution_budget.md first.\n"
        ),
    }
    for rel_path, content in framework_files.items():
        write_file(output_root / rel_path, content)
    ai_researcher_instance = output_root / "AI-Researcher/benchmark/final/psydefdetect/psydefdetect.json"
    ai_researcher_instance.parent.mkdir(parents=True, exist_ok=True)
    ai_researcher_instance.write_text(
        json.dumps(build_ai_researcher_payload(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_file(
        output_root / "automation/psydefdetect_native_manifest.json",
        json.dumps(
            {
                "topic": "psydefdetect",
                "dataset_root": str(dataset_root),
                "contract_file": str(contract_file),
                "primary_model": args.primary_model,
                "provider_base_url": args.provider_base_url,
                "generated_files": [
                    "docs/psydefdetect_task_summary.md",
                    "docs/psydefdetect_metric_spec.md",
                    "docs/psydefdetect_submission_spec.md",
                    "docs/psydefdetect_experiment_requirements.md",
                    "docs/psydefdetect_literature_catalog.md",
                    "automation/psydefdetect_runtime_brief.md",
                    "automation/psydefdetect_split.json",
                    "automation/scripts/run_psydefdetect_local_score.py",
                    "AI-Researcher/benchmark/final/psydefdetect/psydefdetect.json",
                    *framework_files,
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    scorer_src = REPO_ROOT / "automation/scripts/run_psydefdetect_local_score.py"
    scorer_dst = output_root / "automation/scripts/run_psydefdetect_local_score.py"
    scorer_dst.parent.mkdir(parents=True, exist_ok=True)
    scorer_dst.write_text(scorer_src.read_text(encoding="utf-8"), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
