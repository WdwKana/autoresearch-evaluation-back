#!/usr/bin/env python3
"""AI-Scientist-v2 runtime adapter for TDC-ADMET-Tox (reconstructed).

Referenced by real_eval/scripts/02_ai_scientist_v2_tdc_admet_tox_fullrun.sh but
not shipped in the public release. That wrapper carries none of the inline
patches the ARC wrapper applies, so this file must perform them. All logic is
ported verbatim from the working 02xARC wrapper blocks:

1. register OPENAI_MODEL in AVAILABLE_LLMS and route the OpenAI client through
   the injected OPENAI_API_KEY / OPENAI_BASE_URL;
2. rewrite chat completion call sites to the gpt_responses_compat shim
   (created by patch_ai_scientist_v2_common.py, which runs before this);
3. guard token_tracker against providers that return None token details;
4. route every model reference in bfts_config.yaml onto OPENAI_MODEL
   (materializing agent.summary / agent.select_node, whose absence makes
   treesearch/journal.py fall back to a hardcoded gpt-4o).

Idempotent; fails loudly when an upstream anchor is missing. Replace with the
maintainers' original when available. Run from the AI-Scientist-v2 source root.
"""
from __future__ import annotations

import os
from pathlib import Path

MODEL = os.environ.get("OPENAI_MODEL", "")


def patch_llm() -> None:
    path = Path("ai_scientist/llm.py")
    text = path.read_text(encoding="utf-8")
    if MODEL and f'"{MODEL}"' not in text:
        text = text.replace("AVAILABLE_LLMS = [", f'AVAILABLE_LLMS = [\n    "{MODEL}",', 1)
    text = text.replace(
        'elif "gpt" in model:', 'elif "gpt" in model or model == "' + MODEL + '":'
    )
    text = text.replace(
        "return openai.OpenAI(), model",
        'return openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"], '
        'base_url=os.environ["OPENAI_BASE_URL"]), model',
    )
    path.write_text(text, encoding="utf-8")


def patch_chat_create() -> None:
    for raw in ("ai_scientist/llm.py", "ai_scientist/treesearch/backend/backend_openai.py"):
        path = Path(raw)
        text = path.read_text(encoding="utf-8")
        if "from ai_scientist.gpt_responses_compat import chat_create" not in text:
            text = "from ai_scientist.gpt_responses_compat import chat_create\n" + text
        text = text.replace("client.chat.completions.create(", "chat_create(client,")
        path.write_text(text, encoding="utf-8")


def patch_token_tracker() -> None:
    path = Path("ai_scientist/utils/token_tracker.py")
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


