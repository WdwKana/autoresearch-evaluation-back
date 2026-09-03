#!/usr/bin/env python3
"""Add the missing guardrails to the framework's agent loop (v3).

core.py's agent loop has no repetition detection, max_turns defaults to
float("inf"), and an empty completion (no content, no tool calls) is appended
to history and answered with a generic "Please use the tools" nag -- which,
fed to a model that IS using tools but never finalising, reads as "keep doing
what you're doing" (observed: 79-minute Coding Plan churn, peak 105k tokens,
alternating plan_* calls and empty replies, case_resolved never called).
Billing showed those "empty" turns each burned 51-500+ completion tokens, so
tokens are produced (likely reasoning) that never become an action.

Guardrails, all model-agnostic and inert on healthy sessions:

  1. Repetition brake: 3rd consecutive identical tool call (name+arguments)
     appends an explicit [loop-guard] note; at AI_RESEARCHER_LOOP_GUARD_LIMIT
     (default 8) a final notice plus ONE grace turn, then hard stop. Empty
     completions are transparent to the streak (v3 fix: they no longer reset
     the counter -- that was a free escape hatch).
  2. Turn cap: max_turns left at infinity resolves from
     AI_RESEARCHER_MAX_TURNS (wrapper default 300 messages).
  3. Empty-completion handling (v3): an empty completion is never useful
     history. Retry it up to AI_RESEARCHER_EMPTY_RETRY times (default 1)
     without polluting the transcript; if emptiness persists it is appended
     (so max_turns still advances) and at AI_RESEARCHER_EMPTY_LIMIT (default
     6) consecutive empties the session ends. The generic nag becomes a
     directive controller message pointing at finalisation.

The guard ends only the current agent session; the outer pipeline continues.
Both the sync and async loops are patched by occurrence count. Validated by
replaying real archives: healthy luna/DS sessions trigger nothing. Idempotent;
loud on anchor drift. Run from the AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

CORE = Path("research_agent/inno/core.py")

IMPORT_ANCHOR = "import copy"
IMPORT_ADD = '''import copy
import os as _lg_os
_LG_LIMIT = max(3, int(_lg_os.getenv("AI_RESEARCHER_LOOP_GUARD_LIMIT", "8")))
_LG_EMPTY_RETRY = max(0, int(_lg_os.getenv("AI_RESEARCHER_EMPTY_RETRY", "1")))
_LG_EMPTY_LIMIT = max(2, int(_lg_os.getenv("AI_RESEARCHER_EMPTY_LIMIT", "6")))'''


# per-loop finish_reason capture (sync/async response variables differ)
SYNC_FINISH_OLD = """            message: Message = completion.choices[0].message
            message.sender = active_agent.name"""
SYNC_FINISH_NEW = """            message: Message = completion.choices[0].message
            message.sender = active_agent.name
            _lg_finish = getattr(completion.choices[0], "finish_reason", None)"""
ASYNC_FINISH_OLD = """            message: Message = completion_response.choices[0].message
            message.sender = active_agent.name"""
ASYNC_FINISH_NEW = """            message: Message = completion_response.choices[0].message
            message.sender = active_agent.name
            _lg_finish = getattr(completion_response.choices[0], "finish_reason", None)"""

WHILE_OLD = """        while len(history) - init_len < max_turns and active_agent:"""
WHILE_NEW = """        if max_turns == float("inf") and _lg_os.getenv("AI_RESEARCHER_MAX_TURNS"):
            try:
                max_turns = float(_lg_os.getenv("AI_RESEARCHER_MAX_TURNS"))
            except ValueError:
                pass
        _lg_last_sig = None
        _lg_rep = 0
        _lg_empty_run = 0
        _lg_finish = None
        while len(history) - init_len < max_turns and active_agent:"""

APPEND_OLD = """            history.append(
                json.loads(message.model_dump_json())
            )  # to avoid OpenAI types (?)"""
