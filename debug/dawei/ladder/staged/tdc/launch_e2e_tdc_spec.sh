#!/usr/bin/env bash
# TDC 端到端(诊断,不进计分板):tdc_admet_tox × 02 × luna,规格体路线(正式 topic,由 generate_tdc_admet_tox_native_inputs.py 生成)。
# 与主题体 launcher 相同,另:--cpus 32 + 线程上限 32;容器退出后先快照框架自己写到根目录的契约文件,再 host 组装。
#   ideation(主题体) -> research_idea.json(BFTS 前,从 idea 映射) -> BFTS stage 1-4(20/6/6/2,种子 1,CPU)
#   -> 容器退出 -> host 组装(复现各阶段 best_solution,契约包:runs/、predictions.csv、trace、paper、报告)
#   -> host 校验 framework 阶段 -> host 隐藏标签打分 -> host 校验 final 阶段。隐藏标签从不进容器。
# 用法: launch_e2e_tdc_spec.sh <rep>
set -euo pipefail
REP="${1:?rep}"
PUB=/data/daweiwang/claude-home/researchclaweval-public
SP=/tmp/claude-0/-root-researchclaweval-public/51dbc20a-062b-4219-ba2a-1b69cde17c93/scratchpad
DATA=$PUB/data/tdc_admet_tox
HIDDEN_ROOT="$(grep -E '^TDC_ADMET_TOX_HIDDEN_LABELS_ROOT=' "$PUB/.env" | cut -d= -f2-)"
TS=$(date +%Y%m%d_%H%M%S)
RUN=$PUB/real_eval/runs/control_e2etdcspec_rep${REP}_tdc02_luna_${TS}
WS=$RUN/workspace; INP=$RUN/inputs
mkdir -p "$WS" "$RUN/logs" "$INP"
rsync -a --exclude .git --exclude experiments --exclude "ai_scientist/ideas/my_research_topic.md" --exclude "ai_scientist/ideas/topic2_topic.md" "$PUB/AI-Scientist-v2/" "$WS/"
mkdir -p "$WS/real_eval/adapters/ai_scientist_v2" "$WS/real_eval/adapters/tdc_admet_tox" "$WS/tier" "$WS/automation/scripts" "$WS/data"
cp "$PUB/real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_semantic_scholar_bounded.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_prompt_logging.py" "$WS/real_eval/adapters/ai_scientist_v2/"
cp "$PUB/real_eval/adapters/tdc_admet_tox/patch_ai_scientist_v2.py" "$WS/real_eval/adapters/tdc_admet_tox/"
cp "$SP/tier/tier_apply.py" "$WS/tier/"
python3 "$SP/tier/tier_build.py" 0 "$REP" "$WS" "$PUB" >/dev/null
python3 - "$WS/tier/tier.json" <<'PY'
import json,sys; p=sys.argv[1]; T=json.load(open(p)); T.update(arm="e2e-tdc-spec",topic_input="tdc_admet_tox_topic.md (production spec, generate_tdc_admet_tox_native_inputs.py) + hf_dataset_reference.py (tdc_reference_v1, --add_dataset_ref)",cpus=32,thread_caps=32,data_mounted=True,stages_open="1-4 (20/6/6/2)",assembly="host deterministic (assemble_tdc.py) + host hidden-label scoring"); json.dump(T,open(p,"w"),ensure_ascii=False,indent=1)
PY
PROVIDER_ENV=$PUB/real_eval/runs/fullrun_arc_02_luna_20260917_085638/provider.env
BASE_URL="$(grep -E '^OPENAI_BASE_URL=' "$PROVIDER_ENV" | cut -d= -f2-)"
cp "$PUB/automation/scripts/run_tdc_admet_tox_validation_score.py" "$WS/automation/scripts/"
ln -sfn /data/tdc_admet_tox "$WS/data/tdc_admet_tox"
python3 "$PUB/real_eval/adapters/shared_layer_overlay.py" generate ai_scientist_v2 automation/scripts/generate_tdc_admet_tox_native_inputs.py --output-root "$INP" --primary-model gpt-5.6-luna --provider-base-url "$BASE_URL" >/dev/null
cp "$INP/AI-Scientist-v2/ai_scientist/ideas/tdc_admet_tox_topic.md" "$WS/ai_scientist/ideas/tdc_admet_tox_topic.md"
cp "$SP/staged/tdc/tdc_reference_v1.py" "$WS/hf_dataset_reference.py"
cp "$SP/staged/tdc/launch_e2e_tdc_spec.sh" "$SP/staged/tdc/assemble_tdc.py" "$SP/staged/tdc/tdc_reference_v1.py" "$WS/ai_scientist/ideas/tdc_admet_tox_topic.md" "$SP/tier/tier_apply.py" "$RUN/"
echo "$RUN" > "$SP/current_e2etdcspec"; NAME=control_e2etdcspec_rep${REP}_${TS}; echo "$NAME" > "$SP/current_e2etdcspec_container"
python3 - "$RUN/state.json" "$REP" <<'PY'
import json,sys,datetime
json.dump({"project_id":"control_e2etdcspec_tdc02_luna","phase":"diagnostic","status":"running","summary":f"TDC end-to-end SPEC arm rep {sys.argv[2]}: production spec topic, reference loader via dataset-reference slot, stages 1-4 on CPU, host deterministic assembly + framework audit + hidden-label scoring + final audit","updated_at":datetime.datetime.now(datetime.UTC).isoformat()},open(sys.argv[1],"w"),indent=2)
PY
T_START=$(date +%s)
set +e
timeout 14400s docker run --rm --name "$NAME" --cpus 32 --memory 16g --shm-size 8g \
  -v "$WS":/workspace -w /workspace -v "$DATA:/data/tdc_admet_tox:ro" --env-file "$PROVIDER_ENV" \
  -e HF_HUB_OFFLINE=1 -e HF_DATASETS_OFFLINE=1 -e PYTHONUNBUFFERED=1 -e CUDA_VISIBLE_DEVICES= -e OMP_NUM_THREADS=32 -e MKL_NUM_THREADS=32 -e OPENBLAS_NUM_THREADS=32 -e TORCH_NUM_THREADS=32 -e PROMPT_LOG_DIR=/workspace/prompt_logs \
  ai-scientist-v2:runtime-ready bash -lc '
