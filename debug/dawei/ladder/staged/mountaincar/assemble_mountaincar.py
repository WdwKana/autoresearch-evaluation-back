#!/usr/bin/env python3
"""Deterministic host-side assembly of the MountainCar handoff from AI-Scientist-v2's
own promoted artifacts. No LLM call is made here.

Inputs (a finished run workspace):
  workspace/experiments/<exp>/logs/0-run/stage_*/best_solution_<node>.py   framework's per-stage selection
  workspace/experiments/<exp>/logs/0-run/stage_*/journal.json               node facts (plan, exec_time, verdicts)
  workspace/experiments/<exp>/idea.json                                     framework's idea
  workspace/logs/0-run/{draft,baseline,research,ablation}_summary.json      native summaries, if present
Steps:
  1. replay every per-stage best_solution in a clean offline container (cwd = replay dir,
     exec() like the native interpreter); collect working/<name>.evaluation.json
  2. experiments = one entry per stage best_solution (2-4); local_final_layer_mse = the best
     configuration the node itself evaluated (highest official Reward Mean); selected = the last stage with an official record
  3. promote the selected configuration's src/, checkpoints/ and the frozen evaluate.py;
     the launcher then scores them with the frozen evaluator in the JAX image
  4. write <out>/experiment_trace.json (facts only) and <out>/final_report.md (rendered
     from journal facts + native summaries when present)
Usage: assemble_mountaincar.py --workspace WS --out OUT --model M --base-url URL [--data-root D] [--image IMG]
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
ap.add_argument("--data-root", default="/data/daweiwang/claude-home/researchclaweval-public/data/mountaincar_continuous")
ap.add_argument("--gpu", default="none")
ap.add_argument("--image", default="ai-scientist-v2:runtime-mountaincar")
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


# ---- 2. replay each selection in a clean offline CPU container (JAX runtime) ----
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
    cmd = ["docker", "run", "--rm", "--network", "none", "--cpus", "32", "--memory", "32g",
           "-v", f"{a.data_root}:/data/mountaincar_continuous:ro", "-v", f"{rd}:/replay", "-w", "/replay",
           "-e", "CUDA_VISIBLE_DEVICES=", "-e", "JAX_PLATFORMS=cpu", "-e", "OMP_NUM_THREADS=32", a.image,
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
    scores, sub_for, std_for = {}, {}, {}
    for sf in sorted(glob.glob(str(rd / "working" / "*.evaluation.json"))):
        try:
            payload = json.load(open(sf))
            v = float(payload["reward_mean"])
        except Exception:
            continue
        if payload.get("official") is not True:
            continue
        name = Path(sf).name[:-len(".evaluation.json")]
        sub = rd / "working" / f"{name}.submission"
        if not (sub / "evaluate.py").exists() or len(list((sub / "checkpoints").glob("config*.pkl"))) != 5:
            continue
        scores[name] = v; std_for[name] = float(payload.get("reward_std", 0.0)); sub_for[name] = sub
    say(f"  rc={rc} {secs:.0f}s official reward_mean by configuration: " + json.dumps({k: round(v, 3) for k, v in scores.items()}))
    facts = node_facts(d, nid)
    best_cfg = max(scores, key=scores.get) if scores else None   # higher reward is better
    experiments.append({
        "experiment_id": f"stage{st}_{nid[:8]}", "stage": st, "node_id": nid,
        "framework_selection": "best_solution written by the framework at the end of this stage",
        "plan": facts.get("plan", ""), "exec_time_seconds_in_run": facts.get("exec_time"),
        "replay": {"return_code": rc, "seconds": round(secs), "dir": str(rd.relative_to(OUT))},
        "reward_mean_by_configuration": scores, "best_configuration": best_cfg,
        "reward_mean": scores.get(best_cfg) if best_cfg else None, "reward_std": std_for.get(best_cfg) if best_cfg else None,
        "submission_artifact": (str(sub_for[best_cfg].relative_to(OUT)) if best_cfg else None),
    })

scored = [e for e in experiments if e["reward_mean"] is not None]
if len(scored) < 2:
    say(f"only {len(scored)} replays produced an official evaluation with a complete submission; contract needs 2")
    sys.exit(4)

# ---- 3. selection = the framework's final stage (last scored stage); no cross-stage score comparison ----
selected = scored[-1]
say(f"selected {selected['experiment_id']} ({selected['best_configuration']}, reward_mean {selected['reward_mean']:.3f})")
sub = OUT / selected["submission_artifact"]
for name in ("src", "checkpoints"):
    if (OUT / name).exists():
        shutil.rmtree(OUT / name)
    shutil.copytree(sub / name, OUT / name)
shutil.copy(Path(a.data_root) / "protected" / "evaluate.py", OUT / "evaluate.py")   # byte-exact frozen evaluator (host scorer checks the hash)
say("promoted: src/ (with config.yaml), checkpoints/ (5 files), evaluate.py (frozen copy)")

# ---- 4. trace + report (facts only) ----
idea_files = glob.glob(str(WS / "experiments/*/idea.json"))
idea = json.load(open(idea_files[0])) if idea_files else {}
def _text(v):
    return "\n".join(str(x) for x in v) if isinstance(v, list) else str(v or "")
trace = {
    "task_id": "mountaincar_continuous",
    "framework": "AI-Scientist-v2",
    "framework_native_execution": True,
    "consumed_topic_input": True,
    "workspace_trace_root": "/workspace",
    "framework_internal_model": a.model,
    "framework_internal_api_base_url": a.base_url,
    "idea_artifact": "research_idea.json",
    "idea_locked_before_experiments": True,
    "experiment_definition": "one experiment per BFTS stage: the best_solution the framework itself wrote at the end of that stage; its official Reward Mean obtained by replaying it offline through the reference module's official_evaluation (frozen evaluate.py)",
    "experiments": [{k: v for k, v in e.items() if k != "plan"} | {"plan_excerpt": e["plan"][:600]} for e in experiments],
    "selected_experiment_id": selected["experiment_id"],
    "selection_rule": "the framework's final stage: the best_solution of the last stage that produced an official record (no score comparison across stages)",
    "submission_artifact": "checkpoints/ + src/ + evaluate.py",
    "score_artifact": "score.json (written by the host scorer after assembly)",
    "assembled_by": "host deterministic assembly (assemble_mountaincar.py): replay + relocation; no LLM call",
    "assembled_at": dt.datetime.now(dt.UTC).isoformat(),
}
(OUT / "experiment_trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
lines = [f"# {_text(idea.get('Title', 'MountainCar study'))}", "", "## Research idea (framework-authored)", "", _text(idea.get("Abstract", "")), "",
         "**Hypothesis.** " + _text(idea.get("Short Hypothesis", "")), "",
         "## Experiments (the framework's per-stage selections, replayed offline)", ""]
for e in experiments:
    lines += [f"### {e['experiment_id']} (stage {e['stage']})", "", "```text", e["plan"][:1200] or "(no plan text)", "```", "",
              f"- official Reward Mean by configuration: {json.dumps({k: round(v, 3) for k, v in e['reward_mean_by_configuration'].items()})}",
              f"- best configuration: {e['best_configuration']} -> {e['reward_mean']}", ""]
lines += ["## Selection", "", f"Selected: **{selected['experiment_id']}** (configuration `{selected['best_configuration']}`), the framework's final stage.", "",
          "## Provenance", "", f"Assembled deterministically from the framework's saved artifacts on {trace['assembled_at']}; no LLM call in assembly.", ""]
(OUT / "final_report.md").write_text("\n".join(lines), encoding="utf-8")
(OUT / "assembly_log.txt").write_text("\n".join(log), encoding="utf-8")
say("done: src/, checkpoints/, evaluate.py, experiment_trace.json, final_report.md")
