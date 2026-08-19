#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
export FRAMEWORK_NAME="DeepScientist"
export FRAMEWORK_SLUG="05_deepscientist_babylm_gpt_fullrun"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 05)"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
automation/babylm_method_free_contract.md
EOF
)
export FRAMEWORK_ENTRYPOINT="bash"
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="deepscientist:runtime-ready"
export FRAMEWORK_NATIVE_ENTRYPOINT="ds new + ds run (headless)"
export FRAMEWORK_PROVIDER_INJECTION="DeepScientist reads CODEX_HOME config from /home/agent/.codex/config.toml"
export FRAMEWORK_NATIVE_LOG_MARKER="DEEPSCIENTIST_BABYLM_GPT_NATIVE"
export FRAMEWORK_EXECUTOR_KIND="framework_internal_codex_runner"
export FRAMEWORK_COMMAND_LABEL="ds new research goal + ds run experiment skill"
export FRAMEWORK_DOCKER_ARGS=$(cat <<'EOF'
--user
0:0
-v
/var/run/docker.sock:/var/run/docker.sock
EOF
)
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
echo "DEEPSCIENTIST_BABYLM_GPT_NATIVE"
export HOME=/home/agent
mkdir -p /home/agent/.codex
export DEEPSCIENTIST_SOURCE_CODEX_CONFIG="${CODEX_HOME:?CODEX_HOME is required}/config.toml"
python3 -c "
import shutil, os
shutil.copy2(os.environ['DEEPSCIENTIST_SOURCE_CODEX_CONFIG'], '/home/agent/.codex/config.toml')
os.chmod('/home/agent/.codex', 0o700)
os.chmod('/home/agent/.codex/config.toml', 0o600)
os.chown('/home/agent/.codex', 1001, 1001)
os.chown('/home/agent/.codex/config.toml', 1001, 1001)
" 2>/dev/null || echo "WARNING: Could not set up Codex config"
export CODEX_HOME=/home/agent/.codex
mkdir -p /workspace/DeepScientist
echo "DEEPSCIENTIST_BABYLM_GPT_NATIVE: Starting daemon..."
# Start daemon in background
ds --here --daemon-only --port 20999 &
DS_PID=$!
# Wait for daemon to be ready
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:20999/health >/dev/null 2>&1; then
    echo "Daemon ready after ${i}s"
    break
  fi
  sleep 2
done
echo "DEEPSCIENTIST_BABYLM_GPT_NATIVE: Submitting research via API..."
# Submit research via daemon REST API
curl -s -X POST http://127.0.0.1:20999/api/quests \
  -H "Content-Type: application/json" \
  -d "{\"goal\": \"BabyLM Strict-Small: Run 2-4 materially different experiments on BabyLM Strict-Small under the official 2026 rules. The framework must own idea formation, method selection, experiment design, execution, comparison, selection, analysis, and final artifact delivery. The host does not prescribe an algorithm, architecture, hyperparameter, baseline, or experiment order. Use dataset at /data/BabyLM-2026-Strict-Small (only .txt files, no separate validation set -- split train/val yourself, do not silently catch file errors, verify non-empty). Write and lock research_idea.json before the first experiment. Compare by word-level validation perplexity, select the best, and write research_idea.json, experiment_trace.json (strict JSON, no NaN, use experiments array with idea_artifact/idea_locked_before_experiments), and final_report.md to /workspace.\"}" 2>&1 || true
echo ""
echo "DEEPSCIENTIST_BABYLM_GPT_NATIVE: Waiting for research to complete..."
# Poll for completion
for i in $(seq 1 60); do
  sleep 30
  STATUS=$(curl -sf http://127.0.0.1:20999/api/quests 2>/dev/null || echo "")
  if echo "$STATUS" | grep -q '"status":"completed"'; then
    echo "Research completed!"
    break
  fi
  echo "Waiting... ($i/60)"
done
echo "DEEPSCIENTIST_BABYLM_GPT_NATIVE: Stopping daemon..."
kill $DS_PID 2>/dev/null || true
wait $DS_PID 2>/dev/null || true
EOF
)
exec "$ROOT"/real_eval/scripts/babylm_framework_fullrun.sh
