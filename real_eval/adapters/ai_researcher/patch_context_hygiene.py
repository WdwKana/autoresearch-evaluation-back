#!/usr/bin/env python3
"""AI-Researcher context hygiene: bound tool results before they enter history.

WHY
    AI-Researcher's research loop appends every tool result verbatim to a
    transcript that is resent in full on every subsequent call, with no
    trimming, summarisation, or budget check. Measured on the 2026-09-01 ARC
    runs: tool-result blocks are median 644 characters but long-tailed to
    350,716 (~87k tokens for a single open_local_file), and the prompt grew
    monotonically from 100k to 474k tokens within ten minutes, with none of the
    sawtooth that any reclamation mechanism would produce.

    Consequences measured the same day:
      - kimi-k2.6 (256k window) died in the idea stage: the provider returned
        "Range of input length should be [1, 262144]", which the framework's own
        recovery path (try_completion_with_truncation) does not recognise --
        it string-matches only "context length"/"context_length_exceeded" -- so
        it re-raises and the whole run ends.
      - deepseek-v4-flash (larger window) absorbed 119 calls above 256k, peaking
        at 531k, costing $12.30 for a single run against $5.19 for four luna
        runs, and still delivered nothing.
      - gpt-5.6-luna happened to stay under 256k and silently masked the defect.

DESIGN INTENT
    This is not a mechanism invented by the evaluation harness. The framework
    already declares its own position on message size: core.py defines
    truncate_message() with max_length = 10000 tokens. That function is merely
    wired defensively -- invoked only after a provider error, and only on the
    last message, which cannot help when the pressure comes from accumulated
    history. This adapter changes WHEN the framework's own rule applies, not
    WHAT the rule is:

      1. Bound each tool result at ingestion, on the framework's own 10k budget,
         and mark every truncation visibly so the agent knows material was
         elided and can re-read a specific region or filter it with a command.
      2. Widen the framework's error recogniser so provider phrasings other than
         OpenAI's also reach the recovery path instead of killing the run.

    Nothing else is touched. The agent still chooses what to read, what to run,
    and what to conclude; only the volume of verbatim tool output retained in
    the transcript is bounded, exactly as the framework itself prescribes.

SCOPE / REPRODUCIBILITY
    Applied to the per-run source copy by 01 wrappers. Runs made with hygiene
    enabled are not directly comparable to earlier ones, because the agent sees
    a different (bounded) transcript: any model-comparison matrix must state
    whether hygiene was on.
"""
from __future__ import annotations

from pathlib import Path

CORE = Path("research_agent/inno/core.py")

OLD_APPEND = '''            partial_response.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": name,
                    "content": result.value,
                }
            )'''

NEW_APPEND = '''            _bounded_value = result.value
            if isinstance(_bounded_value, str):
                _full_tokens = encode_string_by_tiktoken(_bounded_value)
                if len(_full_tokens) > TOOL_RESULT_TOKEN_BUDGET:
                    _kept = decode_tokens_by_tiktoken(_full_tokens[:TOOL_RESULT_TOKEN_BUDGET])
                    _bounded_value = (
                        _kept
                        + "\\n\\n[context-hygiene] This tool result was truncated to "
                        + str(TOOL_RESULT_TOKEN_BUDGET)
                        + " tokens of "
                        + str(len(_full_tokens))
                        + ". The omitted remainder is still on disk: re-read the specific "
                        + "file region, or filter/aggregate it with a command, rather than "
                        + "requesting the whole artifact again."
                    )
            partial_response.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": name,
                    "content": _bounded_value,
                }
            )'''

OLD_MATCH = '''            if "context length" in error_msg.lower() or "context_length_exceeded" in error_msg:'''

NEW_MATCH = '''            _lowered = error_msg.lower()
            if any(
                marker in _lowered
                for marker in (
                    "context length",
                    "context_length_exceeded",
                    "range of input length",
                    "input length",
                    "too many tokens",
                    "maximum context",
                )
            ):'''

BUDGET_DECL = '''
# The framework's own declared per-message budget (see truncate_message below),
# applied at ingestion rather than only after a provider error.
TOOL_RESULT_TOKEN_BUDGET = 10000
'''


def main() -> None:
    if not CORE.is_file():
        raise SystemExit("run from the AI-Researcher source root: research_agent/inno/core.py not found")
    text = CORE.read_text(encoding="utf-8")

    if "TOOL_RESULT_TOKEN_BUDGET" in text:
        print("[context-hygiene] already applied")
        return

    anchor = '__CTX_VARS_NAME__ = "context_variables"'
    if anchor not in text:
        raise SystemExit("context-hygiene: budget declaration anchor not found in core.py")
    text = text.replace(anchor, anchor + "\n" + BUDGET_DECL, 1)

    if OLD_APPEND not in text:
        raise SystemExit("context-hygiene: tool-result append anchor not found in core.py")
    text = text.replace(OLD_APPEND, NEW_APPEND, 1)

    if OLD_MATCH not in text:
        raise SystemExit("context-hygiene: context-error matcher anchor not found in core.py")
    text = text.replace(OLD_MATCH, NEW_MATCH, 1)

    CORE.write_text(text, encoding="utf-8")
    print("[context-hygiene] tool results bounded at 10000 tokens; error matcher widened")


if __name__ == "__main__":
    main()
