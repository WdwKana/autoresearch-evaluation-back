#!/usr/bin/env python3
"""02 x ARC (formal wrapper): carry the ARC delivery contract into the idea record the BFTS stages read.

The delivery contract is injected only into the ideation system prompt, so the BFTS coding agent -- which
loads the idea JSON and never sees that prompt -- has no way to learn where artifacts must land
(fullrun_arc_02_bounded_20260828_054050 finished all stages and delivered nothing). Host defines the output
schema only. NOTE: this writes host text into the framework's idea record (agent_prompt_replacement class).

argv: <idea json> <model> <base url>
"""
from pathlib import Path
import json
import sys

# The delivery contract is injected only into the ideation system prompt, so the
# BFTS coding agent -- which loads this idea JSON and never sees that prompt --
# has no way to learn where artifacts must land (run
# fullrun_arc_02_bounded_20260828_054050 finished all stages and delivered
# nothing to /workspace). Carry the same requirements into the idea record the
# BFTS stages actually read. Host defines the output schema only; the method,
# experiments and results stay entirely framework-authored.
path = Path(sys.argv[1])
model, base_url = sys.argv[2], sys.argv[3]
ideas = json.loads(path.read_text(encoding="utf-8"))
spec = (
    "\n\nARC delivery contract (host output schema; the method remains yours). "
    "ALL FIVE files below are mandatory; a run missing ANY of them is scored as a "
    "total failure, so write submission.json and final_report.md even if brief:\n"
    "- write these five files at the workspace root /workspace: research_idea.json, "
    "estimator.py, submission.json, experiment_trace.json, final_report.md;\n"
    "- estimator.py must define `class Estimator` with `predict(self, mlp)` returning "
    "a (32, 256) numpy array; numpy and the standard library only (the official "
    "scorer provides nothing else); ship learned parameters beside it as .npz;\n"
    "- CRITICAL interface fact: the mlp argument is an OBJECT, not an array. "
    "np.asarray(mlp) raises 'float() argument must be ... not MLP' and forfeits the "
    "run (a prior attempt failed on all 100 evaluation MLPs exactly this way). Read "
    "mlp.weights -- an ordered list of per-layer (width, width) numpy weight "
    "matrices -- plus mlp.width, mlp.depth, and mlp.seed for any randomness. "
    "Design and test every experiment against this interface;\n"
    "- never return zeros/ones/full/empty constants and never use the words "
    "placeholder or fallback prediction (the scorer rejects them);\n"
    "- experiment_trace.json must contain framework_native_execution=true, "
    "consumed_topic_input=true, workspace_trace_root='/workspace', a list of 2-4 "
    "experiments each with a unique string experiment_id, selected_experiment_id "
    "matching one of them, framework_internal_model='" + model + "', "
    "framework_internal_api_base_url='" + base_url + "', "
    "idea_artifact='research_idea.json', idea_locked_before_experiments=true;\n"
    "- research_idea.json needs non-empty hypothesis, method_rationale, "
    "expected_failure_modes and comparison_logic."
)
changed = False
for idea in ideas if isinstance(ideas, list) else []:
    if isinstance(idea, dict) and "ARC delivery contract" not in str(idea.get("Experiments", "")):
        idea["Experiments"] = str(idea.get("Experiments", "")) + spec
        changed = True
if not changed:
    print("SKIP: no idea record to annotate")
path.write_text(json.dumps(ideas, indent=2), encoding="utf-8")
