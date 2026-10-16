#!/usr/bin/env python3
"""Run-local input-fact injection for 01 x ARC (the former [arc01-model-fact] inline block).

WHY (2026-09-28)
    The trace gate requires framework_internal_model / framework_internal_api_base_url to equal
    the injected values byte-for-byte, but the brief never stated the literals; kimi hallucinated
    "gpt-4" (fullrun_arc_01_kimi_20260927_131103). Append the literals, read from THIS container's
    env, to every run-local copy of ARC_WBE_2026_BRIEF.md. Facts only; no method content.

Runs inside the framework container (cwd /workspace) before the native entrypoint; idempotent.

NOTE (2026-10-16, found while extracting): until this extraction the body lived in the wrapper's
UNQUOTED `RUNTIME_COMMAND=$(cat <<EOF ...)` heredoc, where bash command-substituted the
`OPENAI_BASE_URL` backticks on the second anchor at host time (stderr: "OPENAI_BASE_URL: command
not found") and the container received "   environment variable" as the anchor. Every deployed
01 x ARC run (9 retained logs) therefore appended ONE literal (the model); the base-URL literal
was never appended. As a standalone file the text below runs as written: both literals.
"""
import os
from pathlib import Path

MARK = "arc01-model-fact"
model = os.environ.get("OPENAI_MODEL", "")
base = os.environ.get("OPENAI_BASE_URL", "")
pairs = [
    ("  \"not_called\")", f'  "not_called"); in this run that value is exactly "{model}"'),
    ("  `OPENAI_BASE_URL` environment variable", f'  `OPENAI_BASE_URL` environment variable; in this run that value is exactly "{base}"'),
]
if model and base:
    for f in Path("/workspace").rglob("ARC_WBE_2026_BRIEF.md"):
        text = f.read_text(encoding="utf-8")
        if MARK in text or "in this run that value is exactly" in text:
            print(f"[{MARK}] already present: {f}")
            continue
        n = 0
        for old, new in pairs:
            if text.count(old) == 1:
                text = text.replace(old, new, 1)
                n += 1
        if n:
            text += f"\n<!-- {MARK}: injected-model literals appended by the 01 wrapper -->\n"
            f.write_text(text, encoding="utf-8")
            print(f"[{MARK}] {n} literal(s) appended: {f}")
        else:
            print(f"[{MARK}] anchors not found in {f}; brief left untouched")
else:
    print(f"[{MARK}] OPENAI_MODEL/OPENAI_BASE_URL not set; nothing done")
