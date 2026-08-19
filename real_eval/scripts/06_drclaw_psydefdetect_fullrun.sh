#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
BASE="${REAL_EVAL_RUN_ROOT:?REAL_EVAL_RUN_ROOT is required}"
EVAL_MODEL="${PSYDEFDETECT_EVAL_MODEL:-gpt-5.4}"
mkdir -p "$BASE/logs"
python3 - "$BASE/fullrun_manifest.json" "$BASE/state.json" "$EVAL_MODEL" <<'PY'
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

reason = (
    "Dr. Claw's official node server/cli.js chat entrypoint and project-local research skill "
    "loading passed technical native-entrypoint admission, but docs/internal-beta-user-agreement.en-US.md "
    "section 8.6 requires prior written consent for benchmark or comparative evaluation. "
    "No authorization record is available in the evaluation inputs, so fullrun dispatch is blocked."
)
now = datetime.now(timezone.utc).astimezone().isoformat()
Path(sys.argv[1]).write_text(json.dumps({
    "framework": "Dr. Claw",
    "slug": "06_drclaw_psydefdetect_fullrun",
    "framework_orchestration": True,
    "native_entrypoint": f"node server/cli.js chat --model {sys.argv[3]}",
    "native_entrypoint_source": "README.md Option C / server/cli.js",
    "provider_injection": "OPENAI_BASE_URL, OPENAI_API_KEY, and OPENAI_MODEL through the Dr. Claw CLI provider adapter",
    "admission_status": "technical_pass_legal_block",
    "blocked_reason": reason,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
Path(sys.argv[2]).write_text(json.dumps({
    "project_id": "psydefdetect",
    "phase": "fullrun",
    "status": "blocked_benchmark_authorization",
    "summary": reason,
    "updated_at": now,
    "exit_code": 0,
}, ensure_ascii=False) + "\n", encoding="utf-8")
PY
printf '%s\n' 'DRCLAW_BLOCKED_BENCHMARK_AUTHORIZATION' > "$BASE/logs/e2e.log"
