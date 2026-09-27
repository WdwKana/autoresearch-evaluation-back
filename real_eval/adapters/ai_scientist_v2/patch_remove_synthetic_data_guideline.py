#!/usr/bin/env python3
"""Remove the one native guideline line that commands the coder to create synthetic data.

WHY (2026-09-27, user-approved framework-cognition change; ledger B11)
    AI-Scientist-v2 is built for open-ended research with no fixed benchmark, so its
    draft sketch guideline natively says "Make sure to create synthetic data if
    needed." (ai_scientist/treesearch/parallel_agent.py:473; byte-identical to
    SakanaAI/AI-Scientist-v2 main @96bd516). On benchmark topics with a provided
    dataset and a frozen scorer this is a counter-instruction: stage-1 nodes follow
    it, the lineage locks at stage 1, and DS/kimi judges do not veto (ARC/BabyLM
    synthetic failures). The provided-data rule already sits in the topic text and
    the reference-module docstring; this patch removes only the opposing command.

WHAT IT DOES NOT TOUCH
    Stage goals (incl. stage 1 "Use a simple dataset"), the judge prompt/spec, the
    num_syn_datasets block (inactive at 1), and the stage-4 ablation line remain
    unchanged.

Idempotent; loud on anchor drift. Run from the AI-Scientist-v2 source root.
Every 02 result produced with this patch must be marked: one native guideline
line removed.
"""
from __future__ import annotations

from pathlib import Path

TARGET = Path("ai_scientist/treesearch/parallel_agent.py")
MARK = "remove-synthetic-data-guideline"

ANCHOR = '''            "Experiment design sketch guideline": [
                "This first experiment design should be relatively simple, without extensive hyper-parameter optimization.",
                "Take the Memory section into consideration when proposing the design. ",
                "The solution sketch should be 6-10 sentences. ",
                "Don't suggest to do EDA.",
                "Make sure to create synthetic data if needed.",
'''
REPLACEMENT = '''            "Experiment design sketch guideline": [
                "This first experiment design should be relatively simple, without extensive hyper-parameter optimization.",
                "Take the Memory section into consideration when proposing the design. ",
                "The solution sketch should be 6-10 sentences. ",
                "Don't suggest to do EDA.",
                # removed (remove-synthetic-data-guideline): "Make sure to create synthetic data if needed.",
'''


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if MARK in text:
        print(f"[{MARK}] already applied")
        return
    if ANCHOR not in text:
        raise SystemExit(f"[{MARK}] anchor not found (upstream drift?)")
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"[{MARK}] anchor not unique")
    TARGET.write_text(text.replace(ANCHOR, REPLACEMENT, 1), encoding="utf-8")
    print(f"[{MARK}] applied: the draft sketch guideline no longer commands synthetic data creation")


if __name__ == "__main__":
    main()
