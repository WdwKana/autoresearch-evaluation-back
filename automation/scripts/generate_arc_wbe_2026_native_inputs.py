#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


TOPIC_ID = "arc_wbe_2026"
TOPIC_LABEL = "ARC-WBE-2026"
RESULT_FIELDS = ["score", "score_source", "score_artifact", "submission_artifact"]
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_ROOT = REPO_ROOT / "data" / "arc_white_box_estimation_2026"
DEFAULT_CONTRACT_FILE = REPO_ROOT / "automation" / "arc_wbe_2026_contract.md"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_shared_summary(dataset_root: Path, contract_file: Path) -> str:
    return f"""# ARC WBE 2026 Summary

## Topic
- Topic id: `{TOPIC_ID}`
- Topic label: `{TOPIC_LABEL}`
- Dataset root: `{dataset_root}`
- Contract file: `{contract_file}`

## Goal
Produce official-comparable ARC White-Box Estimation Challenge 2026 results.

## Required normalized result fields
- `score`
- `score_source`
- `score_artifact`
- `submission_artifact`

## Expected deliverables
- root-level `estimator.py`, `submission.json`, `score.json`, `experiment_trace.json`, and `final_report.md`
- official local score evidence produced from the selected estimator
- manifest and state references
- logs and preserved workspace traces

## Phase-one scope
- keep topic-specific inputs explicit for each framework
- preserve tool-use traces for later analysis
- do not require tool-call scoring in phase one
"""


def render_ai_scientist_topic(dataset_root: Path, contract_file: Path) -> str:
    return f"""# Title
ARC-WBE-2026: White-Box Estimation Benchmark Execution

# TL;DR
Build a reproducible ARC White-Box Estimation Challenge 2026 workflow that produces official-format outputs, records benchmark evidence, and optimizes the benchmark score where local scoring exists.

# Dataset
- standardized local dataset root: {dataset_root}

# Contract
- topic label: {TOPIC_LABEL}
- contract file: {contract_file}

# Concrete Goal
Implement and evaluate one ARC-WBE-2026 run path that:
1. consumes the challenge contract directly,
2. produces official-format outputs or score evidence,
3. emits a runnable `estimator.py` when possible so the official local scorer can be replayed,
4. records reproducible commands and artifact locations,
5. writes a concise final report.

# Required Result Fields
- score
- score_source
- score_artifact
- submission_artifact
"""


def render_framework_brief(dataset_root: Path, contract_file: Path) -> str:
    return f"""# {TOPIC_LABEL}

## Objective
Execute the ARC White-Box Estimation Challenge 2026 topic directly instead of falling back to another benchmark.

## Inputs
- dataset root: {dataset_root}
- contract file: {contract_file}

## Success Criteria
- run 2-4 materially different framework-native estimator experiments, then finalize
- produce root-level `estimator.py`, `submission.json`, `score.json`, `experiment_trace.json`, and `final_report.md`
- use the injected OpenAI-compatible API environment and record the model/base URL in the trace
- preserve logs, manifests, and workspace traces
- write `final_report.md`

## Normalized Result Fields
- score
- score_source
- score_artifact
- submission_artifact
"""


def render_autoresearchclaw_topic() -> str:
    return """ARC-WBE-2026: White-Box Estimation of Transformer MLP Activations

Execute the ARC White-Box Estimation Challenge 2026 contract in
/workspace/automation/arc_wbe_2026_contract.md using the prepared dataset at
/data/arc_wbe_2026. Design and run two bounded, materially different estimator
experiments under the supplied execution budget, compare their official local
scores, and select the better estimator. The framework must perform its own
experiment planning, code generation, execution, and result selection. Deliver
root-level estimator.py, submission.json, score.json, experiment_trace.json,
and final_report.md. Record the injected model and API base URL in the trace.
"""


def render_ai_researcher_metaprompt(dataset_root: Path, contract_file: Path) -> str:
    return f'''TASK = "ARC White-Box Estimation Challenge 2026 benchmark execution."
DATASET = """
Use the real ARC-WBE-2026 dataset mounted by ResearchClawEval.
The dataset is available at:
- /data/arc_wbe_2026
- /workplace/project/data/arc_wbe_2026
- /workplace/dataset_candidate/arc_wbe_2026
- {dataset_root}
"""
BASELINE = "Restore one real ARC benchmark execution path before attempting any improvement."
COMPARISON = "Compare only official-format outputs or score evidence generated from the same ARC-WBE-2026 contract."
EVALUATION = "Run 2-4 bounded framework-native estimator experiments. Use the injected OPENAI_BASE_URL, OPENAI_API_KEY, and OPENAI_MODEL for all internal calls. Promote the selected result to root-level estimator.py, submission.json, score.json, experiment_trace.json (including model/base URL), and final_report.md; score with the local scorer."
REF = "Do not use unrelated benchmarks, toy datasets, placeholder results, synthetic submissions, or outputs from previous topics. The contract file is: {contract_file}"
DATA_INSPECTION_RULES = """
When inspecting ARC-WBE-2026 parquet or dataset rows, Do not print raw weights, all_layer_means, final_means, or other large tensor/array payloads.
Inspect schema, column names, dtypes, shapes, and concise scalar summaries only.
If you need examples, print only field names, array shapes, lengths, and a tiny bounded preview; never dump full arrays or full row dictionaries to stdout.
"""
'''


