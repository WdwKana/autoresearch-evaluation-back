#!/usr/bin/env python3
"""In-session, ground-truth exit gate for the ML implementation phase.

The ML agent (tool_choice="required") ends its session by calling
case_resolved (done) or case_not_resolved (give up). Both are legitimate --
an agent MUST be able to declare honest failure; forcing "never give up"
only produces fabrication, which the ARC/TDC contracts forbid. The real
defect the earlier version of this patch had was checking the wrong thing:
it policed the *self-report* (whether task_response was empty), so it nagged
an agent that had already written files ("go implement" when it just had)
and left case_not_resolved as an unlocked side door.

This version checks GROUND TRUTH -- the files actually on disk -- exactly
like SWE-bench (success = tests pass, defined outside the agent), CI
(failure is first-class), and structured-output retry (bounce with the
specific missing thing, not "try harder"):

  * The gate validates ONLY this phase's deliverable: estimator.py, the
    implementation the ML agent is responsible for. Later artifacts
    (research_idea.json / experiment_trace.json / submission.json /
    final_report.md) belong to other phases and to the final acceptance
    layer -- demanding them here would be a false premise all over again.
  * case_resolved: if estimator.py exists anywhere under the agent's real
    workplace, the exit passes through byte-identical regardless of the
    task_response payload (fixes the "already done but reported emptily"
    misfire). If it is genuinely absent, the call bounces with a precise
    message naming what is missing.
  * case_not_resolved: an empty/trivial failure_reason is not honest
    failure, it is bailing -- it bounces. A substantive reason (a real
    blocker) passes through and the run records honest failure; content is
    never fabricated to avoid a zero.

Both functions gain an `env` parameter so the ML agent's own
`with_env(code_env)` wrapper injects the DockerEnv and hides `env` from the
model-facing schema; env.local_workplace is the host-side mount of the
agent's /workplace. Bounce messages start with "[Tool Call Error]" because
that prefix is core.py's only continue-the-session path after a
required-tool exit call. Insistence is bounded by the loop guard /
max_turns. If env is unavailable the gate degrades to the payload check
rather than deadlocking. Idempotent; loud on anchor drift. Run from the
AI-Researcher source root.
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
   return task_response

def case_not_resolved(failure_reason):
   """
   The failure reason is the reason why you cannot find a solution to the task. You can use this function only after you have tried multiple times and still cannot find a solution.

   Args:
      failure_reason: The reason why you cannot find a solution to the task.
   """
   return failure_reason'''

NEW = '''def _ml_delivery_estimator_on_disk(env):
   """True if the topic's ML deliverable exists under the agent's real workplace.

   The deliverable name(s) come from AI_RESEARCHER_ML_DELIVERY_GLOBS (comma
   separated fnmatch patterns, default 'estimator.py'). Any non-empty file
   matching any pattern anywhere under the workplace counts as delivered."""
   try:
      import os as _os, fnmatch as _fn
      root = getattr(env, "local_workplace", None)
      if not root or not _os.path.isdir(root):
         return None  # cannot verify
      pats = [g.strip() for g in _os.getenv("AI_RESEARCHER_ML_DELIVERY_GLOBS", "estimator.py").split(",") if g.strip()]
      if not pats:
         pats = ["estimator.py"]
      for _dir, _subs, _files in _os.walk(root):
         _subs[:] = [d for d in _subs if d not in ("data", "__pycache__", ".git", "downloads")]
         for _f in _files:
            if any(_fn.fnmatch(_f, pat) for pat in pats):
               if _os.path.getsize(_os.path.join(_dir, _f)) > 0:
                  return True
      return False
   except Exception:
      return None  # cannot verify

def _ml_delivery_run_validator(env):
   """Optional official-validator hook (AI_RESEARCHER_ML_DELIVERY_VALIDATOR).

   When the env var holds a shell command, run it; a clean nonzero exit means
   the artifacts fail the SAME validator the host will apply, and its own
   output is returned so the agent can fix and retry (psydef-style bounce).
   Returns None when unset, passing, or when the hook itself crashes -- the
   gate must never wedge a run on its own tooling (fail-open for tool faults
   only, never for validation verdicts)."""
   import os as _os
   import subprocess as _sp
   cmd = _os.getenv("AI_RESEARCHER_ML_DELIVERY_VALIDATOR", "").strip()
   if not cmd:
      return None
   try:
      r = _sp.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
      if r.returncode == 0:
         return None
      out = ((r.stdout or "") + "\\n" + (r.stderr or "")).strip()
      return out[-800:] if out else "validator exited nonzero without output"
   except Exception:
      return None

def case_resolved(task_response, env=None):
   """
   The task response is the result of the task. Use this function only after you have successfully completed the task, which means estimator.py has been written and run.

   Args:
      task_response: The result of the task.
   """
   _present = _ml_delivery_estimator_on_disk(env)
   if _present is True:
      _v = _ml_delivery_run_validator(env)
      if _v:
         return ("[Tool Call Error] case_resolved rejected: the official artifact validator failed:\\n"
                 + _v +
                 "\\nFix your artifacts so the validator passes, then call case_resolved again.")
      return task_response
   if _present is None:
      # cannot verify on disk -> degrade to the self-report check
      _s = str(task_response).strip() if task_response is not None else ""
      if _s in ("", "{}", "[]", "''", '""', "None", "null") or len(_s) < 40:
         return ("[Tool Call Error] case_resolved rejected: no result was provided. "
                 "Complete the implementation -- write estimator.py, run it, verify the outputs -- "
                 "then call case_resolved again with a substantive description; "
                 "or, if you are genuinely blocked, call case_not_resolved with a concrete reason.")
      _v = _ml_delivery_run_validator(env)
      if _v:
         return ("[Tool Call Error] case_resolved rejected: the official artifact validator failed:\\n"
                 + _v +
                 "\\nFix your artifacts so the validator passes, then call case_resolved again.")
      return task_response
   # verified absent on disk
   return ("[Tool Call Error] case_resolved rejected: estimator.py was not found in your workplace. "
           "The implementation is not complete. Write estimator.py (it must expose predict(mlp) returning "
           "a (32, 256) array of per-layer activations that genuinely depends on mlp.weights), run it to "
           "verify it works, and then call case_resolved again. If you are genuinely unable to proceed, "
           "call case_not_resolved with a concrete technical reason instead.")

def case_not_resolved(failure_reason, env=None):
   """
   The failure reason is the reason why you cannot find a solution to the task. You can use this function only after you have tried multiple times and still cannot find a solution. Provide a concrete, specific reason.

   Args:
      failure_reason: The reason why you cannot find a solution to the task.
   """
   _r = str(failure_reason).strip() if failure_reason is not None else ""
   if _r in ("", "{}", "[]", "''", '""', "None", "null") or len(_r) < 20:
      return ("[Tool Call Error] case_not_resolved rejected: an empty failure reason is not accepted. "
              "If you can still make progress, implement estimator.py and call case_resolved. "
              "If you are truly blocked, call case_not_resolved again with a concrete, specific technical "
              "reason (what you tried, the exact error, why it cannot be resolved).")
   return failure_reason'''


def main() -> None:
    if not ML_AGENT.is_file():
        raise SystemExit("ml-delivery-validation: run from the AI-Researcher source root")
    text = ML_AGENT.read_text(encoding="utf-8")
    if "_ml_delivery_estimator_on_disk" in text:
        print("[ml-delivery-validation] already applied")
        return
    if OLD not in text:
        raise SystemExit("ml-delivery-validation: case_resolved/case_not_resolved anchor not found")
    ML_AGENT.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("[ml-delivery-validation] exit gate now checks estimator.py on disk; both exits covered")


if __name__ == "__main__":
    main()
