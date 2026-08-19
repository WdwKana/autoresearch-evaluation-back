#!/usr/bin/env bash

real_eval_require_clean_dir() {
  local path="$1"
  if [[ -e "$path" ]]; then
    echo "Refusing to reuse existing run directory: $path" >&2
    exit 10
  fi
}

real_eval_snapshot_forbidden_artifacts() {
  local root="$1"
  local out="$2"
  mkdir -p "$(dirname "$out")"
  if [[ ! -d "$root" ]]; then
    : > "$out"
    return 0
  fi
  find "$root" \
    \( \
      -name 'final_report.md' -o \
      -name 'submission.json' -o \
      -name 'submission.csv' -o \
      -name 'predictions.csv' -o \
      -name 'predictions.jsonl' -o \
      -name 'score.json' -o \
      -name 'experiment_trace.json' -o \
      -name 'paper.md' -o \
      -name 'environment.json' -o \
      -path '*/logs/*' -o \
      -path '*/artifacts/*' -o \
      -path '*/outputs/*' -o \
      -path '*/runs/*' \
    \) \
    -print 2>/dev/null | sort > "$out"
}

real_eval_assert_no_new_forbidden_artifacts() {
  local root="$1"
  local before="$2"
  local after
  after="$(mktemp)"
  real_eval_snapshot_forbidden_artifacts "$root" "$after"
  if ! comm -13 "$before" "$after" | sed '/^[[:space:]]*$/d' > "$after.new"; then
    rm -f "$after" "$after.new"
    exit 14
  fi
  if [[ -s "$after.new" ]]; then
    echo "Framework template source gained forbidden artifacts:" >&2
    cat "$after.new" >&2
    rm -f "$after" "$after.new"
    return 14
  fi
  rm -f "$after" "$after.new"
}

real_eval_rsync_repo() {
  local src="$1"
  local dst="$2"
  mkdir -p "$dst"
  if ! command -v rsync >/dev/null 2>&1; then
    echo "rsync is required for isolated source snapshots" >&2
    exit 11
  fi
  rsync -a \
    --exclude '.git' \
    --exclude '.codex-*' \
    --exclude '.claude' \
    --exclude '.aris' \
    --exclude '.evoscientist' \
    --exclude '.env' \
    --exclude '.env.*' \
    --exclude '*.env' \
    --exclude 'provider.env' \
    --exclude 'semantic.env' \
    --exclude 'config.toml' \
    --exclude '.researchclaw_cache' \
    --exclude '.runtime-home' \
    --exclude '.deepscientist_home' \
    --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'artifacts' \
    --exclude 'outputs' \
    --exclude 'runs' \
    --exclude 'logs' \
    --exclude 'experiments' \
    --exclude 'workspaces' \
    --exclude 'cache_*' \
    --exclude 'workplace_*' \
    --exclude 'workplace_paper' \
    --exclude 'paper_db/.paper_memory_*' \
    "$src"/ "$dst"/
}

real_eval_purge_cross_topic_residue() {
  local dst="$1"
  local topic_label="${2:-}"
  case "$topic_label" in
    gave2)
      find "$dst" \
        \( -iname '*babylm*' -o -iname 'Dockerfile.ngc-babylm' -o -iname 'run_babylm*.sh' -o -iname 'bfts_config.babylm*.yaml' \) \
        -print0 2>/dev/null | xargs -0 -r rm -rf
      ;;
    arc_wbe_2026)
      find "$dst" \
        \( \
          -iname '*babylm*' -o \
          -iname '*gave2*' -o \
          -iname 'my_research_topic.*' -o \
          -iname 'config.project4.yaml' -o \
          -iname '.env' -o \
          -iname '.env.*' -o \
          -iname '*.env' -o \
          -iname 'provider.env' -o \
          -iname 'semantic.env' -o \
          -iname 'config.toml' -o \
          -iname 'RESEARCH_BRIEF.md' -o \
          -iname 'babylm_proxy' -o \
          -name '.aris-codex-project' -o \
          -path '*/verify_workspace' -o \
          -path '*/workspace/workspace' \
        \) \
        -print0 2>/dev/null | xargs -0 -r rm -rf
      find "$dst" \
        \( \
          -name 'final_report.md' -o \
          -name 'submission.json' -o \
          -name 'score.json' \
        \) \
        -path '*/workspace/*' \
        -print0 2>/dev/null | xargs -0 -r rm -f
      ;;
    psydefdetect)
      find "$dst" \
        \( \
          -iname '*babylm*' -o \
          -iname '*gave2*' -o \
          -iname '*arc_wbe_2026*' -o \
          -iname '*arc-wbe-2026*' -o \
          -iname 'config.arc.yaml' -o \
          -iname 'config.project4.yaml' -o \
          -iname 'Dockerfile.ngc-babylm' -o \
          -iname 'run_babylm*.sh' -o \
          -iname 'bfts_config.babylm*.yaml' -o \
          -iname 'provider.env' -o \
          -iname 'semantic.env' -o \
          -iname 'config.toml' -o \
          -name '.runtime-home' -o \
          -name '.deepscientist_home' -o \
          -name '.aris-codex-project' -o \
          -path '*/verify_workspace' -o \
          -path '*/workspace/workspace' \
        \) \
        -print0 2>/dev/null | xargs -0 -r rm -rf
      find "$dst" \
        \( \
          -name 'final_report.md' -o \
          -name 'submission.json' -o \
          -name 'submission.csv' -o \
          -name 'predictions.jsonl' -o \
          -name 'score.json' \
        \) \
        -print0 2>/dev/null | xargs -0 -r rm -f
      ;;
    tdc_admet_tox)
      find "$dst" \
        \( \
          -iname '*babylm*' -o \
          -iname '*gave2*' -o \
          -iname '*arc_wbe_2026*' -o \
          -iname '*arc-wbe-2026*' -o \
          -iname '*psydefdetect*' -o \
          -iname 'provider.env' -o \
          -iname 'semantic.env' -o \
          -iname 'config.toml' -o \
          -name '.runtime-home' -o \
          -name '.deepscientist_home' -o \
          -name '.aris-codex-project' -o \
          -path '*/verify_workspace' -o \
          -path '*/workspace/workspace' \
        \) \
        -print0 2>/dev/null | xargs -0 -r rm -rf
      find "$dst" \
        \( \
          -name 'final_report.md' -o \
          -name 'submission.json' -o \
          -name 'submission.csv' -o \
          -name 'predictions.csv' -o \
          -name 'predictions.jsonl' -o \
          -name 'score.json' -o \
          -name 'experiment_trace.json' -o \
          -name 'paper.md' -o \
          -name 'environment.json' \
        \) \
        -print0 2>/dev/null | xargs -0 -r rm -f
      ;;
    *)
      ;;
  esac
}

