#!/usr/bin/env python3
"""AI-Researcher idea-loop corrections: two verified implementation errors.

Both fixes correct plain implementation mistakes. Neither changes the research
procedure the paper prescribes (five-idea generation and ranking, iterative
implement-review refinement) nor adds any capability; API call counts are
unchanged -- only erroneous payload duplication is removed and one mislabeled
variable is corrected.

FIX 1 -- transcript self-extension (exponential history doubling)
    AgentModule.__call__ (inno/workflow/flowcache.py) extends the CALLER'S
    message list in place and returns that same list object. The idea loop in
    run_infer_idea.py then does `messages.extend(survey_messages)` where
    `survey_messages is messages` -- a list self-extension that doubles the
    entire transcript every round.

    Probe evidence (debug/dawei/evidence/2026-09-01-context-bloat/): message
    counts 42 -> 86 -> 174 -> 350 -> 702 across five rounds; every history
    sha's multiplicity doubles in lockstep (11->22->44->88->176, 6->...->96)
    while the freshly-prepended system message stays at 1 -- the exact
    fingerprint of list.extend(self). The 702-message request held only 32
    unique messages; 86% of its 241,746 tokens were byte-identical duplicates.
    kimi-k2.6 (262,144-token window) is killed by this mechanism alone.

    Fix: delete the redundant extend. AgentModule has already appended this
    round's messages in place; every piece of information remains present
    exactly once.

FIX 2 -- wrong artifact in the ML brief ("model survey notes" slot)
    ml_dev_query interpolates {survey_res} twice in one message: once as the
    innovative idea and again four lines later labeled "the model survey
    notes". The genuine survey artifact exists and is generated immediately
    before: code_survey_res, which this same file stores as
    context_variables["model_survey"]. Verified on run probe_ds_20260901_181553:
    survey_res is the idea-selection document (59,503 chars), while
    code_survey_res is a "Comprehensive Implementation Report" with a full
    concept-to-code mapping grounded in the real dataset environment
    (39,354 chars) -- the content the label promises and the implementing
    agent otherwise never receives. The duplicate copy of survey_res adds
    zero information by construction (byte-identical text in the same
    message).

    Fix: interpolate code_survey_res in the "model survey notes" slot.
    Caveat recorded for the team: the sibling pipeline run_infer_plan.py binds
    model_survey to survey_res, so upstream naming is not fully consistent;
    within run_infer_idea.py, the local assignment (model_survey =
    code_survey_res), the prompt's own wording, and the artifact contents all
    support this correction.

Idempotent; fails loudly if an upstream anchor moves. Run from the
AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

ENTRY = Path("research_agent/run_infer_idea.py")

FIX1_OLD = '''for i in range(IDEA_NUM - 1):
            messages.extend(survey_messages)
            messages.append({"role": "user", "content": "please survey again and give me another idea"})'''

FIX1_NEW = '''for i in range(IDEA_NUM - 1):
            # AgentModule already extended `messages` in place and returned the
            # same list (survey_messages is messages); re-extending doubled the
            # whole transcript every round. See patch_idea_loop_fixes.py.
            messages.append({"role": "user", "content": "please survey again and give me another idea"})'''

FIX2_OLD = '''And I have conducted the comprehensive survey on the innovative idea and the papers, and give you the model survey notes:
{survey_res}'''

FIX2_NEW = '''And I have conducted the comprehensive survey on the innovative idea and the papers, and give you the model survey notes:
{code_survey_res}'''


def main() -> None:
    if not ENTRY.is_file():
        raise SystemExit("run from the AI-Researcher source root: research_agent/run_infer_idea.py not found")
    text = ENTRY.read_text(encoding="utf-8")

    applied = []
    if "re-extending doubled the" in text:
        applied.append("fix1(already)")
    elif FIX1_OLD in text:
        text = text.replace(FIX1_OLD, FIX1_NEW, 1)
        applied.append("fix1")
    else:
        raise SystemExit("idea-loop-fixes: FIX1 anchor (self-extension loop) not found")

    if "{code_survey_res}\nYou should carefully go through" in text:
        applied.append("fix2(already)")
    elif FIX2_OLD in text:
        text = text.replace(FIX2_OLD, FIX2_NEW, 1)
        applied.append("fix2")
    else:
        raise SystemExit("idea-loop-fixes: FIX2 anchor (model survey notes slot) not found")

    ENTRY.write_text(text, encoding="utf-8")
    print(f"[idea-loop-fixes] applied: {', '.join(applied)}")


if __name__ == "__main__":
    main()
