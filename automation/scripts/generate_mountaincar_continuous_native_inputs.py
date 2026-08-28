#!/usr/bin/env python3
"""MountainCar-Continuous native input generator (thin adapter over topic2's).

The topic was renamed topic2 -> mountaincar_continuous, but the rename only
reached the wrappers. `real_eval/scripts/mountaincar_framework_fullrun.sh`
copies four mountaincar_continuous_* files out of the staged input root, while
this path used to be a symlink to generate_topic2_native_inputs.py, which emits
topic2_* names -- so every run died at that copy (see
real_eval/runs/fullrun_mcar_01_20260828_121504_m2).

This adapter runs the topic2 generator untouched and then duplicates the
renamed artifacts alongside the originals. generate_topic2_native_inputs.py is
not modified and the topic2 flow is unaffected: collaborators' topic2 runs
produce exactly what they did before.

This is scaffolding, not the fix. Completing the rename properly means the
generator emitting mountaincar names directly, plus a contract file and a
runs.json mapping for the topic (see debug/dawei/collaborator-checklist.md).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOPIC2_GENERATOR = HERE / "generate_topic2_native_inputs.py"

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


def output_root_from(argv: list[str]) -> Path | None:
    for index, item in enumerate(argv):
        if item == "--output-root" and index + 1 < len(argv):
            return Path(argv[index + 1])
        if item.startswith("--output-root="):
            return Path(item.split("=", 1)[1])
    return None


def main() -> int:
    argv = sys.argv[1:]
    result = subprocess.run([sys.executable, str(TOPIC2_GENERATOR), *argv])
    if result.returncode != 0:
        return result.returncode

    output_root = output_root_from(argv)
    if output_root is None:
        print("[mcar-inputs] no --output-root given; nothing to rename")
        return 0

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
            target.write_text(
                body.replace("dataset_candidate/topic2", "dataset_candidate/mountaincar_continuous"),
                encoding="utf-8",
            )
        print(f"[mcar-inputs] {source_rel} -> {target_rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
