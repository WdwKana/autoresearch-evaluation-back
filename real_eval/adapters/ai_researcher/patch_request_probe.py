#!/usr/bin/env python3
"""AI-Researcher request probe: record what each outgoing prompt is made of.

PURPOSE
    Aggregate provider billing shows deepseek-v4-flash issuing 124 requests
    above 250k tokens on ARC (P90 464k, max 531k, 87% of run cost) while
    gpt-5.6-luna on the same wrapper and task peaks at 256k with a P90 of 160k.
    Four hypotheses were eliminated by inverse reasoning from billing data
    alone -- tool output (only one result above 10k), open_local_file (it
    paginates at 4096 chars), the in-context example block (1.5k), and the
    five-idea selection block (luna's is 38k, larger than DS's 18k, yet luna
    never produced a 400k request). What builds those requests is therefore
    still unknown, and billing aggregates cannot answer it.

    This probe replaces inverse reasoning with direct measurement: for every
    outgoing request it records a per-message breakdown -- role, token count,
    a content hash, and a short preview -- plus which agent issued it. That is
    enough to distinguish the three candidate causes, which need different
    fixes and must not be conflated:

        A. one artifact carried verbatim across stages  -> artifact handoff
        B. intra-agent history growth                   -> history compaction
        C. a single oversized tool observation          -> tool-output bounds

OBSERVATION ONLY
    Nothing the model receives changes: the probe reads the assembled message
    list and writes a JSONL line beside the run. It cannot alter, truncate, or
    reorder anything. Failure inside the probe is swallowed so instrumentation
    can never break a run.

    Content is not stored verbatim. Each message contributes a token count, a
    sha256 prefix (so a block repeated across requests is recognisable), and a
    200-character preview for identification.

OUTPUT
    $AI_RESEARCHER_PROBE_LOG (default /workspace/request_probe.jsonl), one
    object per request:
        {ts, seq, agent, model, total_tokens, n_messages,
         by_role: {system: n, user: n, assistant: n, tool: n},
         messages: [{i, role, tokens, sha, preview}]}
"""
from __future__ import annotations

from pathlib import Path

CORE = Path("research_agent/inno/core.py")

PROBE_SRC = '''
# ---- request probe (observation only; see patch_request_probe.py) ----
import hashlib as _probe_hashlib
import json as _probe_json
import os as _probe_os
import time as _probe_time

_PROBE_LOG = _probe_os.getenv("AI_RESEARCHER_PROBE_LOG", "/workspace/request_probe.jsonl")
_PROBE_SEQ = [0]


def _probe_record(messages, agent_name, model_name):
    """Write a per-message size breakdown for one outgoing request."""
    try:
        _PROBE_SEQ[0] += 1
        rows = []
        by_role = {}
        total = 0
        for i, m in enumerate(messages):
            content = m.get("content")
            if isinstance(content, list):
                content = " ".join(
                    part.get("text", "") for part in content if isinstance(part, dict)
                )
            text = content if isinstance(content, str) else ("" if content is None else str(content))
            # tool_calls carry payload too and must be counted
            if m.get("tool_calls"):
                text += _probe_json.dumps(m["tool_calls"], default=str)
            try:
                n = len(encode_string_by_tiktoken(text))
            except Exception:
                n = len(text) // 4
            role = m.get("role", "?")
            by_role[role] = by_role.get(role, 0) + n
            total += n
            rows.append({
                "i": i,
                "role": role,
                "name": m.get("name"),
                "tokens": n,
                "sha": _probe_hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:12],
                "preview": text[:200].replace("\\n", " "),
            })
        with open(_PROBE_LOG, "a", encoding="utf-8") as fh:
            fh.write(_probe_json.dumps({
                "ts": _probe_time.strftime("%H:%M:%S"),
                "seq": _PROBE_SEQ[0],
                "agent": agent_name,
                "model": model_name,
                "total_tokens": total,
                "n_messages": len(messages),
                "by_role": by_role,
                "messages": rows,
            }, ensure_ascii=False) + "\\n")
    except Exception:
        pass  # instrumentation must never break a run
# ---- end request probe ----
'''

ANCHOR_DECL = '__CTX_VARS_NAME__ = "context_variables"'

OLD_CALL = '''        messages = [{"role": "system", "content": instructions}] + history'''

NEW_CALL = '''        messages = [{"role": "system", "content": instructions}] + history
        _probe_record(messages, getattr(agent, "name", "?"), model_override or getattr(agent, "model", "?"))'''


def main() -> None:
    if not CORE.is_file():
        raise SystemExit("run from the AI-Researcher source root: research_agent/inno/core.py not found")
    text = CORE.read_text(encoding="utf-8")
    if "_probe_record" in text:
        print("[request-probe] already applied")
        return
    if ANCHOR_DECL not in text:
        raise SystemExit("request-probe: declaration anchor not found in core.py")
    text = text.replace(ANCHOR_DECL, ANCHOR_DECL + "\n" + PROBE_SRC, 1)
    if OLD_CALL not in text:
        raise SystemExit("request-probe: message assembly anchor not found in core.py")
    text = text.replace(OLD_CALL, NEW_CALL, 1)
    CORE.write_text(text, encoding="utf-8")
    print("[request-probe] instrumentation installed (observation only)")


if __name__ == "__main__":
    main()
