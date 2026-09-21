#!/usr/bin/env bash
# BabyLM 端到端(诊断,不进计分板):babylm × 02 × <model>,规格体路线(正式 babylm_topic.md 由 generate_babylm_native_inputs.py 生成)。
#   参考模块 babylm_reference_v1 走 --add_dataset_ref 槽;BFTS stage 1-4(12/4/4/2,单节点上限 3600 s)在 GPU $BABYLM_GPU(默认 1)上,启动时校验容器只看到该卡;
#   容器退出 -> host 组装(复现各阶段 best_solution 于同一 GPU,选最低词级验证困惑度,submission/、trace、报告)
#   -> host 打分(run_babylm_score.py,读 trace)-> host 校验(从 babylm runner 逐行抽出)。
# 用法: launch_e2e_babylm.sh <rep> <tag> <provider_env>   (可选 VLM_MODEL=... 只覆盖图表反馈模型)
set -euo pipefail
REP="${1:?rep}"; TAG="${2:?model tag}"; PROVIDER_ENV="${3:?provider env}"
MODEL="$(grep -E '^OPENAI_MODEL=' "$PROVIDER_ENV" | cut -d= -f2-)"
VLM_MODEL="${VLM_MODEL:-}"
PUB=/data/daweiwang/claude-home/researchclaweval-public
SP=/tmp/claude-0/-root-researchclaweval-public/51dbc20a-062b-4219-ba2a-1b69cde17c93/scratchpad
DATA=/data/daweiwang/claude-home/researchclaweval-public/data/BabyLM-2026-Strict-Small
GPU="${BABYLM_GPU:-1}"
EXPECTED_GPU_UUID="$(nvidia-smi --query-gpu=index,uuid --format=csv,noheader | awk -F', ' -v g="$GPU" '$1==g{print $2}')"
[ -n "$EXPECTED_GPU_UUID" ] || { echo "no GPU with index $GPU on this host"; exit 96; }
TS=$(date +%Y%m%d_%H%M%S)
RUN=$PUB/real_eval/runs/control_e2ebabylm_rep${REP}_babylm02_${TAG}_${TS}
WS=$RUN/workspace; INP=$RUN/inputs
mkdir -p "$WS" "$RUN/logs" "$INP"
rsync -a --exclude .git --exclude experiments --exclude "ai_scientist/ideas/my_research_topic.md" --exclude "ai_scientist/ideas/topic2_topic.md" "$PUB/AI-Scientist-v2/" "$WS/"
mkdir -p "$WS/real_eval/adapters/ai_scientist_v2" "$WS/real_eval/adapters/tdc_admet_tox" "$WS/tier" "$WS/automation/scripts" "$WS/data"
cp "$PUB/real_eval/adapters/ai_scientist_v2/patch_ideation_action_format.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_ideation_tolerant_parser.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_semantic_scholar_bounded.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_prompt_logging.py" "$WS/real_eval/adapters/ai_scientist_v2/"
cp "$PUB/real_eval/adapters/tdc_admet_tox/patch_ai_scientist_v2.py" "$WS/real_eval/adapters/tdc_admet_tox/"
cp "$SP/tier/tier_apply.py" "$WS/tier/"
python3 "$SP/tier/tier_build.py" 0 "$REP" "$WS" "$PUB" >/dev/null
python3 - "$WS/tier/tier.json" "$TAG" "$VLM_MODEL" "$GPU" <<'PY'
import json,sys; p=sys.argv[1]; T=json.load(open(p)); T.update(arm="e2e-babylm-spec",model_tag=sys.argv[2],vlm_model_override=(sys.argv[3] or None),gpu=sys.argv[4],stage_iters="12/4/4/2",ideation_patches="label normalization, tolerant parser, MAX_NUM_TOKENS 16384, retry x3",topic_input="babylm_topic.md (production spec, generate_babylm_native_inputs.py) + hf_dataset_reference.py (babylm_reference_v1: corpus loader, default split, word-level perplexity, submission keeper)",data_mounted=True,stages_open="1-4 (12/4/4/2)",assembly="host deterministic (assemble_babylm.py) + run_babylm_score.py"); json.dump(T,open(p,"w"),ensure_ascii=False,indent=1)
PY
BASE_URL="$(grep -E '^OPENAI_BASE_URL=' "$PROVIDER_ENV" | cut -d= -f2-)"
python3 "$PUB/automation/scripts/generate_babylm_native_inputs.py" --output-root "$INP" --dataset-root /data/BabyLM-2026-Strict-Small --contract-file /input/babylm_contract.md --provider-base-url "$BASE_URL" --primary-model "$MODEL" >/dev/null
cp "$INP/AI-Scientist-v2/ai_scientist/ideas/babylm_topic.md" "$WS/ai_scientist/ideas/babylm_topic.md"
ln -sfn /data/BabyLM-2026-Strict-Small "$WS/data/BabyLM-2026-Strict-Small"
cp "$SP/staged/babylm/babylm_reference_v1.py" "$WS/hf_dataset_reference.py"
cp "$SP/staged/babylm/launch_e2e_babylm.sh" "$SP/staged/babylm/assemble_babylm.py" "$SP/staged/babylm/babylm_host_validate.py" "$SP/staged/babylm/babylm_reference_v1.py" "$WS/ai_scientist/ideas/babylm_topic.md" "$SP/tier/tier_apply.py" "$PUB/automation/babylm_contract.md" "$RUN/"
echo "$RUN" > "$SP/current_e2ebabylm_${TAG}"; NAME=control_e2ebabylm_${TAG}_rep${REP}_${TS}; echo "$NAME" > "$SP/current_e2ebabylm_${TAG}_container"
python3 - "$RUN/state.json" "$REP" "$TAG" "$VLM_MODEL" "$GPU" <<'PY'
import json,sys,datetime
json.dump({"project_id":"control_e2ebabylm_babylm02_"+sys.argv[3],"phase":"diagnostic","status":"running","summary":f"BabyLM end-to-end SPEC arm rep {sys.argv[2]} model={sys.argv[3]} vlm_override={sys.argv[4] or 'none'}: production spec topic, reference loader via dataset-reference slot, stages 1-4 (12/4/4/2) on GPU {sys.argv[5]}, host deterministic assembly + run_babylm_score + validation","updated_at":datetime.datetime.now(datetime.UTC).isoformat()},open(sys.argv[1],"w"),indent=2)
PY
set +e
timeout 14400s docker run --rm --name "$NAME" --gpus "device=$GPU" --cpus 8 --shm-size 16g \
  -v "$WS":/workspace -w /workspace -v "$DATA:/data/BabyLM-2026-Strict-Small:ro" -v "$PUB/automation/babylm_contract.md:/input/babylm_contract.md:ro" --env-file "$PROVIDER_ENV" \
  -e EXPECTED_GPU_UUID="$EXPECTED_GPU_UUID" -e HF_HUB_OFFLINE=1 -e HF_DATASETS_OFFLINE=1 -e OMP_NUM_THREADS=8 -e MKL_NUM_THREADS=8 -e OPENBLAS_NUM_THREADS=8 -e TORCH_NUM_THREADS=8 -e VLM_MODEL="$VLM_MODEL" -e PYTHONUNBUFFERED=1 -e PROMPT_LOG_DIR=/workspace/prompt_logs \
  ai-scientist-v2:runtime-ready bash -lc '
