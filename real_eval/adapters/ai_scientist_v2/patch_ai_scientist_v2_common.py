#!/usr/bin/env python3
"""Shared AI-Scientist-v2 runtime adapter (reconstructed).

The public release of this repository omitted the original
``patch_ai_scientist_v2_common.py``. This file is a minimal faithful
reconstruction based on the contract visible in the topic wrappers
(``real_eval/scripts/02_ai_scientist_v2_*_fullrun.sh``), which require:

- an importable module ``ai_scientist/gpt_responses_compat.py`` providing
  ``chat_create(client, **kwargs)``; the wrappers rewrite every
  ``client.chat.completions.create(...)`` call site into
  ``chat_create(client, ...)``.

``chat_create`` is a transport-level compatibility shim only: it forwards to
the OpenAI-compatible chat completions endpoint and retries with
``max_completion_tokens`` when a provider rejects ``max_tokens`` (reasoning
model API differences). It contains no scientific or agent logic.

If the original private version of this file becomes available, diff and
replace this reconstruction.
"""
from __future__ import annotations

from pathlib import Path

COMPAT_MODULE = Path("ai_scientist/gpt_responses_compat.py")

COMPAT_SOURCE = '''"""Transport compatibility shim for OpenAI-compatible chat endpoints."""
from __future__ import annotations


def chat_create(client, **kwargs):
    """Forward to client.chat.completions.create with parameter fallbacks.

    Some OpenAI-compatible providers or reasoning models reject
    ``max_tokens`` (expecting ``max_completion_tokens``) or reject
    ``temperature``. Retry with adjusted parameters instead of failing the
    whole agent step.
    """
    try:
        return client.chat.completions.create(**kwargs)
    except Exception as exc:  # noqa: BLE001 - provider error classes vary
        message = str(exc)
        retry = dict(kwargs)
        changed = False
        if "max_tokens" in retry and (
            "max_completion_tokens" in message or "max_tokens" in message
        ):
            retry["max_completion_tokens"] = retry.pop("max_tokens")
            changed = True
        if "temperature" in retry and "temperature" in message:
            retry.pop("temperature")
            changed = True
        if not changed:
            raise
        return client.chat.completions.create(**retry)
'''


def main() -> None:
    if not Path("ai_scientist").is_dir():
        raise SystemExit("run from the AI-Scientist-v2 source root: ai_scientist/ not found")
    existing = COMPAT_MODULE.read_text(encoding="utf-8") if COMPAT_MODULE.is_file() else ""
    if existing != COMPAT_SOURCE:
        COMPAT_MODULE.write_text(COMPAT_SOURCE, encoding="utf-8")
    print("gpt_responses_compat ready")


if __name__ == "__main__":
    main()
