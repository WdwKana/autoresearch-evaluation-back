#!/usr/bin/env bash
# ============================================================================
# setup.sh — ResearchClawEval 一键协作设置脚本
# One-click collaboration setup for ResearchClawEval
#
# Usage:
#   bash setup.sh                        # Set up all 3 frameworks (01, 02, 04)
#   bash setup.sh --frameworks 01,04     # Set up specific frameworks only
#   bash setup.sh --dir /path/to/dir     # Clone frameworks to a custom directory
#   bash setup.sh --skip-venv            # Skip Python virtual environment setup
#   bash setup.sh --help                 # Show help
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# ---- Framework definitions (from real_eval/registry/frameworks.json) ----
declare -A FRAMEWORKS
FRAMEWORKS["01"]="AI-Researcher|https://github.com/HKUDS/AI-Researcher.git|f9a6f8480860c193afff600eeffe3defcee8a978|adapters/01-ai-researcher|pip"
FRAMEWORKS["02"]="AI-Scientist-v2|https://github.com/SakanaAI/AI-Scientist-v2.git|96bd51617cfdbb494a9fc283af00fe090edfae48|adapters/02-ai-scientist-v2|pip"
FRAMEWORKS["04"]="AutoResearchClaw|https://github.com/aiming-lab/AutoResearchClaw.git|ea77ec19fefe9198ac1364d2cdb4f9e928cf0705|adapters/04-autoresearchclaw|uv"

# ---- Colors ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ---- Parse arguments ----
SELECTED_FRAMEWORKS="01,02,04"
FRAMEWORK_DIR="$ROOT"
SKIP_VENV=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --frameworks) SELECTED_FRAMEWORKS="$2"; shift 2 ;;
    --dir) FRAMEWORK_DIR="$(cd "$2" && pwd)"; shift 2 ;;
    --skip-venv) SKIP_VENV=true; shift ;;
    --help)
      echo "Usage: bash setup.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --frameworks LIST    Comma-separated framework IDs to set up (default: 01,02,04)"
      echo "  --dir PATH           Directory to clone frameworks into (default: repo root)"
      echo "  --skip-venv          Skip Python venv creation"
      echo "  --help               Show this help"
      exit 0
      ;;
    *) error "Unknown option: $1"; exit 1 ;;
  esac
done

# ---- Pre-flight checks ----
info "Checking prerequisites..."

command -v git  >/dev/null 2>&1 || { error "git is required but not installed."; exit 1; }
command -v python3 >/dev/null 2>&1 || { error "python3 is required but not installed."; exit 1; }
command -v uv   >/dev/null 2>&1 || warn "uv is not installed. Will use pip instead."
command -v docker >/dev/null 2>&1 || warn "docker is not installed. Framework runs will require Docker."
ok "Prerequisites check passed"

# ---- Parse selected frameworks ----
IFS=',' read -ra SELECTED_IDS <<< "$SELECTED_FRAMEWORKS"

# ============================================================================
# Step 1: Clone / update frameworks
# ============================================================================
echo ""
info "=== Step 1: Cloning framework source code ==="
echo ""

