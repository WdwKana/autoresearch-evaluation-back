#!/usr/bin/env bash
# ARC 端到端 rep 2(诊断):与 rep 1 完全相同,只换 (i) 参考模块 v2(进程内验证 + 打包 + 默认 20 条记录)和 (ii) 主题 v2(结果只定义在提供的记录上)。
#   ideation(challenge 说明体) -> research_idea.json(BFTS 前,从 idea 映射) -> BFTS stage 1-4(20/6/6/2,种子 1)
#   -> 容器退出 -> host 组装(复现各阶段 best_solution,提升 estimator.py + submission.json,trace,报告)
#   -> host 官方打分(whest 官方 adapter -> score.json) -> host 校验(从 ARC runner 逐行抽出)。
# 用法: launch_e2e_arc_v2.sh <rep>
set -euo pipefail
REP="${1:?rep}"; TAG="${2:?model tag}"; PROVIDER_ENV="${3:?provider env}"
MODEL="$(grep -E '^OPENAI_MODEL=' "$PROVIDER_ENV" | cut -d= -f2-)"
VLM_MODEL="${VLM_MODEL:-}"   # optional vision-capable model for the plot-feedback step only
RUN_TIMEOUT="${RUN_TIMEOUT:-86400}"   # native wall-clock cap in seconds (watchdog stops the container)
PUB=/data/daweiwang/claude-home/researchclaweval-public
SP=/tmp/claude-0/-root-researchclaweval-public/51dbc20a-062b-4219-ba2a-1b69cde17c93/scratchpad
DATA=/data/daweiwang/claude-home/researchclaweval-public/data/arc_white_box_estimation_2026
WHEST=/data/daweiwang/claude-home/whest-starterkit/.venv
GPU="${ARC_GPU:-5}"   # "none" = CPU-only (used when GPU 5 is busy with another tenant)
TS=$(date +%Y%m%d_%H%M%S)
RUN=$PUB/real_eval/runs/control_e2earc_rep${REP}_arc02_${TAG}_${TS}
WS=$RUN/workspace; INP=$RUN/inputs
mkdir -p "$WS" "$RUN/logs" "$INP"
rsync -a --exclude .git --exclude experiments --exclude "ai_scientist/ideas/my_research_topic.md" --exclude "ai_scientist/ideas/topic2_topic.md" "$PUB/AI-Scientist-v2/" "$WS/"
mkdir -p "$WS/real_eval/adapters/ai_scientist_v2" "$WS/real_eval/adapters/tdc_admet_tox" "$WS/tier" "$WS/automation/scripts" "$WS/data"
cp "$PUB/real_eval/adapters/ai_scientist_v2/patch_ideation_action_format.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_ideation_tolerant_parser.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_semantic_scholar_bounded.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_remove_synthetic_data_guideline.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_remove_hf_dataset_goals.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_prompt_logging.py" "$WS/real_eval/adapters/ai_scientist_v2/"
cp "$PUB/real_eval/adapters/tdc_admet_tox/patch_ai_scientist_v2.py" "$WS/real_eval/adapters/tdc_admet_tox/"
cp "$SP/tier/tier_apply.py" "$WS/tier/"
python3 "$SP/tier/tier_build.py" 0 "$REP" "$WS" "$PUB" >/dev/null
python3 - "$WS/tier/tier.json" "$TAG" "$VLM_MODEL" <<'PY'
import json,sys; p=sys.argv[1]; T=json.load(open(p)); T.update(arm="e2e-arc-v2",model_tag=sys.argv[2],vlm_model_override=(sys.argv[3] or None),ideation_patches="label normalization, tolerant parser, MAX_NUM_TOKENS 16384, retry x3",topic_input="arc_wbe_2026_native_v2.md (theme + results-on-provided-records rule) + hf_dataset_reference.py (arc_reference_v2: in-process validation, packaging, 20-record default)",data_mounted=True,stages_open="1-4 (20/6/6/2)",assembly="host deterministic (assemble_arc.py) + official adapter scoring"); json.dump(T,open(p,"w"),ensure_ascii=False,indent=1)
PY
BASE_URL="$(grep -E '^OPENAI_BASE_URL=' "$PROVIDER_ENV" | cut -d= -f2-)"
cp "$PUB/automation/arc_wbe_2026_contract.md" "$WS/automation/"; cp "$PUB/automation/scripts/run_arc_wbe_2026_local_score.py" "$PUB/automation/scripts/arc_wbe_2026_official_adapter.py" "$WS/automation/scripts/"
ln -sfn /data/arc_wbe_2026 "$WS/data/arc_wbe_2026"
cp "$SP/staged/arc/arc_wbe_2026_native_v2.md" "$WS/ai_scientist/ideas/arc_wbe_2026_native.md"
cp "$SP/staged/arc/arc_reference_v2.py" "$WS/hf_dataset_reference.py"
cp "$SP/staged/arc/launch_e2e_arc_model.sh" "$SP/staged/arc/assemble_arc.py" "$SP/staged/arc/arc_host_validate.py" "$SP/staged/arc/arc_reference_v2.py" "$SP/staged/arc/arc_wbe_2026_native_v2.md" "$SP/tier/tier_apply.py" "$RUN/"
echo "$RUN" > "$SP/current_e2earc_${TAG}"; NAME=control_e2earc_${TAG}_rep${REP}_${TS}; echo "$NAME" > "$SP/current_e2earc_${TAG}_container"
python3 - "$RUN/state.json" "$REP" "$TAG" "$VLM_MODEL" <<'PY'
import json,sys,datetime,os
json.dump({"project_id":"control_e2earc_arc02_"+sys.argv[3],"phase":"diagnostic","status":"running","summary":f"ARC end-to-end rep {sys.argv[2]} model={sys.argv[3]} vlm_override={sys.argv[4] or 'none'} (v2: reference in-process validation + results-on-provided-records rule): challenge-style theme, reference loader via dataset-reference slot, stages 1-4 (ARC_GPU={os.environ.get('ARC_GPU','5')}), host deterministic assembly + official adapter scoring + validation","updated_at":datetime.datetime.now(datetime.UTC).isoformat()},open(sys.argv[1],"w"),indent=2)
PY
set +e
GPU_ARGS=(); CUDA_ENV=(); if [ "$GPU" = "none" ]; then CUDA_ENV=(-e CUDA_VISIBLE_DEVICES=); else GPU_ARGS=(--gpus "device=$GPU"); fi
( sleep "${RUN_TIMEOUT}"; docker stop -t 30 "$NAME" >/dev/null 2>&1 && echo "[e2e-arc] time cap reached: container stopped" ) & WATCHDOG=$!
timeout "${RUN_TIMEOUT}s" docker run --rm --name "$NAME" "${GPU_ARGS[@]}" "${CUDA_ENV[@]}" --cpus 32 --memory 64g --shm-size 16g \
  -v "$WS":/workspace -w /workspace -v "$DATA:/data/arc_wbe_2026:ro" --env-file "$PROVIDER_ENV" \
  -e HF_HUB_OFFLINE=1 -e HF_DATASETS_OFFLINE=1 -e OMP_NUM_THREADS=32 -e MKL_NUM_THREADS=32 -e OPENBLAS_NUM_THREADS=32 -e TORCH_NUM_THREADS=32 -e VLM_MODEL="$VLM_MODEL" -e PYTHONUNBUFFERED=1 -e PROMPT_LOG_DIR=/workspace/prompt_logs \
  ai-scientist-v2:runtime-ready bash -lc '
