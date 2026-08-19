#!/usr/bin/env bash
set -euo pipefail

ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
FRAMEWORK_MODEL_RAW="${REAL_EVAL_FRAMEWORK_MODEL:-${REAL_EVAL_MODEL:-gpt-5.4}}"
AI_RESEARCHER_COMPLETION_MODEL="${AI_RESEARCHER_COMPLETION_MODEL:-openai/${FRAMEWORK_MODEL_RAW}}"
AI_RESEARCHER_CHEAP_MODEL="${AI_RESEARCHER_CHEAP_MODEL:-$AI_RESEARCHER_COMPLETION_MODEL}"
RUN_ID="${REAL_EVAL_RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
BASE="${REAL_EVAL_RUN_ROOT:?REAL_EVAL_RUN_ROOT is required}"
SRC="${RESEARCHCLAWEVAL_AI_RESEARCHER_ROOT:-$(real_eval_resolve_framework_source "$ROOT" 01)}"
WORKSPACE="$BASE/workspace"
REPO="$WORKSPACE/AI-Researcher"
INPUT_ROOT="$BASE/inputs"
FRAMEWORK_DATASET_ROOT="$INPUT_ROOT/arc_wbe_2026_weights_only"
LOG_DIR="$BASE/logs"
LOG_FILE="$BASE/logs/e2e.log"
STATE_FILE="$BASE/state.json"
MANIFEST_FILE="$BASE/fullrun_manifest.json"
DATASET_ROOT="${ARC_WBE_2026_DATASET_ROOT:-$(real_eval_resolve_topic_dataset "$ROOT" arc_wbe_2026)}"
CONTRACT_FILE="${ARC_WBE_2026_CONTRACT_FILE:-$ROOT/automation/arc_wbe_2026_contract.md}"
PROVIDER_CONFIG="${PROVIDER_CONFIG:-$ROOT/api/codex_gpt54_shubiaobiao.toml}"
SEMANTIC_SOURCE="${SEMANTIC_SOURCE:-$ROOT/api/_semantic_scholar_api_usage.md}"
PROVIDER_ENV="$BASE/provider.env"
SEMANTIC_ENV="$BASE/semantic.env"
OUTER_IMAGE="ai-researcher:runtime-ready"
OUTER_CONTAINER_NAME="ai_researcher_arc_wbe_2026_outer_${RUN_ID}"
INNER_CONTAINER_NAME="arc_wbe_2026_eval_${RUN_ID}"
TOPIC_INSTANCE_REL="AI-Researcher/benchmark/final/arc_wbe_2026/arc_wbe_2026.json"
TOPIC_METAPROMPT_REL="AI-Researcher/benchmark/process/dataset_candidate/arc_wbe_2026/metaprompt.py"
TOPIC_SUMMARY_REL="docs/arc_wbe_2026_summary.md"
TOPIC_CONTRACT_REL="automation/arc_wbe_2026_contract.md"
TOPIC_BUDGET_REL="automation/arc_wbe_2026_execution_budget.md"
SCORE_SOURCE_ARTIFACT="${ARC_WBE_2026_LOCAL_SCORE_ARTIFACT:-}"

cleanup_containers() {
  docker ps -a --format '{{.Names}}' | rg "^(${OUTER_CONTAINER_NAME}|${INNER_CONTAINER_NAME})$" | xargs -r docker rm -f >/dev/null 2>&1 || true
}
trap cleanup_containers EXIT

write_state() {
  local status="$1"
  local summary="$2"
  local exit_code="${3:-0}"
  local command="${4:-}"
  python3 - "$STATE_FILE" "$status" "$summary" "$exit_code" "$command" <<'PY'
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

payload = {
    "project_id": "arc_wbe_2026",
    "phase": "fullrun",
    "status": sys.argv[2],
    "summary": sys.argv[3],
    "updated_at": datetime.now(timezone.utc).astimezone().isoformat(),
    "exit_code": int(sys.argv[4]),
}
if sys.argv[5]:
    payload["e2e_command"] = sys.argv[5]
Path(sys.argv[1]).write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
PY
}

