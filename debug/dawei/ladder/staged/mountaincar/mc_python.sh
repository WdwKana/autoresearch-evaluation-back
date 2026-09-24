#!/usr/bin/env bash
# Host-side "python" for the frozen evaluator: the host has no JAX, so run the command inside the
# MountainCar runtime image with the current directory (the run workspace) mounted at the same path.
set -euo pipefail
WD="$(pwd)"
exec docker run --rm --network none --cpus 16 -v "$WD:$WD" -w "$WD" -e CUDA_VISIBLE_DEVICES= -e JAX_PLATFORMS=cpu -e OMP_NUM_THREADS=16 ai-scientist-v2:runtime-mountaincar python "$@"
