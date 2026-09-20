from pathlib import Path
import json
import sys

workspace = Path(sys.argv[1])
expected_model = sys.argv[2]
required = ["research_idea.json", "estimator.py", "submission.json", "score.json", "experiment_trace.json", "final_report.md"]
missing = [name for name in required if not (workspace / name).is_file() or not (workspace / name).stat().st_size]
if missing:
    raise SystemExit("missing framework-native ARC handoff artifacts: " + ", ".join(missing))

def load(name: str) -> dict:
    try:
        value = json.loads((workspace / name).read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"invalid {name}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{name} must be a JSON object")
    return value

trace = load("experiment_trace.json")
if trace.get("framework_native_execution") is not True or trace.get("consumed_topic_input") is not True:
    raise SystemExit("experiment_trace.json must prove framework-native ARC execution and topic input consumption")
if trace.get("workspace_trace_root") != "/workspace":
    raise SystemExit("experiment_trace.json must set workspace_trace_root=/workspace")
experiments = trace.get("experiments")
if not isinstance(experiments, list) or not 2 <= len(experiments) <= 4:
    raise SystemExit("experiment_trace.json must record 2-4 experiments")
if not isinstance(trace.get("selected_experiment_id"), str) or not trace["selected_experiment_id"].strip():
    raise SystemExit("experiment_trace.json must identify selected_experiment_id")
if trace.get("framework_internal_model") != expected_model:
    raise SystemExit(f"experiment_trace.json must set framework_internal_model={expected_model}")
if not isinstance(trace.get("framework_internal_api_base_url"), str) or not trace["framework_internal_api_base_url"].strip():
    raise SystemExit("experiment_trace.json must record framework_internal_api_base_url")
if trace.get("idea_artifact") != "research_idea.json":
    raise SystemExit("experiment_trace.json must set idea_artifact=research_idea.json")
if trace.get("idea_locked_before_experiments") is not True:
    raise SystemExit("experiment_trace.json must prove the idea was locked before experiments")
idea = load("research_idea.json")

def nonempty_idea_field(value):
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value) and all(isinstance(item, str) and item.strip() for item in value) if isinstance(value, list) else True
    return False

for key in ("hypothesis", "method_rationale", "expected_failure_modes", "comparison_logic"):
    field = idea.get(key)
    if not nonempty_idea_field(field) and key == "method_rationale":
        field = idea.get("rationale")
    if not nonempty_idea_field(field):
        raise SystemExit(f"research_idea.json must contain non-empty {key}")
score = load("score.json")
if score.get("score_source") != "official_adapter_whest_run":
    raise SystemExit("ARC score.json must be produced by the official_adapter_whest_run scorer")
load("submission.json")
