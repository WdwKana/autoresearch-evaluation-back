#!/usr/bin/env python3
"""TDC-ADMET-Tox wiring smoke probe (agent-agnostic).

The stock smoke path drives these checks through `codex exec`. This side runs
Claude Code rather than Codex (see debug/dawei/), and Codex CLI 0.150.1 dropped
the `wire_api = "chat"` transport the provider relay assumes, so the Codex probe
cannot run here at all. AGENTS.md allows a generic agent for smoke/diagnostics
only -- it is never the native research executor -- so which agent performs the
wiring inspection does not affect native-execution integrity.

This script performs exactly the six checks the smoke prompt asks for, from
inside the same container and mounts, and writes the same evidence artifact.
Every check is executed for real; nothing is asserted without being tested.

Usage (inside the smoke container):
    python3 tdc_admet_tox_wiring_probe.py --framework <name> --entrypoint-file <rel path>
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

DATASET = Path("/data/tdc_admet_tox")
EXPECTED_FILES = {"train.csv", "validation.csv", "test.csv", "dataset_manifest.json"}
EXPECTED_ENDPOINTS = {"AMES", "hERG", "DILI"}
LABELLED_HEADER = ["sample_id", "endpoint", "smiles", "label"]
UNLABELLED_HEADER = ["sample_id", "endpoint", "smiles"]
CONTRACTS = [
    Path("/input/automation/tdc_admet_tox_contract.md"),
    Path("/input/docs/tdc_admet_tox_compute_budget.md"),
]
HIDDEN_MARKERS = ("hidden_labels", "hidden_label", "test_labels", "label_root")


def header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return next(csv.reader(handle))


def endpoints(path: Path) -> set[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["endpoint"] for row in csv.DictReader(handle)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--framework", required=True)
    parser.add_argument("--entrypoint-file", required=True)
    parser.add_argument("--output", default="/workspace/tdc_admet_tox_smoke_evidence.json")
    args = parser.parse_args()

    details: dict[str, object] = {}

    entrypoint = Path("/workspace") / args.entrypoint_file
    native_entrypoint = entrypoint.is_file()
    details["native_entrypoint_path"] = str(entrypoint)

    present = {p.name for p in DATASET.iterdir()} if DATASET.is_dir() else set()
    public_files = present == EXPECTED_FILES
    details["public_files_present"] = sorted(present)

    schemas = (
        header(DATASET / "train.csv") == LABELLED_HEADER
        and header(DATASET / "validation.csv") == LABELLED_HEADER
        and header(DATASET / "test.csv") == UNLABELLED_HEADER
    ) if public_files else False

    endpoint_sets = {
        name: sorted(endpoints(DATASET / f"{name}.csv"))
        for name in ("train", "validation", "test")
    } if public_files else {}
    endpoints_ok = bool(endpoint_sets) and all(
        set(values) == EXPECTED_ENDPOINTS for values in endpoint_sets.values()
    )
    details["endpoint_sets"] = endpoint_sets

    contracts = all(path.is_file() and os.access(path, os.R_OK) for path in CONTRACTS)

    # Names only -- never print or inspect values.
    flagged_env = [n for n in os.environ if any(m in n.lower() for m in HIDDEN_MARKERS)]
    flagged_paths = [
        n for n in sorted(present) if any(m in n.lower() for m in HIDDEN_MARKERS)
    ]
    test_unlabelled = public_files and "label" not in header(DATASET / "test.csv")
    hidden_labels_absent = not flagged_env and not flagged_paths and test_unlabelled
    details["flagged_env_names"] = flagged_env
    details["flagged_paths"] = flagged_paths

    checks = {
        "native_entrypoint": native_entrypoint,
        "public_files": public_files,
        "schemas": schemas,
        "endpoints": endpoints_ok,
        "contracts": contracts,
        "hidden_labels_absent": hidden_labels_absent,
    }
    payload = {
        "task_id": "tdc_admet_tox",
        "framework": args.framework,
        "checks": checks,
        "all_passed": all(checks.values()),
        "probe_agent": "claude-code",
        "probe_note": (
            "Wiring checks executed by this script under Claude Code instead of the "
            "stock `codex exec` probe; the framework-native full-run path is unchanged."
        ),
        "details": details,
    }
    Path(args.output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"all_passed": payload["all_passed"], "checks": checks}))
    return 0 if payload["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
