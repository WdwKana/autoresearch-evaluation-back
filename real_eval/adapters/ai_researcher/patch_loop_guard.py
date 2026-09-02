#!/usr/bin/env python3
"""Add the two missing guardrails to the framework's agent loop.

Four kimi-k2.6 runs on 2026-09-02 each ended in a different non-convergent
tool loop (hand-rolled GitHub search x505 msgs, filename guessing x2, and
261 consecutive re-opens of the same file that ran the context to 268k
tokens). The model supplies the pathological policy, but the framework
supplies unbounded amplification: core.py's agent loop has

  - no repetition detection of any kind, and
  - max_turns defaulting to float("inf"), with AgentModule never passing a
    finite value,

whereas every mainstream scaffold (Claude Code, OpenHands, SWE-agent,
smolagents, AutoGen) bounds iterations and/or brakes repeated actions.

Two guardrails, both model-agnostic and inert on healthy sessions:

  1. Repetition brake: on the 3rd consecutive tool call with identical
     name+arguments, append an explicit [loop-guard] note to the tool result
     telling the model the result cannot change and to act differently; at
     AI_RESEARCHER_LOOP_GUARD_LIMIT (default 8) consecutive identical calls,
     end the session with a final instruction to produce the best answer
     from what it already has. Varied calls never trigger it (the healthy
     luna/DS archives contain no 3-in-a-row identical calls).
  2. Turn cap: when the caller left max_turns at float("inf"), resolve it
     from AI_RESEARCHER_MAX_TURNS (messages per agent session; unset keeps
     infinity). The longest healthy session observed is 103 messages, the
     pathological ones 505-557.

Both loops (sync run and async run_async) are instrumented -- the two code
blocks are textually identical and are patched by occurrence count, exactly
like the request probe. Idempotent; fails loudly if anchors move or the
occurrence count is not 2. Run from the AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

CORE = Path("research_agent/inno/core.py")

IMPORT_ANCHOR = "import copy"
IMPORT_ADD = '''import copy
import os as _lg_os
_LG_LIMIT = max(3, int(_lg_os.getenv("AI_RESEARCHER_LOOP_GUARD_LIMIT", "8")))'''

WHILE_OLD = """        while len(history) - init_len < max_turns and active_agent:"""
WHILE_NEW = """        if max_turns == float("inf") and _lg_os.getenv("AI_RESEARCHER_MAX_TURNS"):
            try:
                max_turns = float(_lg_os.getenv("AI_RESEARCHER_MAX_TURNS"))
            except ValueError:
                pass
        _lg_last_sig = None
        _lg_rep = 0
        while len(history) - init_len < max_turns and active_agent:"""

EXTEND_OLD = """            history.extend(partial_response.messages)
            context_variables.update(partial_response.context_variables)
            if partial_response.agent:
                active_agent = partial_response.agent"""
EXTEND_NEW = """            history.extend(partial_response.messages)
            context_variables.update(partial_response.context_variables)
            if partial_response.agent:
                active_agent = partial_response.agent
            # loop-guard: brake consecutive identical tool calls
            _lg_sig = None
            try:
                if message.tool_calls:
                    _lg_sig = (message.tool_calls[0].function.name or "") + "|" + (message.tool_calls[0].function.arguments or "")
            except Exception:
                _lg_sig = None
            if _lg_sig is not None and _lg_sig == _lg_last_sig:
                _lg_rep += 1
            else:
                _lg_last_sig = _lg_sig
                _lg_rep = 1
            if (
                _lg_rep >= 3
                and history
                and isinstance(history[-1], dict)
                and history[-1].get("role") == "tool"
                and isinstance(history[-1].get("content"), str)
            ):
                if _lg_rep >= _LG_LIMIT:
                    history[-1]["content"] += (
                        "\\n\\n[loop-guard] You have now made " + str(_lg_rep)
                        + " consecutive identical tool calls. The loop guard is ending this session:"
                        + " summarize and produce your best final answer from the information you already have."
                    )
                    self.logger.info("loop-guard: ending session after " + str(_lg_rep) + " identical calls", title="Loop Guard", color="red")
                    break
                history[-1]["content"] += (
                    "\\n\\n[loop-guard] This was consecutive identical call #" + str(_lg_rep)
                    + " to the same tool with the same arguments. Its result has not changed and will not change."
                    + " Take a DIFFERENT action: different arguments, a different tool"
                    + " (e.g. page_down_markdown to read the next page of an open document),"
                    + " or produce your final answer as plain text."
                )"""


def main() -> None:
    if not CORE.is_file():
        raise SystemExit("loop-guard: run from the AI-Researcher source root")
    text = CORE.read_text(encoding="utf-8")
    if "_LG_LIMIT" in text:
        print("[loop-guard] already applied")
        return
    for label, old, expected in (
        ("while", WHILE_OLD, 2),
        ("extend", EXTEND_OLD, 2),
    ):
        n = text.count(old)
        if n != expected:
            raise SystemExit(f"loop-guard: anchor '{label}' found {n} times, expected {expected}")
    if IMPORT_ANCHOR not in text:
        raise SystemExit("loop-guard: import anchor not found")
    text = text.replace(IMPORT_ANCHOR, IMPORT_ADD, 1)
    text = text.replace(WHILE_OLD, WHILE_NEW)
    text = text.replace(EXTEND_OLD, EXTEND_NEW)
    CORE.write_text(text, encoding="utf-8")
    print("[loop-guard] applied: repetition brake (warn@3, stop@" 
          + "limit) + env-resolved max_turns, both loops")


if __name__ == "__main__":
    main()
