#!/usr/bin/env bash
# ============================================================================
# build_docker.sh — Build Docker images for all frameworks
#
# Usage:
#   bash scripts/build_docker.sh              # Build all images for frameworks 01, 02, 04
#   bash scripts/build_docker.sh 01 04        # Build specific frameworks only
#   bash scripts/build_docker.sh --all        # Build all 7 frameworks
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}   $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ---- Framework images ----
# Format: "name|Dockerfile|image_tag|context_dir"
declare -A IMAGES
IMAGES["01"]="AI-Researcher|AI-Researcher/docker/Dockerfile|ai-researcher:runtime-ready|AI-Researcher"
IMAGES["01-exec"]="AI-Researcher (exec)|AI-Researcher/docker/Dockerfile|ai-researcher-exec:runtime-ready|AI-Researcher"
IMAGES["02"]="AI-Scientist-v2|AI-Scientist-v2/Dockerfile|ai-scientist-v2:runtime-ready|AI-Scientist-v2"
IMAGES["04"]="AutoResearchClaw|AutoResearchClaw/researchclaw/docker/Dockerfile|autoresearchclaw:runtime-ready|AutoResearchClaw"

# ---- Parse arguments ----
if [[ $# -gt 0 ]]; then
  if [[ "$1" == "--all" ]]; then
    SELECTED=("01" "01-exec" "02" "04")
  else
    SELECTED=("$@")
    # Also add exec images for AI-Researcher if requested
    for fw in "$@"; do
      if [[ "$fw" == "01" ]]; then
        SELECTED+=("01-exec")
      fi
    done
  fi
else
  SELECTED=("01" "01-exec" "02" "04")
fi

# ============================================================================
# Build images
# ============================================================================
for fw_key in "${SELECTED[@]}"; do
  IFS='|' read -r fw_name dockerfile image_tag context_dir <<< "${IMAGES[$fw_key]:-}"
  if [[ -z "$fw_name" ]]; then
    warn "Unknown image key: $fw_key"
    continue
  fi

  echo ""
  info "Building $image_tag for $fw_name..."

  if [[ ! -f "$ROOT/$dockerfile" ]]; then
    error "Dockerfile not found: $ROOT/$dockerfile"
    info "Make sure the framework source is cloned first:"
    info "  bash setup.sh --frameworks ${fw_key%%-*}"
    continue
  fi

  if [[ ! -d "$ROOT/$context_dir" ]]; then
    error "Framework directory not found: $ROOT/$context_dir"
    info "Run: bash setup.sh --frameworks ${fw_key%%-*}"
    continue
  fi

  # AI-Researcher exec image uses the same Dockerfile but with a different target
  if [[ "$fw_key" == "01-exec" ]]; then
    # The exec image is built from the same Dockerfile, often as a separate stage
    docker build -t "$image_tag" \
      -f "$ROOT/$dockerfile" \
      --target exec \
      "$ROOT/$context_dir" 2>/dev/null && \
      ok "$image_tag built successfully" || {
      # If no explicit target, build with a different Dockerfile name convention
      exec_dockerfile="${ROOT}/AI-Researcher/docker/Dockerfile.exec"
      if [[ -f "$exec_dockerfile" ]]; then
        docker build -t "$image_tag" -f "$exec_dockerfile" "$ROOT/$context_dir" && \
          ok "$image_tag built successfully" || \
          error "Failed to build $image_tag"
      else
        # Build outer image first, then exec as same image
        warn "No separate exec Dockerfile found, using outer image as exec"
        docker tag ai-researcher:runtime-ready ai-researcher-exec:runtime-ready 2>/dev/null || true
        ok "$image_tag tagged (same as outer image)"
      fi
    }
  else
    docker build -t "$image_tag" \
      -f "$ROOT/$dockerfile" \
      "$ROOT/$context_dir" && \
      ok "$image_tag built successfully" || \
      error "Failed to build $image_tag"
  fi
done

echo ""
ok "Docker build complete"
echo ""
info "Available images:"
docker images --format "  {{.Repository}}:{{.Tag}}" | grep -E "runtime-ready" | sort || true
echo ""