set -euo pipefail
echo "CONTROL_E2E_ARC model=$OPENAI_MODEL gpu=$(nvidia-smi -L 2>/dev/null | head -1) cuda_visible=${CUDA_VISIBLE_DEVICES-unset}"
python3 tier/tier_apply.py
python3 real_eval/adapters/ai_scientist_v2/patch_ideation_action_format.py
python3 real_eval/adapters/ai_scientist_v2/patch_ideation_tolerant_parser.py
python3 - <<PY
from pathlib import Path
llm = Path("ai_scientist/llm.py"); text = llm.read_text(encoding="utf-8")
if "MAX_NUM_TOKENS = 4096" not in text and "MAX_NUM_TOKENS = 16384" not in text: raise SystemExit("MAX_NUM_TOKENS anchor not found")
llm.write_text(text.replace("MAX_NUM_TOKENS = 4096", "MAX_NUM_TOKENS = 16384"), encoding="utf-8"); print("ideation MAX_NUM_TOKENS = 16384")
PY
python3 - <<PY
import yaml
p="bfts_config.yaml"; c=yaml.safe_load(open(p))
c["agent"]["stages"].update({"stage1_max_iters":20,"stage2_max_iters":6,"stage3_max_iters":6,"stage4_max_iters":2})
c["agent"]["multi_seed_eval"]["num_seeds"]=1
import os
if os.environ.get("VLM_MODEL"): c["agent"]["vlm_feedback"]["model"]=os.environ["VLM_MODEL"]; print("VLM (plot feedback) model override:", c["agent"]["vlm_feedback"]["model"])
yaml.safe_dump(c,open(p,"w"),sort_keys=False); print("stage iters 20/6/6/2, num_seeds 1, generate_report", c.get("generate_report"))
PY
for ideation_attempt in 1 2 3; do
  rm -f ai_scientist/ideas/arc_wbe_2026_native.json
  timeout 1800s python ai_scientist/perform_ideation_temp_free.py --workshop-file ai_scientist/ideas/arc_wbe_2026_native.md --model "$OPENAI_MODEL" --max-num-generations 2 --num-reflections 5 || true
  if python3 -c "import json,sys; d=json.load(open('"'"'ai_scientist/ideas/arc_wbe_2026_native.json'"'"')); sys.exit(0 if isinstance(d, list) and d else 1)" 2>/dev/null; then echo "IDEATION_OK attempt $ideation_attempt"; break; fi
  echo "IDEATION_EMPTY attempt $ideation_attempt"
