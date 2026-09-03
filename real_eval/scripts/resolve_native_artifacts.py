#!/usr/bin/env python3
"""Delivery-map resolver: find contract artifacts where the framework's
worldview natively puts them, and alias them (symlinks) where validators and
frozen scorers expect them. Read-only with respect to content: no bytes are
authored, transformed, or copied — only symlinks are created, and only for
artifacts absent at the expected location.

WHY
    Each framework has a native artifact worldview (survey
    debug/dawei/2026-08-31-native-artifact-survey.md): AI-Researcher's own
    code mandates "ALL code must reside within the project directory". The
    eval's expected layout (workspace root) is not in any framework's native
    vocabulary, so artifacts land in a small, predictable set of native
    locations. This resolver replaces per-wrapper relocation code with one
    declared, ordered candidate list per topic — the delivery map. First
    match wins; every resolution and collision is recorded to
    delivery_map_resolution.json for audit.

USAGE
    resolve_native_artifacts.py --workspace /path --topic arc_wbe_2026
    Exit status is always 0: resolution failure must not mask the run's own
    result — the downstream gate still decides on the materialized layout.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Per-topic delivery map. `roots` are searched in declared order, relative to
# the workspace; the FIRST root containing the artifact (non-empty file) wins.
# `sidecar_globs` name files that must travel next to the primary artifact
# (aliased into the same directory as the materialized primary).
MAPS: dict[str, dict] = {
    "arc_wbe_2026": {
        "roots": [
            ".",  # workspace root: already-delivered artifacts win outright
            "AI-Researcher/research_agent/workplace_paper/task_*/workplace/workplace",
            "AI-Researcher/research_agent/workplace_paper/task_*/workplace/workplace/project",
        ],
        "artifacts": [
            "research_idea.json",
            "estimator.py",
            "submission.json",
            "experiment_trace.json",
            "final_report.md",
        ],
        "sidecars_for": {
            # estimator.py must run standalone at the workspace root; its
            # numpy param files live beside it in the native location.
            "estimator.py": ["*.npz", "estimator*.json"],
        },
    },
    "babylm": {
        # ARC-convention layout (unified 2026-09-03): resolver runs with
        # --workspace $BASE/workspace, framework lives under AI-Researcher/.
        "roots": [
            ".",
            "AI-Researcher/research_agent/workplace_paper/task_*/workplace*/workplace*",
            "AI-Researcher/research_agent/workplace_paper/task_*/workplace*/workplace*/project",
        ],
        "artifacts": [
            "research_idea.json",
            "experiment_trace.json",
            "final_report.md",
        ],
        "sidecars_for": {},
    },
    "mountaincar_continuous": {
        # workplace_name unified to 'workplace' (framework itself is staged at
        # the workspace root by the shared seven-framework runner).
        "roots": [
            ".",
            "workspace/workplace_paper/task_*/workplace/workplace",
            "workspace/workplace_paper/task_*/workplace/workplace/project",
        ],
        "artifacts": [
            "research_idea.json",
            "experiment_trace.json",
            "final_report.md",
            "config.yaml",
        ],
        "sidecars_for": {},
    },
}


def resolve_root(workspace: Path, pattern: str) -> list[Path]:
    if pattern == ".":
        return [workspace]
    return sorted(p for p in workspace.glob(pattern) if p.is_dir())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--topic", required=True, choices=sorted(MAPS))
    args = ap.parse_args()

    ws = Path(args.workspace).resolve()
    spec = MAPS[args.topic]
    record: dict = {
        "topic": args.topic,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "map_roots": spec["roots"],
        "resolutions": {},
        "collisions": {},
        "unresolved": [],
        "note": (
            "Symlink aliasing only; no artifact content was authored, "
            "transformed or copied by the host."
        ),
    }

    expanded: list[Path] = []
    for pat in spec["roots"]:
        expanded.extend(resolve_root(ws, pat))

    for name in spec["artifacts"]:
        target = ws / name
        if target.is_file() and target.stat().st_size and not target.is_symlink():
            record["resolutions"][name] = {"at": ".", "action": "already-present"}
            continue
        hits = []
        for root in expanded:
            cand = root / name
            # lstat discipline: never follow symlinks out of the workspace.
            if cand.is_symlink():
                continue
            if cand.is_file() and cand.stat().st_size and cand != target:
                hits.append(cand)
        if not hits:
            record["unresolved"].append(name)
            print(f"[delivery-map] {name}: not found in any declared root")
            continue
        chosen = hits[0]
        if len(hits) > 1:
            record["collisions"][name] = [str(h.relative_to(ws)) for h in hits]
        if target.is_symlink() or target.exists():
            try:
                target.unlink()
            except OSError:
                pass
        os.symlink(chosen, target)
        record["resolutions"][name] = {
            "at": str(chosen.relative_to(ws)),
            "action": "symlinked",
        }
        print(f"[delivery-map] {name} <- {chosen.relative_to(ws)}")
        for glob_pat in spec["sidecars_for"].get(name, []):
            for sc in sorted(chosen.parent.glob(glob_pat)):
                if sc.is_symlink() or not sc.is_file() or sc.name == name:
                    continue
                sc_target = ws / sc.name
                if not sc_target.exists():
                    os.symlink(sc, sc_target)
                    record["resolutions"].setdefault("_sidecars", []).append(
                        str(sc.relative_to(ws))
                    )
                    print(f"[delivery-map] sidecar {sc.name} <- {sc.relative_to(ws)}")

    (ws / "delivery_map_resolution.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
