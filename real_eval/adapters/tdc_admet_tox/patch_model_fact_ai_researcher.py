#!/usr/bin/env python3
"""Run-local input-fact injection for 01 x TDC-ADMET-Tox (the former [tdc01-model-fact] inline block).

WHY (2026-09-28, user-approved topic-wide rollout)
    The TDC inputs tell the agent the trace fields come "from OPENAI_MODEL/OPENAI_BASE_URL";
    append the actual injected literals so the agent cannot substitute a hallucinated public URL.

Runs inside the framework container (cwd /workspace) before the native entrypoint; idempotent.
"""
import os
from pathlib import Path

MARK = "tdc01-model-fact"
model = os.environ.get("OPENAI_MODEL", "")
base = os.environ.get("OPENAI_BASE_URL", "")
FACT = (
    f"\n<!-- {MARK}: injected-provider literals appended by the 01 wrapper -->\n"
    f"Injected provider facts for this run: `framework_internal_model` must be exactly "
    f"\"{model}\" and `framework_internal_api_base_url` must be exactly \"{base}\". Copy "
    f"these two literals verbatim into experiment_trace.json; do not guess or substitute "
    f"other values such as public provider URLs.\n"
)
if model and base:
    hits = 0
    for f in Path("/workspace").rglob("*.md"):
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        if MARK in text:
            hits += 1
            print(f"[{MARK}] already present: {f}")
            continue
        if "framework_internal_model" in text or "internal API model" in text:
            f.write_text(text + FACT, encoding="utf-8")
            hits += 1
            print(f"[{MARK}] appended: {f}")
    print(f"[{MARK}] {hits} run-local input file(s) carry the injected literals")
else:
    print(f"[{MARK}] OPENAI_MODEL/OPENAI_BASE_URL not set; nothing done")
