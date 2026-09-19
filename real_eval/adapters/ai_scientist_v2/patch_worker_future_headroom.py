#!/usr/bin/env python3
"""Infrastructure fix for an AI-Scientist-v2 process-supervision bug.

parallel_agent.py waits for each worker with `future.result(timeout=self.timeout)`
where self.timeout == cfg.exec.timeout, and the timer starts at submission
(before the LLM drafting call). The interpreter enforces the same exec.timeout on
the child, but only sends SIGINT at T, kills at T+60 s, and then returns a
TimeoutError result whose term_out tells the coder the time limit was exceeded.
That result can therefore never arrive before the future expires: every node that
reaches the time limit is dropped with "Worker process timed out" and is not
journaled, so the tree never learns the code was too slow (babylm run 051954 lost
drafts 1 and 2 this way, 3600 s apart to the second).

This patch only gives the parent wait headroom over the child's own limit, so the
framework's existing timeout feedback path becomes reachable. Nothing about the
limit itself, the judge, or the search changes. Margin is configurable via
AI_SCIENTIST_V2_WORKER_FUTURE_HEADROOM_SECONDS (default 900).
Idempotent; run from the AI-Scientist-v2 source root.
"""
from __future__ import annotations

import os
from pathlib import Path

MARK = "worker-future-headroom"
OLD = "                result_data = future.result(timeout=self.timeout)\n"
NEW = (
    "                # " + MARK + ": child enforces exec.timeout itself (SIGINT at T,\n"
    "                # kill at T+60 s, then returns a TimeoutError result); the parent\n"
    "                # wait needs headroom or that result is never received.\n"
    "                result_data = future.result(\n"
    "                    timeout=self.timeout\n"
    '                    + int(os.environ.get("AI_SCIENTIST_V2_WORKER_FUTURE_HEADROOM_SECONDS", "900"))\n'
    "                )\n"
)


def main() -> None:
    path = Path("ai_scientist/treesearch/parallel_agent.py")
    if not path.is_file():
        raise SystemExit("run from the AI-Scientist-v2 source root: parallel_agent.py not found")
    text = path.read_text(encoding="utf-8")
    if MARK in text:
        print("worker future headroom patch already applied")
        return
    # two worker-wait loops: the main step loop and the multi-seed eval loop
    if text.count(OLD) != 2:
        raise SystemExit(f"expected two future.result anchors, found {text.count(OLD)}")
    if "\nimport os\n" not in text:
        text = "import os\n" + text
    path.write_text(text.replace(OLD, NEW), encoding="utf-8")
    print("worker future headroom patch applied")


if __name__ == "__main__":
    main()
