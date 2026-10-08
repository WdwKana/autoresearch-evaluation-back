#!/usr/bin/env python3
"""MountainCar-Continuous native inputs for 01 / 02 (adapter over the topic2 generator).

Upstream renamed the topic topic2 -> mountaincar_continuous in the wrappers and
the runner only. automation/scripts/generate_mountaincar_continuous_native_inputs.py
is a symlink to the topic2 generator and emits topic2_* names, while
real_eval/scripts/mountaincar_framework_fullrun.sh copies four
mountaincar_continuous_* files out of the staged input root -- so every run died
at that copy (see real_eval/runs/fullrun_mcar_01_20260828_121504_m2) -- and
automation/mountaincar_continuous_contract.md is a 0-byte file.

All of that stays at upstream. This adapter
  1. runs the topic2 generator through the calling framework's overlay
     (real_eval/adapters/shared_layer_overlay.py),
  2. stages the topic's contract text -- upstream's automation/topic2_contract.md,
     the same topic under its pre-rename name -- when the contract file it was
     handed is empty,
  3. duplicates the staged topic2_* artifacts under the mountaincar_continuous_*
     names the runner reads.

usage: generate_native_inputs.py <framework> [topic2 generator arguments...]

This is scaffolding, not the fix. Completing the rename properly means the
generator emitting mountaincar names directly, plus a contract file and a
runs.json mapping for the topic (see debug/dawei/collaborator-checklist.md).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# the checkout this file lives in, spelled as the caller invoked it (a RESEARCHCLAWEVAL_ROOT
# naming another checkout is rejected by the overlay engine this script calls)
ROOT = Path(os.path.abspath(__file__)).parents[3]
OVERLAY = ROOT / "real_eval" / "adapters" / "shared_layer_overlay.py"
TOPIC2_GENERATOR = "automation/scripts/generate_topic2_native_inputs.py"
TOPIC2_CONTRACT = ROOT / "automation" / "topic2_contract.md"

# staged path emitted by the topic2 generator -> path the mountaincar wrapper reads
RENAMES = {
    "docs/topic2_summary.md": "docs/mountaincar_continuous_summary.md",
    "automation/topic2_contract.md": "automation/mountaincar_continuous_contract.md",
    "automation/topic2_execution_budget.md": "automation/mountaincar_continuous_execution_budget.md",
    "automation/scripts/run_topic2_host_score.py": "automation/scripts/run_mountaincar_continuous_host_score.py",
    "AI-Researcher/benchmark/process/dataset_candidate/topic2/metaprompt.py": (
        "AI-Researcher/benchmark/process/dataset_candidate/mountaincar_continuous/metaprompt.py"
    ),
}


def option_from(argv: list[str], name: str) -> Path | None:
    for index, item in enumerate(argv):
        if item == name and index + 1 < len(argv):
            return Path(argv[index + 1])
        if item.startswith(f"{name}="):
            return Path(item.split("=", 1)[1])
    return None


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        print("usage: generate_native_inputs.py <framework> [topic2 generator arguments...]", file=sys.stderr)
        return 2
    framework, argv = sys.argv[1], sys.argv[2:]
    result = subprocess.run([sys.executable, str(OVERLAY), "generate", framework, TOPIC2_GENERATOR, *argv])
    if result.returncode != 0:
        return result.returncode

    output_root = option_from(argv, "--output-root")
    if output_root is None:
        print("[mcar-inputs] no --output-root given; nothing to rename")
        return 0

    contract_file = option_from(argv, "--contract-file")
    if contract_file is not None and contract_file.is_file() and not contract_file.read_text(encoding="utf-8").strip():
        # same normalisation the generator applies to the contract it stages
        staged = output_root / "automation" / "topic2_contract.md"
        staged.write_text(TOPIC2_CONTRACT.read_text(encoding="utf-8").rstrip() + "\n", encoding="utf-8")
        print(f"[mcar-inputs] {contract_file} is empty; staged the contract text of automation/topic2_contract.md")

    for source_rel, target_rel in RENAMES.items():
        source = output_root / source_rel
        if not source.is_file():
            print(f"[mcar-inputs] expected generator output missing: {source_rel}")
            continue
        target = output_root / target_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        # the metaprompt addresses its own dataset_candidate directory by name
        if target.suffix == ".py" and "dataset_candidate" in target_rel:
            body = target.read_text(encoding="utf-8")
            body = body.replace("dataset_candidate/topic2", "dataset_candidate/mountaincar_continuous")
            # Run fullrun_mcar_01_20260828_154742 (retained) delivered a root
            # experiment_trace.json whose model field was the literal string
            # "${OPENAI_MODEL}" -- the agent transcribed the shell placeholder
            # instead of the resolved value, and the handoff gate rejects
            # unexpanded provider placeholders by regex. State the requirement
            # in the brief the agent actually reads. mountaincar-only copy;
            # the topic2 original is not touched.
            body += (
                '\nTRACE_VALUE_RULE = "In experiment_trace.json and all delivered files, record the '
                'ACTUAL resolved values of the model name and API base URL (for example the literal '
                "model string you are running as), never shell placeholder text such as ${OPENAI_MODEL} "
                'or ${OPENAI_BASE_URL}. Unexpanded placeholders fail the handoff audit."\n'
            )
            target.write_text(body, encoding="utf-8")
        print(f"[mcar-inputs] {source_rel} -> {target_rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
