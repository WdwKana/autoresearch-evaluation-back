#!/usr/bin/env python3
"""Stop the paging storm: honest read_file errors + a single-page hint.

WHY (2026-09-07)
    kimi ARC 133748: read_file("estimator.py") on a file that did not exist
    yet triggered 160 paging calls stuck on "page 1 of 1". Mechanism (traced,
    code-verified):
      - read_file runs `cat {path}`; a missing file prints "cat: ... No such
        file" to the command output and run_command returns it as ordinary
        result (the `except FileNotFoundError` never fires -- the cat process
        exists, only its target is missing).
      - read_file carries @process_terminal_response, which wraps ANY result
        in a "Terminal viewport position: Showing page 1 of 1" shell -- so the
        error text looks like a normal, pageable terminal page.
      - The agent, seeing a paging shell, reasonably assumes content is
        further down and pages; every page is the same one-line error, and
        terminal_page_to(2) on a 1-page buffer silently returns page 1 again
        with no "only page" signal. It tried page_down / page_to(1) /
        page_to(2) -- distinct strategies to find content -- i.e. rational
        confusion driven by a misleading shell, not a blind loop.

FIX (two honest signals; no behavior shaping)
    1. read_file: detect the shell's "No such file / not found" and return a
       plain, un-pageable error string naming the file and saying it does not
       exist yet -- so the agent creates it rather than paging.
    2. _get_browser_state: when total_pages == 1, the header states it is the
       only page and paging further will not reveal more -- removing the false
       "there might be more" cue.

Anchors are pristine lines; loud on drift. Idempotent. Run from the
AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

TOOLS = Path("research_agent/inno/tools/terminal_tools.py")
MARK = "file-browser-paging"

# ---- fix 1: honest read_file error for a missing file ----
READ_OLD = '''    try:
        command = f"cat {file_path}"
        response = env.run_command(command) # status, result
        # res_output = truncate_by_tokens(env, response['result'], 10000)
        # return f"Exit code: {response['status']} \\nOutput: \\n{res_output}"
        return response
    except FileNotFoundError:
        return f"Error in reading file: {file_path}"'''
READ_NEW = '''    try:
        command = f"cat {file_path}"
        response = env.run_command(command) # status, result
        # file-browser-paging: a missing file makes `cat` print "No such file"
        # into the result; without this the error gets wrapped in a pageable
        # viewport shell and the agent pages a one-line error forever.
        try:
            _fbp_out = response.get("result", "") if isinstance(response, dict) else str(response)
        except Exception:
            _fbp_out = ""
        if isinstance(_fbp_out, str) and ("No such file" in _fbp_out or "cat: " in _fbp_out and "No such" in _fbp_out):
            return (f"[read_file error] The file does not exist yet: {file_path}. "
                    f"Nothing to read -- do NOT page; create the file first (write it), then read it if needed.")
        # res_output = truncate_by_tokens(env, response['result'], 10000)
        # return f"Exit code: {response['status']} \\nOutput: \\n{res_output}"
        return response
    except FileNotFoundError:
        return f"[read_file error] The file does not exist yet: {file_path}. Create it first before reading."'''

# ---- fix 2: single-page hint in the viewport header ----
HDR_OLD = '''    header += f"Terminal viewport position: Showing page {current_page+1} of {total_pages}.\\n"
    if total_pages > 1:'''
HDR_NEW = '''    header += f"Terminal viewport position: Showing page {current_page+1} of {total_pages}.\\n"
    if total_pages <= 1:
        header += "[NOTE] This is the only page; paging further (page_down/page_to) will not reveal more content.\\n"
    if total_pages > 1:'''


def main() -> None:
    text = TOOLS.read_text(encoding="utf-8")
    if MARK in text:
        print(f"[{MARK}] already applied")
        return
    for old, new, label in [(READ_OLD, READ_NEW, "read_file"), (HDR_OLD, HDR_NEW, "single-page header")]:
        if old not in text:
            raise SystemExit(f"[{MARK}] anchor not found: {label}")
        text = text.replace(old, new, 1)
    TOOLS.write_text(text, encoding="utf-8")
    print(f"[{MARK}] applied: honest read_file missing-file error + single-page paging hint")


if __name__ == "__main__":
    main()
