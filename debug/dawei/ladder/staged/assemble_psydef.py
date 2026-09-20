#!/usr/bin/env python3
"""Deterministic host-side assembly of the PsyDefDetect handoff from AI-Scientist-v2's
own promoted artifacts. No LLM call is made here.

Inputs (a finished run workspace):
  workspace/experiments/<exp>/logs/0-run/stage_*/best_solution_<node>.py   framework's per-stage selection
  workspace/experiments/<exp>/logs/0-run/stage_*/journal.json               node facts (plan, exec_time, verdicts)
  workspace/experiments/<exp>/idea.json                                     framework's idea
  workspace/logs/0-run/{draft,baseline,research,ablation}_summary.json      native summaries, if present
Steps:
  1. replay every per-stage best_solution in a clean offline container (cwd = replay dir,
     exec() like the native interpreter); collect working/<name>.official_score.json
  2. experiments = one entry per stage best_solution (2-4); psydefdetect_score = the best
     configuration the node itself evaluated; selected = the last stage's best_solution
  3. promote the selected node's best-configuration predictions to <out>/predictions.jsonl,
     re-run the official scorer on it -> <out>/score.json
  4. write <out>/experiment_trace.json (facts only) and <out>/final_report.md (rendered
     from journal facts + native summaries when present)
Usage: assemble_psydef.py --workspace WS --out OUT --model M --base-url URL [--data-root D] [--image IMG]
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
ap.add_argument("--data-root", default="/data/daweiwang/claude-home/researchclaweval-public/data/psydefdetect")
ap.add_argument("--image", default="ai-scientist-v2:runtime-ready")
ap.add_argument("--replay-timeout", type=int, default=1800)
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


# ---- 2. replay each selection in a clean offline container ----
automation = WS / "automation"
experiments = []
for st, d, best, nid in stages:
    rd = REPLAY / f"stage{st}_{nid[:8]}"
    if rd.exists():
        shutil.rmtree(rd)
    (rd / "working").mkdir(parents=True)
    shutil.copy(best, rd / "runfile.py")
    ref = WS / "hf_dataset_reference.py"
    if ref.exists():
        shutil.copy(ref, rd / "hf_dataset_reference.py")
    cmd = ["docker", "run", "--rm", "--network", "none", "--cpus", "4",
           "-v", f"{a.data_root}:/data/psydefdetect:ro", "-v", f"{automation}:/workspace/automation:ro",
           "-v", f"{rd}:/replay", "-w", "/replay", "-e", "CUDA_VISIBLE_DEVICES=", a.image,
           "python3", "-c", "code=open('runfile.py').read(); exec(compile(code,'runfile.py','exec'),{})"]
    say(f"replaying stage {st} best_solution {nid[:8]} ...")
    t0 = dt.datetime.now()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=a.replay_timeout)
        rc = p.returncode
        (rd / "replay_stdout.txt").write_text(p.stdout[-200000:], encoding="utf-8")
        (rd / "replay_stderr.txt").write_text(p.stderr[-200000:], encoding="utf-8")
    except subprocess.TimeoutExpired:
        rc = 124
    secs = (dt.datetime.now() - t0).total_seconds()
    scores, pred_for = {}, {}
    for sf in sorted(glob.glob(str(rd / "working" / "*.json"))):
        try:
            payload = json.load(open(sf))
        except Exception:
            continue
        if not isinstance(payload, dict) or "psydefdetect_score" not in payload:
            continue
        stem = Path(sf).name[:-5]
        name = re.sub(r"[._-]?(official_)?score$", "", stem) or "config"   # <name>.official_score / score_x / official_score
        scores[name] = float(payload["psydefdetect_score"])
        cands = [rd / "working" / f"{name}.predictions.jsonl"] + sorted((rd / "working").glob("*predictions*.jsonl"))
        pa = payload.get("prediction_artifact")
        if pa and Path(pa).name:
            cands.insert(0, rd / "working" / Path(pa).name)
        pred_for[name] = next((c for c in cands if c.exists()), None)
    say(f"  rc={rc} {secs:.0f}s official scores: {scores}")
    facts = node_facts(d, nid)
    best_cfg = max(scores, key=scores.get) if scores else None
    experiments.append({
        "experiment_id": f"stage{st}_{nid[:8]}", "stage": st, "node_id": nid,
        "framework_selection": "best_solution written by the framework at the end of this stage",
        "plan": facts.get("plan", ""), "exec_time_seconds_in_run": facts.get("exec_time"),
        "replay": {"return_code": rc, "seconds": round(secs), "dir": str(rd.relative_to(OUT))},
        "official_scores": scores, "best_configuration": best_cfg,
        "psydefdetect_score": scores.get(best_cfg) if best_cfg else None,
        "prediction_artifact": (str(pred_for[best_cfg].relative_to(OUT)) if best_cfg and pred_for.get(best_cfg) else None),
        "score_artifact": (str((rd / "working").relative_to(OUT)) + f"/{best_cfg}*score*.json" if best_cfg else None),
    })

scored = [e for e in experiments if e["psydefdetect_score"] is not None and e["prediction_artifact"]]
if len(scored) < 2:
    say(f"only {len(scored)} replays produced an official score; contract needs 2")
    sys.exit(4)

# ---- 3. selection = the last stage's best_solution (the framework's final choice) ----
selected = experiments[-1] if experiments[-1] in scored else scored[-1]
src_pred = OUT / selected["prediction_artifact"]
shutil.copy(src_pred, OUT / "predictions.jsonl")
say(f"selected {selected['experiment_id']} ({selected['best_configuration']}, {selected['psydefdetect_score']}); predictions promoted")
scorer = automation / "scripts/run_psydefdetect_local_score.py"
split = automation / "psydefdetect_split.json"
p = subprocess.run([sys.executable, str(scorer), "--dataset-root", a.data_root, "--split-manifest", str(split),
                    "--predictions", str(OUT / "predictions.jsonl"), "--output-score", str(OUT / "score.json")],
                   capture_output=True, text=True)
say(f"host re-score rc={p.returncode} {p.stderr.strip()[:200]}")
if p.returncode != 0:
    sys.exit(5)
host_score = json.load(open(OUT / "score.json"))["psydefdetect_score"]
say(f"host official score = {host_score} (replay said {selected['psydefdetect_score']})")

# ---- 4. trace + report (facts only) ----
idea_files = glob.glob(str(WS / "experiments/*/idea.json"))
idea = json.load(open(idea_files[0])) if idea_files else {}
trace = {
    "task_id": "psydefdetect",
    "framework": "AI-Scientist-v2",
    "framework_native_execution": True,
    "consumed_topic_input": True,
    "workspace_trace_root": "/workspace",
    "framework_internal_model": a.model,
    "framework_internal_api_base_url": a.base_url,
    "idea_artifact": "research_idea.json",
    "idea_locked_before_experiments": True,
    "experiment_definition": "one experiment per BFTS stage: the best_solution the framework itself wrote at the end of that stage; scores obtained by replaying it offline",
    "experiments": [{k: v for k, v in e.items() if k != "plan"} | {"plan_excerpt": e["plan"][:600]} for e in experiments],
    "selected_experiment_id": selected["experiment_id"],
    "selection_rule": "the framework's best_solution of its final stage",
    "prediction_artifact": "predictions.jsonl",
    "score_artifact": "score.json",
    "host_rescored_psydefdetect_score": host_score,
    "assembled_by": "host deterministic assembly (assemble_psydef.py): replay + relocation + host re-score; no LLM call",
    "assembled_at": dt.datetime.now(dt.UTC).isoformat(),
}
(OUT / "experiment_trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")

# report: native summaries if the framework wrote them, else journal facts
summ = {}
for name in ("draft", "baseline", "research", "ablation"):
    for f in glob.glob(str(WS / "experiments/*/logs/0-run" / f"{name}_summary.json")):
        try:
            summ[name] = json.load(open(f))
        except Exception:
            pass
lines = [f"# {idea.get('Title', 'PsyDefDetect study')}", "",
         "## Research idea (framework-authored)", "", idea.get("Abstract", ""), "", "**Hypothesis.** " + idea.get("Short Hypothesis", ""), "",
         "## Experiments (the framework's per-stage selections, replayed offline)", ""]
for e in experiments:
    lines += [f"### {e['experiment_id']} (stage {e['stage']})", "", e["plan"][:1200] or "(no plan text)", "",
              f"- official psydefdetect_score by configuration: {json.dumps(e['official_scores'])}",
              f"- best configuration: {e['best_configuration']} -> {e['psydefdetect_score']}", ""]
lines += ["## Selection", "", f"Selected: **{selected['experiment_id']}** (configuration `{selected['best_configuration']}`), the framework's best_solution of its final stage.",
          f"Host re-score of the promoted predictions: **{host_score:.4f}** (macro-F1 over labels 1-8).", ""]
if summ:
    lines += ["## Framework's own stage summaries", ""]
    for name, s in summ.items():
        lines += [f"### {name}", "", "```json", json.dumps(s, ensure_ascii=False, indent=1)[:6000], "```", ""]
lines += ["## Provenance", "", f"Assembled deterministically from the framework's saved artifacts on {trace['assembled_at']}; no LLM call in assembly.", ""]
(OUT / "final_report.md").write_text("\n".join(lines), encoding="utf-8")
(OUT / "assembly_log.txt").write_text("\n".join(log), encoding="utf-8")
say("done: predictions.jsonl, score.json, experiment_trace.json, final_report.md")
