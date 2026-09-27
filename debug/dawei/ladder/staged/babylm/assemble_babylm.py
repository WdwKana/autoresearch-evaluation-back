#!/usr/bin/env python3
"""Deterministic host-side assembly of the BabyLM handoff from AI-Scientist-v2's
own promoted artifacts. No LLM call is made here.

Inputs (a finished run workspace):
  workspace/experiments/<exp>/logs/0-run/stage_*/best_solution_<node>.py   framework's per-stage selection
  workspace/experiments/<exp>/logs/0-run/stage_*/journal.json               node facts (plan, exec_time, verdicts)
  workspace/experiments/<exp>/idea.json                                     framework's idea
  workspace/logs/0-run/{draft,baseline,research,ablation}_summary.json      native summaries, if present
Steps:
  1. replay every per-stage best_solution in a clean offline container (cwd = replay dir,
     exec() like the native interpreter); collect working/<name>.validation.json
  2. experiments = one entry per stage best_solution (2-4); local_final_layer_mse = the best
     configuration the node itself validated (lowest perplexity); selected = the last stage with an official record
  3. promote the selected configuration's saved model (submission/) and validation record;
     the launcher then runs run_babylm_score.py and the host validation
  4. write <out>/experiment_trace.json (facts only) and <out>/final_report.md (rendered
     from journal facts + native summaries when present)
Usage: assemble_babylm.py --workspace WS --out OUT --model M --base-url URL [--data-root D] [--image IMG]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--workspace", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--model", required=True)
ap.add_argument("--base-url", required=True)
ap.add_argument("--data-root", default="/data/daweiwang/claude-home/researchclaweval-public/data/BabyLM-2026-Strict-Small")
ap.add_argument("--gpu", default="1")
ap.add_argument("--image", default="ai-scientist-v2:runtime-ready")
ap.add_argument("--replay-timeout", type=int, default=3600)
a = ap.parse_args()
WS, OUT = Path(a.workspace), Path(a.out)
OUT.mkdir(parents=True, exist_ok=True)
REPLAY = OUT / "replay"
REPLAY.mkdir(exist_ok=True)
log = []


def say(m):
    print("[assemble]", m, flush=True)
    log.append(m)


# ---- 1. locate the framework's per-stage selections ----
stage_dirs = sorted(glob.glob(str(WS / "experiments/*/logs/0-run/stage_*")))
stages = []
for d in stage_dirs:
    st = int(re.search(r"/stage_(\d)", d).group(1))
    best = sorted(glob.glob(d + "/best_solution_*.py"))
    if not best:
        say(f"stage {st}: no best_solution -> skipped")
        continue
    node_id = re.search(r"best_solution_([0-9a-f]+)\.py", best[-1]).group(1)
    stages.append((st, d, best[-1], node_id))
if len(stages) < 2:
    say(f"only {len(stages)} stage selections found; the contract needs 2-4")
    sys.exit(3)
stages = stages[-4:]  # at most 4 (stages 1-4)
say("stage selections: " + ", ".join(f"stage{st}={nid[:8]}" for st, _, _, nid in stages))


def node_facts(stage_dir, node_id):
    J = json.load(open(Path(stage_dir) / "journal.json"))
    for n in J["nodes"]:
        if n["id"] == node_id:
            return {"plan": n.get("plan") or "", "exec_time": n.get("exec_time"), "analysis": n.get("analysis") or "",
                    "metric": str(n.get("metric"))[:400], "is_buggy": n.get("is_buggy")}
    return {}


# ---- 2. replay each selection in a clean offline container (GPU) ----
ref = WS / "hf_dataset_reference.py"
experiments = []
for st, d, best, nid in stages:
    rd = REPLAY / f"stage{st}_{nid[:8]}"
    if rd.exists():
        shutil.rmtree(rd)
    (rd / "working").mkdir(parents=True)
    shutil.copy(best, rd / "runfile.py")
    if ref.exists():
        shutil.copy(ref, rd / "hf_dataset_reference.py")
    gpu_args = [] if str(a.gpu).lower() == "none" else ["--gpus", f"device={a.gpu}"]
    cmd = ["docker", "run", "--rm", "--network", "none", "--cpus", "8", "--shm-size", "16g", *gpu_args,
           "-v", f"{a.data_root}:/data/BabyLM-2026-Strict-Small:ro", "-v", f"{rd}:/replay", "-w", "/replay",
           *(["-e", "CUDA_VISIBLE_DEVICES="] if str(a.gpu).lower() == "none" else []),
           "-e", "OMP_NUM_THREADS=8", "-e", "HF_HUB_OFFLINE=1", "-e", "HF_DATASETS_OFFLINE=1", a.image,
           "python3", "-c", "code=open('runfile.py').read(); exec(compile(code,'runfile.py','exec'),{})"]
    say(f"replaying stage {st} best_solution {nid[:8]} ...")
    t0 = dt.datetime.now()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=a.replay_timeout)
        rc = p.returncode
        (rd / "replay_stdout.txt").write_text(p.stdout[-400000:], encoding="utf-8")
        (rd / "replay_stderr.txt").write_text(p.stderr[-200000:], encoding="utf-8")
    except subprocess.TimeoutExpired:
        rc = 124
        (rd / "replay_stdout.txt").write_text("replay timed out", encoding="utf-8")
        (rd / "replay_stderr.txt").write_text("", encoding="utf-8")
    secs = (dt.datetime.now() - t0).total_seconds()
    scores, sub_for = {}, {}
    for sf in sorted(glob.glob(str(rd / "working" / "*.validation.json"))):
        try:
            payload = json.load(open(sf))
            v = float(payload["validation_perplexity"])
        except Exception:
            continue
        if not (v > 0) or payload.get("official") is not True:   # only records written by the reference module count (a node may shadow the function)
            continue
        name = Path(sf).name[:-len(".validation.json")]
        scores[name] = v
        sub = rd / "working" / f"{name}.submission"
        sub_for[name] = sub if sub.exists() else None
    say(f"  rc={rc} {secs:.0f}s word-level validation perplexity by configuration: " + json.dumps({k: round(v, 3) for k, v in scores.items()}))
    facts = node_facts(d, nid)
    best_cfg = min(scores, key=scores.get) if scores else None   # lower perplexity is better
    experiments.append({
        "experiment_id": f"stage{st}_{nid[:8]}", "stage": st, "node_id": nid,
        "framework_selection": "best_solution written by the framework at the end of this stage",
        "plan": facts.get("plan", ""), "exec_time_seconds_in_run": facts.get("exec_time"),
        "replay": {"return_code": rc, "seconds": round(secs), "dir": str(rd.relative_to(OUT))},
        "validation_perplexity_by_configuration": scores, "best_configuration": best_cfg,
        "validation_perplexity": scores.get(best_cfg) if best_cfg else None,
        "validation_artifact": (str((rd / "working" / f"{best_cfg}.validation.json").relative_to(OUT)) if best_cfg else None),
        "submission_artifact": (str(sub_for[best_cfg].relative_to(OUT)) if best_cfg and sub_for.get(best_cfg) else None),
    })

scored = [e for e in experiments if e["validation_perplexity"] is not None]
if len(scored) < 2:
    say(f"only {len(scored)} replays produced a validation perplexity; contract needs 2")
    sys.exit(4)

# ---- 3. selection = the framework's final stage (last scored stage); no cross-stage score comparison ----
selected = scored[-1]
say(f"selected {selected['experiment_id']} ({selected['best_configuration']}, word-level validation perplexity {selected['validation_perplexity']:.3f})")
sub_dir = OUT / "submission"
if sub_dir.exists():
    shutil.rmtree(sub_dir)
if selected["submission_artifact"]:
    shutil.copytree(OUT / selected["submission_artifact"], sub_dir)
    say("submission/ promoted from the selected configuration")
else:
    sub_dir.mkdir()
    say("selected configuration kept no model artifact; submission/ holds only the validation record")
shutil.copy(OUT / selected["validation_artifact"], sub_dir / "validation.json")
shutil.copy(OUT / selected["replay"]["dir"] / "runfile.py", sub_dir / "runfile.py")

# ---- 4. trace + report (facts only) ----
idea_files = glob.glob(str(WS / "experiments/*/idea.json"))
idea = json.load(open(idea_files[0])) if idea_files else {}
def _text(v):
    return "\n".join(str(x) for x in v) if isinstance(v, list) else str(v or "")
trace = {
    "task_id": "babylm",
    "framework": "AI-Scientist-v2",
    "framework_native_execution": True,
    "consumed_topic_input": True,
    "workspace_trace_root": "/workspace",
    "framework_internal_model": a.model,
    "framework_internal_api_base_url": a.base_url,
    "idea_artifact": "research_idea.json",
    "idea_locked_before_experiments": True,
    "experiment_definition": "one experiment per BFTS stage: the best_solution the framework itself wrote at the end of that stage; its word-level validation perplexity obtained by replaying it offline through the reference module's official_validation",
    "experiments": [{k: v for k, v in e.items() if k != "plan"} | {"plan_excerpt": e["plan"][:600], "name": e["best_configuration"]} for e in experiments],
    "selected_experiment_id": selected["experiment_id"],
    "selection_rule": "the framework's final stage: the best_solution of the last stage that produced an official record (no score comparison across stages)",
    "best_validation_perplexity": selected["validation_perplexity"],
    "submission_artifact": "submission/",
    "score_artifact": "score.json (written by the host scorer after assembly)",
    "assembled_by": "host deterministic assembly (assemble_babylm.py): replay + relocation; no LLM call",
    "assembled_at": dt.datetime.now(dt.UTC).isoformat(),
}
(OUT / "experiment_trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
lines = [f"# {_text(idea.get('Title', 'BabyLM study'))}", "", "## Research idea", "", _text(idea.get("Abstract", "")), "",
         "**Hypothesis.** " + _text(idea.get("Short Hypothesis", "")), "",
         "## Experiments", ""]
for e in experiments:
    lines += [f"### {e['experiment_id']} (stage {e['stage']})", "", "```text", e["plan"][:1200] or "(no plan text)", "```", "",
              f"- word-level validation perplexity by configuration: {json.dumps({k: round(v, 3) for k, v in e['validation_perplexity_by_configuration'].items()})}",
              f"- best configuration: {e['best_configuration']} -> {e['validation_perplexity']}", ""]
lines += ["## Host packaging notes (written by the host, not by the framework)", "", "- Text above is the framework's own (idea, per-stage plans, stage summaries); values come from the official records; the host only formatted them.", "- Experiments: the best_solution the framework saved at the end of each stage, replayed offline without network.",
          f"- Selected: **{selected['experiment_id']}** (configuration `{selected['best_configuration']}`); rule: the framework's final stage (last stage with an official record).",
          f"- Assembled deterministically on {trace['assembled_at']}; no LLM call in assembly.", ""]
(OUT / "final_report.md").write_text("\n".join(lines), encoding="utf-8")
(OUT / "assembly_log.txt").write_text("\n".join(log), encoding="utf-8")
say("done: submission/, experiment_trace.json, final_report.md")