real_eval_require_clean_dir "$BASE"
mkdir -p "$WORKSPACE" "$INPUT_ROOT" "$LOG_DIR"

[[ -d "$DATASET_ROOT" ]] || { echo "missing dataset root: $DATASET_ROOT" >&2; exit 21; }
[[ -f "$CONTRACT_FILE" ]] || { echo "missing contract file: $CONTRACT_FILE" >&2; exit 22; }
[[ -d "$SRC" ]] || { echo "missing framework source: $SRC" >&2; exit 23; }

write_state "starting" "Preparing AI-Researcher ARC-WBE-2026 fullrun workspace"

"${ARC_WBE_2026_WHEST_PYTHON:-/tmp/whest-starterkit/.venv/bin/python}" \
  "$ROOT/automation/scripts/generate_arc_wbe_2026_weights_only_dataset.py" \
  --source-root "$DATASET_ROOT" \
  --output-root "$FRAMEWORK_DATASET_ROOT"

python3 "$ROOT/automation/scripts/generate_arc_wbe_2026_native_inputs.py" \
  --output-root "$INPUT_ROOT" \
  --dataset-root /data/arc_wbe_2026 \
  --contract-file "$CONTRACT_FILE" >/dev/null

real_eval_rsync_repo "$SRC" "$REPO"
real_eval_purge_cross_topic_residue "$REPO" "arc_wbe_2026"
real_eval_provider_env_from_codex_toml "$PROVIDER_CONFIG" "$PROVIDER_ENV"
real_eval_semantic_env_from_usage_md "$SEMANTIC_SOURCE" "$SEMANTIC_ENV"

mkdir -p \
  "$REPO/benchmark/final/arc_wbe_2026" \
  "$REPO/benchmark/process/dataset_candidate/arc_wbe_2026" \
  "$WORKSPACE/docs" \
  "$WORKSPACE/automation"
cp "$INPUT_ROOT/$TOPIC_INSTANCE_REL" "$REPO/benchmark/final/arc_wbe_2026/arc_wbe_2026.json"
cp "$INPUT_ROOT/$TOPIC_METAPROMPT_REL" "$REPO/benchmark/process/dataset_candidate/arc_wbe_2026/metaprompt.py"
cp "$INPUT_ROOT/$TOPIC_SUMMARY_REL" "$WORKSPACE/docs/arc_wbe_2026_summary.md"
cp "$INPUT_ROOT/$TOPIC_CONTRACT_REL" "$WORKSPACE/automation/arc_wbe_2026_contract.md"
cp "$INPUT_ROOT/$TOPIC_BUDGET_REL" "$WORKSPACE/automation/arc_wbe_2026_execution_budget.md"
mkdir -p "$WORKSPACE/automation/scripts"
cp "$INPUT_ROOT/automation/scripts/run_arc_wbe_2026_local_score.py" "$WORKSPACE/automation/scripts/"
cp "$INPUT_ROOT/automation/scripts/arc_wbe_2026_official_adapter.py" "$WORKSPACE/automation/scripts/"
cp "$INPUT_ROOT/automation/scripts/prepare_arc_wbe_2026_dataset.py" "$WORKSPACE/automation/scripts/"

