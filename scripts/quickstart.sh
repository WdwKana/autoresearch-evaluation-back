#!/usr/bin/env bash
# ============================================================================
# quickstart.sh — ResearchClawEval 快速验证脚本
# Verifies that the setup is correct and ready for evaluation runs.
#
# Usage:
#   bash scripts/quickstart.sh                          # Run all checks
#   bash scripts/quickstart.sh --env /path/to/.env      # Use custom env file
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()      { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }
header()  { echo -e "\n${CYAN}════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $*${NC}"; echo -e "${CYAN}════════════════════════════════════════════${NC}"; }

# ---- Parse arguments ----
ENV_FILE="$ROOT/.env"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env) ENV_FILE="$2"; shift 2 ;;
    *) error "Unknown option: $1"; exit 1 ;;
  esac
done

# ---- Load .env if exists ----
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
  ok "Loaded environment from $ENV_FILE"
else
  warn "No .env file found at $ENV_FILE"
  warn "Create one from .env.example: cp .env.example .env"
fi

# ============================================================================
# Check 1: Prerequisites
# ============================================================================
header "Check 1: Prerequisites"

FAILED=0
command -v python3 >/dev/null 2>&1 && ok "python3 found: $(python3 --version)" || { error "python3 not found"; FAILED=1; }
command -v uv >/dev/null 2>&1 && ok "uv found: $(uv --version)" || warn "uv not found (will use pip)"
command -v docker >/dev/null 2>&1 && ok "docker found" || warn "docker not found (needed for full runs)"
command -v git >/dev/null 2>&1 && ok "git found: $(git --version)" || { error "git not found"; FAILED=1; }

# ============================================================================
# Check 2: Framework source code
# ============================================================================
header "Check 2: Framework Source Code"

FRAMEWORKS=("01:AI-Researcher" "02:AI-Scientist-v2" "04:AutoResearchClaw")
for fw in "${FRAMEWORKS[@]}"; do
  IFS=':' read -r fw_id fw_name <<< "$fw"
  if [[ -d "$ROOT/$fw_name/.git" ]]; then
    ok "$fw_name [$fw_id] — ready"
  else
    warn "$fw_name [$fw_id] — not found. Run: bash setup.sh --frameworks $fw_id"
  fi
done

# ============================================================================
# Check 3: Project dependencies
# ============================================================================
header "Check 3: Project Dependencies"

if command -v uv >/dev/null 2>&1; then
  uv run rceval --help >/dev/null 2>&1 && ok "rceval CLI is available" || { error "rceval CLI not working"; FAILED=1; }
else
  python3 -m researchclaweval.cli --help >/dev/null 2>&1 && ok "rceval CLI is available" || { error "rceval CLI not working"; FAILED=1; }
fi

# ============================================================================
# Check 4: API connectivity
# ============================================================================
header "Check 4: API Connectivity"

if [[ -n "${OPENAI_API_KEY:-}" && -n "${OPENAI_BASE_URL:-}" ]]; then
  masked_key="${OPENAI_API_KEY:0:8}...${OPENAI_API_KEY: -4}"
  ok "API key configured: $masked_key"
  ok "API endpoint: $OPENAI_BASE_URL"
  if [[ -n "${OPENAI_MODEL:-}" ]]; then
    ok "Default model: $OPENAI_MODEL"
  else
    warn "OPENAI_MODEL not set"
  fi
else
  warn "API key not configured. Set OPENAI_API_KEY and OPENAI_BASE_URL in .env"
fi

# ============================================================================
# Check 5: Registry validation
# ============================================================================
header "Check 5: Registry Validation"

if command -v uv >/dev/null 2>&1; then
  uv run rceval validate registry 2>/dev/null && ok "Registry is valid" || warn "Registry validation had issues"
else
  warn "uv not available, skipping registry validation"
fi

# ============================================================================
# Check 6: Dry-run test
# ============================================================================
header "Check 6: Dry-Run Test (no Docker required)"

DRY_RUN_DIR="/tmp/rceval-quickstart-$$"
if command -v uv >/dev/null 2>&1; then
  if uv run rceval dry-run --topic arc_wbe_2026 --mode smoke --output-dir "$DRY_RUN_DIR" 2>/dev/null; then
    ok "Dry-run passed for arc_wbe_2026/smoke"
    rm -rf "$DRY_RUN_DIR"
  else
    warn "Dry-run failed (expected if datasets are not available)"
    rm -rf "$DRY_RUN_DIR" 2>/dev/null || true
  fi
else
  warn "uv not available, skipping dry-run"
fi

# ============================================================================
# Summary
# ============================================================================
header "Quickstart Summary"

if [[ "$FAILED" -eq 1 ]]; then
  echo ""
  error "Some checks failed. Fix the issues above and re-run."
  exit 1
else
  echo ""
  echo "  ✅ Setup looks good!"
  echo ""
  echo "  Next steps:"
  echo ""
  echo "  1. Ensure your .env has API keys configured"
  echo "  2. Run a smoke test for a specific framework + topic:"
  echo ""
  echo "     export REAL_EVAL_RUN_ROOT=/tmp/rceval-smoke"
  echo "     bash real_eval/scripts/01_ai_researcher_arc_wbe_2026_smoke.sh"
  echo ""
  echo "  3. Available smoke tests:"
  echo "     01 - AI-Researcher:     arc_wbe_2026  gave2_task2  psydefdetect  tdc_admet_tox"
  echo "     02 - AI-Scientist-v2:   arc_wbe_2026  gave2_task2  psydefdetect"
  echo "     04 - AutoResearchClaw:  arc_wbe_2026  gave2_task2  psydefdetect"
  echo ""
  echo "  4. For full runs, build Docker images first:"
  echo "     bash scripts/build_docker.sh"
  echo ""
fi