set -euo pipefail
echo "CONTROL_E2E_TDC_SPEC model=$OPENAI_MODEL cpus=32"
python3 tier/tier_apply.py
python3 - <<PY
import yaml
p="bfts_config.yaml"; c=yaml.safe_load(open(p))
c["agent"]["stages"].update({"stage1_max_iters":20,"stage2_max_iters":6,"stage3_max_iters":6,"stage4_max_iters":2})
c["agent"]["multi_seed_eval"]["num_seeds"]=1
yaml.safe_dump(c,open(p,"w"),sort_keys=False); print("stage iters 20/6/6/2, num_seeds 1, generate_report", c.get("generate_report"))
PY
rm -f ai_scientist/ideas/tdc_admet_tox_topic.json
timeout 1800s python ai_scientist/perform_ideation_temp_free.py --workshop-file ai_scientist/ideas/tdc_admet_tox_topic.md --model "$OPENAI_MODEL" --max-num-generations 2 --num-reflections 5
python3 - <<PY
import json
ideas=json.load(open("ai_scientist/ideas/tdc_admet_tox_topic.json")); print("NATIVE_IDEAS",len(ideas)); [print(" idea",i,":",x["Title"]) for i,x in enumerate(ideas)]
idea=ideas[0]
ri={"framework":"AI-Scientist-v2","source_artifact":"ai_scientist/ideas/tdc_admet_tox_topic.json","hypothesis":idea.get("Short Hypothesis") or idea.get("Abstract",""),"method_rationale":idea.get("Experiments",""),"expected_failure_modes":idea.get("Risk Factors and Limitations") or "","comparison_logic":idea.get("Experiments",""),"native_idea":idea}
json.dump(ri,open("/workspace/research_idea.json","w"),ensure_ascii=False,indent=2); print("RESEARCH_IDEA_LOCKED (mapped from the framework idea before BFTS)")
PY
echo "NATIVE_BFTS_START"
python launch_scientist_bfts.py --load_ideas ai_scientist/ideas/tdc_admet_tox_topic.json --idea_idx 0 --add_dataset_ref \
  --model_writeup "$OPENAI_MODEL" --model_citation "$OPENAI_MODEL" --model_review "$OPENAI_MODEL" --model_agg_plots "$OPENAI_MODEL" --num_cite_rounds 0 --skip_writeup --skip_review
