#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
export FRAMEWORK_NAME="AI-Scientist-v2"
export FRAMEWORK_SLUG="02_ai_scientist_v2_tdc_admet_tox_smoke"
export FRAMEWORK_SRC="$(real_eval_resolve_framework_source "$ROOT" 02)"
export FRAMEWORK_RUNTIME_IMAGE="ai-scientist-v2:runtime-ready"
export FRAMEWORK_NATIVE_ENTRYPOINT="perform_ideation_temp_free.py -> launch_scientist_bfts.py"
export FRAMEWORK_NATIVE_ENTRYPOINT_FILE="ai_scientist/perform_ideation_temp_free.py"
# The shared runner stays at upstream; 02's changes to it are applied to a copy
# (real_eval/adapters/ai_scientist_v2/shared_layer_patches/, see real_eval/adapters/shared_layer_overlay.py).
SHARED_RUNNER="$(python3 "$ROOT/real_eval/adapters/shared_layer_overlay.py" materialize ai_scientist_v2 real_eval/scripts/tdc_admet_tox_framework_smoke.sh)"
export RESEARCHCLAWEVAL_ROOT="$ROOT"
exec "$SHARED_RUNNER"
