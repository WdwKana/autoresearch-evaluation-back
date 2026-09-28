#!/usr/bin/env python3
"""Provider compatibility: retry a rejected function-tool request with reasoning_effort='none'.

WHY (2026-09-24)
    Since the 2026-09-03 runs the gpt-5.6-luna relay started rejecting every
    /chat/completions request that carries function tools unless the request
    sets reasoning_effort='none' (HTTP 400, type rix_api_error, param
    reasoning_effort; 5/5 rejected without it, 5/5 accepted with it in a direct
    probe). AI-Researcher never sends reasoning_effort, so its very first
    tool-using agent (Paper Survey) dies in ideation -- run
    fullrun_mcar_01_luna_20260924_115332. The AI-Scientist-v2 side got the same
    fallback on 2026-09-21 (patch_ai_scientist_v2_common.py).

HOW
    Shadow `acompletion` in research_agent/inno/core.py with a wrapper that
    forwards unchanged and, only when the provider answers with that specific
    rejection, repeats the identical request once with reasoning_effort='none'.
    Requests the provider accepts are untouched, so model behaviour is
    unchanged for every other model/provider.

Idempotent; loud on anchor drift. Run from the AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

CORE = Path("research_agent/inno/core.py")
MARK = "reasoning-effort-fallback"

ANCHOR = "from litellm import completion, acompletion"
ADD = '''from litellm import completion, acompletion
# reasoning-effort-fallback: the relay rejects function tools unless reasoning_effort='none'
# (observed 2026-09-24, gpt-5.6-luna). Retry that one rejection only; never alter accepted requests.
_ref_acompletion = acompletion


async def acompletion(**kw):  # noqa: F811 -- deliberate shadow of litellm.acompletion
    # Protocol sanitize: tool_choice without tools is invalid in the OpenAI schema and the
    # relay's gpt-6-luna path rejects it (observed 2026-09-28, psydef run 045919).
    if not kw.get("tools") and "tool_choice" in kw:
        kw = dict(kw)
        kw.pop("tool_choice", None)
    try:
        return await _ref_acompletion(**kw)
    except Exception as exc:  # litellm.BadRequestError carries the provider text in str(exc)
        text = str(exc)
        if "reasoning_effort" in text and "not supported" in text and kw.get("reasoning_effort") != "none":
            print("[reasoning-effort-fallback] provider rejected function tools with reasoning_effort; "
                  "retrying the same request with reasoning_effort='none'", flush=True)
            kw = dict(kw, reasoning_effort="none")
            return await _ref_acompletion(**kw)
        if "tool_choice" in text and "only allowed" in text and "tool_choice" in kw:
            print("[reasoning-effort-fallback] provider rejected tool_choice without tools; "
                  "retrying the same request without tool_choice", flush=True)
            kw = dict(kw); kw.pop("tool_choice", None)
            return await _ref_acompletion(**kw)
        raise'''


def main() -> None:
    text = CORE.read_text(encoding="utf-8")
    if MARK in text:
        print(f"[{MARK}] already applied")
        return
    if ANCHOR not in text:
        raise SystemExit(f"[{MARK}] anchor not found: {ANCHOR!r}")
    CORE.write_text(text.replace(ANCHOR, ADD, 1), encoding="utf-8")
    print(f"[{MARK}] applied: acompletion retries once with reasoning_effort='none' on the provider's function-tool rejection")


if __name__ == "__main__":
    main()
