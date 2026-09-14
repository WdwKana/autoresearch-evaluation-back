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

SECOND edit (2026-09-14, same factual-only principle): dataset documentation.
    Run fullrun_arc_02_luna_20260914_034336 showed the blueprint names only the
    dataset ROOT; with zero format information, the coding agent blind-guessed
    npy/pkl/json record files and a targets file, found nothing in the real
    parquet-only mount, and every real-data node died ("No valid ARC-WBE MLP
    records were found") -- so BFTS routed around to synthetic data. Describing
    the host-provided input's format is dataset documentation (host's own
    input, not a framework artifact) and states facts only: file, columns,
    shape, and that no labels are provided. No method is suggested.

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
    # Edit 2: dataset documentation (facts only -- file, columns, shape, no
    # labels). Without it the coding agent blind-guesses the on-disk format
    # (observed: npy/pkl guesses + an imagined targets file; every real-data
    # node died on "No valid ARC-WBE MLP records were found").
    (
        "- standardized local dataset root: /data/arc_wbe_2026",
        "- standardized local dataset root: /data/arc_wbe_2026\n"
        "- contents: a single parquet file at data/arc_wbe_2026_weights-00000-of-00001.parquet"
        " (100 records; columns mlp_id, mlp_name, mlp_seed, weights; each weights entry is a"
        " (32, 256, 256) float32 array of per-layer weight matrices; readable with pandas or"
        " pyarrow), plus a metadata.json describing the dataset\n"
        "- the dataset contains weights only: no labels, activations, or targets are provided",
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
    print("[ideation-task-framing] applied: estimator deliverable status + dataset format documentation")


if __name__ == "__main__":
    main()
