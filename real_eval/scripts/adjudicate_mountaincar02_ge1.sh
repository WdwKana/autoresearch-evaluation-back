#!/usr/bin/env bash
# Retroactive >=1 adjudication for retained 02 MountainCar runs that failed at the
# old 2-stage-selection assembly floor (2026-09-28 user approval). Mirrors the
# staged e2e launcher's assemble -> host-validate -> host-score chain, with
# --workspace pointing READ-ONLY at the retained run workspace (assembly writes
# only under --out) and every product under the adjudication directory.
# Candidates (journal sweep 2026-09-28): each has exactly 1 stage selection and
# 0 stages with official records; kimi rep1 (4 selections) is not a candidate.
set -uo pipefail

PUB=/data/daweiwang/claude-home/researchclaweval-public
SP=/tmp/claude-0/-root-researchclaweval-public/51dbc20a-062b-4219-ba2a-1b69cde17c93/scratchpad
STAGED=$SP/staged/mountaincar
DATA=$PUB/data/mountaincar_continuous
ADJROOT=$PUB/real_eval/runs/adjudication_mcar02_ge1_20260928
BASE_URL=https://api.bianxie.ai/v1

adjudicate() {
  local tag=$1 run=$2 model=$3
  local ws=$PUB/real_eval/runs/$run/workspace
  local adj=$ADJROOT/$tag
  if [ -s "$adj/verdict.json" ]; then
    echo "== [$tag] verdict already recorded; skipping"
    return 0
  fi
  echo "== [$tag] source run: $run"
  mkdir -p "$adj/out" "$adj/logs"

  python3 "$STAGED/assemble_mountaincar.py" --workspace "$ws" --out "$adj/out" \
    --model "$model" --base-url "$BASE_URL" --data-root "$DATA" \
    >"$adj/logs/assembly.log" 2>&1
  local asm_rc=$?
  echo "   assembly rc=$asm_rc ($(tail -1 "$adj/logs/assembly.log" | cut -c1-120))"

  local val_rc=-1 score_rc=-1
  if [ "$asm_rc" -eq 0 ]; then
    python3 "$STAGED/mountaincar_host_validate.py" "$adj/out" "$model" "$BASE_URL" \
      >"$adj/logs/host_validation.log" 2>&1
    val_rc=$?
    echo "   validation rc=$val_rc"
    if [ "$val_rc" -eq 0 ]; then
      python3 "$PUB/automation/scripts/run_mountaincar_continuous_host_score.py" \
        --workspace "$adj/out" --output-score "$adj/out/score.json" \
        --dataset-root "$DATA" --python "$STAGED/mc_python.sh" \
        --config-fname src/config.yaml >"$adj/logs/official_score.log" 2>&1
      score_rc=$?
      echo "   score rc=$score_rc"
    fi
  fi

  python3 - "$adj" "$run" "$model" "$asm_rc" "$val_rc" "$score_rc" <<'PROV'
import json, subprocess, sys, datetime
adj, run, model, asm_rc, val_rc, score_rc = sys.argv[1:7]
sha = subprocess.run(["git", "-C", "/data/daweiwang/claude-home/researchclaweval-public",
                      "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
score = None
try:
    score = json.load(open(f"{adj}/out/score.json"))
except Exception:
    pass
json.dump({
    "adjudication": "mcar02_ge1_20260928",
    "source_run": run,
    "source_workspace_untouched": True,
    "model": model,
    "assembly_version": f"assemble_mountaincar.py @ {sha} (stage-selection floor >=1)",
    "decision_refs": ["2026-09-28 user approvals: 02 assembly floor >=1 / retro adjudication of floor-blocked runs"],
    "assembly_rc": int(asm_rc),
    "validation_rc": int(val_rc),
    "score_rc": int(score_rc),
    "score": score,
    "adjudicated_at": datetime.datetime.now().isoformat(timespec="seconds"),
}, open(f"{adj}/verdict.json", "w"), indent=2)
print("   verdict:", json.dumps({"assembly_rc": int(asm_rc), "validation_rc": int(val_rc),
      "score_rc": int(score_rc), "score": (score or {}).get("score")}))
PROV
}

adjudicate luna_085312 control_e2emcar_rep1_mcar02_luna_20260924_085312 gpt-5.6-luna
adjudicate ds_055912  control_e2emcar_rep1_mcar02_ds_20260927_055912  deepseek-v4-flash
adjudicate ds_132821  control_e2emcar_rep2_mcar02_ds_20260927_132821  deepseek-v4-flash
echo "ADJUDICATION02_DONE"
