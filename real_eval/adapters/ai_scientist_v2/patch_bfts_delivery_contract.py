#!/usr/bin/env python3
"""Attach the ARC deliverable contract to BFTS's own per-stage output flow.

02-scoped runtime patch (applied to the run workspace copy by the ARC wrapper;
upstream checkout untouched). Same anchored-replace / fail-loud / idempotent
style as patch_semantic_scholar_bounded.

WHY
    BFTS natively asks each node for a single self-contained script that saves
    results into experiment_data.npy (see parallel_agent._prompt_impl_guideline)
    -- that script becomes best_solution_<hash>.py. The ARC contract instead
    needs a runnable estimator + four root files. Rather than bolt a foreign
    requirement on, we make the contract ride BFTS's existing flow, without
    displacing any stage's research goal:

    A. Interface kernel (ALL stages, in _prompt_impl_guideline): the node's
       single-file script must expose predict(mlp)->(32,256). This is the SAME
       artifact as best_solution -- keeping the interface just makes it
       scorable. It does not conflict with any stage goal.
    A'. Real-data requirement (stage 2+ only): predict() must run over the real
       /data/arc_wbe_2026 weights, NOT synthetic/toy data. Deliberately skips
       stage 1, whose native goal is "use a simple dataset / basic functional
       correctness" (a preliminary prototype) -- forcing real data there would
       fight the stage's design.
    B. Final export (closing stage 4 only, in _curate_task_desc): also export
       the selected implementation to /workspace/estimator.py and write
       /workspace/{submission.json, experiment_trace.json, final_report.md}.
       Intermediate stages produce mid-search artifacts; only the closing stage
       is asked for the final contract files. This is best-effort by the agent;
       the host exit-delivery check remains the backstop for what it cannot
       produce (never fabricated).

    The wording附着 (attaches) to each stage's goal ("regardless of this
    stage's objective, keep the interface / export at the end"), so it does not
    replace baseline-tuning / creative-research / ablation exploration.

WHERE
    - parallel_agent.py::_prompt_impl_guideline  (self.stage_name available)
    - agent_manager.py::_curate_task_desc         (stage.name available)
Ideation is NOT touched (idea iteration stays clean; both anchors are BFTS-only).
Fail-loud if anchors drift; idempotent.
"""
from pathlib import Path

PARALLEL = Path("ai_scientist/treesearch/parallel_agent.py")
MANAGER = Path("ai_scientist/treesearch/agent_manager.py")
MARK = "ARC-WBE deliverable interface"

# ---- A + A': impl guideline, stage-layered, appended before the return ----
PA_OLD = '        return {"Implementation guideline": impl_guideline}'
PA_NEW = '''        # bfts-delivery-contract: ride BFTS's own per-node output flow.
        impl_guideline.append(
            "ARC-WBE deliverable interface: your single-file script must define "
            "predict(mlp) -> a numpy array of shape (32, 256) (per-layer activation "
            "means). This is the same artifact as your best solution -- keeping this "
            "interface makes it directly replayable by the official scorer."
        )
        if getattr(self, "stage_name", None) and not str(self.stage_name).startswith("1_"):
            impl_guideline.append(
                "From this stage on, predict() must operate on the REAL MLP weights in "
                "/data/arc_wbe_2026 (load them), not synthetic or toy data, so the "
                "reported results reflect the actual task."
            )
        return {"Implementation guideline": impl_guideline}'''

# ---- B: final export, only in the closing (4_) stage ----
MG_OLD = '            task_desc += "Risk Factors and Limitations: " + risk_factors_str + "\\n"'
MG_NEW = '''            task_desc += "Risk Factors and Limitations: " + risk_factors_str + "\\n"
            # bfts-delivery-contract: closing stage also produces the contract files.
            task_desc += (
                "Final delivery (this is the closing stage): in addition to the above, "
                "export your selected implementation to /workspace/estimator.py (exposing "
                "predict(mlp)->(32,256) over /data/arc_wbe_2026) and write "
                "/workspace/submission.json, /workspace/experiment_trace.json, and "
                "/workspace/final_report.md.\\n"
            )'''


def _apply(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if MARK in text and path == PARALLEL:
        print(f"[bfts-delivery-contract] {path.name} already patched")
        return
    if "Final delivery (this is the closing stage)" in text and path == MANAGER:
        print(f"[bfts-delivery-contract] {path.name} already patched")
        return
    if old not in text:
        raise SystemExit(f"[bfts-delivery-contract] anchor not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    _apply(PARALLEL, PA_OLD, PA_NEW)
    _apply(MANAGER, MG_OLD, MG_NEW)
    print("[bfts-delivery-contract] applied: interface kernel (all stages) + real-data (stage2+) + final export (stage4)")


if __name__ == "__main__":
    main()
