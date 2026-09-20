#!/usr/bin/env bash
# 消融梯子(用户 2026-09-20 批准):psydef × 02 × luna,从原生流水线出发逐档加回我们的改动。
# 用法: launch_tier.sh <档位 1-4> <重复序号>   (第 0 档 = 已有的原生臂 B)
# 只跑 ideation + stage 1;stage 1 结束由外部看护(watch_tier.sh)停容器。诊断用途,不进计分板。
set -euo pipefail
TIERARG="${1:?tier, e.g. 2a or 2b}"; REP="${2:?rep}"
TIER="${TIERARG%[ab]}"; ARM="${TIERARG#$TIER}"; ARM="${ARM:-a}"
PUB=/data/daweiwang/claude-home/researchclaweval-public
SP=/tmp/claude-0/-root-researchclaweval-public/51dbc20a-062b-4219-ba2a-1b69cde17c93/scratchpad
TS=$(date +%Y%m%d_%H%M%S)
RUN=$PUB/real_eval/runs/control_tier${TIER}${ARM}_rep${REP}_psydef02_luna_${TS}
WS=$RUN/workspace; INP=$RUN/inputs
mkdir -p "$WS" "$RUN/logs" "$INP"
rsync -a --exclude .git --exclude experiments --exclude "ai_scientist/ideas/my_research_topic.md" --exclude "ai_scientist/ideas/topic2_topic.md" "$PUB/AI-Scientist-v2/" "$WS/"
mkdir -p "$WS/real_eval/adapters/ai_scientist_v2" "$WS/real_eval/adapters/tdc_admet_tox" "$WS/tier"
cp "$PUB/real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py" \
   "$PUB/real_eval/adapters/ai_scientist_v2/patch_semantic_scholar_bounded.py" \
   "$PUB/real_eval/adapters/ai_scientist_v2/patch_prompt_logging.py" "$WS/real_eval/adapters/ai_scientist_v2/"
cp "$PUB/real_eval/adapters/tdc_admet_tox/patch_ai_scientist_v2.py" "$WS/real_eval/adapters/tdc_admet_tox/"
cp "$SP/tier/tier_apply.py" "$WS/tier/"
python3 "$SP/tier/tier_build.py" "$TIERARG" "$REP" "$WS" "$PUB"
cp "$SP/tier/launch_tier.sh" "$SP/tier/tier_build.py" "$SP/tier/tier_apply.py" "$RUN/"   # snapshot of what ran

# ---- topic input for ideation ----
PROVIDER_ENV=$PUB/real_eval/runs/fullrun_arc_02_luna_20260917_085638/provider.env
if [ "$TIER" -ge 1 ]; then
  python3 "$PUB/automation/scripts/generate_psydefdetect_native_inputs.py" \
    --output-root "$INP" --dataset-root "$PUB/data/psydefdetect" \
    --contract-file "$PUB/automation/psydefdetect_contract.md" \
    --provider-base-url "$(grep -E '^OPENAI_BASE_URL=' "$PROVIDER_ENV" | cut -d= -f2-)" \
    --primary-model gpt-5.6-luna >/dev/null
  if [ "$TIER" = "2" ] && [ "$ARM" = "b" ]; then
    # native-form input pair: theme-style topic file for ideation + host loader as "Code To Use"
    cp "$SP/tier/psydefdetect_native.md" "$WS/ai_scientist/ideas/psydefdetect_native.md"
    cp "$SP/tier/psydefdetect_native.py" "$WS/ai_scientist/ideas/psydefdetect_native.py"
    TOPIC_MD=ai_scientist/ideas/psydefdetect_native.md; IDEAS_JSON=ai_scientist/ideas/psydefdetect_native.json; LOAD_CODE=--load_code
  else
    cp "$INP/AI-Scientist-v2/ai_scientist/ideas/psydefdetect_topic.md" "$WS/ai_scientist/ideas/psydefdetect_topic.md"
    TOPIC_MD=ai_scientist/ideas/psydefdetect_topic.md; IDEAS_JSON=ai_scientist/ideas/psydefdetect_topic.json; LOAD_CODE=
  fi