APPEND_NEW = """            # loop-guard: an empty completion (no content, no tool calls) is
            # never useful history. Retry a bounded number of times without
            # polluting the transcript; persistent emptiness ends the session.
            _lg_is_empty = (not message.tool_calls) and not (message.content or "").strip()
            if _lg_is_empty:
                _lg_empty_run += 1
                if _lg_empty_run <= _LG_EMPTY_RETRY:
                    if _lg_finish == "length":
                        # truncated giant output: a blind retry regenerates the
                        # same giant and burns the same tokens -- inform the
                        # retry instead (mirrors the TDC/topic2 budget clause
                        # against pasting long content into the conversation).
                        history.append({"role": "user", "content": "[controller] Your previous response exceeded the provider's output limit and was discarded -- nothing was received. Re-issue it in a much shorter form; long code or content can be written into files instead of into the message."})
                        self.logger.info("loop-guard: length-truncated empty; guided retry (" + str(_lg_empty_run) + "/" + str(_LG_EMPTY_RETRY) + ")", title="Loop Guard", color="yellow")
                        continue
                    self.logger.info("loop-guard: empty completion; retrying (" + str(_lg_empty_run) + "/" + str(_LG_EMPTY_RETRY) + ")", title="Loop Guard", color="yellow")
                    continue
                if _lg_empty_run >= _LG_EMPTY_LIMIT:
                    self.logger.info("loop-guard: ending session after " + str(_lg_empty_run) + " consecutive empty completions", title="Loop Guard", color="red")
                    history.append({"role": "assistant", "content": "[loop-guard] Session ended after repeated empty completions.", "sender": active_agent.name})
                    break
            else:
                _lg_empty_run = 0
            history.append(
                json.loads(message.model_dump_json())
            )  # to avoid OpenAI types (?)"""

NAG_OLD = "Please use the tools provided to complete the task."
NAG_NEW = ("[controller] Your previous reply took no action. If this phase's work is "
           "already complete, call case_resolved now with your final result. If you are "
           "genuinely blocked, call case_not_resolved with the concrete reason. Otherwise "
           "take the next concrete action with a tool call -- do not reply with empty or "
           "action-free messages.")

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
            elif _lg_sig is not None:
                # v3: an action-free turn (sig None) leaves the streak intact
                # instead of resetting it -- empties are transparent here.
                _lg_last_sig = _lg_sig
                _lg_rep = 1
            if (
                _lg_rep >= 3
                and history
                and isinstance(history[-1], dict)
                and history[-1].get("role") == "tool"
                and isinstance(history[-1].get("content"), str)
            ):
                if _lg_rep > _LG_LIMIT:
                    # grace turn expired: the model saw the final notice and
                    # still repeated the same call -- end the session now.
                    self.logger.info("loop-guard: ending session after " + str(_lg_rep) + " identical calls", title="Loop Guard", color="red")
                    break
                if _lg_rep == _LG_LIMIT:
                    # final notice + ONE grace turn, so the model can write its
                    # summary and the phase result is model text, not a raw
                    # tool result. One more identical call -> hard stop above.
                    history[-1]["content"] += (
                        "\\n\\n[loop-guard] You have now made " + str(_lg_rep)
                        + " consecutive identical tool calls. This session is about to be ended:"
                        + " do NOT call any more tools -- respond now with your best final answer"
                        + " (your summary, findings, or result) from the information you already have."
                    )
                    self.logger.info("loop-guard: final notice at " + str(_lg_rep) + " identical calls (grace turn)", title="Loop Guard", color="yellow")
                    continue
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
    if "_lg_finish" in text:
        print("[loop-guard] already applied (v4)")
        return
    if "_LG_LIMIT" in text:
        raise SystemExit("loop-guard: an older guard version is present; refusing mixed application")
    for label, old, expected in (
        ("while", WHILE_OLD, 2),
        ("append", APPEND_OLD, 2),
        ("extend", EXTEND_OLD, 2),
    ):
        n = text.count(old)
        if n != expected:
            raise SystemExit(f"loop-guard: anchor '{label}' found {n} times, expected {expected}")
    if IMPORT_ANCHOR not in text:
        raise SystemExit("loop-guard: import anchor not found")
    if NAG_OLD not in text:
        raise SystemExit("loop-guard: nag anchor not found")
    for label, o in (("sync-finish", SYNC_FINISH_OLD), ("async-finish", ASYNC_FINISH_OLD)):
        if text.count(o) != 1:
            raise SystemExit(f"loop-guard: anchor '{label}' count != 1")
    text = text.replace(SYNC_FINISH_OLD, SYNC_FINISH_NEW, 1)
    text = text.replace(ASYNC_FINISH_OLD, ASYNC_FINISH_NEW, 1)
    text = text.replace(IMPORT_ANCHOR, IMPORT_ADD, 1)
    text = text.replace(WHILE_OLD, WHILE_NEW)
    text = text.replace(APPEND_OLD, APPEND_NEW)
    text = text.replace(EXTEND_OLD, EXTEND_NEW)
    text = text.replace(NAG_OLD, NAG_NEW)
    CORE.write_text(text, encoding="utf-8")
    print("[loop-guard] applied v4: repetition brake + turn cap + empty retry/stop (length-aware guided retry) + directive nag")


if __name__ == "__main__":
    main()
