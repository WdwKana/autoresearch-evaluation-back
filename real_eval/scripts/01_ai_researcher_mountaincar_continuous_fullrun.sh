#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
FRAMEWORK_MODEL_RAW="${REAL_EVAL_FRAMEWORK_MODEL:-${REAL_EVAL_MODEL:-gpt-5.4}}"
export FRAMEWORK_NAME="AI-Researcher"
export FRAMEWORK_SLUG="01_ai_researcher_mountaincar_continuous_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 01)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
AI-Researcher/benchmark/final/mountaincar_continuous/mountaincar_continuous.json
AI-Researcher/benchmark/process/dataset_candidate/mountaincar_continuous/metaprompt.py
real_eval/adapters/mountaincar_continuous/patch_ai_researcher.py
real_eval/adapters/ai_researcher/patch_idea_loop_fixes.py
real_eval/adapters/ai_researcher/patch_prepare_bypass.py
real_eval/adapters/ai_researcher/patch_empty_input_truth.py
real_eval/adapters/ai_researcher/patch_loop_guard.py
real_eval/adapters/ai_researcher/patch_budget_clock.py
real_eval/adapters/ai_researcher/patch_browser_tool_timeout.py
real_eval/adapters/ai_researcher/patch_nested_gpu_isolation.py
real_eval/adapters/ai_researcher/patch_nested_cpu_isolation.py
real_eval/adapters/ai_researcher/patch_resource_visibility.py
real_eval/adapters/ai_researcher/patch_logger_resilience.py
real_eval/adapters/ai_researcher/patch_tool_args_resilience.py
real_eval/adapters/ai_researcher/patch_file_browser_text.py
real_eval/adapters/ai_researcher/patch_file_browser_paging.py
real_eval/adapters/ai_researcher/patch_exec_env_provision.py
real_eval/adapters/ai_researcher/patch_ml_delivery_validation.py
real_eval/adapters/ai_researcher/patch_request_probe.py
real_eval/adapters/ai_researcher/patch_response_probe.py
real_eval/adapters/ai_researcher/patch_reasoning_effort_fallback.py
real_eval/adapters/ai_scientist_v2/exit_delivery_check.py
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="ai-researcher:runtime-ready"
export FRAMEWORK_DISABLE_GPU="1"
export FRAMEWORK_NATIVE_ENTRYPOINT="python research_agent/run_infer_idea.py"
export FRAMEWORK_KIMI_INJECTION="OPENAI_BASE_URL, OPENAI_API_KEY, and OPENAI_MODEL resolve to the isolated provider"
export FRAMEWORK_NATIVE_LOG_MARKER="AI_RESEARCHER_NATIVE_INFER_IDEA"
export FRAMEWORK_EXECUTOR_KIND="framework_cli"
export FRAMEWORK_COMMAND_LABEL="python research_agent/run_infer_idea.py"
# NOTE: refine this per-framework native launch command during smoke testing.
# The image caches the sentence-transformers model the tools package loads at
# import time, but under HOME=/workspace huggingface_hub looks in
# /workspace/.cache and fails closed with HF_HUB_OFFLINE=1 -- run
# fullrun_mcar_01_20260828_142007 (retained) died there before reaching any
# research work. Point HF at the cache the image actually ships, exactly as the
# TDC wrapper does.
MC_MODEL="${MOUNTAINCAR_CONTINUOUS_MODEL:-${REAL_EVAL_FRAMEWORK_MODEL:-${REAL_EVAL_MODEL:-}}}"
export FRAMEWORK_DOCKER_ARGS=$(cat <<EOF
-e
HF_HOME=/root/.cache/huggingface
-e
HF_HUB_OFFLINE=1
-e
TRANSFORMERS_OFFLINE=1
-e
OPENAI_MODEL=$MC_MODEL
-e
COMPLETION_MODEL=openai/$MC_MODEL
-e
CHEEP_MODEL=openai/$MC_MODEL
-e
AI_RESEARCHER_PREPARE_BYPASS=1
-e
AI_RESEARCHER_ML_DELIVERY_GLOBS=networks.py,config-*.pkl,*.py
-e
AI_RESEARCHER_MAX_TURNS=300
-e
AI_RESEARCHER_TOTAL_BUDGET_SECONDS=${MOUNTAINCAR_CONTINUOUS_INFER_TIMEOUT_SECONDS:-7000}
-e
AI_RESEARCHER_LOOP_GUARD_LIMIT=8
-e
AI_RESEARCHER_EXEC_PIP=
-e
AI_RESEARCHER_REQUEST_PROBE=1
-e
AI_RESEARCHER_PROBE_LOG=/workspace/request_probe.jsonl
-e
MOUNTAINCAR_CONTINUOUS_INFER_TIMEOUT_SECONDS=${MOUNTAINCAR_CONTINUOUS_INFER_TIMEOUT_SECONDS:-7000}
-e
AI_RESEARCHER_RESPONSE_PROBE_LOG=/workspace/response_probe.jsonl
EOF
)

