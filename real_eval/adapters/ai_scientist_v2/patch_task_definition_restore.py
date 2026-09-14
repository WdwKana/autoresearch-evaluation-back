#!/usr/bin/env python3
"""PROVISIONAL, opt-in: restore the official ARC-WBE task definition to the
run-workspace blueprint. Canonical files are NOT touched.

STATUS
    Pending team ratification. Gated by ARC_WBE_2026_RESTORE_DEFINITION=1
    (default: no-op). To remove later: stop setting the env var (instant),
    or delete this file + its two wrapper lines. The canonical task files
    (automation/arc_wbe_2026_contract.md, the summary generator) are never
    modified by this patch -- it appends only to the RUN WORKSPACE COPY of
    the 02 blueprint, so every canonical byte stays as the team wrote it.

WHY (2026-09-14 investigation, all independently verified)
    The official AIcrowd starterkit (local copy: /root/whest-starterkit)
    states the task definition in its README's first paragraph: predict the
    per-neuron mean activation under N(0,1) input; scored on final-layer MSE
    x max(0.1, C/B); lower is better. Its reference implementation
    local_engine.py:77-80 fixes the semantics: x = standard_normal(...);
    x = maximum(matmul(x, w), 0) per layer. Our materialization carried the
    data, scorer, and budget machinery but dropped this sentence; an
    exhaustive sweep of every framework-visible byte (workspace docs,
    contract, prompts, mounts) found no definition anywhere. Effects
    measured: 01-DS's estimator guessed the transposed convention (cos 0.348
    as-is vs 0.956 transposed); 02 stage-1 nodes cannot construct valid
    supervision and die to the judge (6 wipeouts). Restoring the definition
    is restoring the official exam paper, not prescribing a method.

WHAT
    Appends an "Official task definition" block (facts only, faithful to the
    starterkit README + local_engine.py) to the workspace blueprint
    ai_scientist/ideas/arc_wbe_2026_topic.md. Ideation reads the blueprint,
    and the framework's own idea record carries the definition to every BFTS
    stage natively -- no per-stage injection is added.

Idempotent; fail-loud on missing blueprint; no-op unless the env gate is set.
"""
from __future__ import annotations

import os
from pathlib import Path

TOPIC = Path("ai_scientist/ideas/arc_wbe_2026_topic.md")
MARK = "<!-- official-task-definition-restore -->"

BLOCK = """
## Official Task Definition (restored from the ARC-WBE starterkit README)
- Ground truth: for each MLP, the per-neuron mean activation under standard
  normal input `x ~ N(0, 1)` -- the mean over inputs of each layer's
  post-ReLU activations (the challenge estimates it with N = 1e9 Monte Carlo
  samples).
- Forward convention (starterkit reference implementation `local_engine.py`):
  activations propagate as `x = max(x @ W_l, 0)` for each layer `l`.
- Official score: final-layer MSE (`final_layer_mse`) multiplied by
  `max(0.1, C/B)`, where C is the FLOPs your estimator spends and B is the
  per-MLP FLOP budget; LOWER is better. All-layers MSE is diagnostic only.
""".rstrip() + "\n" + MARK + "\n"


def main() -> None:
    if os.environ.get("ARC_WBE_2026_RESTORE_DEFINITION") != "1":
        print("[task-definition-restore] gate unset; no-op (canonical behavior)")
        return
    if not TOPIC.is_file():
        raise SystemExit(f"[task-definition-restore] blueprint not found: {TOPIC}")
    text = TOPIC.read_text(encoding="utf-8")
    if MARK in text:
        print("[task-definition-restore] already applied")
        return
    TOPIC.write_text(text.rstrip("\n") + "\n" + BLOCK, encoding="utf-8")
    print("[task-definition-restore] applied: official task definition appended to workspace blueprint")


if __name__ == "__main__":
    main()