real_eval_write_state() {
  local path="$1"
  local json="$2"
  mkdir -p "$(dirname "$path")"
  printf '%s\n' "$json" > "$path"
}

real_eval_select_framework_config() {
  local root="$1"
  local base_run_root="$2"
  local default_config="$3"
  local topic_id="$4"
  local mode="$5"
  local generated_config

  if [[ -n "${REAL_EVAL_FRAMEWORK_CONFIG:-}" ]]; then
    printf '%s\n' "$REAL_EVAL_FRAMEWORK_CONFIG"
  elif [[ "${REAL_EVAL_USE_REGISTRY:-0}" == "1" ]]; then
    generated_config="$base_run_root/registry_framework_config.json"
    python3 "$root/real_eval/scripts/registry_to_config.py" --topic "$topic_id" --mode "$mode" > "$generated_config"
    printf '%s\n' "$generated_config"
  else
    printf '%s\n' "$default_config"
  fi
}

real_eval_write_serial_dry_run() {
  local config="$1"
  local out="$2"
  python3 - "$config" <<'PY' > "$out"
import json, sys
cfg = json.load(open(sys.argv[1], encoding='utf-8'))
for item in cfg['frameworks']:
    print(json.dumps({
        'id': item['id'],
        'name': item['name'],
        'run_dir': item['run_dir'],
        'wrapper': item['wrapper'],
        'validator': item['validator'],
    }, ensure_ascii=False))
PY
}

real_eval_write_frameworks_tsv() {
  local config="$1"
  local out="$2"
  python3 - "$config" <<'PY' > "$out"
import json, sys
cfg = json.load(open(sys.argv[1], encoding='utf-8'))
for item in cfg['frameworks']:
    print('\t'.join([
        item['id'],
        item['name'],
        item['run_dir'],
        item['wrapper'],
        item['validator'],
    ]))
PY
}

real_eval_write_serial_status() {
  local out="$1"
  shift
  python3 - "$out" "$@" <<'PY'
import json, sys
out = sys.argv[1]
rows = [json.loads(x) for x in sys.argv[2:]]
with open(out, 'w', encoding='utf-8') as f:
    json.dump({'rows': rows}, f, ensure_ascii=False, indent=2)
    f.write('\n')
PY
}

real_eval_state_status() {
  local state_file="$1"
  if [[ ! -f "$state_file" ]]; then
    printf 'unknown\n'
    return 0
  fi
  python3 - "$state_file" <<'PY'
import json, sys
try:
    print(json.loads(open(sys.argv[1], encoding='utf-8').read()).get('status', 'unknown'))
except Exception:
    print('unknown')
PY
}

real_eval_resolve_framework_source() {
  local root="$1"
  local framework_id="$2"
  python3 "$root/real_eval/scripts/registry_paths.py" --kind framework --id "$framework_id" --format path
}

real_eval_resolve_topic_dataset() {
  local root="$1"
  local topic_id="$2"
  python3 "$root/real_eval/scripts/registry_paths.py" --kind dataset --id "$topic_id" --format path
}

