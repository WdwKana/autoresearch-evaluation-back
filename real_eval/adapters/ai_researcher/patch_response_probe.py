#!/usr/bin/env python3
"""Response-side observation probe: log what each completion actually returned.

The request-side probe records what we SEND; billing showed churn-phase empty
assistant turns were billed 51-500+ completion tokens each, meaning the model
produced tokens (likely reasoning) that never became content or a tool call --
and litellm's message serialisation carries no reasoning_content field into
history. Attribution between provider/adapter failure and model policy is
impossible without seeing the raw response. This probe logs, per completion:

    ts, agent, finish_reason, completion_tokens, prompt_tokens,
    content_len, reasoning_len (reasoning_content attr if present),
    n_tool_calls, has_provider_fields

Observation only: no behavior change, exceptions swallowed. Enabled when
AI_RESEARCHER_RESPONSE_PROBE_LOG is set (the wrapper sets it). Instruments
both the sync and async loops (variable names differ: completion vs
completion_response). Idempotent; loud on anchor drift. Run from the
AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

CORE = Path("research_agent/inno/core.py")

HELPER_ANCHOR = "import copy"
HELPER = '''import copy

def _rp_log_response(resp, agent_name):
    """Response-probe: append one JSON line describing this completion."""
    try:
        import json as _j, os as _o, time as _t
        path = _o.getenv("AI_RESEARCHER_RESPONSE_PROBE_LOG")
        if not path:
            return
        ch = resp.choices[0]
        msg = ch.message
        usage = getattr(resp, "usage", None)
        rec = {
            "ts": _t.strftime("%H:%M:%S"),
            "agent": agent_name,
            "finish_reason": getattr(ch, "finish_reason", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "content_len": len(msg.content or ""),
            "reasoning_len": len(getattr(msg, "reasoning_content", None) or ""),
            "n_tool_calls": len(msg.tool_calls or []),
            "has_provider_fields": bool(getattr(msg, "provider_specific_fields", None)),
        }
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(_j.dumps(rec, ensure_ascii=False) + "\\n")
    except Exception:
        pass
'''

SYNC_OLD = '''            message: Message = completion.choices[0].message
            message.sender = active_agent.name'''
SYNC_NEW = '''            message: Message = completion.choices[0].message
            message.sender = active_agent.name
            _rp_log_response(completion, active_agent.name)'''

ASYNC_OLD = '''            message: Message = completion_response.choices[0].message
            message.sender = active_agent.name'''
ASYNC_NEW = '''            message: Message = completion_response.choices[0].message
            message.sender = active_agent.name
            _rp_log_response(completion_response, active_agent.name)'''


def main() -> None:
    if not CORE.is_file():
        raise SystemExit("response-probe: run from the AI-Researcher source root")
    text = CORE.read_text(encoding="utf-8")
    if "_rp_log_response" in text:
        print("[response-probe] already applied")
        return
    for label, old in (("sync", SYNC_OLD), ("async", ASYNC_OLD)):
        if text.count(old) != 1:
            raise SystemExit(f"response-probe: {label} anchor count != 1")
    if HELPER_ANCHOR not in text:
        raise SystemExit("response-probe: import anchor not found")
    text = text.replace(HELPER_ANCHOR, HELPER, 1)
    text = text.replace(SYNC_OLD, SYNC_NEW, 1)
    text = text.replace(ASYNC_OLD, ASYNC_NEW, 1)
    CORE.write_text(text, encoding="utf-8")
    print("[response-probe] installed on both loops (observation only)")


if __name__ == "__main__":
    main()
