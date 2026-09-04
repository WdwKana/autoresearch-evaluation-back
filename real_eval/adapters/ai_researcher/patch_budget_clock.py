#!/usr/bin/env python3
"""Make time visible to the agent: live budget clock + upfront declaration.

WHY (2026-09-04)
    Agents design experiments blind to wall time (luna's endless refinement,
    kimi launching a training command that blocked the pipeline for ~2h at
    19151% CPU until the wall clock killed the run). Doctrine (user-set): time
    control must be EXPLICIT information, never an invisible guillotine. A
    forced single-command timeout was prototyped and removed by user decision
    (2026-09-04): enforcement is out, visibility only.

      1. Live clock: execute_command/run_python results are PREFIXED
         (pagination-safe) with one line:
         `[clock] elapsed 42m / budget 180m, remaining ~138m`.
         Only the experiment-pacing tools carry it (file ops stay clean).
         Without a declared budget only elapsed is shown (babylm stays
         unbounded by prior decision).
      2. Upfront declaration prefixed to ml_dev_query: the total budget and
         the advice to ESTIMATE a command's runtime before launching it --
         generated at runtime from the SAME env var the clock reads, so
         declaration and display cannot drift.

    Known limit (accepted): the clock is visible only when a command RETURNS.
    A command that blocks for hours gives the agent no mid-flight signal; the
    outer wall clock plus the timeout-finalization fixes are the backstop.

ENV
    AI_RESEARCHER_TOTAL_BUDGET_SECONDS   whole-run wall budget (unset/0 = no cap shown)

Anchors are pristine framework lines; loud SystemExit on drift. Idempotent.
Run from the AI-Researcher source root. Applies to docker_env.py (clock
helper), terminal_tools.py (clock on the two pacing tools), run_infer_idea.py
(declaration).
"""
from __future__ import annotations

from pathlib import Path

DOCKER_ENV = Path("research_agent/inno/environment/docker_env.py")
TOOLS = Path("research_agent/inno/tools/terminal_tools.py")
ENTRY = Path("research_agent/run_infer_idea.py")

MARK = "budget-clock"

# ------------------------------------------------------------- docker_env
# Clock helper only; T0 = process start of run_infer_idea (docker_env import),
# which is exactly what the wrapper wall clock times for mcar/psydef and a few
# boot seconds late for ARC (conservative direction, negligible at 3h scale).
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
"""

# ------------------------------------------------------- terminal_tools
TOOLS_IMPORT_OLD = "from research_agent.inno.environment.docker_env import DockerEnv, DockerConfig"
TOOLS_IMPORT_NEW = "from research_agent.inno.environment.docker_env import DockerEnv, DockerConfig, _bc_clock_line as _bc_clock"

EXEC_OLD = """        response = env.run_command(command, print_stream)
        return response"""
EXEC_NEW = """        response = env.run_command(command, print_stream)
        # budget-clock: experiment-pacing tools carry the live clock
        if isinstance(response, dict) and isinstance(response.get('result'), str):
            response['result'] = _bc_clock() + "\\n" + response['result']
        return response"""

RUNPY_OLD = """        result = env.run_command(command, print_stream)
        return result"""
RUNPY_NEW = """        result = env.run_command(command, print_stream)
        # budget-clock: experiment-pacing tools carry the live clock
        if isinstance(result, dict) and isinstance(result.get('result'), str):
            result['result'] = _bc_clock() + "\\n" + result['result']
        return result"""

# ------------------------------------------------------------ run_infer_idea
QUERY_ANCHOR = '        messages = [{"role": "user", "content": ml_dev_query}]'
QUERY_NEW = '''        _bc_total = int(__import__("os").getenv("AI_RESEARCHER_TOTAL_BUDGET_SECONDS", "0") or 0)
        _bc_rules = "[budget] "
        _bc_rules += (f"Total wall-clock budget for this run: {_bc_total // 60} minutes. " if _bc_total > 0 else "This run has no declared total wall-clock cap. ")
        _bc_rules += ("Every execute_command/run_python result begins with a [clock] line showing elapsed and remaining time. "
                      "Before launching any long-running command, estimate its runtime; if the estimate does not comfortably fit the remaining budget, redesign the experiment (smaller scale, staged training with checkpoints). "
                      "Reserve time at the end to write and deliver every required artifact.\\n\\n")
        ml_dev_query = _bc_rules + ml_dev_query
        messages = [{"role": "user", "content": ml_dev_query}]'''


def patch(path: Path, pairs: list[tuple[str, str]]) -> None:
    text = path.read_text(encoding="utf-8")
    changed = False
    for old, new in pairs:
        if new in text:
            continue
        if old not in text:
            raise SystemExit(f"[{MARK}] anchor not found in {path}: {old[:70]!r}")
        text = text.replace(old, new, 1)
        changed = True
    if changed:
        path.write_text(text, encoding="utf-8")


def main() -> None:
    patch(DOCKER_ENV, [(IMPORT_ANCHOR, IMPORT_ADD)])
    patch(TOOLS, [(TOOLS_IMPORT_OLD, TOOLS_IMPORT_NEW), (EXEC_OLD, EXEC_NEW), (RUNPY_OLD, RUNPY_NEW)])
    patch(ENTRY, [(QUERY_ANCHOR, QUERY_NEW)])
    print(f"[{MARK}] applied: live clock on execute/run_python + upfront declaration (no command enforcement -- visibility only)")


if __name__ == "__main__":
    main()
