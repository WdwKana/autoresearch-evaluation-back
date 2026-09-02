#!/usr/bin/env python3
"""Reject empty case_resolved submissions from the ML agent.

Third member of the zero-validation family (after plan tools accepting
"placeholder"/"final" and the judge approving an empty implementation): the
ML agent's case_resolved returns task_response verbatim, so
case_resolved({"task_response": {}}) ends the implementation phase with "{}"
as the deliverable -- observed twice in fullrun_arc_01_dsv_20260902_101926
(first ML session and the submit session), after which the judge ruled the
empty implementation fully_correct and the whole pipeline ran hollow.

The rejection message MUST start with "[Tool Call Error]": core.py ends the
required-tool session on any case_resolved result UNLESS the content starts
with that prefix (that is its retry path). A substantive response passes
through byte-identical; empty/trivial ones bounce back with instructions to
actually implement first, or to use case_not_resolved honestly. Bounded by
the loop guard / max_turns if a model insists. Idempotent; loud on anchor
drift. Run from the AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

ML_AGENT = Path("research_agent/inno/agents/inno_agent/ml_agent.py")

OLD = '''def case_resolved(task_response):
   """
   The task response is the result of the task. Use this function only after you have successfully completed the task. 

   Args:
      task_response: The result of the task.
   """
   return task_response'''

NEW = '''def case_resolved(task_response):
   """
   The task response is the result of the task. Use this function only after you have successfully completed the task. The task_response must substantively describe what you implemented and the results; an empty or trivial task_response is not accepted.

   Args:
      task_response: The result of the task.
   """
   _s = str(task_response).strip() if task_response is not None else ""
   if _s in ("", "{}", "[]", "''", '""', "None", "null") or len(_s) < 40:
       return ("[Tool Call Error] case_resolved rejected: your task_response is empty or trivial. "
               "case_resolved may only be called after the task is actually completed. "
               "Implement the project now -- write the code files, run them, and verify the outputs -- "
               "then call case_resolved again with a substantive description of what you built and the results. "
               "If you are genuinely unable to proceed, call case_not_resolved with the concrete reason instead.")
   return task_response'''


def main() -> None:
    if not ML_AGENT.is_file():
        raise SystemExit("ml-delivery-validation: run from the AI-Researcher source root")
    text = ML_AGENT.read_text(encoding="utf-8")
    if "case_resolved rejected" in text:
        print("[ml-delivery-validation] already applied")
        return
    if OLD not in text:
        raise SystemExit("ml-delivery-validation: case_resolved anchor not found")
    ML_AGENT.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("[ml-delivery-validation] empty case_resolved now bounces with retry instructions")


if __name__ == "__main__":
    main()
