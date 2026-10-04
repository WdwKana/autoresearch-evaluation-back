#!/usr/bin/env bash
# Retroactive adjudication of retained 01 MountainCar runs under the unified
# ">=1 experiments" contract (2026-09-28 user decision; see grill-decisions Q10 and
# the 2026-09-28 rulings). Scope: runs whose ONLY gate failure was the former 2-4
# experiment count. The original run directories are never modified: required
# artifacts are copied into a fresh adjudication workspace, the delivery gate is
# extracted verbatim from the runner 01 actually runs -- the shared runner plus 01's
# patch (real_eval/adapters/ai_researcher/shared_layer_patches/) -- and the
# official frozen scorer runs inside the same JAX image the framework trained in.
set -euo pipefail

ROOT=/data/daweiwang/claude-home/researchclaweval-public
RUNNER=real_eval/scripts/mountaincar_framework_fullrun.sh
DATASET="${MOUNTAINCAR_CONTINUOUS_DATASET_ROOT:-$ROOT/data/mountaincar_continuous}"
IMG=ai-researcher-exec:mountaincar-jax
BASE_URL=https://api.bianxie.ai/v1
ADJROOT="$ROOT/real_eval/runs/adjudication_mcar01_ge1_20260928"

adjudicate() {
  local tag=$1 run=$2 model=$3 base=${4:-$BASE_URL}
  local src="$ROOT/real_eval/runs/$run/workspace"
  local adj="$ADJROOT/$tag"
  if [ -s "$adj/verdict.json" ]; then
    echo "== [$tag] verdict already recorded; skipping (delete verdict.json to re-adjudicate)"
    return 0
  fi
  echo "== [$tag] source run: $run"
  mkdir -p "$adj/workspace" "$adj/logs"

  for f in research_idea.json experiment_trace.json final_report.md evaluate.py; do
    cp "$src/$f" "$adj/workspace/$f"
  done
  cp -r "$src/src" "$adj/workspace/src"
  cp -r "$src/checkpoints" "$adj/workspace/checkpoints"

  # Gate logic extracted verbatim from the patched runner heredoc (line ~260).
  python3 "$ROOT/real_eval/adapters/shared_layer_overlay.py" show ai_researcher "$RUNNER" > "$adj/runner_patched.sh"
  awk '/python3 - "\$WORKSPACE" "\$MC_MODEL" "\$FRAMEWORK_PROVIDER_BASE_URL"/{f=1;next} f&&/^PY$/{exit} f' \
    "$adj/runner_patched.sh" > "$adj/gate_extracted.py"
  [ -s "$adj/gate_extracted.py" ] || { echo "[$tag] gate extraction failed"; return 1; }

  local gate_rc=0
  python3 "$adj/gate_extracted.py" "$adj/workspace" "$model" "$base" \
    >"$adj/logs/gate.log" 2>&1 || gate_rc=$?
  echo "   gate rc=$gate_rc ($(tail -1 "$adj/logs/gate.log" 2>/dev/null || true))"

  local score_rc=-1
  if [ "$gate_rc" -eq 0 ]; then
    score_rc=0
    timeout 3600 docker run --rm --name "adjudicate_mcar_${tag}_$$" --network none --cpus 32 \
      -v "$adj/workspace":/adjwork \
      -v "$ROOT/automation":/automation:ro \
      -v "$DATASET":/dataset:ro \
      "$IMG" python /automation/scripts/run_mountaincar_continuous_host_score.py \
        --workspace /adjwork --output-score /adjwork/score.json \
        --dataset-root /dataset --python python --config-fname src/config.yaml \
      >"$adj/logs/official_score.log" 2>&1 || score_rc=$?
    echo "   score rc=$score_rc"
  fi

  python3 - "$adj" "$run" "$model" "$gate_rc" "$score_rc" <<'PROV'
import json, subprocess, sys, datetime
adj, run, model, gate_rc, score_rc = sys.argv[1:6]
sha = subprocess.run(["git", "-C", "/data/daweiwang/claude-home/researchclaweval-public",
                      "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
score = None
try:
    score = json.load(open(f"{adj}/workspace/score.json"))
except Exception:
    pass
json.dump({
    "adjudication": "mcar01_ge1_20260928",
    "source_run": run,
    "source_workspace_untouched": True,
    "model": model,
    "gate_version": f"mountaincar_framework_fullrun.sh + 01 shared-layer patch @ {sha} (>=1)",
    "decision_refs": ["grill Q10", "2026-09-28 user approvals: gate>=1 / wrapper wording removal / retro adjudication"],
    "gate_rc": int(gate_rc),
    "score_rc": int(score_rc),
    "score": score,
    "adjudicated_at": datetime.datetime.now().isoformat(timespec="seconds"),
}, open(f"{adj}/verdict.json", "w"), indent=2)
print("   verdict:", json.dumps({"gate_rc": int(gate_rc), "score_rc": int(score_rc),
      "score": (score or {}).get("score")}))
PROV
}

adjudicate luna_121831 fullrun_mcar_01_luna_20260924_121831 gpt-5.6-luna
adjudicate ds_124914  fullrun_mcar_01_ds_20260927_124914  deepseek-v4-flash
# kimi added 2026-09-28 on explicit user approval: run was terminated pre-gate
# (container-level stop), all five deliverables present, trace records 1 experiment.
adjudicate kimi_044203 fullrun_mcar_01_kimi_20260928_044203 kimi-k2.6
# g6 rep2 added 2026-10-02: the run completed its research with all deliverables
# (5 checkpoints, idea/trace/report, trace model=gpt-6-luna correct) but the
# in-container gate compared the trace against the wrong expected model
# (gpt-5.6-luna from the .env default) and rejected it with 42 -- host-side
# defect, not a framework failure. Adjudicate under the run's actual model.
adjudicate g6_113815 fullrun_mcar_01_g6luna_rep2_20260928_113815 gpt-6-luna
# kimi 163455 added 2026-10-04: the run passed the in-run delivery gate (5 checkpoints,
# idea fields, trace model/base URL correct) and was then failed with exit 43 because
# the host scorer ran evaluate.py with the host python, which has no JAX/gymnax
# ("No module named gymnax") -- host scoring-environment defect. Provider is paratera.
adjudicate kimi_163455 fullrun_mcar_01_kimi_20261003_163455 Kimi-K2.6 https://llmapi.paratera.com/v1
echo "ADJUDICATION_DONE"