def build_ai_researcher_payload(dataset_root: Path, contract_file: Path) -> dict[str, object]:
    return {
        "instance_id": TOPIC_ID,
        "target": "ARC White-Box Estimation Challenge 2026",
        "title": "ARC-WBE-2026: White-Box Estimation Benchmark Execution",
        "authors": ["Project-local custom benchmark"],
        "year": 2026,
        "url": "http://arxiv.org/abs/2606.18001v1",
        "abstract": "A local benchmark configuration for ARC-WBE-2026 with explicit benchmark-native inputs and normalized score reporting fields.",
        "venue": "Local Benchmark",
        "topic": "benchmark_execution",
        "field": "benchmarking",
        "source_papers": [
            {
                "reference": "White-Box Estimation for Transformer MLP Activations",
                "usage": "Use as a conceptual reference for the target estimator design and error analysis.",
            },
            {
                "reference": "A Public Benchmark for White-Box Estimation Under Compute Budgets",
                "usage": "Use as a reference for benchmark setup, scoring, and compute-budget-aware reporting.",
            },
            {
                "reference": "Covariance Propagation for ReLU Network Mean Estimation",
                "usage": "Use as a lightweight technical baseline for estimating hidden and final-layer means.",
            },
        ],
        "dataset_root": str(dataset_root),
        "contract_file": str(contract_file),
        "result_fields": RESULT_FIELDS,
        "task1": "Consume the ARC-WBE-2026 contract, run the benchmark workflow, and preserve official-format outputs, score evidence, logs, a runnable estimator.py when possible, and a concise final report.",
        "task2": "Implement one minimal but reproducible ARC-WBE-2026 path that records score provenance, estimator entrypoints, and submission artifact paths.",
    }


def build_dr_claw_brief(dataset_root: Path, contract_file: Path) -> dict[str, object]:
    return {
        "project_name": TOPIC_ID,
        "project_type": "benchmark_task",
        "objective": "Produce official-comparable ARC-WBE-2026 outputs with normalized score reporting.",
        "dataset": {
            "name": TOPIC_LABEL,
            "root": str(dataset_root),
        },
        "contract_file": str(contract_file),
        "result_fields": RESULT_FIELDS,
        "deliverables": [
            "submission_artifact",
            "score_evidence",
            "final_report.md",
            "logs",
            "workspace_traces",
        ],
    }


def build_dr_claw_tasks() -> dict[str, object]:
    return {
        "tasks": [
            {
                "id": "t1_contract_audit",
                "title": "Read ARC contract and dataset layout",
                "goal": "Confirm the workflow consumes ARC-WBE-2026 inputs directly.",
            },
            {
                "id": "t2_execution",
                "title": "Run a benchmark-oriented ARC workflow",
                "goal": "Produce official-format outputs or local score evidence, preferably via a runnable estimator.py.",
            },
            {
                "id": "t3_reporting",
                "title": "Record normalized result fields",
                "goal": "Write score, score_source, score_artifact, and submission_artifact in the final outputs.",
            },
        ]
    }


def build_autoresearchclaw_config(
    dataset_root: Path,
    contract_file: Path,
    provider_base_url: str,
    primary_model: str,
) -> str:
    return f"""project:
  name: "{TOPIC_ID}"
  mode: "full-auto"
  output_dir: "./outputs/{TOPIC_ID}"

research:
  topic: "{TOPIC_LABEL}"

runtime:
  timezone: "Asia/Shanghai"
  max_parallel_tasks: 1
  retry_limit: 0

notifications:
  channel: "none"

knowledge_base:
  root: "./knowledge_base"

assets:
  dataset_root: "{dataset_root}"
  contract_file: "{contract_file}"

llm:
  provider: "openai-compatible"
  primary_model: "{primary_model}"
  fallback_models: []
  base_url: "{provider_base_url}"
  api_key_env: "OPENAI_API_KEY"

evaluation:
  result_fields:
    - "score"
    - "score_source"
    - "score_artifact"
    - "submission_artifact"

experiment:
  mode: "sandbox"
  time_budget_sec: 300
  max_iterations: 2
  sandbox:
    python_path: "python3"
    gpu_required: false
    allowed_imports: [math, json, pathlib, numpy, sklearn, datasets]
"""


