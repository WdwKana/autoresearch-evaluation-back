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
        if "reasoning_effort" in message and retry.get("reasoning_effort") != "none":
            # Some routes of an OpenAI-compatible provider reject function tools
            # together with a (default) reasoning effort on /v1/chat/completions
            # and ask for reasoning_effort='none' instead (observed 2026-09-21,
            # gpt-5.6-luna, error type rix_api_error, param reasoning_effort).
            retry["reasoning_effort"] = "none"
            changed = True
        if not changed:
            raise
        return client.chat.completions.create(**retry)
'''




INTERPRETER = Path("ai_scientist/treesearch/interpreter.py")

INTERPRETER_OLD = """        # don't wait for gc, clean up immediately
        self.process.close()"""

INTERPRETER_NEW = """        # don't wait for gc, clean up immediately
        try:
            self.process.close()
        except ValueError:
            # kill() + join(timeout=2) above can race a child that has not
            # exited yet; close() then raises and takes the whole worker down
            # mid-run. Escalate and, failing that, abandon the handle.
            self.process.terminate()
            self.process.join(timeout=5)
            try:
                self.process.close()
            except ValueError:
                logger.warning("Child process still running after kill; abandoning handle")"""


def patch_interpreter() -> None:
    if not INTERPRETER.is_file():
        return
    text = INTERPRETER.read_text(encoding="utf-8")
    if "abandoning handle" in text:
        return
    if INTERPRETER_OLD not in text:
        print("SKIP: interpreter cleanup anchor not found")
        return
    INTERPRETER.write_text(text.replace(INTERPRETER_OLD, INTERPRETER_NEW, 1), encoding="utf-8")


BACKEND_OPENAI = Path("ai_scientist/treesearch/backend/backend_openai.py")
BACKEND_OLD = """    completion = backoff_create(
        client.chat.completions.create,
        OPENAI_TIMEOUT_EXCEPTIONS,"""
BACKEND_NEW = """    completion = backoff_create(
        lambda **_kw: chat_create(client, **_kw),  # transport shim (parameter fallbacks)
        OPENAI_TIMEOUT_EXCEPTIONS,"""


def patch_backend_openai() -> None:
    """Route the tree-search OpenAI backend through the shim too. The wrappers'
    textual rewrite only catches ``client.chat.completions.create(`` call sites;
    this backend passes the bound method to backoff_create, so a provider
    parameter rejection there (raised inside a worker process) escaped every
    fallback and, being unpicklable, broke the whole process pool."""
    if not BACKEND_OPENAI.is_file():
        return
    text = BACKEND_OPENAI.read_text(encoding="utf-8")
    if "chat_create(client, **_kw)" in text:
        return
    if BACKEND_OLD not in text:
        print("SKIP: backend_openai backoff_create anchor not found")
        return
    if "from ai_scientist.gpt_responses_compat import chat_create" not in text:
        text = "from ai_scientist.gpt_responses_compat import chat_create\n" + text
    BACKEND_OPENAI.write_text(text.replace(BACKEND_OLD, BACKEND_NEW, 1), encoding="utf-8")


def main() -> None:
    if not Path("ai_scientist").is_dir():
        raise SystemExit("run from the AI-Scientist-v2 source root: ai_scientist/ not found")
    patch_interpreter()
    patch_backend_openai()
    existing = COMPAT_MODULE.read_text(encoding="utf-8") if COMPAT_MODULE.is_file() else ""
    if existing != COMPAT_SOURCE:
        COMPAT_MODULE.write_text(COMPAT_SOURCE, encoding="utf-8")
    print("gpt_responses_compat ready")


if __name__ == "__main__":
    main()
