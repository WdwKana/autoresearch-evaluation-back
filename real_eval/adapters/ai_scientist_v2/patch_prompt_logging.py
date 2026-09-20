#!/usr/bin/env python3
"""Logging-only diagnostic patch for AI-Scientist-v2 BFTS (no behavior change).

Writes, under <cwd>/prompt_logs/ :
  <stage>_step_<k>_memory.md  the Memory summary generated at the start of step k of that stage
                              (stage prefix added 2026-09-20: without it, stage 2 overwrote stage 1's files)
  q_<n>_<kind>_<pid>.md       every compiled prompt sent through
                              MinimalAgent.plan_and_code_query / ParallelAgent.plan_and_code_query
                              (kind = draft | debug | improve | other, inferred from prompt keys)
  q_<n>_<kind>_<pid>.reply.md the raw completion text returned for it

The patched functions return exactly what upstream returns; failures inside the
logging code are swallowed so they can never alter a run. Idempotent; fails loudly
if the upstream anchors move. Run from the AI-Scientist-v2 source root.
"""
from __future__ import annotations

from pathlib import Path

TARGET = Path("ai_scientist/treesearch/parallel_agent.py")
MARK = "prompt-logging-diagnostic"

HELPER = '''
# ''' + MARK + ''': logging-only helpers (no behavior change)
import json as _pl_json, os as _pl_os, time as _pl_time, itertools as _pl_it
_pl_counter = _pl_it.count(1)


def _pl_dir():
    d = _pl_os.environ.get("PROMPT_LOG_DIR") or _pl_os.path.join(_pl_os.getcwd(), "prompt_logs")
    _pl_os.makedirs(d, exist_ok=True)
    return d


def _pl_kind(prompt):
    try:
        keys = set(prompt.keys())
    except Exception:
        return "other"
    if "Previous (buggy) implementation" in keys:
        return "debug"
    if "Previous solution" in keys:
        return "improve"
    if "Research idea" in keys and "Memory" in keys:
        return "draft"
    return "other"


def _pl_log_prompt(prompt, completion_text):
    try:
        from ai_scientist.treesearch.backend.utils import compile_prompt_to_md
        n = next(_pl_counter)
        kind = _pl_kind(prompt)
        base = _pl_os.path.join(_pl_dir(), f"q_{n:03d}_{kind}_{_pl_os.getpid()}")
        with open(base + ".md", "w", encoding="utf-8") as f:
            f.write(f"<!-- {_pl_time.strftime('%Y-%m-%dT%H:%M:%SZ', _pl_time.gmtime())} kind={kind} -->\\n")
            f.write(compile_prompt_to_md(prompt))
        with open(base + ".reply.md", "w", encoding="utf-8") as f:
            f.write(completion_text if isinstance(completion_text, str) else repr(completion_text))
    except Exception:
        pass


def _pl_log_memory(step_index, memory_summary, stage_name=None):
    try:
        tag = (str(stage_name)[:12] + "_") if stage_name else ""
        with open(_pl_os.path.join(_pl_dir(), f"{tag}step_{step_index:03d}_memory.md"), "w", encoding="utf-8") as f:
            f.write(memory_summary if isinstance(memory_summary, str) else repr(memory_summary))
    except Exception:
        pass
'''

# 1. hook the two plan_and_code_query loops: log the compiled prompt and the raw completion.
Q_OLD = (
    "            completion_text = query(\n"
    "                system_message=prompt,\n"
    "                user_message=None,\n"
    "                model=self.cfg.agent.code.model,\n"
    "                temperature=self.cfg.agent.code.temp,\n"
    "            )\n"
)
Q_NEW = Q_OLD + "            _pl_log_prompt(prompt, completion_text)  # " + MARK + "\n"

# 2. hook the memory summary generated at the start of each step.
M_OLD = (
    "        else:\n"
    "            memory_summary = self.journal.generate_summary(include_code=False)\n"
)
M_NEW = M_OLD + (
    "        _pl_log_memory(len(self.journal.nodes), memory_summary, getattr(self, \"stage_name\", None))  # " + MARK + "\n"
)


def main() -> None:
    if not TARGET.is_file():
        raise SystemExit("run from the AI-Scientist-v2 source root: parallel_agent.py not found")
    text = TARGET.read_text(encoding="utf-8")
    if MARK in text:
        print("prompt logging patch already applied")
        return
    if text.count(Q_OLD) != 2:
        raise SystemExit(f"expected 2 plan_and_code_query anchors, found {text.count(Q_OLD)}")
    if text.count(M_OLD) != 1:
        raise SystemExit("memory summary anchor not found")
    text = text.replace(Q_OLD, Q_NEW).replace(M_OLD, M_NEW, 1)
    # helpers go right after the import block (before the first top-level def/class)
    idx = text.index("\ndef _safe_pickle_test")
    text = text[:idx] + "\n" + HELPER + text[idx:]
    TARGET.write_text(text, encoding="utf-8")
    print("prompt logging patch applied")


if __name__ == "__main__":
    main()
