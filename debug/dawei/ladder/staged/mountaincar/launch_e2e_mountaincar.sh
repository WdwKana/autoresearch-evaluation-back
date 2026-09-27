#!/usr/bin/env bash
# MountainCar 端到端(诊断,不进计分板):mountaincar_continuous × 02 × <model>,规格体路线(正式 topic2_topic.md 由 generate_mountaincar_continuous_native_inputs.py 生成)。
#   参考模块 mountaincar_reference_v1 走 --add_dataset_ref 槽;BFTS stage 1-4(20/6/6/2)在 JAX CPU 运行镜像 ai-scientist-v2:runtime-mountaincar 里,32 核;
#   容器退出 -> host 组装(复现各阶段 best_solution,选官方 Reward Mean 最高者,提升 src/、checkpoints/、evaluate.py、trace、报告)
#   -> host 校验(从 mountaincar runner 逐行抽出)-> host 打分(run_mountaincar_continuous_host_score.py,--python 指向镜像内的 python)。
# 用法: launch_e2e_mountaincar.sh <rep> <tag> <provider_env>   (可选 VLM_MODEL=..., RUN_TIMEOUT=秒,默认 86400)
set -euo pipefail
REP="${1:?rep}"; TAG="${2:?model tag}"; PROVIDER_ENV="${3:?provider env}"
MODEL="$(grep -E '^OPENAI_MODEL=' "$PROVIDER_ENV" | cut -d= -f2-)"
VLM_MODEL="${VLM_MODEL:-}"
RUN_TIMEOUT="${RUN_TIMEOUT:-86400}"
PUB=/data/daweiwang/claude-home/researchclaweval-public
SP=/tmp/claude-0/-root-researchclaweval-public/51dbc20a-062b-4219-ba2a-1b69cde17c93/scratchpad
DATA=/data/daweiwang/claude-home/researchclaweval-public/data/mountaincar_continuous
IMAGE=ai-scientist-v2:runtime-mountaincar
TS=$(date +%Y%m%d_%H%M%S)
RUN=$PUB/real_eval/runs/control_e2emcar_rep${REP}_mcar02_${TAG}_${TS}
WS=$RUN/workspace; INP=$RUN/inputs
mkdir -p "$WS" "$RUN/logs" "$INP"
rsync -a --exclude .git --exclude experiments --exclude "ai_scientist/ideas/my_research_topic.md" --exclude "ai_scientist/ideas/topic2_topic.md" "$PUB/AI-Scientist-v2/" "$WS/"
mkdir -p "$WS/real_eval/adapters/ai_scientist_v2" "$WS/real_eval/adapters/tdc_admet_tox" "$WS/tier" "$WS/automation/scripts" "$WS/data"
cp "$PUB/real_eval/adapters/ai_scientist_v2/patch_ideation_action_format.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_ideation_tolerant_parser.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_semantic_scholar_bounded.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_remove_synthetic_data_guideline.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_remove_hf_dataset_goals.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_prompt_logging.py" "$WS/real_eval/adapters/ai_scientist_v2/"
cp "$PUB/real_eval/adapters/tdc_admet_tox/patch_ai_scientist_v2.py" "$WS/real_eval/adapters/tdc_admet_tox/"
cp "$SP/tier/tier_apply.py" "$WS/tier/"
python3 "$SP/tier/tier_build.py" 0 "$REP" "$WS" "$PUB" >/dev/null
python3 - "$WS/tier/tier.json" "$TAG" "$VLM_MODEL" <<'PY'
import json,sys; p=sys.argv[1]; T=json.load(open(p)); T.update(arm="e2e-mountaincar-spec",model_tag=sys.argv[2],vlm_model_override=(sys.argv[3] or None),image="ai-scientist-v2:runtime-mountaincar",cpus=32,stage_iters="20/6/6/2",ideation_patches="label normalization, tolerant parser, MAX_NUM_TOKENS 16384, retry x3",topic_input="topic2_topic.md (production spec, generate_mountaincar_continuous_native_inputs.py) + hf_dataset_reference.py (mountaincar_reference_v1: starter copy, starter training, frozen-evaluator official_evaluation, submission keeper)",data_mounted=True,stages_open="1-4 (20/6/6/2)",assembly="host deterministic (assemble_mountaincar.py) + frozen evaluate.py via image"); json.dump(T,open(p,"w"),ensure_ascii=False,indent=1)
PY
BASE_URL="$(grep -E '^OPENAI_BASE_URL=' "$PROVIDER_ENV" | cut -d= -f2-)"
python3 "$PUB/automation/scripts/generate_mountaincar_continuous_native_inputs.py" --output-root "$INP" --dataset-root "$DATA" --contract-file "$PUB/automation/topic2_contract.md" --provider-base-url "$BASE_URL" --primary-model "$MODEL" --no-gpu-required >/dev/null
cp "$INP/AI-Scientist-v2/ai_scientist/ideas/topic2_topic.md" "$WS/ai_scientist/ideas/mountaincar_topic.md"
ln -sfn /data/mountaincar_continuous "$WS/data/mountaincar_continuous"
cp "$SP/staged/mountaincar/mountaincar_reference_v1.py" "$WS/hf_dataset_reference.py"
cp "$SP/staged/mountaincar/launch_e2e_mountaincar.sh" "$SP/staged/mountaincar/assemble_mountaincar.py" "$SP/staged/mountaincar/mountaincar_host_validate.py" "$SP/staged/mountaincar/mountaincar_reference_v1.py" "$SP/staged/mountaincar/mc_python.sh" "$WS/ai_scientist/ideas/mountaincar_topic.md" "$SP/tier/tier_apply.py" "$PUB/automation/topic2_contract.md" "$RUN/"
echo "$RUN" > "$SP/current_e2emcar_${TAG}"; NAME=control_e2emcar_${TAG}_rep${REP}_${TS}; echo "$NAME" > "$SP/current_e2emcar_${TAG}_container"
python3 - "$RUN/state.json" "$REP" "$TAG" "$VLM_MODEL" <<'PY'
import json,sys,datetime
json.dump({"project_id":"control_e2emcar_mcar02_"+sys.argv[3],"phase":"diagnostic","status":"running","summary":f"MountainCar end-to-end SPEC arm rep {sys.argv[2]} model={sys.argv[3]} vlm_override={sys.argv[4] or 'none'}: production spec topic, reference module via dataset-reference slot, stages 1-4 (20/6/6/2) on CPU in the JAX runtime image, host deterministic assembly + host validation + frozen-evaluator scoring","updated_at":datetime.datetime.now(datetime.UTC).isoformat()},open(sys.argv[1],"w"),indent=2)
PY
set +e
( sleep "${RUN_TIMEOUT}"; docker stop -t 30 "$NAME" >/dev/null 2>&1 && echo "[e2e-mcar] time cap reached: container stopped" ) & WATCHDOG=$!
timeout "${RUN_TIMEOUT}s" docker run --rm --name "$NAME" --cpus 32 --memory 64g --shm-size 16g \
  -v "$WS":/workspace -w /workspace -v "$DATA:/data/mountaincar_continuous:ro" -v "$DATA:$DATA:ro" -v "$PUB/automation/topic2_contract.md:$PUB/automation/topic2_contract.md:ro" --env-file "$PROVIDER_ENV" \
  -e CUDA_VISIBLE_DEVICES= -e JAX_PLATFORMS=cpu -e HF_HUB_OFFLINE=1 -e HF_DATASETS_OFFLINE=1 -e OMP_NUM_THREADS=32 -e MKL_NUM_THREADS=32 -e OPENBLAS_NUM_THREADS=32 -e TORCH_NUM_THREADS=32 -e VLM_MODEL="$VLM_MODEL" -e PYTHONUNBUFFERED=1 -e PROMPT_LOG_DIR=/workspace/prompt_logs \
  "$IMAGE" bash -lc '
