#!/usr/bin/env bash
# 01-scoped python for the MountainCar official scorer.
#
# WHY (2026-10-04)
#   The shared runner executes the host scorer and the frozen evaluate.py with
#   $MC_PYTHON (default: the host `python`). The host interpreter has no JAX or
#   gymnax, so the first 01 run that ever passed the delivery gate
#   (fullrun_mcar_01_kimi_20261003_163455) was failed with exit 43:
#   "No module named 'gymnax'". The 02 launcher avoids this by pointing --python
#   at an in-image interpreter; this helper does the same for 01 through the
#   runner's existing MOUNTAINCAR_CONTINUOUS_PYTHON hook, so no shared file is
#   edited.
#
# HOW
#   Outside the image it re-executes ITSELF inside the JAX image with the repo
#   root mounted at the same path; inside (MC_HOST_PYTHON_INNER=1) it is plain
#   `python`. The scorer's own nested `--python <this file>` call therefore also
#   resolves to the in-image interpreter. No network; nothing is written outside
#   the paths the scorer is given.
set -euo pipefail

if [ "${MC_HOST_PYTHON_INNER:-0}" = 1 ]; then
  exec python "$@"
fi

SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "$SELF")/../../.." && pwd)}"
IMAGE="${MOUNTAINCAR_CONTINUOUS_SCORE_IMAGE:-ai-researcher-exec:mountaincar-jax}"

exec docker run --rm --network none \
  --cpus "${MOUNTAINCAR_CONTINUOUS_SCORE_CPUS:-16}" \
  -e MC_HOST_PYTHON_INNER=1 -e JAX_PLATFORMS=cpu -e CUDA_VISIBLE_DEVICES= \
  -v "$ROOT:$ROOT" -w "$ROOT" \
  "$IMAGE" "$SELF" "$@"
