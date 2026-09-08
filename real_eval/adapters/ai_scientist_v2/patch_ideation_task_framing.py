#!/usr/bin/env python3
"""Frame ARC-WBE-2026 to ideation as a concrete deliverable task, not an open
research question.

WHY (2026-09-07)
    02's ideation blueprint (ai_scientist/ideas/arc_wbe_2026_topic.md) sends
    ideation two conflicting signals, and the research one wins:
      - "emits a runnable estimator.py WHEN POSSIBLE" softens the hard
        deliverable into an optional nicety;
      - a full "Scientific Independence" paragraph reads, to a novelty-seeking
        ideation model, as a licence to invent a research programme.
    Result (traced in run 154034): the idea's Title/Abstract/Hypothesis became
    a self-invented study ("Adaptive Probe Consensus"), estimator.py was never
    the target, and BFTS then trained on 1200x8 SYNTHETIC toy data, producing
    best_solution_<hash>.py that never reads the real MLP weights and never
    writes the four contract files. The delivery contract injected later lands
    only in the idea's Experiments tail and cannot re-aim a soul already set on
    free research.

WHAT (per user decision 2026-09-07: minimal, factual only)
    ONE edit: estimator.py "when possible" -> a runnable estimator.py that
    implements the scorer's predict(mlp)->(32,256) interface over the real
    /data/arc_wbe_2026 weights. This corrects the deliverable's STATUS
    (optional -> stated deliverable) and names the interface + data location.
    It does NOT tell the model this "is not research" or otherwise frame its
    thinking -- earlier drafts that did so were removed as blueprint overreach.
    How the task is understood is left to the model; the blueprint only states
    what the deliverable is.

Idempotent; loud on anchor drift. Run from the AI-Scientist-v2 source root.
"""
from __future__ import annotations

from pathlib import Path

TOPIC = Path("ai_scientist/ideas/arc_wbe_2026_topic.md")
MARK = "<!-- ideation-task-framing -->"

EDITS = [
    # Only edit: estimator.py is a required deliverable, not "when possible".
    # This is a factual correction of the deliverable status (and names the
    # scorer interface + real data location); it does NOT tell the model how to
    # frame the task or forbid research -- that framing is left to the model.
    (
        "3. emits a runnable `estimator.py` when possible so the official local scorer can be replayed,",
        "3. writes a runnable `estimator.py` implementing the scorer's `predict(mlp) -> (32, 256)` interface over the real MLP weights in /data/arc_wbe_2026, so the official local scorer can be replayed,",
    ),
]


def main() -> None:
    if not TOPIC.is_file():
        raise SystemExit(f"[ideation-task-framing] blueprint not found: {TOPIC}")
    text = TOPIC.read_text(encoding="utf-8")
    if MARK in text:
        print("[ideation-task-framing] already applied")
        return
    for old, new in EDITS:
        if old not in text:
            raise SystemExit(f"[ideation-task-framing] anchor not found: {old[:60]!r}")
        text = text.replace(old, new, 1)
    text = text.rstrip("\n") + "\n" + MARK + "\n"
    TOPIC.write_text(text, encoding="utf-8")
    print("[ideation-task-framing] applied: estimator.py stated as a runnable deliverable (predict interface + real data)")


if __name__ == "__main__":
    main()