export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
echo "AI_RESEARCHER_NATIVE_INFER_IDEA"
export PYTHONPATH=/workspace:/workspace/research_agent/inno/tools:${PYTHONPATH:-}
# The framework source is rsynced to /workspace itself; the staged inputs land
# under /workspace/AI-Researcher. Put the freshly generated instance record and
# metaprompt where the framework actually reads them.
if [ -d /workspace/AI-Researcher/benchmark ]; then
  cp -r /workspace/AI-Researcher/benchmark/. /workspace/benchmark/
fi
python3 real_eval/adapters/mountaincar_continuous/patch_ai_researcher.py
# New framework-fix stack (same adapters as ARC; mcar delivery globs).
python3 real_eval/adapters/ai_researcher/patch_idea_loop_fixes.py
python3 real_eval/adapters/ai_researcher/patch_prepare_bypass.py
python3 real_eval/adapters/ai_researcher/patch_empty_input_truth.py
python3 real_eval/adapters/ai_researcher/patch_loop_guard.py
python3 real_eval/adapters/ai_researcher/patch_budget_clock.py
python3 real_eval/adapters/ai_researcher/patch_browser_tool_timeout.py
python3 real_eval/adapters/ai_researcher/patch_nested_gpu_isolation.py
python3 real_eval/adapters/ai_researcher/patch_nested_cpu_isolation.py
python3 real_eval/adapters/ai_researcher/patch_resource_visibility.py
python3 real_eval/adapters/ai_researcher/patch_logger_resilience.py
python3 real_eval/adapters/ai_researcher/patch_tool_args_resilience.py
python3 real_eval/adapters/ai_researcher/patch_file_browser_text.py
python3 real_eval/adapters/ai_researcher/patch_file_browser_paging.py
python3 real_eval/adapters/ai_researcher/patch_exec_env_provision.py
python3 real_eval/adapters/ai_researcher/patch_ml_delivery_validation.py
python3 real_eval/adapters/ai_researcher/patch_request_probe.py
python3 real_eval/adapters/ai_researcher/patch_response_probe.py
python3 real_eval/adapters/ai_researcher/patch_reasoning_effort_fallback.py
PS4='NATIVE_CMD> '
set -x
timeout "${MOUNTAINCAR_CONTINUOUS_INFER_TIMEOUT_SECONDS:-7000}s" python3 research_agent/run_infer_idea.py \
  --instance_path benchmark/final/mountaincar_continuous/mountaincar_continuous.json \
  --container_name mountaincar_ai_researcher \
  --model "$OPENAI_MODEL" \
  --workplace_name workplace \
  --cache_path cache_mountaincar_continuous \
  --port 12374 \
  --max_iter_times 1 \
  --category mountaincar_continuous || echo "[mcar] native infer exited non-zero (rc=$?, e.g. timeout 124) -- proceeding to handoff+score"
