#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
AI_SCIENTIST_MODEL="${REAL_EVAL_FRAMEWORK_MODEL:-${REAL_EVAL_MODEL:-kimi-k2.6}}"
export FRAMEWORK_NAME="AI-Scientist-v2"
export FRAMEWORK_SLUG="02_ai_scientist_v2_arc_wbe_2026_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 02)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
AI-Scientist-v2/ai_scientist/ideas/arc_wbe_2026_topic.md
docs/arc_wbe_2026_summary.md
automation/arc_wbe_2026_contract.md
automation/arc_wbe_2026_execution_budget.md
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="ai-scientist-v2:runtime-ready"
export FRAMEWORK_NATIVE_ENTRYPOINT="perform_ideation_temp_free.py; launch_scientist_bfts.py"
export FRAMEWORK_KIMI_INJECTION="ai_scientist.llm OpenAI client configured from OPENAI_API_KEY and OPENAI_BASE_URL"
export FRAMEWORK_NATIVE_LOG_MARKER="AI_SCIENTIST_V2_NATIVE_BFTS"
export FRAMEWORK_EXECUTOR_KIND="framework_cli"
export FRAMEWORK_COMMAND_LABEL="python ai_scientist/perform_ideation_temp_free.py; python launch_scientist_bfts.py"
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
echo "AI_SCIENTIST_V2_NATIVE_BFTS"
python3 - ai_scientist/llm.py "$OPENAI_MODEL" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
model = sys.argv[2]
text = path.read_text(encoding="utf-8")
if f'"{model}"' not in text:
    text = text.replace("AVAILABLE_LLMS = [", f"AVAILABLE_LLMS = [\n    \"{model}\",", 1)
text = text.replace('elif "gpt" in model:', 'elif "gpt" in model or model == "' + model + '":')
text = text.replace(
    'return openai.OpenAI(), model',
    'return openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url=os.environ["OPENAI_BASE_URL"]), model',
)
path.write_text(text, encoding="utf-8")
PY
python3 - ai_scientist/utils/token_tracker.py <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
text = text.replace(
    "result.usage.completion_tokens_details.reasoning_tokens,",
    "result.usage.completion_tokens_details.reasoning_tokens or 0,",
)
text = text.replace(
    "result.usage.prompt_tokens_details.cached_tokens\n",
    "result.usage.prompt_tokens_details.cached_tokens or 0\n",
)
path.write_text(text, encoding="utf-8")
PY
rm -f ai_scientist/ideas/arc_wbe_2026_topic.json
timeout "${AI_SCIENTIST_V2_ARC_IDEATION_TIMEOUT_SECONDS:-1800}s" python ai_scientist/perform_ideation_temp_free.py \
  --workshop-file ai_scientist/ideas/arc_wbe_2026_topic.md \
  --model "$OPENAI_MODEL" \
  --max-num-generations 1 \
  --num-reflections 2
test -s ai_scientist/ideas/arc_wbe_2026_topic.json
python3 - bfts_config.yaml "$OPENAI_MODEL" <<'PY'
from pathlib import Path
import sys
import yaml

path = Path(sys.argv[1])
model = sys.argv[2]
config = yaml.safe_load(path.read_text(encoding="utf-8"))
config["exp_name"] = "arc_wbe_2026"
config["generate_report"] = False
config["agent"]["num_workers"] = 1
config["agent"]["steps"] = 2
config["agent"]["expose_prediction"] = True
for section in ("code", "feedback", "vlm_feedback"):
    config["agent"][section]["model"] = model
config["report"]["model"] = model
path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
PY
timeout "${ARC_WBE_2026_FRAMEWORK_TIMEOUT_SECONDS:-3600}s" python launch_scientist_bfts.py \
  --load_ideas ai_scientist/ideas/arc_wbe_2026_topic.json \
  --idea_idx 0 \
  --skip_writeup \
  --skip_review \
  --model_agg_plots "$OPENAI_MODEL"
EOF
)
exec "$ROOT"/real_eval/scripts/arc_framework_fullrun.sh