set -euo pipefail
echo "CONTROL_E2E_MCAR model=$OPENAI_MODEL $(python3 -c "import jax,gymnax;print(\"jax\",jax.__version__)")"
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
import yaml, os
p="bfts_config.yaml"; c=yaml.safe_load(open(p))
c["agent"]["stages"].update({"stage1_max_iters":20,"stage2_max_iters":6,"stage3_max_iters":6,"stage4_max_iters":2})
c["agent"]["multi_seed_eval"]["num_seeds"]=1
if os.environ.get("VLM_MODEL"): c["agent"]["vlm_feedback"]["model"]=os.environ["VLM_MODEL"]; print("VLM (plot feedback) model override:", c["agent"]["vlm_feedback"]["model"])
yaml.safe_dump(c,open(p,"w"),sort_keys=False); print("stage iters 20/6/6/2, exec timeout", c["exec"]["timeout"], ", num_seeds 1, generate_report", c.get("generate_report"))
PY
for ideation_attempt in 1 2 3; do
  rm -f ai_scientist/ideas/mountaincar_topic.json
  timeout 1800s python ai_scientist/perform_ideation_temp_free.py --workshop-file ai_scientist/ideas/mountaincar_topic.md --model "$OPENAI_MODEL" --max-num-generations 2 --num-reflections 5 || true
  if python3 -c "import json,sys; d=json.load(open('"'"'ai_scientist/ideas/mountaincar_topic.json'"'"')); sys.exit(0 if isinstance(d, list) and d else 1)" 2>/dev/null; then echo "IDEATION_OK attempt $ideation_attempt"; break; fi
  echo "IDEATION_EMPTY attempt $ideation_attempt"