def generate_native_inputs(
    repo_root: Path,
    output_root: Path,
    dataset_root: Path,
    contract_file: Path,
    provider_base_url: str = "https://api.openai.com/v1",
    primary_model: str = "gpt-5.4",
) -> dict[str, object]:
    output_root.mkdir(parents=True, exist_ok=True)

    shared_summary = render_shared_summary(dataset_root, contract_file)
    authoritative_contract = (
        contract_file.read_text(encoding="utf-8")
        if contract_file.exists()
        else f"# ARC WBE 2026 Contract Pointer\n\nSource contract file: `{contract_file}`\n"
    )
    ai_scientist_topic = render_ai_scientist_topic(dataset_root, contract_file)
    framework_brief = render_framework_brief(dataset_root, contract_file)

    text_files = {
        "docs/arc_wbe_2026_summary.md": shared_summary,
        "automation/arc_wbe_2026_contract.md": authoritative_contract,
        "automation/arc_wbe_2026_execution_budget.md": (
            (REPO_ROOT / "automation" / "arc_wbe_2026_execution_budget.md").read_text(encoding="utf-8")
        ),
        "automation/scripts/run_arc_wbe_2026_local_score.py": (
            (REPO_ROOT / "automation" / "scripts" / "run_arc_wbe_2026_local_score.py").read_text(encoding="utf-8")
        ),
        "automation/scripts/arc_wbe_2026_official_adapter.py": (
            (REPO_ROOT / "automation" / "scripts" / "arc_wbe_2026_official_adapter.py").read_text(encoding="utf-8")
        ),
        "automation/scripts/prepare_arc_wbe_2026_dataset.py": (
            (REPO_ROOT / "automation" / "scripts" / "prepare_arc_wbe_2026_dataset.py").read_text(encoding="utf-8")
        ),
        "AI-Researcher/benchmark/process/dataset_candidate/arc_wbe_2026/metaprompt.py": render_ai_researcher_metaprompt(
            dataset_root, contract_file
        ),
        "AI-Scientist-v2/ai_scientist/ideas/arc_wbe_2026_topic.md": ai_scientist_topic,
        "AI-Scientist-v2/ai_scientist/ideas/my_research_topic.md": ai_scientist_topic,
        "Auto-claude-code-research-in-sleep/ARC_WBE_2026_BRIEF.md": framework_brief,
        "Auto-claude-code-research-in-sleep/.aris-codex-project/ARC_WBE_2026_BRIEF.md": framework_brief,
        "AutoResearchClaw/topic.txt": render_autoresearchclaw_topic(),
        "AutoResearchClaw/config.arc.yaml": build_autoresearchclaw_config(
            dataset_root,
            contract_file,
            provider_base_url,
            primary_model,
        ),
        "DeepScientist/DEEPSCIENTIST_BRIEF.md": framework_brief,
        "EvoScientist/EVOSCIENTIST_BRIEF.md": framework_brief,
        "EvoScientist/arc_wbe_2026_start_message.txt": f"Start ARC-WBE-2026. Read @EVOSCIENTIST_BRIEF.md, @docs/arc_wbe_2026_summary.md, and @automation/arc_wbe_2026_execution_budget.md first.\n",
    }
    json_files = {
        "AI-Researcher/benchmark/final/arc_wbe_2026/arc_wbe_2026.json": build_ai_researcher_payload(
            dataset_root,
            contract_file,
        ),
        "dr-claw/research_brief.json": build_dr_claw_brief(dataset_root, contract_file),
        "dr-claw/tasks.json": build_dr_claw_tasks(),
    }

    manifest_files: dict[str, dict[str, str]] = {}
    for rel_path, content in text_files.items():
        write_text(output_root / rel_path, content)
        manifest_files[rel_path] = {"kind": "text"}
    for rel_path, payload in json_files.items():
        write_json(output_root / rel_path, payload)
        manifest_files[rel_path] = {"kind": "json"}

    manifest = {
        "topic": {
            "id": TOPIC_ID,
            "label": TOPIC_LABEL,
            "dataset_root": str(dataset_root),
            "contract_file": str(contract_file),
        },
        "result_fields": RESULT_FIELDS,
        "files": manifest_files,
    }
    write_json(output_root / "arc_wbe_2026_manifest.json", manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate ARC-WBE-2026 native framework inputs.")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--contract-file", type=Path, default=DEFAULT_CONTRACT_FILE)
    parser.add_argument("--provider-base-url", default="https://api.openai.com/v1")
    parser.add_argument("--primary-model", default="gpt-5.4")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    generate_native_inputs(
        repo_root=REPO_ROOT,
        output_root=args.output_root,
        dataset_root=args.dataset_root,
        contract_file=args.contract_file,
        provider_base_url=args.provider_base_url,
        primary_model=args.primary_model,
    )
    print(
        json.dumps(
            {
                "topic": TOPIC_ID,
                "output_root": str(args.output_root),
                "manifest": str(args.output_root / "arc_wbe_2026_manifest.json"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
