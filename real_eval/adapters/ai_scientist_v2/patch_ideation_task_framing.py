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

SECOND edit RETRACTED (2026-09-14, same day it was added): dataset docs moved
    out of the blueprint entirely. Adding the format facts here (visible to
    ideation) steered every subsequent idea into "label-free" spectral/
    transport geometry -- mathematically treacherous themes whose stage-1
    implementations the framework's own judge wiped out three runs straight
    (051027/065524/081118: 50+ nodes, 0 non-buggy), while the docs-free run
    034336 passed stage 1 with 5/13 non-buggy nodes. The blind-guessing
    problem the docs were meant to fix lives at the CODING layer (stage 2+
    find_records guessing npy/pkl + an imagined targets file), and its fix
    stays exactly there: the format facts remain in
    patch_bfts_delivery_contract's stage-2+ implementation guideline. Each
    fix at the layer where its disease was observed; ideation reads only what
    034336 proved sufficient.

Idempotent; loud on anchor drift. Run from the AI-Scientist-v2 source root.
"""
from __future__ import annotations

from pathlib import Path

TOPIC = Path("ai_scientist/ideas/arc_wbe_2026_topic.md")
MARK = "<!-- ideation-task-framing -->"

EDITS = [
    # Edit 1: estimator.py is a required deliverable, not "when possible".
    # This is a factual correction of the deliverable status (and names the
    # scorer interface + real data location); it does NOT tell the model how to
    # frame the task or forbid research -- that framing is left to the model.
    (
        "3. emits a runnable `estimator.py` when possible so the official local scorer can be replayed,",
        "3. writes a runnable `estimator.py` implementing the scorer's `predict(mlp) -> (32, 256)` interface over the real MLP weights in /data/arc_wbe_2026, so the official local scorer can be replayed,",
    ),
    # (Edit 2 -- blueprint dataset docs -- RETRACTED; see docstring. The
    # format facts live in the stage-2+ implementation guideline instead.)
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
    print("[ideation-task-framing] applied: estimator deliverable status + dataset format documentation")


if __name__ == "__main__":
    main()
