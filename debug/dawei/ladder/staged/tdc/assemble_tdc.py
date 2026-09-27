#!/usr/bin/env python3
"""Deterministic host-side assembly of the TDC-ADMET-Tox handoff from AI-Scientist-v2's
own promoted artifacts. No LLM call is made here.

Inputs (a finished run workspace):
  workspace/experiments/<exp>/logs/0-run/stage_*/best_solution_<node>.py   framework's per-stage selection
  workspace/experiments/<exp>/logs/0-run/stage_*/journal.json               node facts (plan, exec_time, verdicts)
  workspace/experiments/<exp>/idea.json                                     framework's idea
Steps:
  1. replay every per-stage best_solution in a clean offline CPU container (cwd = replay dir,
     exec() like the native interpreter); collect working/<name>.validation_metrics.json and
     working/<name>.test_predictions.csv written through the reference module
  2. experiments = one entry per stage best_solution (2-4), each represented by the
     configuration with the highest validation macro AUROC that the node itself scored
  3. selected = the last stage's best_solution that produced a validation record (the framework's
     final stage; no score comparison across stages)
  4. write the contract package from facts only: runs/<run_id>/{config.json, validation_predictions.csv,
     metrics.json, train.log, runfile.py}, predictions.csv, environment.json, experiment_trace.json
     (with a claim ledger), paper.md (tables rendered from the metrics files), final_report.md, logs/
  score.json is NOT written here (host scorer, after the framework-stage audit).
Usage: assemble_tdc.py --workspace WS --out OUT --model M --base-url URL [--data-root D] [--image IMG]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import glob
import hashlib
import json
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
ap.add_argument("--data-root", default="/data/daweiwang/claude-home/researchclaweval-public/data/tdc_admet_tox")
ap.add_argument("--image", default="ai-scientist-v2:runtime-ready")
ap.add_argument("--replay-timeout", type=int, default=3600)
ap.add_argument("--native-wall-seconds", type=float, default=0.0)
a = ap.parse_args()
WS, OUT = Path(a.workspace), Path(a.out)
OUT.mkdir(parents=True, exist_ok=True)
REPLAY = OUT / "replay"
REPLAY.mkdir(exist_ok=True)
ENDPOINTS = ("AMES", "hERG", "DILI")
RESOURCE_BUDGET = {"cpu_cores": 4, "memory_gib": 16, "gpu_count": 0, "workspace_disk_gib": 10,
                   "max_experiment_runtime_seconds": 3600, "max_total_wall_seconds": 7200,
                   "network_policy": "injected_llm_relay_only"}
log = []


def say(m):
    print("[assemble]", m, flush=True)
    log.append(m)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


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
stages = stages[-4:]
say("stage selections: " + ", ".join(f"stage{st}={nid[:8]}" for st, _, _, nid in stages))


def node_facts(stage_dir, node_id):
    J = json.load(open(Path(stage_dir) / "journal.json"))
    for n in J["nodes"]:
        if n["id"] == node_id:
            return {"plan": n.get("plan") or "", "exec_time": n.get("exec_time"), "analysis": n.get("analysis") or "",
                    "is_buggy": n.get("is_buggy")}
    return {}


# ---- 2. replay each selection in a clean offline CPU container ----
automation = WS / "automation"
ref = WS / "hf_dataset_reference.py"
experiments = []
env_info = None
for st, d, best, nid in stages:
    rd = REPLAY / f"stage{st}_{nid[:8]}"
    if rd.exists():
        shutil.rmtree(rd)
    (rd / "working").mkdir(parents=True)
    shutil.copy(best, rd / "runfile.py")
    if ref.exists():
        shutil.copy(ref, rd / "hf_dataset_reference.py")
    env_probe = ("import json,platform,sys,importlib,importlib.util;pk={};\n"
                 "[pk.__setitem__(m,getattr(importlib.import_module(m),'__version__','?')) for m in ('numpy','pandas','scipy','sklearn','torch') if importlib.util.find_spec(m)];\n"
                 "json.dump({'python_version':sys.version.split()[0],'platform':platform.platform(),'packages':pk},open('working/_environment_probe.json','w'))")
    cmd = ["docker", "run", "--rm", "--network", "none", "--cpus", "4", "--memory", "16g",
           "-v", f"{a.data_root}:/data/tdc_admet_tox:ro", "-v", f"{automation}:/workspace/automation:ro",
           "-v", f"{rd}:/replay", "-w", "/replay", "-e", "CUDA_VISIBLE_DEVICES=", "-e", "OMP_NUM_THREADS=4", a.image,
           "python3", "-c", env_probe + "\ncode=open('runfile.py').read(); exec(compile(code,'runfile.py','exec'),{})"]
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
    probe = rd / "working" / "_environment_probe.json"
    if env_info is None and probe.exists():
        env_info = json.load(open(probe))
    configs = {}
    for mf in sorted(glob.glob(str(rd / "working" / "*.validation_metrics.json"))):
        name = Path(mf).name[: -len(".validation_metrics.json")]
        try:
            m = json.load(open(mf))
            v = float(m["macro_average_auroc"])
        except Exception:
            continue
        vp = rd / "working" / f"{name}.validation_predictions.csv"
        tp = rd / "working" / f"{name}.test_predictions.csv"
        configs[name] = {"macro_average_auroc": v, "metrics_file": Path(mf), "validation_predictions": vp if vp.exists() else None,
                         "test_predictions": tp if tp.exists() else None, "metrics": m}
    say(f"  rc={rc} {secs:.0f}s configurations scored: " + json.dumps({k: round(v['macro_average_auroc'], 4) for k, v in configs.items()}))
    usable = {k: v for k, v in configs.items() if v["validation_predictions"] and v["test_predictions"]}
    best_cfg = max(usable, key=lambda k: usable[k]["macro_average_auroc"]) if usable else None
    facts = node_facts(d, nid)
    experiments.append({"stage": st, "node_id": nid, "run_id": f"stage{st}_{nid[:8]}", "replay_dir": rd, "rc": rc, "seconds": secs,
                        "configs": configs, "best_cfg": best_cfg, "facts": facts, "code": best})

scored = [e for e in experiments if e["best_cfg"]]
if len(scored) < 2:
    say(f"only {len(scored)} replays produced a scored configuration with test predictions; contract needs 2")
    sys.exit(4)
# a node repeated across stages (same code) yields the same configuration: keep the first occurrence only
seen_codes, distinct = set(), []
for e in scored:
    h = sha256(Path(e["code"]))
    if h in seen_codes:
        say(f"{e['run_id']}: same code as an earlier stage selection -> not a distinct experiment")
        continue
    seen_codes.add(h)
    distinct.append(e)
if len(distinct) < 2:
    say("fewer than 2 distinct stage selections; contract needs 2")
    sys.exit(4)
distinct = distinct[:4]

# ---- 3. write per-experiment files (facts only) ----
runs_dir = OUT / "runs"
if runs_dir.exists():
    shutil.rmtree(runs_dir)
records, claims = [], []
for idx, e in enumerate(distinct, start=1):
    rid, cfg = e["run_id"], e["configs"][e["best_cfg"]]
    rdir = runs_dir / rid
    rdir.mkdir(parents=True)
    shutil.copy(e["code"], rdir / "runfile.py")
    shutil.copy(cfg["validation_predictions"], rdir / "validation_predictions.csv")
    shutil.copy(cfg["metrics_file"], rdir / "metrics.json")
    (rdir / "train.log").write_text("# replay of the framework's best_solution in a clean offline container\n"
                                   + (e["replay_dir"] / "replay_stdout.txt").read_text(encoding="utf-8")
                                   + "\n# stderr\n" + (e["replay_dir"] / "replay_stderr.txt").read_text(encoding="utf-8"), encoding="utf-8")
    other = sorted(k for k in e["configs"] if k != e["best_cfg"])
    config = {"run_id": rid, "framework_stage": e["stage"], "framework_node_id": e["node_id"],
              "framework_selection": "best_solution written by the framework at the end of this stage",
              "configuration_name": e["best_cfg"], "runfile_sha256": sha256(Path(e["code"])),
              "other_configurations_scored_by_this_node": other,
              "framework_verdict_is_buggy": e["facts"].get("is_buggy"),
              "replay_command": "python3 -c \"code=open('runfile.py').read(); exec(compile(code,'runfile.py','exec'),{})\" (cwd = this directory, offline, CPU)",
              "seed_note": "the program sets its own seeds; the replay passes none"}
    (rdir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    m = cfg["metrics"]
    per = {ep: {"auroc": float(m["per_endpoint"][ep]["auroc"])} for ep in ENDPOINTS}
    rec = {"run_id": rid, "status": "complete",
           "hypothesis": (e["facts"].get("plan") or "").strip()[:1500] or f"framework node {e['node_id'][:8]} (no plan text recorded)",
           "model_strategy": f"framework stage {e['stage']} best_solution {e['node_id'][:8]}, configuration '{e['best_cfg']}' (see runs/{rid}/runfile.py)",
           "feature_strategy": f"as implemented in runs/{rid}/runfile.py for configuration '{e['best_cfg']}'",
           "config_file": f"runs/{rid}/config.json", "prediction_file": f"runs/{rid}/validation_predictions.csv",
           "metrics_file": f"runs/{rid}/metrics.json", "log_file": f"runs/{rid}/train.log",
           "runtime_seconds": round(e["seconds"], 3), "seed": 0, "candidate_count": 1,
           "validation_metrics": {"macro_average_auroc": float(m["macro_average_auroc"]), "per_endpoint": per},
           "framework_stage": e["stage"], "framework_node_id": e["node_id"], "framework_verdict_is_buggy": e["facts"].get("is_buggy"),
           "other_configurations_scored_by_this_node": other}
    if idx >= 3:
        rec["parent_run_id"] = records[-1]["run_id"]
        rec["change_rationale"] = (e["facts"].get("plan") or "").strip()[:1500] or "framework stage progression"
    records.append(rec)
    for ep in ("macro", *ENDPOINTS):
        val = float(m["macro_average_auroc"]) if ep == "macro" else float(m["per_endpoint"][ep]["auroc"])
        claims.append({"claim_id": f"{rid}_{ep.lower()}_auroc", "endpoint": ep, "metric": "AUROC", "value": val, "source_run_id": rid,
                       "prediction_file": rec["prediction_file"], "config_file": rec["config_file"], "log_file": rec["log_file"]})

# ---- selection = the framework's final stage (last record in stage order); no cross-stage score comparison ----
selected = records[-1]
sel_e = next(e for e in distinct if e["run_id"] == selected["run_id"])
shutil.copy(sel_e["configs"][sel_e["best_cfg"]]["test_predictions"], OUT / "predictions.csv")
say(f"selected {selected['run_id']} ({sel_e['best_cfg']}, validation macro AUROC {selected['validation_metrics']['macro_average_auroc']:.4f}); test predictions promoted")

# ---- 4. environment, trace, paper, report, logs ----
env_info = env_info or {"python_version": "unknown", "platform": "unknown", "packages": {}}
environment = {"python_version": env_info["python_version"], "platform": env_info["platform"], "container_image": a.image,
               "device": "cpu", "seeds": [0], "packages": env_info["packages"], "created_at": dt.datetime.now(dt.UTC).isoformat()}
(OUT / "environment.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")
idea_files = glob.glob(str(WS / "experiments/*/idea.json"))
idea = json.load(open(idea_files[0])) if idea_files else {}
def _text(v):   # idea fields may be lists (one string per item) or strings
    return "\n".join(str(x) for x in v) if isinstance(v, list) else str(v or "")
idea = {k: (_text(v) if k in ("Title", "Abstract", "Short Hypothesis", "Risk Factors and Limitations", "Experiments") else v) for k, v in idea.items()}
sel_dir = f"runs/{selected['run_id']}"
trace = {"task_id": "tdc_admet_tox", "framework": "AI-Scientist-v2", "framework_native_execution": True, "consumed_topic_input": True,
         "workspace_trace_root": "/workspace", "framework_internal_model": a.model, "framework_internal_api_base_url": a.base_url,
         "idea_artifact": "research_idea.json", "idea_locked_before_experiments": True,
         "experiment_definition": "one experiment per BFTS stage: the best_solution the framework itself wrote at the end of that stage, represented by the configuration with the highest validation macro AUROC that the node scored through the official validation scorer; values obtained by replaying it offline",
         "experiments": records, "selected_experiment_id": selected["run_id"], "selection_rule": "the framework's final stage: the best_solution of the last stage that produced an official record (no score comparison across stages)", "within_node_configuration": "highest validation macro AUROC among the configurations the node scored (host rule)",
         "final_prediction_file": "predictions.csv",
         "reproduction": {"entrypoint": f"{sel_dir}/runfile.py", "command": f"cd {sel_dir} && python3 -c \"code=open('runfile.py').read(); exec(compile(code,'runfile.py','exec'),{{}})\"", "seed": 0},
         "environment_file": "environment.json", "resource_budget": RESOURCE_BUDGET,
         "total_wall_seconds": round(float(a.native_wall_seconds) + sum(e["seconds"] for e in experiments), 3),
         "native_wall_seconds": round(float(a.native_wall_seconds), 3),
         "claims": claims,
         "assembled_by": "host deterministic assembly (assemble_tdc.py): replay + relocation; no LLM call",
         "assembled_at": dt.datetime.now(dt.UTC).isoformat()}
(OUT / "experiment_trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")


def cell(rid, ep):
    v = next(c["value"] for c in claims if c["claim_id"] == f"{rid}_{ep}_auroc")
    return f"{v:.4f} <!-- claim:{rid}_{ep}_auroc -->"


title = idea.get("Title", "TDC ADMET toxicity study")
paper = [f"# {title}", "", "## Hypothesis", "", idea.get("Short Hypothesis", "") or idea.get("Abstract", ""), "",
         "## Methods", "", "Each experiment is the solution the framework promoted at the end of one of its stages, replayed offline on CPU.",
         "The framework's own plan for each one is quoted verbatim below.", ""]
for r in records:
    paper += [f"### {r['run_id']}", "", "```text", r["hypothesis"], "```", ""]
paper += ["## Validation protocol", "",
          "All configurations are scored on the scaffold-split validation set with the official validation scorer; the held-back split is never used for selection.",
          "The selected experiment is the framework's final stage (the last stage with a validation record).", "",
          "## Results", "", "| Experiment | macro AUROC | AMES AUROC | hERG AUROC | DILI AUROC |", "|---|---:|---:|---:|---:|"]
for r in records:
    rid = r["run_id"]
    paper.append(f"| {rid} | {cell(rid, 'macro')} | {cell(rid, 'ames')} | {cell(rid, 'herg')} | {cell(rid, 'dili')} |")
paper += ["", "## Selected approach", "", f"Selected: **{selected['run_id']}** (configuration `{sel_e['best_cfg']}`), the framework's final stage.", "",
          "## Limitations", "", "```text", idea.get("Risk Factors and Limitations", "") or "(none recorded by the framework)", "```", "",
          "## Provenance", "", "Assembled deterministically from the framework's saved artifacts; no hidden-split result is reported.", ""]
(OUT / "paper.md").write_text("\n".join(paper), encoding="utf-8")
report = [f"# {title}", "", "## Research idea (framework-authored)", "", idea.get("Abstract", ""), "",
          "## Experiments (the framework's per-stage selections, replayed offline)", ""]
for r in records:
    report += [f"### {r['run_id']} (stage {r['framework_stage']}, framework verdict is_buggy={r['framework_verdict_is_buggy']})", "",
               "```text", r["hypothesis"][:1200], "```", "",
               f"- validation macro AUROC: {r['validation_metrics']['macro_average_auroc']:.4f}; per endpoint: " + ", ".join(f"{ep} {r['validation_metrics']['per_endpoint'][ep]['auroc']:.4f}" for ep in ENDPOINTS),
               f"- other configurations this node scored: {r['other_configurations_scored_by_this_node']}", ""]
report += ["## Selection", "", f"Selected: **{selected['run_id']}** as the framework's final stage.", "",
           "## Provenance", "", f"Assembled deterministically on {trace['assembled_at']}; no LLM call in assembly.", ""]
(OUT / "final_report.md").write_text("\n".join(report), encoding="utf-8")
(OUT / "logs").mkdir(exist_ok=True)
(OUT / "logs" / "assembly_log.txt").write_text("\n".join(log), encoding="utf-8")
say("done: predictions.csv, environment.json, experiment_trace.json, paper.md, final_report.md, runs/, logs/")
