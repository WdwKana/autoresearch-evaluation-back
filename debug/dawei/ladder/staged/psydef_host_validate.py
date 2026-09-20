from __future__ import annotations

import json
import sys
from pathlib import Path

workspace = Path(sys.argv[1])
expected_model = sys.argv[2]
required_paths = {
    "research_idea": workspace / "research_idea.json",
    "final_report": workspace / "final_report.md",
    "score": workspace / "score.json",
    "experiment_trace": workspace / "experiment_trace.json",
}
prediction_candidates = [workspace / "predictions.jsonl", workspace / "submission.csv"]
missing = [name for name, path in required_paths.items() if not path.exists()]
if not any(path.exists() for path in prediction_candidates):
    missing.append("prediction_artifact")
if missing:
    raise SystemExit("missing required artifacts: " + ", ".join(missing))

trace = json.loads((workspace / "experiment_trace.json").read_text(encoding="utf-8"))
if not isinstance(trace, dict):
    raise SystemExit("experiment_trace.json must be a JSON object")
idea = json.loads((workspace / "research_idea.json").read_text(encoding="utf-8"))
if not isinstance(idea, dict):
    raise SystemExit("research_idea.json must be a JSON object")
if not isinstance(idea, dict) or not idea:
    raise SystemExit("research_idea.json must be a non-empty JSON object")
if (workspace / "research_idea.json").stat().st_mtime_ns >= (
    workspace / "experiment_trace.json"
).stat().st_mtime_ns:
    raise SystemExit("research_idea.json must be locked before experiment_trace.json")
if trace.get("framework_native_execution") is not True:
    raise SystemExit("experiment_trace.json must set framework_native_execution=true")
if trace.get("consumed_topic_input") is not True:
    raise SystemExit("experiment_trace.json must set consumed_topic_input=true")
experiments = trace.get("experiments")
if not isinstance(experiments, list) or len(experiments) < 2:
    raise SystemExit("experiment_trace.json must record at least 2 experiments")
if len(experiments) > 4:
    raise SystemExit("experiment_trace.json may record at most 4 experiments")
if trace.get("framework_internal_model") != expected_model:
    raise SystemExit(f"experiment_trace.json must set framework_internal_model={expected_model}")
if not isinstance(trace.get("framework_internal_api_base_url"), str) or not trace["framework_internal_api_base_url"].strip():
    raise SystemExit("experiment_trace.json must include framework_internal_api_base_url")
selected_experiment_id = trace.get("selected_experiment_id")
if (
    isinstance(selected_experiment_id, bool)
    or not isinstance(selected_experiment_id, (str, int))
    or (isinstance(selected_experiment_id, str) and not selected_experiment_id.strip())
):
    raise SystemExit("experiment_trace.json must include selected_experiment_id")
if not isinstance(trace.get("workspace_trace_root"), str) or not trace["workspace_trace_root"].strip():
    raise SystemExit("experiment_trace.json must include workspace_trace_root")
