#!/usr/bin/env python3
"""Bounce malformed tool-call arguments back to the model instead of dying.

WHY (2026-09-07)
    kimi emits large tool-call arguments that occasionally contain a JSON
    syntax error (observed: char 5645 in run 120826, char 2721 in run 143805
    -- both multi-KB argument strings). core.py parses them at
    `args = json.loads(tool_call.function.arguments)` which sits in an
    unprotected gap: the missing-tool guard is above it, the try/except
    around tool EXECUTION is below it. A JSONDecodeError there bubbles to the
    run loop's outer handler (history gets role:"error") and flowcache then
    raises, killing the ENTIRE run. Two full runs died this way -- one bad
    argument string should cost one retry, not the experiment.

FIX (framework-native pattern, mirrored from the adjacent handler)
    Wrap the parse; on failure append the same style of "[Tool Call Error]"
    tool message the missing-tool case uses -- naming the tool, quoting the
    parse error, telling the model nothing was executed and to re-issue the
    call with valid JSON (long content belongs in files, in smaller pieces)
    -- and `continue`. The model retries; loop-guard/turn caps bound the
    retries. No behavior change for well-formed arguments.

Anchor is the single parse line (grep-verified unique; the other json.loads
in core.py are model_dump round-trips). Idempotent; loud on drift. Run from
the AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

CORE = Path("research_agent/inno/core.py")
MARK = "tool-args-resilience"

OLD = """            args = json.loads(tool_call.function.arguments)
"""
NEW = """            # tool-args-resilience: a malformed arguments string must cost
            # one retry, not the whole run (it previously escaped to the run
            # loop, became role:error, and flowcache raised).
            try:
                args = json.loads(tool_call.function.arguments)
            except Exception as _tar_e:
                self.logger.info(f"[Tool Call Error] Invalid JSON arguments for {name}: {_tar_e}", title="Tool Call Error", color="red")
                partial_response.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": name,
                        "content": f"[Tool Call Error] The arguments for `{name}` were not valid JSON ({_tar_e}). Nothing was executed. Re-issue the tool call with valid JSON arguments -- keep string values properly escaped, and put long content into a file in smaller pieces instead of one giant argument.",
                    }
                )
                continue
"""


def main() -> None:
    text = CORE.read_text(encoding="utf-8")
    if MARK in text:
        print(f"[{MARK}] already applied")
        return
    n = text.count(OLD)
    if n == 0:
        raise SystemExit(f"[{MARK}] anchor not found (arguments parse line)")
    text = text.replace(OLD, NEW)
    CORE.write_text(text, encoding="utf-8")
    print(f"[{MARK}] applied at {n} site(s): malformed tool args now bounce to the model instead of killing the run")


if __name__ == "__main__":
    main()
