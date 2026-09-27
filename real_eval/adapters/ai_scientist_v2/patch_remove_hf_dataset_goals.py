#!/usr/bin/env python3
"""Remove the HuggingFace / dataset-count instructions that are impossible under the topic environment.

WHY (2026-09-27, user-approved framework-cognition change; ledger B12)
    The topics are single-dataset and every container runs HF-offline
    (HF_HUB_OFFLINE=1), yet the native stage goals order the coder to
    "Introduce TWO more new datasets from HuggingFace" (stage 2) and to
    "use THREE HuggingFace dataset in total" (stage 3), and the stage-2
    completion evaluation requires "tested on at least two datasets".
    Measured cost: BabyLM x ds stage 3 lost 5/7 nodes to guaranteed-failing
    dataset downloads; completion evaluations fail with "Missing: Only a
    single ..." / "Missing: Use THREE ..." in real runs, so stages 2/3 can
    only ever end at max iterations. Same class as B11: a house-style
    instruction that commands the impossible here.

WHAT IT DOES NOT TOUCH
    The rest of every stage goal, stage 4's "same datasets" line, the
    curve-stability and no-instability completion requirements, the judge
    spec, and B11's target line (separate patch).

Idempotent; loud on anchor drift. Run from the AI-Scientist-v2 source root.
Every 02 result produced with this patch must be marked: native HF/dataset-count
guideline lines removed.
"""
from __future__ import annotations

from pathlib import Path

TARGET = Path("ai_scientist/treesearch/agent_manager.py")
MARK = "remove-hf-dataset-goals"

EDITS = [
    (
        '''                - DO NOT change the model architecture from the previous stage
                - Introduce TWO more new datasets from HuggingFace test the model. Try very hard to think what Huggingface datasets can be used here for testing.""",''',
        '''                - DO NOT change the model architecture from the previous stage""",''',
    ),
    (
        '''                - Be creative and think outside the box
                - MAKE SURE you use THREE HuggingFace dataset in total to test your models""",''',
        '''                - Be creative and think outside the box""",''',
    ),
    (
        '''            2. Datasets Tested: {best_node.datasets_successfully_tested}

            Requirements for completion:
            1. Training curves should show stable convergence
            2. Results should be tested on at least two datasets
            3. No major instabilities or issues in the plots''',
        '''            Requirements for completion:
            1. Training curves should show stable convergence
            2. No major instabilities or issues in the plots''',
    ),
]


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if MARK in text:
        print(f"[{MARK}] already applied")
        return
    for i, (old, _new) in enumerate(EDITS):
        if text.count(old) != 1:
            raise SystemExit(f"[{MARK}] anchor {i} not found or not unique (upstream drift?)")
    for old, new in EDITS:
        text = text.replace(old, new, 1)
    text += f"\n# {MARK}: applied\n"
    TARGET.write_text(text, encoding="utf-8")
    print(f"[{MARK}] applied: stage-2/3 HF goal lines and the stage-2 dataset-count completion requirement removed")


if __name__ == "__main__":
    main()
