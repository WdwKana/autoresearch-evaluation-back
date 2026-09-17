#!/usr/bin/env python3
"""TRIAL (2026-09-17): state the official ARC-WBE task definition in the BFTS
task description -- the per-stage "Research idea" text that the coder, the
judge and the metric-definer all read -- WITHOUT touching ideation.

STATUS
    Single-variable experiment scoped to the 02 ARC wrapper. Not scoreboard
    grade until the team decides the canonical placement (the same facts
    would then go into the shared summary/contract for every framework, since
    the definition is currently missing for all of them). Remove by dropping
    this file's two wrapper lines.

WHY (code-verified, see debug/dawei/2026-09-14-arc-task-definition-gap.md and
the 2026-09-17 stage-1 mechanics analysis)
    No framework-visible text defines what "mean activation" is averaged
    over, so in all nine ARC runs the framework's own metric definer
    (_define_global_metrics, fed by task_desc) fell back to a
    permutation-consistency metric that is tautological for invariant
    features, and coders fabricated circular synthetic targets; the native
    judge (consistent 40/42 on re-judging) flagged every draft on exactly
    those two defects. Placing the definition in the blueprint (run 102631)
    instead inflated ideation ambition; task_desc is read only at experiment
    time, so ideation is untouched.

WHAT
    Appends a facts-only paragraph (README first paragraph + local_engine.py
    convention + official score rule + this round's FLOP budget) at the end
    of AgentManager._get_task_desc_str. No method is suggested; no checklist
    ("MANDATORY ...") wording -- psydef runs 112949/115325 showed judge-visible
    checklists trigger compliance hunting.

Anchored-replace, fail-loud, idempotent; applied to the run-workspace copy.
"""
from pathlib import Path

TARGET = Path("ai_scientist/treesearch/agent_manager.py")
MARK = "arc-task-definition"

OLD = '''        if "Code" in self.task_desc:
            task_desc += "Code To Use:\\n" + self.task_desc["Code"] + "\\n"
        return task_desc'''
NEW = '''        if "Code" in self.task_desc:
            task_desc += "Code To Use:\\n" + self.task_desc["Code"] + "\\n"
        # arc-task-definition: official task facts (starterkit README + local_engine.py).
        task_desc += (
            "\\nTask definition (official ARC-WBE starterkit README): the ground truth "
            "for each MLP is the per-neuron mean activation under standard normal "
            "input x ~ N(0, 1) -- the mean over inputs of each layer's post-ReLU "
            "activations (the challenge estimates it with N = 1e9 Monte Carlo "
            "samples). Forward convention (starterkit reference implementation "
            "local_engine.py): activations propagate as x = max(x @ W_l, 0) for each "
            "layer l. Official score: final-layer MSE (final_layer_mse) multiplied by "
            "max(0.1, C/B), where C is the FLOPs the estimator spends per MLP and B is "
            "the per-MLP FLOP budget (2.72e11 for this dataset round); lower is better. "
            "All-layers MSE is diagnostic only.\\n"
        )
        return task_desc'''


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if MARK in text:
        print("[task-definition-taskdesc] already applied")
        return
    if OLD not in text:
        raise SystemExit("[task-definition-taskdesc] anchor not found in agent_manager.py")
    TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("[task-definition-taskdesc] applied: official task definition appended to BFTS task_desc (all stages)")


if __name__ == "__main__":
    main()