set +x
# The contract asks for five checkpoints at /workspace/checkpoints, but the
# agent produces them inside its own workplace. Relocate verbatim; never author.
#
# A checkpoint is only evaluable together with the src/ (networks.py, config.yaml,
# helpers.py) it was trained with. The agent may leave several checkpoint sets
# (fullrun_mcar_01_luna_20260903_153128 left workplace/checkpoints and
# workplace/project/checkpoints, each with its own networks.py); copying every
# config-42-*.pkl it can find mixes the sets and leaves the host's starter src/
# at the root, so the frozen evaluator fails with a parameter-shape mismatch even
# though each set scores on its own. So: pick ONE set (newest complete one) and
# carry its code with it -- every src/ on the path from the workplace root down
# to that set, outer first, inner wins, files copied verbatim.
# MCAR_HANDOFF_WORKSPACE exists only so this block can be replayed offline
# against a retained run tree; inside the container it is always /workspace.
python3 - <<'PYRELOC'
import json
import os
import shutil
from pathlib import Path

ws = Path(os.environ.get("MCAR_HANDOFF_WORKSPACE", "/workspace"))
target = ws / "checkpoints"
target.mkdir(parents=True, exist_ok=True)
NAMES = [f"config-42-{i}.pkl" for i in range(5)]
existing = sorted(p.name for p in target.glob("config-42-*.pkl"))
moved = []
provenance = {}
if len(existing) >= 5:
    print(f"[mcar-handoff] checkpoints already at workspace root: {existing}")
else:
    found = list(ws.glob("**/workplace/**/checkpoints/config-42-*.pkl")) or list(
        ws.glob("**/checkpoints/config-42-*.pkl")
    )
    sets = {}
    for source in found:
        if source.parent == target or not source.is_file():
            continue
        sets.setdefault(source.parent, []).append(source)
    complete = [d for d, files in sets.items() if sorted(f.name for f in files) == NAMES]
    pool = complete or list(sets)
    if not pool:
        print("[mcar-handoff] no framework-produced checkpoints found")
    else:
        chosen = max(pool, key=lambda d: max(f.stat().st_mtime for f in sets[d]))
        print(
            f"[mcar-handoff] {len(sets)} checkpoint set(s) found, {len(complete)} complete; "
            f"using newest: {chosen}"
        )
        for source in sorted(sets[chosen]):
            shutil.copy2(source, target / source.name)
            moved.append(str(source))
        print(f"[mcar-handoff] relocated {len(moved)} checkpoint(s)")
        provenance["checkpoint_set"] = str(chosen)
        set_root = chosen.parent
        chain = [a for a in [set_root, *set_root.parents] if a != ws and ws in a.parents]
        overlay = []
        for ancestor in reversed(chain):  # outermost first, innermost wins
            src_dir = ancestor / "src"
            if not src_dir.is_dir():
                continue
            for f in sorted(src_dir.rglob("*")):
                if not f.is_file() or "__pycache__" in f.parts:
                    continue
                dest = ws / "src" / f.relative_to(src_dir)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
                overlay.append(str(f))
        print(f"[mcar-handoff] overlaid {len(overlay)} src file(s) from the chosen set's code")
        moved.extend(overlay)
        provenance["src_overlay"] = overlay

# The gate also requires research_idea.json, experiment_trace.json and
# final_report.md at the workspace root; the agent writes them inside its own
# workplace (run fullrun_mcar_01_20260828_142606 had a complete PPO trace there
# while the root had none). Relocate verbatim, newest wins, never author.
for name in ("research_idea.json", "experiment_trace.json", "final_report.md"):
    target = ws / name
    if target.is_file() and target.stat().st_size:
        continue
    candidates = [c for c in ws.rglob(name) if c != target and c.is_file() and c.stat().st_size]
    if not candidates:
        print(f"[mcar-handoff] no framework-authored {name} found")
        continue
    newest = max(candidates, key=lambda c: c.stat().st_mtime)
    shutil.copy2(newest, target)
    moved.append(str(newest))
    print(f"[mcar-handoff] relocated {name} from {newest}")

if moved:
    (ws / "handoff_relocation.json").write_text(
        json.dumps({"topic": "mountaincar_continuous", "relocated": moved, **provenance}, indent=2) + "\n",
        encoding="utf-8",
    )
PYRELOC
EOF
)
exec "$ROOT/real_eval/scripts/mountaincar_framework_fullrun.sh"
