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
PS4='NATIVE_CMD> '
set -x
timeout "${MOUNTAINCAR_CONTINUOUS_INFER_TIMEOUT_SECONDS:-7000}s" python3 research_agent/run_infer_idea.py \
  --instance_path benchmark/final/mountaincar_continuous/mountaincar_continuous.json \
  --container_name mountaincar_ai_researcher \
  --model "$OPENAI_MODEL" \
  --workplace_name . \
  --cache_path cache_mountaincar_continuous \
  --port 12374 \
  --max_iter_times 1 \
  --category mountaincar_continuous
set +x
# The contract asks for five checkpoints at /workspace/checkpoints, but the
# agent produces them inside its own workplace. Relocate verbatim; never author.
python3 - <<'PYRELOC'
import json
import shutil
from pathlib import Path

target = Path("/workspace/checkpoints")
target.mkdir(parents=True, exist_ok=True)
existing = sorted(p.name for p in target.glob("config-42-*.pkl"))
if len(existing) >= 5:
    print(f"[mcar-handoff] checkpoints already at workspace root: {existing}")
else:
    found = sorted(
        Path("/workspace").glob("**/workplace/**/checkpoints/config-42-*.pkl")
    ) or sorted(Path("/workspace").glob("**/checkpoints/config-42-*.pkl"))
    moved = []
    for source in found:
        if source.parent == target:
            continue
        shutil.copy2(source, target / source.name)
        moved.append(str(source))
    print(f"[mcar-handoff] relocated {len(moved)} checkpoint(s)")
    if moved:
        Path("/workspace/handoff_relocation.json").write_text(
            json.dumps({"topic": "mountaincar_continuous", "relocated": moved}, indent=2) + "\n",
            encoding="utf-8",
        )
PYRELOC
EOF
)
exec "$ROOT/real_eval/scripts/mountaincar_framework_fullrun.sh"