done
test -s ai_scientist/ideas/arc_wbe_2026_native.json
python3 - <<PY
import json
ideas=json.load(open("ai_scientist/ideas/arc_wbe_2026_native.json")); print("NATIVE_IDEAS",len(ideas)); [print(" idea",i,":",x["Title"]) for i,x in enumerate(ideas)]
idea=ideas[0]
ri={"framework":"AI-Scientist-v2","source_artifact":"ai_scientist/ideas/arc_wbe_2026_native.json","hypothesis":idea.get("Short Hypothesis") or idea.get("Abstract",""),"method_rationale":idea.get("Experiments",""),"expected_failure_modes":idea.get("Risk Factors and Limitations") or "","comparison_logic":idea.get("Experiments",""),"native_idea":idea}
json.dump(ri,open("/workspace/research_idea.json","w"),ensure_ascii=False,indent=2); print("RESEARCH_IDEA_LOCKED (mapped from the framework idea before BFTS)")
PY
echo "NATIVE_BFTS_START"
python launch_scientist_bfts.py --load_ideas ai_scientist/ideas/arc_wbe_2026_native.json --idea_idx 0 --add_dataset_ref \
  --model_writeup "$OPENAI_MODEL" --model_citation "$OPENAI_MODEL" --model_review "$OPENAI_MODEL" --model_agg_plots "$OPENAI_MODEL" --num_cite_rounds 0 --skip_writeup --skip_review
echo "NATIVE_BFTS_END"
' 2>&1 | tee "$RUN/logs/native.log" "$SP/e2earc_${TAG}_rep${REP}_${TS}.log"
native_rc=${PIPESTATUS[0]}
kill "$WATCHDOG" 2>/dev/null; wait "$WATCHDOG" 2>/dev/null
echo "[e2e-arc] native exit code: $native_rc"
echo "[e2e-arc] host assembly ..."
python3 "$SP/staged/arc/assemble_arc.py" --workspace "$WS" --out "$WS" --model "$MODEL" --base-url "$BASE_URL" --data-root "$DATA" --gpu "$GPU" 2>&1 | tee "$RUN/logs/assembly.log"
asm_rc=${PIPESTATUS[0]}
echo "[e2e-arc] assembly exit code: $asm_rc"
score_rc=1
if [ "$asm_rc" -eq 0 ]; then
  echo "[e2e-arc] host official scoring (whest adapter) ..."
  "$WHEST/bin/python" "$PUB/automation/scripts/run_arc_wbe_2026_local_score.py" --workspace "$WS" --output-score "$WS/score.json" --dataset-root "$DATA" --framework-hint AI-Scientist-v2 --whest-bin "$WHEST/bin/whest" > "$RUN/logs/official_score.log" 2>&1
  score_rc=$?
  echo "[e2e-arc] official scoring exit code: $score_rc"; tail -3 "$RUN/logs/official_score.log" | cut -c1-200
fi
echo "[e2e-arc] host validation ..."
python3 "$SP/staged/arc/arc_host_validate.py" "$WS" "$MODEL" 2>&1 | tee "$RUN/logs/host_validation.log"
val_rc=${PIPESTATUS[0]}
echo "[e2e-arc] validation exit code: $val_rc"
python3 - "$RUN/state.json" "$native_rc" "$asm_rc" "$score_rc" "$val_rc" <<'PY'
import json,sys,datetime
d=json.load(open(sys.argv[1])); n,a,s,v=map(int,sys.argv[2:6])
d.update(status=("finished" if (a==0 and s==0 and v==0) else "failed"),native_exit_code=n,assembly_exit_code=a,official_score_exit_code=s,validation_exit_code=v,summary=d["summary"]+f" | ended: native={n} assembly={a} score={s} validation={v}",updated_at=datetime.datetime.now(datetime.UTC).isoformat()); json.dump(d,open(sys.argv[1],"w"),indent=2)
print("E2E_ARC_DONE native=%d assembly=%d score=%d validation=%d"%(n,a,s,v))
PY
