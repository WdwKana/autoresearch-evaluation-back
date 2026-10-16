#!/usr/bin/env python3
"""Relocate the framework's own MountainCar deliverables to where the contract expects them (01).

The contract asks for five checkpoints at /workspace/checkpoints, but the agent produces them inside
its own workplace. Relocate verbatim; never author. A checkpoint is only evaluable together with the
src/ it was trained with (fullrun_mcar_01_luna_20260903_153128 left two sets, each with its own
networks.py; mixing them made the frozen evaluator fail on a parameter-shape mismatch), so ONE set is
picked (newest complete one) and its code carried with it: every src/ on the path from the workplace
root down to that set, outer first, inner wins. research_idea.json / experiment_trace.json /
final_report.md are relocated the same way (newest wins). MCAR_HANDOFF_WORKSPACE exists only so this
can be replayed offline against a retained run tree; inside the container it is always /workspace.

Runs inside the framework container after the native entrypoint, before the delivery gate.
"""
import json
import os
import shutil
from pathlib import Path

ws = Path(os.environ.get("MCAR_HANDOFF_WORKSPACE", "/workspace"))
target = ws / "checkpoints"
target.mkdir(parents=True, exist_ok=True)
NAMES = [f"config-42-{i}.pkl" for i in range(5)]
existing = sorted(p.name for p in target.glob("config-42-*.pkl"))
moved = []
provenance = {}
if len(existing) >= 5:
    print(f"[mcar-handoff] checkpoints already at workspace root: {existing}")
else:
    found = list(ws.glob("**/workplace/**/checkpoints/config-42-*.pkl")) or list(
        ws.glob("**/checkpoints/config-42-*.pkl")
    )
    sets = {}
    for source in found:
        if source.parent == target or not source.is_file():
            continue
        sets.setdefault(source.parent, []).append(source)
    complete = [d for d, files in sets.items() if sorted(f.name for f in files) == NAMES]
    pool = complete or list(sets)
    if not pool:
        print("[mcar-handoff] no framework-produced checkpoints found")
    else:
        chosen = max(pool, key=lambda d: max(f.stat().st_mtime for f in sets[d]))
        print(
            f"[mcar-handoff] {len(sets)} checkpoint set(s) found, {len(complete)} complete; "
            f"using newest: {chosen}"
        )
        for source in sorted(sets[chosen]):
            shutil.copy2(source, target / source.name)
            moved.append(str(source))
        print(f"[mcar-handoff] relocated {len(moved)} checkpoint(s)")
        provenance["checkpoint_set"] = str(chosen)
        set_root = chosen.parent
        chain = [a for a in [set_root, *set_root.parents] if a != ws and ws in a.parents]
        overlay = []
        for ancestor in reversed(chain):  # outermost first, innermost wins
            src_dir = ancestor / "src"
            if not src_dir.is_dir():
                continue
            for f in sorted(src_dir.rglob("*")):
                if not f.is_file() or "__pycache__" in f.parts:
                    continue
                dest = ws / "src" / f.relative_to(src_dir)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
                overlay.append(str(f))
        print(f"[mcar-handoff] overlaid {len(overlay)} src file(s) from the chosen set's code")
        moved.extend(overlay)
        provenance["src_overlay"] = overlay

# The gate also requires research_idea.json, experiment_trace.json and
# final_report.md at the workspace root; the agent writes them inside its own
# workplace (run fullrun_mcar_01_20260828_142606 had a complete PPO trace there
# while the root had none). Relocate verbatim, newest wins, never author.
for name in ("research_idea.json", "experiment_trace.json", "final_report.md"):
    target = ws / name
    if target.is_file() and target.stat().st_size:
        continue
    candidates = [c for c in ws.rglob(name) if c != target and c.is_file() and c.stat().st_size]
    if not candidates:
        print(f"[mcar-handoff] no framework-authored {name} found")
        continue
    newest = max(candidates, key=lambda c: c.stat().st_mtime)
    shutil.copy2(newest, target)
    moved.append(str(newest))
    print(f"[mcar-handoff] relocated {name} from {newest}")

if moved:
    (ws / "handoff_relocation.json").write_text(
        json.dumps({"topic": "mountaincar_continuous", "relocated": moved, **provenance}, indent=2) + "\n",
        encoding="utf-8",
    )