python3 - "$REPO/research_agent/inno/environment/utils.py" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
old = '''def setup_dataset(category: str, local_workplace: str):
    # 构建目标路径
    dataset_candidate_path = os.path.join(local_workplace, "dataset_candidate")
    
    # 检查目标目录是否存在
    if os.path.exists(dataset_candidate_path):
        print("dataset_candidate exists")
        return
    
    # 检查源目录是否存在
    source_path = f"../benchmark/process/dataset_candidate/{category}"
    if not os.path.exists(source_path):
        raise Exception(f"source path {source_path} not exists")
    
    try:
        # 复制整个目录内容到 dataset_candidate
        shutil.copytree(source_path, dataset_candidate_path)
        print(f"copy {source_path} to {dataset_candidate_path} success")
    except Exception as e:
        raise Exception(f"copy {source_path} to {dataset_candidate_path} failed: {str(e)}")
'''
new = '''def setup_dataset(category: str, local_workplace: str):
    dataset_candidate_path = os.path.join(local_workplace, "dataset_candidate")
    if os.path.exists(dataset_candidate_path):
        print("dataset_candidate exists")
        return

    repo_root = Path(__file__).resolve().parents[3]
    source_path = repo_root / "benchmark" / "process" / "dataset_candidate" / category
    if not source_path.exists():
        raise Exception(f"source path {source_path} not exists")

    if category == "arc_wbe_2026":
        real_dataset = os.getenv("RESEARCHCLAWEVAL_TOPIC_DATASET_ROOT")
        if not real_dataset or not os.path.isdir(real_dataset):
            raise Exception(f"ARC dataset root not available: {real_dataset}")
        try:
            os.makedirs(dataset_candidate_path, exist_ok=True)
            shutil.copy2(source_path / "metaprompt.py", os.path.join(dataset_candidate_path, "metaprompt.py"))
            copied_dataset = os.path.join(dataset_candidate_path, "arc_wbe_2026")
            shutil.copytree(real_dataset, copied_dataset)
            project_dir = os.path.join(local_workplace, "project")
            target = os.path.join(project_dir, "data", "arc_wbe_2026")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if not os.path.exists(target):
                shutil.copytree(real_dataset, target)
            print(f"copy ARC dataset {real_dataset} to {dataset_candidate_path} success")
            return
        except Exception as e:
            raise Exception(f"copy ARC dataset to {dataset_candidate_path} failed: {str(e)}")

    try:
        shutil.copytree(source_path, dataset_candidate_path)
        print(f"copy {source_path} to {dataset_candidate_path} success")
    except Exception as e:
        raise Exception(f"copy {source_path} to {dataset_candidate_path} failed: {str(e)}")
'''
if old not in s:
    raise SystemExit("setup_dataset block not found")
patched = s.replace(old, new)
if "from pathlib import Path" not in patched:
    patched = "from pathlib import Path\n" + patched
p.write_text(patched, encoding="utf-8")
PY

python3 - "$REPO/research_agent/inno/tools/__init__.py" "$REPO/research_agent/constant.py" "$REPO/research_agent/inno/environment/markdown_browser/mdconvert.py" "$REPO/research_agent/inno/environment/markdown_browser/requests_markdown_browser.py" "$REPO/research_agent/run_infer_idea.py" <<'PY'
from pathlib import Path
import sys

tools = Path(sys.argv[1])
text = tools.read_text(encoding="utf-8")
old = "import_tools_recursively(current_dir, 'inno.tools')"
new = '''for module_name in (
    "terminal_tools",
    "inner",
    "inno_tools.planning_tools",
    "inno_tools.web_tools",
):
    importlib.import_module(f"research_agent.inno.tools.{module_name}")'''
if old not in text:
    raise SystemExit("tool registration insertion point not found")
text = text.replace(old, new)
tools.write_text(text, encoding="utf-8")
constants = Path(sys.argv[2])
text = constants.read_text(encoding="utf-8")
if "PLATFORM =" not in text:
    constants.write_text(text + "\nPLATFORM = 'linux/amd64'\n", encoding="utf-8")
mdconvert = Path(sys.argv[3])
text = mdconvert.read_text(encoding="utf-8")
old = "from docling.document_converter import DocumentConverter as DocLingDocumentConverter"
new = '''try:
    from docling.document_converter import DocumentConverter as DocLingDocumentConverter
except ModuleNotFoundError:
    class DocLingDocumentConverter:
        def convert(self, *_args, **_kwargs):
            raise RuntimeError("docling is unavailable in this runtime")
'''
if old not in text:
    raise SystemExit("Docling import insertion point not found")
