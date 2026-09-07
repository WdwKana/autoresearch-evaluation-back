#!/usr/bin/env python3
"""Wire tap (observation only): record RAW chat-completion response bytes.

WHY (2026-09-07)
    Placeholder/empty tool-call arguments (write_file content="{...}",
    case_resolved({}), handoff('')) are certain at the RECEIVING side (they sit
    verbatim in the framework's own history archives) but unproven at the WIRE:
    the original moments were never captured raw, and a 30-trial three-arm
    replay (direct+raw / litellm 1.55.0 / verbatim-history litellm) could not
    reproduce them -- the event is rare and transient. The only way to
    adjudicate model/gateway vs client stack is to capture the raw bytes at
    the moment it recurs in a real run.

HOW
    httpx transport-layer hook: litellm 1.55.0 routes openai-compatible calls
    through the openai SDK, which uses httpx (Client for sync completion,
    AsyncClient for acompletion). Wrapping both send() methods catches every
    /chat/completions response regardless of litellm internals. For each one,
    a JSONL row records ts, status, finish_reasons, usage, every tool_call's
    raw arguments string, and the raw body (capped). Non-JSON (streaming)
    responses are skipped untouched. Every tap operation is wrapped in
    try/except: the tap can never alter or break the request path.

    Gated by AI_RESEARCHER_WIRE_TAP_LOG (unset = fully inert). Body cap via
    AI_RESEARCHER_WIRE_TAP_CAP (default 300000 bytes).

Idempotent; loud on anchor drift. Run from the AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

CORE = Path("research_agent/inno/core.py")
MARK = "wire-tap"

ANCHOR = "from litellm import completion, acompletion"
ADD = '''from litellm import completion, acompletion
# wire-tap (observation only): raw response capture for empty-arg forensics
import os as _wt_os, json as _wt_json, time as _wt_time
_WT_LOG = _wt_os.getenv("AI_RESEARCHER_WIRE_TAP_LOG", "")
if _WT_LOG:
    import httpx as _wt_httpx
    _WT_CAP = int(_wt_os.getenv("AI_RESEARCHER_WIRE_TAP_CAP", "300000"))

    def _wt_record(kind, url, status, content_type, body):
        try:
            fin = usage = None
            args = []
            try:
                j = _wt_json.loads(body)
                fin = [c.get("finish_reason") for c in j.get("choices", [])]
                usage = j.get("usage")
                for c in j.get("choices", []):
                    for tc in (c.get("message", {}).get("tool_calls") or []):
                        args.append({"name": tc.get("function", {}).get("name"),
                                     "arguments": tc.get("function", {}).get("arguments")})
            except Exception:
                pass
            with open(_WT_LOG, "a", encoding="utf-8") as f:
                f.write(_wt_json.dumps({
                    "ts": _wt_time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "kind": kind, "status": status, "url": str(url),
                    "content_type": content_type, "finish": fin, "usage": usage,
                    "tool_call_args": args, "body_len": len(body),
                    "body": body[:_WT_CAP],
                }, ensure_ascii=False) + "\\n")
        except Exception:
            pass

    _wt_send = _wt_httpx.Client.send

    def _wt_send_tap(self, request, **kw):
        resp = _wt_send(self, request, **kw)
        try:
            ct = resp.headers.get("content-type", "")
            if "/chat/completions" in str(request.url) and "json" in ct:
                resp.read()
                _wt_record("sync", request.url, resp.status_code, ct, resp.text)
        except Exception:
            pass
        return resp

    _wt_httpx.Client.send = _wt_send_tap
    _wt_asend = _wt_httpx.AsyncClient.send

    async def _wt_asend_tap(self, request, **kw):
        resp = await _wt_asend(self, request, **kw)
        try:
            ct = resp.headers.get("content-type", "")
            if "/chat/completions" in str(request.url) and "json" in ct:
                await resp.aread()
                _wt_record("async", request.url, resp.status_code, ct, resp.text)
        except Exception:
            pass
        return resp

    _wt_httpx.AsyncClient.send = _wt_asend_tap'''


def main() -> None:
    text = CORE.read_text(encoding="utf-8")
    if MARK in text:
        print(f"[{MARK}] already applied")
        return
    if ANCHOR not in text:
        raise SystemExit(f"[{MARK}] anchor not found: {ANCHOR!r}")
    CORE.write_text(text.replace(ANCHOR, ADD, 1), encoding="utf-8")
    print(f"[{MARK}] applied: raw /chat/completions capture on httpx sync+async (gated by AI_RESEARCHER_WIRE_TAP_LOG)")


if __name__ == "__main__":
    main()
