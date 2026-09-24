# Verbatim host validation block of real_eval/scripts/mountaincar_framework_fullrun.sh (2026-09-24).
# usage: mountaincar_host_validate.py <workspace> <expected_model> <expected_base_url>
from pathlib import Path
import json, re, sys
workspace = Path(sys.argv[1])
expected_model = sys.argv[2]
expected_base_url = sys.argv[3].rstrip("/")
required = ["research_idea.json", "experiment_trace.json", "final_report.md", "evaluate.py"]
missing = [n for n in required if not (workspace / n).is_file() or not (workspace / n).stat().st_size]
if missing:
    raise SystemExit("missing framework-native MountainCar artifacts before scoring: " + ", ".join(missing))
if not (workspace / "src" / "config.yaml").is_file():
    raise SystemExit("missing src/config.yaml")
ckpt_dir = workspace / "checkpoints"
ckpts = sorted(ckpt_dir.glob("*.pkl")) if ckpt_dir.is_dir() else []
if len(ckpts) != 5:
    raise SystemExit(f"expected exactly 5 checkpoints, found {len(ckpts)}")
def load(name):
    try:
        v = json.loads((workspace / name).read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"invalid {name}: {e}") from e
    if not isinstance(v, dict):
        raise SystemExit(f"{name} must be a JSON object")
    return v
trace = load("experiment_trace.json")
if trace.get("framework_native_execution") is not True or trace.get("consumed_topic_input") is not True:
    raise SystemExit("experiment_trace.json must prove native execution and topic input consumption")
if trace.get("workspace_trace_root") != "/workspace":
    raise SystemExit("experiment_trace.json must set workspace_trace_root=/workspace")
experiments = trace.get("experiments")
if not isinstance(experiments, list) or not 2 <= len(experiments) <= 4:
    raise SystemExit("experiment_trace.json must record 2-4 experiments")
ids = []
for row in experiments:
    eid = row.get("experiment_id") or row.get("id") if isinstance(row, dict) else None
    if not isinstance(eid, str) or not eid.strip():
        raise SystemExit("every experiment must have a non-empty experiment_id")
    ids.append(eid.strip())
if len(set(ids)) != len(ids):
    raise SystemExit("experiment_id values must be unique")
selected = trace.get("selected_experiment_id")
if not isinstance(selected, str) or selected.strip() not in ids:
    raise SystemExit("selected_experiment_id must match an experiment record")
if trace.get("framework_internal_model") != expected_model:
    raise SystemExit(f"experiment_trace.json must set framework_internal_model={expected_model}")
actual_url = trace.get("framework_internal_api_base_url")
if not isinstance(actual_url, str) or actual_url.rstrip("/") != expected_base_url:
    raise SystemExit("experiment_trace.json must set framework_internal_api_base_url")
if trace.get("idea_artifact") != "research_idea.json" or trace.get("idea_locked_before_experiments") is not True:
    raise SystemExit("experiment_trace.json must prove the idea was locked before experiments")
idea = load("research_idea.json")
for key in ("hypothesis", "method_rationale", "expected_failure_modes", "comparison_logic"):
    val = idea.get(key) or (idea.get("rationale") if key == "method_rationale" else None)
    if not val or (isinstance(val, str) and not val.strip()):
        raise SystemExit(f"research_idea.json must contain non-empty {key}")
print("HOST_VALIDATION_PASSED")