mdconvert.write_text(text.replace(old, new, 1), encoding="utf-8")
browser = Path(sys.argv[4])
text = browser.read_text(encoding="utf-8")
old = "        self._memory = PaperMemory(project_path=\"./paper_db\", db_name=\".paper_memory_\" + platform, platform=platform, api_key=os.getenv(\"OPENAI_API_KEY\"), embedding_model='text-embedding-3-small')"
new = '''        class _ArcNoopPaperMemory:
            def count(self, *_args, **_kwargs):
                return 1
            def add_paper_content(self, *_args, **_kwargs):
                return None
            def query_paper_content(self, *_args, **_kwargs):
                return []
        self._memory = _ArcNoopPaperMemory()'''
if old not in text:
    raise SystemExit("PaperMemory initialization insertion point not found")
browser.write_text(text.replace(old, new, 1), encoding="utf-8")
entrypoint = Path(sys.argv[5])
text = entrypoint.read_text(encoding="utf-8")
old = "    main(args)"
new = "    main(args, references=\"\")"
if old not in text:
    raise SystemExit("AI-Researcher main invocation insertion point not found")
text = text.replace(old, new, 1)
old = '        github_result = self.git_search({"metadata": metadata})'
new = '        github_result = "" if category == "arc_wbe_2026" else self.git_search({"metadata": metadata})'
if old not in text:
    raise SystemExit("AI-Researcher GitHub-search insertion point not found")
entrypoint.write_text(text.replace(old, new, 1), encoding="utf-8")
PY

python3 - "$REPO/research_agent/inno/environment/docker_env.py" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
old = '''        gpu_cmd = ["--gpus", GPUS] if GPUS else []
        docker_command = [
            "docker", "run", "-d", "--platform", PLATFORM, "--userns=host",] + gpu_cmd + ["--name", self.container_name, 
            "--user", "root", "-v", f"{self.local_workplace}:{self.docker_workplace}",
            "-w", f"{self.docker_workplace}", "-p", f"{self.communication_port}:8000", 
            "--restart", "unless-stopped", BASE_IMAGES
        ]'''
new = '''        gpu_cmd = ["--gpus", GPUS] if GPUS else []
        extra_mounts = []
        host_repo = os.getenv("RESEARCHCLAWEVAL_AI_RESEARCHER_HOST_REPO", "")
        local_workplace = self.local_workplace
        if host_repo and local_workplace.startswith("/workspace/AI-Researcher/"):
            local_workplace = os.path.join(host_repo, local_workplace.removeprefix("/workspace/AI-Researcher/"))
        host_dataset = os.getenv("RESEARCHCLAWEVAL_TOPIC_HOST_DATASET_ROOT", "")
        if host_dataset:
            extra_mounts.extend(["-v", f"{host_dataset}:/data/arc_wbe_2026:ro"])
        host_contract = os.getenv("RESEARCHCLAWEVAL_TOPIC_HOST_CONTRACT_FILE", "")
        if host_contract:
            extra_mounts.extend(["-v", f"{host_contract}:/input/contract.md:ro"])
        docker_command = [
            "docker", "run", "-d", "--platform", PLATFORM, "--userns=host",] + gpu_cmd + ["--name", self.container_name,
            "--user", "root", "-v", f"{local_workplace}:{self.docker_workplace}",
        ] + extra_mounts + [
            "-w", f"{self.docker_workplace}", "-p", f"{self.communication_port}:8000",
            "--restart", "unless-stopped", BASE_IMAGES
        ]'''
if old not in s:
    raise SystemExit("docker_command block not found")
s = s.replace(old, new)
s = s.replace(
    "assert port_info and (port_info[0] == port_info[1])",
    "assert port_info",
)
s = s.replace(
    "hostname = 'localhost'",
    "hostname = os.getenv('RESEARCHCLAWEVAL_DOCKER_HOST', 'localhost')",
)
p.write_text(s, encoding="utf-8")
PY

