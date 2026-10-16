#!/usr/bin/env python3
"""Framework-side delivery bridge for 01 x ARC (the former RELOC inline block of the ARC wrapper).

WHY
    The agent's writable universe (the inner container's /workplace) maps to the task workplace
    under AI-Researcher/research_agent/workplace_paper/task_*/workplace/workplace[/project], not
    to this outer container's /workspace root where the host handoff gate and validators look.
    Copy the five root-level artifacts verbatim from the first complete native set, plus the
    estimator's data sidecars (*.npz / estimator*.json); record what was copied in
    handoff_relocation.json. Content is never generated, repaired, or modified here.

Runs inside the framework container after the native entrypoint (run_infer_idea.py), before the
host-side resolver (real_eval/scripts/resolve_native_artifacts.py) and the handoff gate.
Positioning (2026-10-16 audit of retained runs): in every 01 x ARC run that delivered, THIS step
performed the relocation; the host-side resolver then found everything already present.
"""
import json
import shutil
from pathlib import Path

# Framework-side delivery bridge: the agent's writable universe (the inner
# container's /workplace) maps to the task workplace below, not to this outer
# container's /workspace root where the host handoff gate and validators look.
# Relocate the framework-authored root-level artifacts verbatim; content is
# never generated, repaired, or modified here.
required = ["research_idea.json", "estimator.py", "submission.json", "experiment_trace.json", "final_report.md"]
ws = Path("/workspace")
if all((ws / name).is_file() and (ws / name).stat().st_size for name in required):
    print("[arc-handoff] root-level artifacts already present; nothing to relocate")
else:
    candidates = []
    for base in sorted(ws.glob("AI-Researcher/research_agent/workplace_paper/task_*/workplace/workplace")):
        candidates.append(base)
        candidates.append(base / "project")
    src = next(
        (c for c in candidates if all((c / n).is_file() and (c / n).stat().st_size for n in required)),
        None,
    )
    if src is None:
        print("[arc-handoff] no complete framework-delivered artifact set found; nothing relocated")
    else:
        for name in required:
            shutil.copy2(src / name, ws / name)
        # estimator.py must be runnable at the workspace root: also carry its
        # data sidecars (the brief mandates numpy-loadable .npz/.json params
        # shipped next to estimator.py).
        sidecars = []
        for path in sorted(src.iterdir()):
            if not path.is_file() or path.name in required:
                continue
            if path.suffix == ".npz" or (
                path.name.startswith("estimator") and path.suffix in {".json", ".npz"}
            ):
                shutil.copy2(path, ws / path.name)
                sidecars.append(path.name)
        (ws / "handoff_relocation.json").write_text(
            json.dumps(
                {
                    "relocated_verbatim": required,
                    "estimator_sidecars": sidecars,
                    "source": str(src),
                    "note": (
                        "framework-authored files copied unchanged from the framework's "
                        "native workplace to the wrapper-checked workspace root by the "
                        "framework runtime command"
                    ),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print("[arc-handoff] relocated framework artifacts verbatim from " + str(src))