real_eval_provider_env_from_codex_toml() {
  local provider_toml="$1"
  local out_env="$2"
  local token base_url framework_base_url model
  token="$(sed -n 's/^[[:space:]]*experimental_bearer_token[[:space:]]*=[[:space:]]*"\(.*\)"[[:space:]]*$/\1/p' "$provider_toml" | head -1)"
  base_url="$(sed -n 's/^[[:space:]]*base_url[[:space:]]*=[[:space:]]*"\(.*\)"[[:space:]]*$/\1/p' "$provider_toml" | head -1)"
  model="$(sed -n 's/^[[:space:]]*model[[:space:]]*=[[:space:]]*"\(.*\)"[[:space:]]*$/\1/p' "$provider_toml" | head -1)"
  if [[ -z "$token" || -z "$base_url" || -z "$model" ]]; then
    echo "Failed to parse provider token/base_url/model from $provider_toml" >&2
    exit 12
  fi
  framework_base_url="${base_url%/}"
  if [[ "$framework_base_url" != */v1 ]]; then
    framework_base_url="$framework_base_url/v1"
  fi
  umask 077
  {
    printf 'OPENAI_API_KEY=%s\n' "$token"
    printf 'CODEX_API_KEY=%s\n' "$token"
    printf 'OPENAI_BASE_URL=%s\n' "$framework_base_url"
    printf 'API_BASE_URL=%s\n' "$framework_base_url"
	    printf 'OPENAI_MODEL=%s\n' "$model"
	    printf 'CUSTOM_OPENAI_API_KEY=%s\n' "$token"
	    printf 'CUSTOM_OPENAI_BASE_URL=%s\n' "$framework_base_url"
	    printf 'OPENROUTER_API_KEY=%s\n' "$token"
	    printf 'OPENROUTER_BASE_URL=%s\n' "$framework_base_url"
	    printf 'OPENROUTER_MODEL=%s\n' "$model"
	  } > "$out_env"
}

real_eval_semantic_env_from_usage_md() {
  local usage_md="$1"
  local out_env="$2"
  local s2_key ai4_key ai4_base ai4_auth
  s2_key="$(rg -o 'RZGQ[A-Za-z0-9]+' "$usage_md" | head -1 || true)"
  ai4_key="$(rg -o 'sk-user-[A-Za-z0-9]+' "$usage_md" | head -1 || true)"
  ai4_base="$(rg -o 'https://ai4scholar[.]net' "$usage_md" | head -1 || true)"
  ai4_auth="$(sed -n 's/^|[[:space:]]*Auth Mode[[:space:]]*|[[:space:]]*`\([^`]*\)`[[:space:]]*|[[:space:]]*$/\1/p' "$usage_md" | head -1 || true)"
  umask 077
  if [[ -z "$s2_key" && -z "$ai4_key" ]]; then
    : > "$out_env"
    return 0
  fi
  {
    if [[ -n "$s2_key" ]]; then
      printf 'SEMANTIC_SCHOLAR_OFFICIAL_API_KEY=%s\n' "$s2_key"
      printf 'S2_API_KEY=%s\n' "$s2_key"
    fi
    if [[ -n "$ai4_key" ]]; then
      printf 'AI4SCHOLAR_API_KEY=%s\n' "$ai4_key"
      printf 'SEMANTIC_SCHOLAR_API_KEY=%s\n' "$ai4_key"
    fi
    printf 'SEMANTIC_SCHOLAR_API_BASE_URL=%s\n' "${ai4_base:-https://ai4scholar.net}"
    printf 'SEMANTIC_SCHOLAR_AUTH_MODE=%s\n' "${ai4_auth:-bearer}"
    printf 'AI_RESEARCHER_DISABLE_ARXIV_SOURCE_DOWNLOAD_ON_429=1\n'
    printf 'ARIS_ARXIV_429_RETURNS_PENDING=1\n'
  } > "$out_env"
}

real_eval_has_artifacts() {
  local root="$1"
  local log_count checkpoint_count eval_count report_count
  log_count="$(find "$root" -type f \( -iname '*train*.log' -o -iname 'e2e.log' \) 2>/dev/null | wc -l)"
  checkpoint_count="$(find "$root" -type f \( -iname '*.pt' -o -iname '*.pth' -o -iname '*.safetensors' -o -iname 'pytorch_model.bin' -o -iname 'model.safetensors' \) 2>/dev/null | wc -l)"
  eval_count="$(find "$root" -type f \( -iname '*eval*.json' -o -iname '*metric*.json' -o -iname '*result*.json' \) 2>/dev/null | wc -l)"
  report_count="$(find "$root" -type f \( -iname 'final_report.md' -o -iname '*report*.md' -o -iname 'main.md' \) 2>/dev/null | wc -l)"
  [[ "$log_count" -gt 0 && "$checkpoint_count" -gt 0 && "$eval_count" -gt 0 && "$report_count" -gt 0 ]]
}

real_eval_fail_if_forbidden_log() {
  local log="$1"
  if rg -n 'run_framework_babylm_proxy|run_proxy_babylm_pipeline|iris|digits|old results|placeholder results' "$log" >/dev/null 2>&1; then
    echo "Forbidden proxy/toy/old-result marker found in $log" >&2
    return 1
  fi
}