RUNTIME_COMMAND=$(cat <<EOF
set -euo pipefail
echo "AI_RESEARCHER_NATIVE_INFER_IDEA"
cd /workspace/AI-Researcher/research_agent
PORT=\$(python - <<'PY'
import socket
s = socket.socket()
s.bind(('127.0.0.1', 0))
print(s.getsockname()[1])
s.close()
PY
)
python run_infer_idea.py \
  --instance_path ../benchmark/final/arc_wbe_2026/arc_wbe_2026.json \
  --container_name ${INNER_CONTAINER_NAME} \
  --model $AI_RESEARCHER_COMPLETION_MODEL \
  --workplace_name workplace \
  --cache_path cache_${RUN_ID} \
  --port "\$PORT" \
  --max_iter_times 0 \
  --category arc_wbe_2026
EOF
)

python3 - "$MANIFEST_FILE" "$SRC" "$REPO" "$DATASET_ROOT" "$CONTRACT_FILE" "$OUTER_IMAGE" "$RUNTIME_COMMAND" <<'PY'
from pathlib import Path
import json
import sys

payload = {
    "framework": "AI-Researcher",
    "slug": "01_ai_researcher_arc_wbe_2026_fullrun",
    "source_root": sys.argv[2],
    "workspace_repo": sys.argv[3],
    "dataset_root": sys.argv[4],
    "contract_file": sys.argv[5],
    "runtime_image": sys.argv[6],
    "runtime_command": sys.argv[7],
    "entry_instance": "benchmark/final/arc_wbe_2026/arc_wbe_2026.json",
    "entry_metaprompt": "benchmark/process/dataset_candidate/arc_wbe_2026/metaprompt.py",
    "execution_mode": "framework_native",
    "framework_orchestration": True,
    "native_entrypoint": "research_agent/run_infer_idea.py",
    "kimi_injection": "COMPLETION_MODEL/CHEEP_MODEL with API_BASE_URL from injected environment",
    "native_log_marker": "AI_RESEARCHER_NATIVE_INFER_IDEA",
    "executor_kind": "framework_cli",
    "result_fields": ["score", "score_source", "score_artifact", "submission_artifact"],
}
Path(sys.argv[1]).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

{
  echo "[$(date -Is)] framework=AI-Researcher slug=01_ai_researcher_arc_wbe_2026_fullrun"
  echo "dataset_root=$DATASET_ROOT"
  echo "contract_file=$CONTRACT_FILE"
  echo "workspace_repo=$REPO"
  echo "entry_instance=benchmark/final/arc_wbe_2026/arc_wbe_2026.json"
  echo "entry_metaprompt=benchmark/process/dataset_candidate/arc_wbe_2026/metaprompt.py"
  echo "runtime_image=$OUTER_IMAGE"
  echo "native_entrypoint=research_agent/run_infer_idea.py"
  echo "kimi_injection=COMPLETION_MODEL/CHEEP_MODEL with API_BASE_URL from injected environment"
  echo "native_log_marker=AI_RESEARCHER_NATIVE_INFER_IDEA"
  echo "e2e_command=python run_infer_idea.py --category arc_wbe_2026"
} | tee "$LOG_FILE"

write_state "running" "Launching AI-Researcher ARC native execution" "0" "python run_infer_idea.py --category arc_wbe_2026"

run_rc=0
set +e
docker run --rm \
  --name "$OUTER_CONTAINER_NAME" \
  --add-host=host.docker.internal:host-gateway \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$WORKSPACE":/workspace \
  -v "$FRAMEWORK_DATASET_ROOT":/data/arc_wbe_2026:ro \
  -v "$CONTRACT_FILE":/input/contract.md:ro \
  --env-file "$PROVIDER_ENV" \
  --env-file "$SEMANTIC_ENV" \
  -e COMPLETION_MODEL=$AI_RESEARCHER_COMPLETION_MODEL \
  -e CHEEP_MODEL=$AI_RESEARCHER_CHEAP_MODEL \
  -e BASE_IMAGES=ai-researcher-exec:runtime-ready \
  -e GPUS=all \
  -e PYTHONPATH=/workspace/AI-Researcher \
  -e RESEARCHCLAWEVAL_AI_RESEARCHER_HOST_REPO="$REPO" \
  -e RESEARCHCLAWEVAL_DOCKER_HOST=host.docker.internal \
  -e RESEARCHCLAWEVAL_TOPIC_HOST_DATASET_ROOT="$FRAMEWORK_DATASET_ROOT" \
  -e RESEARCHCLAWEVAL_TOPIC_HOST_CONTRACT_FILE="$CONTRACT_FILE" \
  -e RESEARCHCLAWEVAL_TOPIC_DATASET_ROOT=/data/arc_wbe_2026 \
  -w /workspace/AI-Researcher \
  "$OUTER_IMAGE" \
  bash -lc "$RUNTIME_COMMAND" 2>&1 | tee -a "$LOG_FILE"
