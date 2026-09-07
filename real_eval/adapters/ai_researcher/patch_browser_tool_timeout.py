#!/usr/bin/env python3
"""Bounded execution for the heavy browser tools (leaf-I/O timeout).

WHY (2026-09-07)
    question_answer_on_whole_page hung twice in one day on TDC: the handler
    was entered and never returned (log shows the Tool Call with no Tool
    Execution line; zero TCP connections; likely a transient environment
    stall -- DNS/UDP was never excluded). One unbounded leaf call froze the
    whole pipeline for 30-50 minutes until the outer wall clock fired.

    Peer practice (surveyed 2026-09-07): AI-Scientist-v2 bounds per-step
    execution and tells the agent the limit; ARIS bounds nearly every leaf
    I/O call (fetches 15-60s, CLI bridges 600s). Bounding heavy browser
    tools is normal engineering, not harness overreach. The experiment
    command path (run_command) is deliberately NOT touched -- user decision:
    long experiments are legitimate, visibility only.

WHAT
    Three tools do heavy work and get a bound (default 240s, env
    AI_RESEARCHER_BROWSER_TOOL_TIMEOUT, <=0 disables):
      - question_answer_on_whole_page  (chunk-embed + chromadb + LLM call)
      - open_local_file                (document conversion via mdconvert)
      - visualizer                     (image encode + vision LLM call)
    Pure in-memory viewport ops (page_up/down, find_on_page, find_next)
    are left untouched.

    Mechanism: the original body moves to a _btt_*_impl function; the public
    name (same signature, same docstring -- register_tool builds the tool
    description from it) runs the impl in a daemon thread and joins with the
    bound. On expiry the agent gets an HONEST, actionable message ("usually a
    transient environment stall... retry once, or read the page directly with
    find_on_page_ctrl_f / page_down_markdown") instead of an infinite hang.
    A timed-out worker thread is leaked deliberately (daemon): killing it is
    impossible in Python, and the pipeline moving on is the whole point.
    Exceptions propagate unchanged; the 240s default is generous enough for
    first-time embedding of a large page plus one slow completion.

Idempotent; loud on anchor drift. Run from the AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

TOOLS = Path("research_agent/inno/tools/file_surfer_tool.py")
MARK = "browser-tool-timeout"

HELPER_ANCHOR = "def with_env(env: RequestsMarkdownBrowser):"
HELPER = '''# browser-tool-timeout: bounded execution for heavy browser tools
import os as _btt_os
import threading as _btt_threading
_BTT_T = int(_btt_os.getenv("AI_RESEARCHER_BROWSER_TOOL_TIMEOUT", "240") or 0)


def _btt_bounded(label, fn, hint):
    if _BTT_T <= 0:
        return fn()
    box = {}

    def _btt_run():
        try:
            box["r"] = fn()
        except BaseException as e:
            box["e"] = e

    t = _btt_threading.Thread(target=_btt_run, daemon=True)
    t.start()
    t.join(_BTT_T)
    if t.is_alive():
        return ("[browser-timeout] `" + label + "` did not return within " + str(_BTT_T)
                + "s -- usually a transient environment/network stall, not an error in "
                "your usage. The browser state is unchanged. " + hint)
    if "e" in box:
        raise box["e"]
    return box.get("r")


def with_env(env: RequestsMarkdownBrowser):'''

OPEN_OLD = '''@register_tool("open_local_file")
def open_local_file(env: RequestsMarkdownBrowser, path: str):
    """
    Open a local file at a path in the text-based browser and return current viewport content.

    Args:
        path: The absolute path of a local file to visit.
    """
'''
OPEN_NEW = '''@register_tool("open_local_file")
def open_local_file(env: RequestsMarkdownBrowser, path: str):
    """
    Open a local file at a path in the text-based browser and return current viewport content.

    Args:
        path: The absolute path of a local file to visit.
    """
    return _btt_bounded("open_local_file",
                        lambda: _btt_open_local_file_impl(env, path),
                        "Retry once, or continue without opening this file.")


def _btt_open_local_file_impl(env: RequestsMarkdownBrowser, path: str):
'''

VIS_OLD = '''@register_tool("visualizer")
def visualizer(env: RequestsMarkdownBrowser, image_path: str, question: Optional[str] = None) -> Result:
    """
    A tool that can answer questions about attached images.
    Args:
        image_path: The path to the image on which to answer the question. This should be a local path to downloaded image.
        question: the question to answer (default: "Please write a detailed caption for this image.")
    """
'''
VIS_NEW = '''@register_tool("visualizer")
def visualizer(env: RequestsMarkdownBrowser, image_path: str, question: Optional[str] = None) -> Result:
    """
    A tool that can answer questions about attached images.
    Args:
        image_path: The path to the image on which to answer the question. This should be a local path to downloaded image.
        question: the question to answer (default: "Please write a detailed caption for this image.")
    """
    _btt_r = _btt_bounded("visualizer",
                          lambda: _btt_visualizer_impl(env, image_path, question),
                          "Retry once, or proceed without the image description.")
    if isinstance(_btt_r, str):
        return Result(value=_btt_r)
    return _btt_r


def _btt_visualizer_impl(env: RequestsMarkdownBrowser, image_path: str, question: Optional[str] = None) -> Result:
'''

QA_OLD = '''def question_answer_on_whole_page(env: RequestsMarkdownBrowser, question: str) -> str:
    """
    Ask a question on the whole page and return the answer.
    """
'''
QA_NEW = '''def question_answer_on_whole_page(env: RequestsMarkdownBrowser, question: str) -> str:
    """
    Ask a question on the whole page and return the answer.
    """
    return _btt_bounded("question_answer_on_whole_page",
                        lambda: _btt_qa_impl(env, question),
                        "Retry once, or read the page directly with find_on_page_ctrl_f / page_down_markdown.")


def _btt_qa_impl(env: RequestsMarkdownBrowser, question: str) -> str:
'''


def main() -> None:
    text = TOOLS.read_text(encoding="utf-8")
    if MARK in text:
        print(f"[{MARK}] already applied")
        return
    for old, new, label in [
        (HELPER_ANCHOR, HELPER, "helper"),
        (OPEN_OLD, OPEN_NEW, "open_local_file"),
        (VIS_OLD, VIS_NEW, "visualizer"),
        (QA_OLD, QA_NEW, "question_answer_on_whole_page"),
    ]:
        if old not in text:
            raise SystemExit(f"[{MARK}] anchor not found ({label}): {old[:70]!r}")
        text = text.replace(old, new, 1)
    TOOLS.write_text(text, encoding="utf-8")
    print(f"[{MARK}] applied: bounded open_local_file/visualizer/question_answer (default 240s, AI_RESEARCHER_BROWSER_TOOL_TIMEOUT)")


if __name__ == "__main__":
    main()