def patch_bfts_config() -> None:
    path = Path("bfts_config.yaml")
    if not path.is_file() or not MODEL:
        return
    import yaml

    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    for section in ("summary", "select_node"):
        entry = dict(config["agent"].get(section) or {})
        entry["model"] = MODEL
        entry.setdefault("temp", 0.3)
        config["agent"][section] = entry

    def set_models(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "model" and isinstance(value, str):
                    node[key] = MODEL
                else:
                    set_models(value)
        elif isinstance(node, list):
            for item in node:
                set_models(item)

    set_models(config)
    # Infrastructure: the runner grants 4 CPU cores and no GPU, and without a GPU
    # AI-Scientist-v2 does not cap num_workers (native yaml says 4). Run 065744
    # showed 3 parallel drafts overwriting each other's /workspace/runs/<run_id>/
    # files and the root handoff (trace written 07:03:02, its metrics_file
    # rewritten by a sibling node at 07:03:05 -> host validator mismatch).
    # One worker, like the other 02 topic wrappers; search settings untouched.
    config["agent"]["num_workers"] = int(os.environ.get("TDC_ADMET_TOX_NUM_WORKERS", "1"))
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


HANDOFF_GUIDELINE = [
    "TDC-ADMET-Tox native handoff (facts about the host validator; the program itself must produce everything below in-run):",
    "Data: read only /data/tdc_admet_tox/train.csv, validation.csv and test.csv (columns sample_id, endpoint, smiles, label; test.csv has no label column). Endpoints are AMES, hERG and DILI, identified by the endpoint column. test.csv must never be used for selection. RDKit is not installed; numpy, pandas, scipy and scikit-learn are; do not install or download anything.",
    "Budget: at most 4 CPU cores, 16 GiB memory, no GPU; cumulative experiment runtime must stay under 3600 seconds and the whole program under 7200 seconds; run 2 to 4 distinct configurations total, each with exactly one validation-evaluated candidate (candidate_count 1); never begin a fifth configuration.",
    "Validation evidence: for each configuration write its validation-set predictions to a CSV (sample_id,endpoint,probability) and run the official validation scorer exactly as: python /workspace/automation/scripts/run_tdc_admet_tox_validation_score.py --validation /data/tdc_admet_tox/validation.csv --predictions <that csv> --output-metrics <that run's metrics.json>. The metrics.json it writes (split 'validation', macro_average_auroc, per_endpoint.AMES/hERG/DILI.auroc) is the metrics_file the trace must reference; never put test metrics in it.",
    "Per configuration keep four files under /workspace (for example /workspace/runs/<run_id>/): config.json (its content must differ between configurations), the validation prediction CSV, the metrics.json produced by the scorer, and a log file. Also write at least one file under /workspace/logs/.",
    "Write /workspace/research_idea.json BEFORE the first experiment: a JSON object with non-empty string fields hypothesis, method_rationale, expected_failure_modes, comparison_logic.",
    "Write /workspace/predictions.csv from the SELECTED configuration: header exactly sample_id,endpoint,probability; exactly one row per (sample_id, endpoint) pair of test.csv and no other rows; probabilities within [0, 1]; no label column.",
    "Write /workspace/environment.json with non-empty python_version, platform, device, seeds, packages and created_at.",
    "Write /workspace/experiment_trace.json (strict JSON, no NaN) with: task_id 'tdc_admet_tox'; framework_native_execution true; consumed_topic_input true; framework_internal_model and framework_internal_api_base_url copied from the OPENAI_MODEL and OPENAI_BASE_URL environment variables; selection_metric 'validation_macro_average_auroc'; final_prediction_file 'predictions.csv'; environment_file 'environment.json'; resource_budget exactly {cpu_cores: 4, memory_gib: 16, gpu_count: 0, workspace_disk_gib: 10, max_experiment_runtime_seconds: 3600, max_total_wall_seconds: 7200, network_policy: 'injected_llm_relay_only'}; total_wall_seconds (a number); reproduction {entrypoint: 'reproduce.py', command: 'python reproduce.py', seed (integer)}; the file /workspace/reproduce.py must exist: the source of the running program is written by the framework to runfile.py in the current working directory before execution, so copy os.path.join(os.getcwd(), 'runfile.py') to /workspace/reproduce.py; experiments: a JSON list (not a dict) of the 2-4 configurations, each an object with run_id (unique string), status 'complete', hypothesis, model_strategy, feature_strategy (at least two configurations must differ in both strategy and config content), runtime_seconds (number), seed (integer), candidate_count 1, config_file, prediction_file, metrics_file, log_file (workspace-relative paths that exist) and validation_metrics {macro_average_auroc, per_endpoint {AMES: {auroc}, hERG: {auroc}, DILI: {auroc}}} with values identical to that metrics_file; the third and fourth experiments additionally need parent_run_id (an earlier run_id) and change_rationale; selected_experiment_id: the run_id with the highest validation macro_average_auroc; claims: a JSON list with at least one object {claim_id (letters, digits, _ . : -), source_run_id, endpoint ('AMES', 'hERG', 'DILI' or 'macro'), metric 'auroc', value (the exact number from that run's metrics_file), prediction_file, config_file, log_file (the same paths as the source experiment)}.",
    "Write /workspace/paper.md: a short evidence-backed paper. Host checks on it: every claim_id from the trace must appear somewhere in the paper as the marker <!-- claim:CLAIM_ID -->; EVERY markdown table cell that contains a number must contain, inside that same cell, the marker of the claim whose value that number displays (for example `| independent | 0.8106 <!-- claim:independent_macro_auroc --> |`), so cells such as run names or seeds that are digits also need a claim or must be written without digits; every prose line that reports a metric value must carry the matching marker on that same line; each displayed number must equal its claim value (rounded display is fine). Keep the paper free of hidden-test numbers, and never name any file in the workspace with 'test_labels', 'hidden_labels' or 'labels_test'. Do not create score.json.",
    "At the end print a verification block: each run_id with its validation macro_average_auroc, the selected_experiment_id, the number of rows in predictions.csv, and the byte size of experiment_trace.json, environment.json and paper.md, so the execution log evidences what was produced.",
]


def patch_native_handoff_guideline() -> None:
    """Coder-only: append the host-validated handoff facts to the NATIVE
    implementation guideline (kept intact, so upstream's no-__main__ and
    experiment_data.npy rules stay). Gated by TDC_ADMET_TOX_NATIVE_RUN=1.
    Runs 0828 q/q2/q3 reached stage 2 natively but 0/33 nodes wrote any root
    handoff file: the handoff facts lived only in the ideation blueprint,
    which BFTS nodes never see. Nothing is added to judge-visible task_desc."""
    path = Path("ai_scientist/treesearch/parallel_agent.py")
    text = path.read_text(encoding="utf-8")
    mark = "tdc-native-handoff-guideline"
    if mark in text:
        print("[tdc] handoff guideline already applied")
        return
    anchor = '        return {"Implementation guideline": impl_guideline}'
    if anchor not in text:
        raise SystemExit("[tdc] impl_guideline return anchor not found")
    block = (
        "        # " + mark + ": host-validated handoff facts, coder-only.\n"
        '        if os.getenv("TDC_ADMET_TOX_NATIVE_RUN") == "1":\n'
        "            impl_guideline.extend(" + repr(HANDOFF_GUIDELINE) + ")\n"
        + anchor
    )
    path.write_text(text.replace(anchor, block, 1), encoding="utf-8")


def patch_stage_stop() -> None:
    """The contract is 2-4 configurations in ONE program with a hard budget
    (never a fifth configuration), so stage 1 is the whole experiment: stop
    after it and skip the multi-seed replay, exactly like the psydef/babylm
    wrappers. Stage 2's native goal (add HuggingFace datasets) would violate
    the offline, fixed-dataset contract anyway."""
    path = Path("ai_scientist/treesearch/agent_manager.py")
    text = path.read_text(encoding="utf-8")
    if "TDC_ADMET_TOX_NATIVE_RUN" in text:
        print("[tdc] stage stop already applied")
        return
    if "import os\n" not in text:
        text = "import os\n" + text
    old1 = """        ) = self.parse_stage_names(current_substage.name)
        if main_stage_num == 4:"""
    new1 = """        ) = self.parse_stage_names(current_substage.name)
        if os.getenv("TDC_ADMET_TOX_NATIVE_RUN") == "1":
            return None
        if main_stage_num == 4:"""
    old2 = "                            if current_substage.stage_number in [1, 2, 3, 4]:"
    new2 = """                            if (
                                current_substage.stage_number in [1, 2, 3, 4]
                                and os.getenv("TDC_ADMET_TOX_NATIVE_RUN") != "1"
                            ):"""
    for old in (old1, old2):
        if old not in text:
            raise SystemExit("[tdc] stage-stop anchor not found in agent_manager.py")
    path.write_text(text.replace(old1, new1, 1).replace(old2, new2, 1), encoding="utf-8")


def main() -> None:
    if not Path("ai_scientist").is_dir():
        raise SystemExit("run from the AI-Scientist-v2 source root: ai_scientist/ not found")
    patch_llm()
    patch_chat_create()
    patch_token_tracker()
    patch_bfts_config()
    patch_native_handoff_guideline()
    patch_stage_stop()
    print("tdc_admet_tox AI-Scientist-v2 adapter applied (+ handoff guideline, stage-1 stop)")


if __name__ == "__main__":
    main()