run_rc=${PIPESTATUS[0]}
set -e

if [[ "$run_rc" -ne 0 ]]; then
  write_state "failed" "AI-Researcher ARC native execution exited non-zero; see log" "$run_rc" "python run_infer_idea.py --category arc_wbe_2026"
  exit "$run_rc"
fi

TRACE_ROOT="$REPO/research_agent/workplace"
if [[ ! -d "$TRACE_ROOT" ]]; then
  TRACE_ROOT="$(find "$REPO/research_agent" -type d \( -path '*/workplace/workplace' -o -name 'workplace' \) | head -n 1 || true)"
fi
[[ -d "$TRACE_ROOT" ]] || {
  write_state "blocked" "AI-Researcher exited successfully but did not leave the expected workplace trace root" 31 "python run_infer_idea.py --category arc_wbe_2026"
  exit 31
}

python3 "$ROOT/automation/scripts/run_arc_wbe_2026_local_score.py" \
  --workspace "$WORKSPACE" \
  --output-score "$WORKSPACE/score.json" \
  --dataset-root "$DATASET_ROOT" \
  --explicit-score-artifact "$SCORE_SOURCE_ARTIFACT" >/dev/null 2>&1 || true

python3 - "$WORKSPACE" "$TRACE_ROOT" "${ARC_WBE_2026_MODEL:-$FRAMEWORK_MODEL_RAW}" <<'PY'
from pathlib import Path
import json
import sys

workspace = Path(sys.argv[1])
trace_root = Path(sys.argv[2])
expected_model = sys.argv[3]
required = ["estimator.py", "submission.json", "score.json", "experiment_trace.json", "final_report.md"]
missing = [name for name in required if not (workspace / name).is_file()]
if missing:
    raise SystemExit("AI-Researcher did not produce framework-native ARC handoff artifacts: " + ", ".join(missing))
trace = json.loads((workspace / "experiment_trace.json").read_text(encoding="utf-8"))
if trace.get("framework_internal_model") != expected_model or not trace.get("framework_internal_api_base_url"):
    raise SystemExit("AI-Researcher trace does not prove injected Kimi model/base URL")
score = json.loads((workspace / "score.json").read_text(encoding="utf-8"))
if score.get("score_source") != "official_adapter_whest_run":
    raise SystemExit("AI-Researcher score is not official_adapter_whest_run")
PY

python3 - "$MANIFEST_FILE" "$WORKSPACE" "$LOG_FILE" <<'PY'
from pathlib import Path
import json
import sys

manifest_path = Path(sys.argv[1])
workspace = Path(sys.argv[2])
log_file = sys.argv[3]
payload = json.loads(manifest_path.read_text(encoding="utf-8"))
payload.update(
    {
        "submission_artifact": str(workspace / "submission.json"),
        "final_report": str(workspace / "final_report.md"),
        "score_artifact": str(workspace / "score.json") if (workspace / "score.json").exists() else None,
        "workspace_trace_root": str(workspace / "AI-Researcher" / "research_agent" / "workplace"),
        "log": log_file,
    }
)
manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

write_state "finished" "AI-Researcher ARC workflow produced framework-native official score evidence." "0" "python run_infer_idea.py --category arc_wbe_2026"
