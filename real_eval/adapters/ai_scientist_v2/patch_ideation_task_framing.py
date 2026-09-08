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

WHAT (de-ambiguation, not behavior-shaping -- same doctrine as empty-input
      truth / the phantom-milestone fix). Three minimal edits:
      1. estimator.py: drop "when possible" -> required deliverable.
      2. Scientific Independence: scope the freedom -- method is free, the
         deliverable interface and output files are fixed.
      3. TL;DR: state once this is a concrete implementation task, not an
         open-ended research question.
    Method choice stays entirely the framework's; only the false "maybe just
    do research" framing is removed.

Idempotent; loud on anchor drift. Run from the AI-Scientist-v2 source root.
"""
from __future__ import annotations

from pathlib import Path

TOPIC = Path("ai_scientist/ideas/arc_wbe_2026_topic.md")
MARK = "<!-- ideation-task-framing -->"

EDITS = [
    (
        "3. emits a runnable `estimator.py` when possible so the official local scorer can be replayed,",
        "3. writes a runnable `estimator.py` (required) implementing the scorer's `predict(mlp) -> (32, 256)` interface over the real MLP weights in /data/arc_wbe_2026, so the official local scorer can be replayed,",
    ),
    (
        "# Scientific Independence\nThe framework owns the hypothesis, method choice, experiment design, comparison, and final selection. No algorithm family, feature representation, architecture, hyperparameters, baseline, or experiment sequence is prescribed.",
        "# Scientific Independence\nThe framework owns the hypothesis, method choice, experiment design, comparison, and final selection. No algorithm family, feature representation, architecture, hyperparameters, baseline, or experiment sequence is prescribed. This freedom is over METHOD only: the deliverable interface and the required output files (see Concrete Goal) are fixed and must be produced regardless of the method chosen -- this is not an open-ended research question about benchmark estimation, it is a concrete task to implement a specific estimator against the real dataset.",
    ),
    (
        "# TL;DR\nBuild a reproducible ARC White-Box Estimation Challenge 2026 workflow that produces official-format outputs, records benchmark evidence, and optimizes the benchmark score where local scoring exists.",
        "# TL;DR\nThis is a concrete implementation task with a fixed output interface, not an open-ended research question: build a reproducible ARC White-Box Estimation Challenge 2026 workflow that produces official-format outputs (a runnable estimator over the real dataset), records benchmark evidence, and optimizes the benchmark score where local scoring exists.",
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
    print("[ideation-task-framing] applied: estimator required + method-only independence + concrete-task TL;DR")


if __name__ == "__main__":
    main()