done
test -s ai_scientist/ideas/mountaincar_topic.json
python3 - <<PY
import json
ideas=json.load(open("ai_scientist/ideas/mountaincar_topic.json")); print("NATIVE_IDEAS",len(ideas)); [print(" idea",i,":",x.get("Title")) for i,x in enumerate(ideas)]
idea=ideas[0]
ri={"framework":"AI-Scientist-v2","source_artifact":"ai_scientist/ideas/mountaincar_topic.json","hypothesis":idea.get("Short Hypothesis") or idea.get("Abstract",""),"method_rationale":str(idea.get("Experiments","")),"expected_failure_modes":str(idea.get("Risk Factors and Limitations") or ""),"comparison_logic":str(idea.get("Experiments","")),"native_idea":idea}
json.dump(ri,open("/workspace/research_idea.json","w"),ensure_ascii=False,indent=2); print("RESEARCH_IDEA_LOCKED (mapped from the framework idea before BFTS)")
PY
echo "NATIVE_BFTS_START"
python launch_scientist_bfts.py --load_ideas ai_scientist/ideas/mountaincar_topic.json --idea_idx 0 --add_dataset_ref \
  --model_writeup "$OPENAI_MODEL" --model_citation "$OPENAI_MODEL" --model_review "$OPENAI_MODEL" --model_agg_plots "$OPENAI_MODEL" --num_cite_rounds 0 --skip_writeup --skip_review
echo "NATIVE_BFTS_END"
' 2>&1 | tee "$RUN/logs/native.log" "$SP/e2emcar_${TAG}_rep${REP}_${TS}.log"
native_rc=${PIPESTATUS[0]}
kill "$WATCHDOG" 2>/dev/null; wait "$WATCHDOG" 2>/dev/null
echo "[e2e-mcar] native exit code: $native_rc"
if ls "$WS"/{experiment_trace.json,final_report.md,score.json} >/dev/null 2>&1 || [ -d "$WS/checkpoints" ]; then
  mkdir -p "$RUN/native_root_handoff"; for f in experiment_trace.json final_report.md score.json; do [ -f "$WS/$f" ] && cp -p "$WS/$f" "$RUN/native_root_handoff/"; done; [ -d "$WS/checkpoints" ] && cp -r "$WS/checkpoints" "$RUN/native_root_handoff/checkpoints"
  echo "[e2e-mcar] framework-written root files snapshotted: $(ls "$RUN/native_root_handoff" | tr '\n' ' ')"; rm -f "$WS/score.json"
fi
echo "[e2e-mcar] host assembly ..."
python3 "$SP/staged/mountaincar/assemble_mountaincar.py" --workspace "$WS" --out "$WS" --model "$MODEL" --base-url "$BASE_URL" --data-root "$DATA" 2>&1 | tee "$RUN/logs/assembly.log"
asm_rc=${PIPESTATUS[0]}
echo "[e2e-mcar] assembly exit code: $asm_rc"
val_rc=1; score_rc=1
if [ "$asm_rc" -eq 0 ]; then
  echo "[e2e-mcar] host validation ..."
  python3 "$SP/staged/mountaincar/mountaincar_host_validate.py" "$WS" "$MODEL" "$BASE_URL" 2>&1 | tee "$RUN/logs/host_validation.log"
  val_rc=${PIPESTATUS[0]}; echo "[e2e-mcar] validation exit code: $val_rc"
  if [ "$val_rc" -eq 0 ]; then
    echo "[e2e-mcar] host scoring (frozen evaluate.py in the JAX image) ..."
    python3 "$PUB/automation/scripts/run_mountaincar_continuous_host_score.py" --workspace "$WS" --output-score "$WS/score.json" --dataset-root "$DATA" --python "$SP/staged/mountaincar/mc_python.sh" --config-fname src/config.yaml > "$RUN/logs/official_score.log" 2>&1
    score_rc=$?; echo "[e2e-mcar] host score exit code: $score_rc"; python3 -c "import json;s=json.load(open('$WS/score.json'));print('[e2e-mcar] score',s['score'],'std',s['reward_std'],s['score_source'])" 2>/dev/null
  fi
fi
python3 - "$RUN/state.json" "$native_rc" "$asm_rc" "$val_rc" "$score_rc" <<'PY'
import json,sys,datetime
d=json.load(open(sys.argv[1])); n,a,v,s=map(int,sys.argv[2:6])
d.update(status=("finished" if (a==0 and v==0 and s==0) else "failed"),native_exit_code=n,assembly_exit_code=a,validation_exit_code=v,score_exit_code=s,summary=d["summary"]+f" | ended: native={n} assembly={a} validation={v} score={s}",updated_at=datetime.datetime.now(datetime.UTC).isoformat()); json.dump(d,open(sys.argv[1],"w"),indent=2)
print("E2E_MCAR_DONE native=%d assembly=%d validation=%d score=%d"%(n,a,v,s))
PY