set -euo pipefail
echo "CONTROL_E2E_BABYLM model=$OPENAI_MODEL"
nvidia-smi -L | grep -q "$EXPECTED_GPU_UUID" || { echo "GPU_CHECK_FAILED: container does not see the expected GPU $EXPECTED_GPU_UUID"; exit 97; }
[ "$(nvidia-smi -L | wc -l)" = "1" ] || { echo "GPU_CHECK_FAILED: container sees more than one GPU"; exit 97; }
echo "GPU_CHECK_OK $(nvidia-smi -L)"
python3 -c "import torch; assert torch.cuda.is_available() and torch.cuda.device_count()==1, torch.cuda.device_count(); print(\"TORCH_CUDA_OK\", torch.cuda.get_device_name(0))"
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
c["agent"]["stages"].update({"stage1_max_iters":12,"stage2_max_iters":4,"stage3_max_iters":4,"stage4_max_iters":2})
c["agent"]["multi_seed_eval"]["num_seeds"]=1
if os.environ.get("VLM_MODEL"): c["agent"]["vlm_feedback"]["model"]=os.environ["VLM_MODEL"]; print("VLM (plot feedback) model override:", c["agent"]["vlm_feedback"]["model"])
yaml.safe_dump(c,open(p,"w"),sort_keys=False); print("stage iters 12/4/4/2, exec timeout", c["exec"]["timeout"], ", num_seeds 1, generate_report", c.get("generate_report"))
PY
for ideation_attempt in 1 2 3; do
  rm -f ai_scientist/ideas/babylm_topic.json
  timeout 1800s python ai_scientist/perform_ideation_temp_free.py --workshop-file ai_scientist/ideas/babylm_topic.md --model "$OPENAI_MODEL" --max-num-generations 2 --num-reflections 5 || true
  if python3 -c "import json,sys; d=json.load(open('"'"'ai_scientist/ideas/babylm_topic.json'"'"')); sys.exit(0 if isinstance(d, list) and d else 1)" 2>/dev/null; then echo "IDEATION_OK attempt $ideation_attempt"; break; fi
  echo "IDEATION_EMPTY attempt $ideation_attempt"
