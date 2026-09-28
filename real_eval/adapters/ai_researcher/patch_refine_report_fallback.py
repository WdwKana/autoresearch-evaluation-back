#!/usr/bin/env python3
"""Survive a refine round whose analyser filed no experiment report.

WHY (2026-09-28)
    In the refine loop the exp_analyser agent is expected to file a report tool
    call that populates context_variables["experiment_report"]. When the agent
    ends its turn without doing so (kimi's action-less replies), the flow dies:
        analysis_report = context_variables["experiment_report"][-1][...]
        KeyError: 'experiment_report'   (fullrun_mcar_01_kimi_20260927_124934,
    crash after ~4h, zero deliverables). One line above, the framework already
    computed the same report from the agent's message text -- the fallback is
    the framework's own first choice, so this guard only prevents the crash and
    never invents content.

WHAT IT DOES
    In run_infer_idea.py and run_infer_plan.py, keep the message-derived
    analysis_report when the tool-filed report is absent or malformed, use an
    empty further_plan, and print a loud marker line. Behavior with a filed
    report is byte-identical.

Idempotent; loud on anchor drift. Run from the AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

MARK = "refine-report-fallback"

ANCHOR = '''            analysis_report = context_variables["experiment_report"][-1]["analysis_report"]
            further_plan = context_variables["experiment_report"][-1]["further_plan"]
'''
ADD = '''            # refine-report-fallback: keep the message-derived analysis_report when the
            # analyser filed no report; never crash the whole run on a missing tool call.
            _filed_reports = context_variables.get("experiment_report") or []
            if _filed_reports and isinstance(_filed_reports[-1], dict):
                analysis_report = _filed_reports[-1].get("analysis_report", analysis_report)
                further_plan = _filed_reports[-1].get("further_plan", "")
            else:
                further_plan = ""
                print("[refine-report-fallback] analyser filed no experiment_report; "
                      "continuing with the message-derived analysis and an empty further_plan", flush=True)
'''


def main() -> None:
    changed = 0
    for target in (Path("research_agent/run_infer_idea.py"), Path("research_agent/run_infer_plan.py")):
        if not target.exists():
            continue
        text = target.read_text(encoding="utf-8")
        if MARK in text:
            print(f"[{MARK}] already applied: {target}")
            continue
        n = text.count(ANCHOR)
        if n == 0:
            raise SystemExit(f"[{MARK}] anchor not found in {target} (upstream drift?)")
        text = text.replace(ANCHOR, ADD)
        target.write_text(text, encoding="utf-8")
        print(f"[{MARK}] applied to {target} ({n} site(s))")
        changed += n
    if changed == 0:
        print(f"[{MARK}] nothing to do")


if __name__ == "__main__":
    main()