for fw_id in "${SELECTED_IDS[@]}"; do
  fw_id="$(echo "$fw_id" | xargs)"  # trim whitespace
  IFS='|' read -r fw_name fw_url fw_commit fw_adapter fw_pkg_mgr <<< "${FRAMEWORKS[$fw_id]:-}"

  if [[ -z "$fw_name" ]]; then
    warn "Unknown framework ID: $fw_id, skipping"
    continue
  fi

  TARGET_DIR="$FRAMEWORK_DIR/$fw_name"

  if [[ -d "$TARGET_DIR/.git" ]]; then
    info "Updating $fw_name (existing clone)..."
    cd "$TARGET_DIR"
    git fetch origin
    git checkout "$fw_commit" 2>/dev/null || {
      warn "Could not checkout pinned commit, trying fetch..."
      git fetch --depth=100 origin
      git checkout "$fw_commit" 2>/dev/null || {
        error "Failed to checkout pinned commit for $fw_name"
        cd "$ROOT"
        continue
      }
    }
    cd "$ROOT"
    ok "$fw_name updated to pinned commit"
  else
    info "Cloning $fw_name (this may take a while for large frameworks)..."
    git clone --depth 1 "$fw_url" "$TARGET_DIR" 2>/dev/null || {
      error "Failed to clone $fw_name from $fw_url"
      continue
    }
    cd "$TARGET_DIR"
    # Fetch the specific commit we need
    git fetch --depth=100 origin "$fw_commit" 2>/dev/null || {
      warn "Could not fetch pinned commit, using latest"
    }
    git checkout "$fw_commit" 2>/dev/null || {
      warn "Could not checkout pinned commit for $fw_name, using latest main"
      git checkout main 2>/dev/null || git checkout master 2>/dev/null || true
    }
    cd "$ROOT"
    ok "$fw_name cloned successfully"
  fi

  # ---- Apply patches ----
  PATCH_DIR="$ROOT/$fw_adapter/patches"
  if [[ -d "$PATCH_DIR" ]]; then
    for patch_file in "$PATCH_DIR"/*.patch; do
      if [[ -f "$patch_file" ]]; then
        info "Applying patch: $(basename "$patch_file") to $fw_name..."
        cd "$TARGET_DIR"
        if git apply --check "$patch_file" 2>/dev/null; then
          git apply "$patch_file"
          ok "Patch $(basename "$patch_file") applied to $fw_name"
        else
          warn "Patch $(basename "$patch_file") could not be applied (may already be applied), skipping"
        fi
        cd "$ROOT"
      fi
    done
  fi
done

# ============================================================================
# Step 2: Install project dependencies
# ============================================================================
echo ""
info "=== Step 2: Installing project dependencies ==="
echo ""

if command -v uv >/dev/null 2>&1; then
  info "Installing with uv..."
  uv sync --extra dev 2>/dev/null && ok "Project dependencies installed with uv" || warn "uv sync failed, trying pip..."
else
  warn "uv not found, falling back to pip"
  python3 -m pip install -e ".[dev]" 2>/dev/null && ok "Project dependencies installed with pip" || warn "pip install failed"
fi

# ============================================================================
# Step 3: Install framework dependencies
# ============================================================================
echo ""
info "=== Step 3: Installing framework dependencies ==="
echo ""

for fw_id in "${SELECTED_IDS[@]}"; do
  fw_id="$(echo "$fw_id" | xargs)"
  IFS='|' read -r fw_name fw_url fw_commit fw_adapter fw_pkg_mgr <<< "${FRAMEWORKS[$fw_id]:-}"

  if [[ -z "$fw_name" ]]; then
    continue
  fi

  TARGET_DIR="$FRAMEWORK_DIR/$fw_name"
  if [[ ! -d "$TARGET_DIR" ]]; then
    warn "$fw_name directory not found, skipping dependency installation"
    continue
  fi

  info "Installing dependencies for $fw_name..."

  if [[ "$fw_pkg_mgr" == "uv" ]] && command -v uv >/dev/null 2>&1; then
    if [[ -f "$TARGET_DIR/pyproject.toml" ]]; then
      cd "$TARGET_DIR"
      uv sync 2>/dev/null && ok "$fw_name dependencies installed (uv)" || warn "uv sync failed for $fw_name"
      cd "$ROOT"
    fi
  elif [[ -f "$TARGET_DIR/requirements.txt" ]]; then
    python3 -m pip install -r "$TARGET_DIR/requirements.txt" 2>/dev/null && \
      ok "$fw_name dependencies installed (pip)" || \
      warn "pip install failed for $fw_name"
  elif [[ -f "$TARGET_DIR/setup.cfg" ]] || [[ -f "$TARGET_DIR/setup.py" ]]; then
    python3 -m pip install -e "$TARGET_DIR" 2>/dev/null && \
      ok "$fw_name installed (pip -e)" || \
      warn "pip install -e failed for $fw_name"
  elif [[ -f "$TARGET_DIR/pyproject.toml" ]]; then
    python3 -m pip install -e "$TARGET_DIR" 2>/dev/null && \
      ok "$fw_name installed (pip -e from pyproject.toml)" || \
      warn "pip install failed for $fw_name"
  else
    warn "No dependency file found for $fw_name, skipping"
  fi
done

# ============================================================================
# Step 4: Verify setup
# ============================================================================
echo ""
info "=== Step 4: Verifying setup ==="
echo ""

# Run registry validation
if command -v uv >/dev/null 2>&1; then
  uv run rceval validate registry 2>/dev/null && \
    ok "Registry validation passed" || \
    warn "Registry validation had issues (this is expected if datasets are not available)"
  echo ""
  uv run rceval registry list 2>/dev/null || true
fi

# Print summary
echo ""
echo "============================================"
echo -e "${GREEN}  ResearchClawEval setup complete!${NC}"
echo "============================================"
echo ""
echo "Framework directories:"
for fw_id in "${SELECTED_IDS[@]}"; do
  fw_id="$(echo "$fw_id" | xargs)"
  IFS='|' read -r fw_name fw_url fw_commit fw_adapter fw_pkg_mgr <<< "${FRAMEWORKS[$fw_id]:-}"
  if [[ -z "$fw_name" ]]; then continue; fi
  TARGET_DIR="$FRAMEWORK_DIR/$fw_name"
  if [[ -d "$TARGET_DIR" ]]; then
    echo "  ✅ $fw_name ($fw_id) → $TARGET_DIR"
  else
    echo "  ❌ $fw_name ($fw_id) → not found"
  fi
done

echo ""
echo "Next steps:"
echo "  1. Configure your LLM provider API key:"
echo "     export OPENAI_API_KEY=your_key_here"
echo "     export OPENAI_BASE_URL=https://your-provider-url/v1"
echo "     export OPENAI_MODEL=your-model-name"
echo "  2. (Optional) Set up framework source paths:"
echo "     export RESEARCHCLAWEVAL_AI_RESEARCHER_ROOT=\"$FRAMEWORK_DIR/AI-Researcher\""
echo "     export RESEARCHCLAWEVAL_AI_SCIENTIST_V2_ROOT=\"$FRAMEWORK_DIR/AI-Scientist-v2\""
echo "     export RESEARCHCLAWEVAL_AUTORESEARCHCLAW_ROOT=\"$FRAMEWORK_DIR/AutoResearchClaw\""
echo "  3. Run a smoke test:"
echo "     uv run rceval dry-run --topic arc_wbe_2026 --mode smoke --output-dir /tmp/rceval-test"
echo "  4. For full runs with Docker, build the required images first"
echo ""
echo "See SETUP.md for detailed instructions."
echo ""