else
  TOPIC_MD=ai_scientist/ideas/i_cant_believe_its_not_better.md; IDEAS_JSON=ai_scientist/ideas/i_cant_believe_its_not_better.json; LOAD_CODE=
  rm -f "$WS/$IDEAS_JSON"
fi
# ---- real data / split / scorer (tier >= 1), mounted exactly like the production runner ----
# (2026-09-20 correction: our topic file points at the fixed dataset, so tier 1 without the data only
#  produces unsatisfiable ideas; the data ships with the input channel, the guideline FACTS stay tier 2)
DATA_ARGS=()
if [ "$TIER" -ge 1 ]; then
  mkdir -p "$WS/automation" "$WS/data"
  rsync -a "$INP/automation/" "$WS/automation/"
  cp "$PUB/automation/psydefdetect_contract.md" "$WS/automation/psydefdetect_contract.md"
  ln -sfn /data/psydefdetect "$WS/data/psydefdetect"
  DATA_ARGS=(-v "$PUB/data/psydefdetect:/data/psydefdetect:ro")
fi
echo "$RUN" > "$SP/current_tier"
NAME=control_tier${TIER}${ARM}_rep${REP}_${TS}; echo "$NAME" > "$SP/current_tier_container"
python3 - "$RUN/state.json" "$TIER" "$REP" <<'PY'
import json,sys,datetime
json.dump({"project_id":"control_tier_psydef02_luna","phase":"diagnostic","status":"running","summary":f"ablation ladder tier {sys.argv[2]} rep {sys.argv[3]}: native pipeline + cumulative contract pieces, stage 1 only","updated_at":datetime.datetime.now(datetime.UTC).isoformat()},open(sys.argv[1],"w"),indent=2)
PY
# 2026-09-20: physical GPU 5 is now busy with another tenant (99% util) -> the ladder runs CPU-only
# (psydef is sklearn/CPU; the native toy nodes ran at 0% GPU in arm B). Deviation recorded in tier docs.
docker run --rm --name "$NAME" --cpus 8 --shm-size 8g \
  -v "$WS":/workspace -w /workspace "${DATA_ARGS[@]}" --env-file "$PROVIDER_ENV" \
  -e HF_ENDPOINT=https://hf-mirror.com -e PYTHONUNBUFFERED=1 -e CUDA_VISIBLE_DEVICES= -e PROMPT_LOG_DIR=/workspace/prompt_logs -e TOPIC_MD="$TOPIC_MD" -e IDEAS_JSON="$IDEAS_JSON" -e TIER="$TIER" -e LOAD_CODE="$LOAD_CODE" \
  ai-scientist-v2:runtime-ready bash -lc '
set -euo pipefail
echo "CONTROL_TIER tier=$TIER model=$OPENAI_MODEL topic=$TOPIC_MD load_code=[$LOAD_CODE]"
python3 tier/tier_apply.py
if [ "$TIER" -ge 4 ]; then export AI_SCIENTIST_PSYDEFDETECT_TWO_EXPERIMENTS=1; fi
grep -n "num_workers\|stage1_max_iters\|num_drafts\|debug_prob\|timeout:" bfts_config.yaml
rm -f "$IDEAS_JSON"
timeout 1800s python ai_scientist/perform_ideation_temp_free.py --workshop-file "$TOPIC_MD" --model "$OPENAI_MODEL" --max-num-generations 2 --num-reflections 5
python3 -c "import json;d=json.load(open(\"$IDEAS_JSON\"));print(\"NATIVE_IDEAS\",len(d));[print(\" idea\",i,\":\",x[\"Title\"]) for i,x in enumerate(d)]"
echo "NATIVE_BFTS_START"
python launch_scientist_bfts.py --load_ideas "$IDEAS_JSON" --idea_idx 0 $LOAD_CODE \
  --model_writeup "$OPENAI_MODEL" --model_citation "$OPENAI_MODEL" --model_review "$OPENAI_MODEL" --model_agg_plots "$OPENAI_MODEL" --num_cite_rounds 0
' 2>&1 | tee "$RUN/logs/native.log" "$SP/tier${TIER}${ARM}_rep${REP}_${TS}.log"
