#!/usr/bin/env bash
# ============================================================================
# build_docker.sh — Build Docker images for all frameworks
#
# Usage:
#   bash scripts/build_docker.sh              # Build all images
#   bash scripts/build_docker.sh 01 04        # Build specific frameworks only
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

# Framework ID → (name, Dockerfile path, image tag, context dir)
declare -A IMAGES
IMAGES["01"]="AI-Researcher|AI-Researcher/docker/Dockerfile|ai-researcher:runtime-ready|AI-Researcher"
IMAGES["02"]="AI-Scientist-v2|AI-Scientist-v2/Dockerfile|ai-scientist-v2:runtime-ready|AI-Scientist-v2"
IMAGES["04"]="AutoResearchClaw|AutoResearchClaw/researchclaw/docker/Dockerfile|autoresearchclaw:runtime-ready|AutoResearchClaw"

if [[ $# -gt 0 ]]; then
  SELECTED=("$@")
else
  SELECTED=("01" "02" "04")
fi

for fw_id in "${SELECTED[@]}"; do
  IFS='|' read -r fw_name dockerfile image_tag context_dir <<< "${IMAGES[$fw_id]:-}"
  if [[ -z "$fw_name" ]]; then
    warn "Unknown framework ID: $fw_id"
    continue
  fi

  echo ""
  info "Building $image_tag for $fw_name..."

  if [[ ! -f "$ROOT/$dockerfile" ]]; then
    error "Dockerfile not found: $ROOT/$dockerfile"
    info "You may need to create this Dockerfile or check the framework source."
    info "Run: bash setup.sh --frameworks $fw_id"
    continue
  fi

  if [[ ! -d "$ROOT/$context_dir" ]]; then
    error "Framework directory not found: $ROOT/$context_dir"
    info "Run: bash setup.sh --frameworks $fw_id"
    continue
  fi

  docker build -t "$image_tag" \
    -f "$ROOT/$dockerfile" \
    "$ROOT/$context_dir" && \
    ok "$image_tag built successfully" || \
    error "Failed to build $image_tag"
done

echo ""
ok "Docker build complete"