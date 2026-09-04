#!/usr/bin/env python3
"""Make time visible to the agent: budget clock + single-command cap.

WHY (2026-09-04)
    run_command (docker_env.py) is a bare socket loop with NO timeout of any
    kind: it blocks until the exec container's tcp_server sends the 'final'
    message. Observed: kimi's `python -m run_training_testing` consumed 19151%
    CPU for ~2h and the whole agent pipeline sat blocked behind it until the
    wall clock killed the run unfinalized. Separately, agents design
    experiments blind to how much wall time remains (luna's endless-refinement
    runs, kimi/DS exploring past the budget).

    Doctrine (user-set): time controls must be EXPLICIT, never an invisible
    guillotine. Three visible layers, one choke point:

      1. Single-command cap: the command is wrapped in `timeout {cap}s
         bash -c ...` so enforcement happens inside the exec container. On
         rc=124 the result is PREFIXED with an instructive notice (split long
         training into resumable stages, checkpoint), not silently killed.
      2. Live clock: every command result is PREFIXED (pagination-safe) with
         one line: `[clock] elapsed 42m / budget 180m, remaining ~138m`.
         Without a declared budget only elapsed is shown (babylm stays
         unbounded by prior decision).
      3. Upfront declaration: ml_dev_query is prefixed with the budget rules,
         generated at runtime from the SAME env vars the enforcement reads, so
         declaration and enforcement cannot drift.

ENV
    AI_RESEARCHER_TOTAL_BUDGET_SECONDS   whole-run wall budget (unset/0 = no cap shown)
    AI_RESEARCHER_COMMAND_TIMEOUT_SECONDS single-command cap (unset/0 = disabled)

Anchors are the pristine framework lines; loud SystemExit on drift. Idempotent.
Run from the AI-Researcher source root (research_agent/..). Applies to
docker_env.py (choke point) and run_infer_idea.py (declaration).
"""
from __future__ import annotations

from pathlib import Path

DOCKER_ENV = Path("research_agent/inno/environment/docker_env.py")
ENTRY = Path("research_agent/run_infer_idea.py")

MARK = "budget-clock"

# ---------------------------------------------------------------- docker_env
IMPORT_ANCHOR = "import socket"
IMPORT_ADD = """import socket
import time as _bc_time
import os as _bc_os
_BC_T0 = _bc_time.time()  # budget-clock: process start ~= run start


def _bc_clock_line() -> str:
    elapsed = int(_bc_time.time() - _BC_T0)
    total = int(_bc_os.getenv("AI_RESEARCHER_TOTAL_BUDGET_SECONDS", "0") or 0)
    e = f"{elapsed // 60}m"
    if total > 0:
        rem = max(0, total - elapsed)
        return f"[clock] elapsed {e} / budget {total // 60}m, remaining ~{rem // 60}m"
    return f"[clock] elapsed {e} (no total wall-clock cap declared)"


def _bc_wrap_command(command: str) -> str:
    cap = int(_bc_os.getenv("AI_RESEARCHER_COMMAND_TIMEOUT_SECONDS", "0") or 0)
    if cap <= 0:
        return command
    quoted = command.replace("'", "'\\"'\\"'")
    return f"timeout {cap}s bash -c '{quoted}'"


def _bc_timeout_notice(result: str) -> str:
    cap = int(_bc_os.getenv("AI_RESEARCHER_COMMAND_TIMEOUT_SECONDS", "0") or 0)
    return (
        f"[budget] This command hit the {cap // 60}-minute single-command cap and "
        "was terminated (exit 124). Split long work into resumable stages: save "
        "checkpoints, run shorter commands, and continue from the last checkpoint.\\n"
    )"""

SEND_OLD = """            s.sendall(command.encode())"""
SEND_NEW = """            s.sendall(_bc_wrap_command(command).encode())  # budget-clock"""

FINAL_OLD = """                            elif response['type'] == 'final':
                                # return the final result
                                return {
                                    'status': response['status'],
                                    'result': response['result']
                                }"""
FINAL_NEW = """                            elif response['type'] == 'final':
                                # budget-clock: prefix (pagination-safe) the live
                                # clock; on a cap kill (124) prefix the guidance.
                                _bc_res = response['result']
                                if not isinstance(_bc_res, str):
                                    _bc_res = str(_bc_res)
                                _bc_prefix = _bc_clock_line() + "\\n"
                                if str(response.get('status')) == '124' or 'Exit code: 124' in _bc_res:
                                    _bc_prefix += _bc_timeout_notice(_bc_res)
                                return {
                                    'status': response['status'],
                                    'result': _bc_prefix + _bc_res
                                }"""

# ------------------------------------------------------------ run_infer_idea
QUERY_ANCHOR = '        messages = [{"role": "user", "content": ml_dev_query}]'
QUERY_NEW = '''        _bc_total = int(__import__("os").getenv("AI_RESEARCHER_TOTAL_BUDGET_SECONDS", "0") or 0)
        _bc_cap = int(__import__("os").getenv("AI_RESEARCHER_COMMAND_TIMEOUT_SECONDS", "0") or 0)
        _bc_rules = "[budget] "
        _bc_rules += (f"Total wall-clock budget for this run: {_bc_total // 60} minutes. " if _bc_total > 0 else "This run has no declared total wall-clock cap. ")
        _bc_rules += (f"Single-command cap: {_bc_cap // 60} minutes -- a command exceeding it is terminated with exit 124. " if _bc_cap > 0 else "")
        _bc_rules += ("Every command result begins with a [clock] line showing elapsed and remaining time. "
                      "Plan experiments to fit the remaining budget, split long training into resumable stages with checkpoints, "
                      "and reserve time at the end to write and deliver every required artifact.\\n\\n")
        ml_dev_query = _bc_rules + ml_dev_query
        messages = [{"role": "user", "content": ml_dev_query}]'''


def patch(path: Path, pairs: list[tuple[str, str]]) -> None:
    text = path.read_text(encoding="utf-8")
    if MARK in text and path == DOCKER_ENV:
        print(f"[{MARK}] {path} already patched")
        return
    for old, new in pairs:
        if new in text:
            continue
        if old not in text:
            raise SystemExit(f"[{MARK}] anchor not found in {path}: {old[:70]!r}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch(DOCKER_ENV, [(IMPORT_ANCHOR, IMPORT_ADD), (SEND_OLD, SEND_NEW), (FINAL_OLD, FINAL_NEW)])
    patch(ENTRY, [(QUERY_ANCHOR, QUERY_NEW)])
    print(f"[{MARK}] applied: single-command cap (wrapped, instructive 124 notice) + live clock prefix + upfront declaration")


if __name__ == "__main__":
    main()