echo "NATIVE_BFTS_END"
' 2>&1 | tee "$RUN/logs/native.log" "$SP/e2etdc_rep${REP}_${TS}.log"
native_rc=${PIPESTATUS[0]}
NATIVE_WALL=$(( $(date +%s) - T_START ))
echo "[e2e-tdc] native exit code: $native_rc (wall ${NATIVE_WALL}s)"
if ls "$WS"/{predictions.csv,experiment_trace.json,paper.md,environment.json,final_report.md,score.json} >/dev/null 2>&1; then
  mkdir -p "$RUN/native_root_handoff"; for f in predictions.csv experiment_trace.json paper.md environment.json final_report.md score.json; do [ -f "$WS/$f" ] && cp -p "$WS/$f" "$RUN/native_root_handoff/"; done
  echo "[e2e-tdc] framework-written root files snapshotted: $(ls "$RUN/native_root_handoff" | tr '\n' ' ')"
fi
echo "[e2e-tdc] host assembly ..."
python3 "$SP/staged/tdc/assemble_tdc.py" --workspace "$WS" --out "$WS" --model gpt-5.6-luna --base-url "$BASE_URL" --data-root "$DATA" --native-wall-seconds "$NATIVE_WALL" 2>&1 | tee "$RUN/logs/assembly.log"
asm_rc=${PIPESTATUS[0]}
echo "[e2e-tdc] assembly exit code: $asm_rc"
fw_rc=1; score_rc=1; final_rc=1
if [ "$asm_rc" -eq 0 ]; then
  echo "[e2e-tdc] host audit (framework stage) ..."
  python3 "$PUB/automation/scripts/validate_tdc_admet_tox_run.py" --workspace "$WS" --stage framework --public-dataset-root "$DATA" > "$RUN/logs/framework_audit.json" 2>&1
  fw_rc=$?; echo "[e2e-tdc] framework audit exit code: $fw_rc"; grep -E '"status"|"error"' "$RUN/logs/framework_audit.json" | cut -c1-300
  if [ "$fw_rc" -eq 0 ]; then
    echo "[e2e-tdc] host hidden-label scoring ..."
    python3 "$PUB/automation/scripts/run_tdc_admet_tox_host_score.py" --public-dataset-root "$DATA" --hidden-labels "$HIDDEN_ROOT/test_labels.csv" --predictions "$WS/predictions.csv" --output-score "$WS/score.json" > "$RUN/logs/host_score.log" 2>&1
    score_rc=$?; echo "[e2e-tdc] host score exit code: $score_rc"; python3 -c "import json;s=json.load(open('$WS/score.json'));print('[e2e-tdc] main_score',s['main_score'],{k:round(v['auroc'],4) for k,v in s['per_endpoint'].items()})" 2>/dev/null
    echo "[e2e-tdc] host audit (final stage) ..."
    python3 "$PUB/automation/scripts/validate_tdc_admet_tox_run.py" --workspace "$WS" --stage final --public-dataset-root "$DATA" > "$RUN/logs/final_audit.json" 2>&1
    final_rc=$?; echo "[e2e-tdc] final audit exit code: $final_rc"; grep -E '"status"|"error"' "$RUN/logs/final_audit.json" | cut -c1-300
  fi
fi
python3 - "$RUN/state.json" "$native_rc" "$asm_rc" "$fw_rc" "$score_rc" "$final_rc" <<'PY'
import json,sys,datetime
d=json.load(open(sys.argv[1])); n,a,f,s,v=map(int,sys.argv[2:7])
d.update(status=("finished" if (a==0 and f==0 and s==0 and v==0) else "failed"),native_exit_code=n,assembly_exit_code=a,framework_audit_exit_code=f,host_score_exit_code=s,final_audit_exit_code=v,summary=d["summary"]+f" | ended: native={n} assembly={a} framework_audit={f} score={s} final_audit={v}",updated_at=datetime.datetime.now(datetime.UTC).isoformat()); json.dump(d,open(sys.argv[1],"w"),indent=2)
print("E2E_TDC_DONE native=%d assembly=%d framework_audit=%d score=%d final_audit=%d"%(n,a,f,s,v))
PY
