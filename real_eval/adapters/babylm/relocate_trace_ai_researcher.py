#!/usr/bin/env python3
"""01 x BabyLM: copy the framework-authored experiment_trace.json to the workspace root for host scoring (host-side, after the run).

The framework writes its trace inside its own workplace; the host scorer reads <run>/workspace/
experiment_trace.json. Copied unchanged (newest wins) and recorded in handoff_relocation.json; nothing
is authored. argv: <framework repo copy> <run base dir>
"""
import json, shutil, sys
from pathlib import Path

repo, base = Path(sys.argv[1]), Path(sys.argv[2])
target = base / "workspace" / "experiment_trace.json"
if not target.is_file():
    candidates = sorted(
        repo.glob("research_agent/workplace_paper/task_*/workplace*/workplace*/experiment_trace.json")
    ) + sorted(repo.glob("research_agent/workplace_paper/task_*/workplace*/workplace*/project/experiment_trace.json"))
    newest = max(candidates, key=lambda c: c.stat().st_mtime, default=None)
    if newest is not None:
        shutil.copy2(newest, target)
        (base / "workspace" / "handoff_relocation.json").write_text(json.dumps({
            "relocated_verbatim": ["experiment_trace.json"],
            "source": str(newest),
            "note": "framework-authored trace copied unchanged for host scoring",
        }, indent=2) + "\n", encoding="utf-8")
        print(f"[babylm-handoff] relocated trace from {newest}")
    else:
        print("[babylm-handoff] framework wrote no experiment_trace.json; nothing relocated")