done
test -s ai_scientist/ideas/babylm_topic.json
python3 - <<PY
import json
ideas=json.load(open("ai_scientist/ideas/babylm_topic.json")); print("NATIVE_IDEAS",len(ideas)); [print(" idea",i,":",x.get("Title")) for i,x in enumerate(ideas)]
idea=ideas[0]
ri={"framework":"AI-Scientist-v2","source_artifact":"ai_scientist/ideas/babylm_topic.json","hypothesis":idea.get("Short Hypothesis") or idea.get("Abstract",""),"method_rationale":str(idea.get("Experiments","")),"expected_failure_modes":str(idea.get("Risk Factors and Limitations") or ""),"comparison_logic":str(idea.get("Experiments","")),"native_idea":idea}
json.dump(ri,open("/workspace/research_idea.json","w"),ensure_ascii=False,indent=2); print("RESEARCH_IDEA_LOCKED (mapped from the framework idea before BFTS)")
PY
echo "NATIVE_BFTS_START"
python launch_scientist_bfts.py --load_ideas ai_scientist/ideas/babylm_topic.json --idea_idx 0 --add_dataset_ref \
  --model_writeup "$OPENAI_MODEL" --model_citation "$OPENAI_MODEL" --model_review "$OPENAI_MODEL" --model_agg_plots "$OPENAI_MODEL" --num_cite_rounds 0 --skip_writeup --skip_review
echo "NATIVE_BFTS_END"
' 2>&1 | tee "$RUN/logs/native.log" "$SP/e2ebabylm_${TAG}_rep${REP}_${TS}.log"
native_rc=${PIPESTATUS[0]}
echo "[e2e-babylm] native exit code: $native_rc"
if ls "$WS"/{experiment_trace.json,final_report.md,score.json} >/dev/null 2>&1; then
  mkdir -p "$RUN/native_root_handoff"; for f in experiment_trace.json final_report.md score.json; do [ -f "$WS/$f" ] && cp -p "$WS/$f" "$RUN/native_root_handoff/"; done
  echo "[e2e-babylm] framework-written root files snapshotted: $(ls "$RUN/native_root_handoff" | tr '\n' ' ')"; rm -f "$WS/score.json"
fi
echo "[e2e-babylm] host assembly ..."
python3 "$SP/staged/babylm/assemble_babylm.py" --workspace "$WS" --out "$WS" --model "$MODEL" --base-url "$BASE_URL" --data-root "$DATA" --gpu "$GPU" 2>&1 | tee "$RUN/logs/assembly.log"
asm_rc=${PIPESTATUS[0]}
echo "[e2e-babylm] assembly exit code: $asm_rc"
score_rc=1
if [ "$asm_rc" -eq 0 ]; then
  echo "[e2e-babylm] host scoring (run_babylm_score.py) ..."
  python3 "$PUB/automation/scripts/run_babylm_score.py" --run-root "$RUN" --output-score "$WS/score.json" > "$RUN/logs/host_score.log" 2>&1
  score_rc=$?; echo "[e2e-babylm] host score exit code: $score_rc"; tail -1 "$RUN/logs/host_score.log" | cut -c1-200
fi
echo "[e2e-babylm] host validation ..."
python3 "$SP/staged/babylm/babylm_host_validate.py" "$WS" "$MODEL" 2>&1 | tee "$RUN/logs/host_validation.log"
val_rc=${PIPESTATUS[0]}
echo "[e2e-babylm] validation exit code: $val_rc"
python3 - "$RUN/state.json" "$native_rc" "$asm_rc" "$score_rc" "$val_rc" <<'PY'
import json,sys,datetime
d=json.load(open(sys.argv[1])); n,a,s,v=map(int,sys.argv[2:6])
d.update(status=("finished" if (a==0 and s==0 and v==0) else "failed"),native_exit_code=n,assembly_exit_code=a,score_exit_code=s,validation_exit_code=v,summary=d["summary"]+f" | ended: native={n} assembly={a} score={s} validation={v}",updated_at=datetime.datetime.now(datetime.UTC).isoformat()); json.dump(d,open(sys.argv[1],"w"),indent=2)
print("E2E_BABYLM_DONE native=%d assembly=%d score=%d validation=%d"%(n,a,s,v))
PY
