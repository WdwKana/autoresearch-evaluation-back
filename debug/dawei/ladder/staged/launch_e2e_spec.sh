#!/usr/bin/env bash
# 端到端 对照臂 SPEC(诊断):与 launch_e2e.sh 完全相同,只把主题文件换回正式的说明书式 psydefdetect_topic.md,
# 并加上正式 wrapper 的 ideation 契约段。数据通道(参考代码 v2 走数据集参考槽位)、阶段、组装、校验一律相同。
#   ideation(主题体) -> research_idea.json(BFTS 前,从 idea 映射) -> BFTS stage 1-4(20/6/6/2,种子 1)
#   -> 容器退出 -> host 组装(复现各阶段 best_solution、搬运、重算分数、trace、报告) -> host 校验。
# 用法: launch_e2e.sh <rep>
set -euo pipefail
REP="${1:?rep}"
PUB=/data/daweiwang/claude-home/researchclaweval-public
SP=/tmp/claude-0/-root-researchclaweval-public/51dbc20a-062b-4219-ba2a-1b69cde17c93/scratchpad
TS=$(date +%Y%m%d_%H%M%S)
RUN=$PUB/real_eval/runs/control_e2espec_rep${REP}_psydef02_luna_${TS}
WS=$RUN/workspace; INP=$RUN/inputs
mkdir -p "$WS" "$RUN/logs" "$INP"
rsync -a --exclude .git --exclude experiments --exclude "ai_scientist/ideas/my_research_topic.md" --exclude "ai_scientist/ideas/topic2_topic.md" "$PUB/AI-Scientist-v2/" "$WS/"
mkdir -p "$WS/real_eval/adapters/ai_scientist_v2" "$WS/real_eval/adapters/tdc_admet_tox" "$WS/tier" "$WS/automation" "$WS/data"
cp "$PUB/real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_semantic_scholar_bounded.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_prompt_logging.py" "$WS/real_eval/adapters/ai_scientist_v2/"
cp "$PUB/real_eval/adapters/tdc_admet_tox/patch_ai_scientist_v2.py" "$WS/real_eval/adapters/tdc_admet_tox/"
cp "$SP/tier/tier_apply.py" "$WS/tier/"
python3 "$SP/tier/tier_build.py" 0 "$REP" "$WS" "$PUB" >/dev/null
python3 - "$WS/tier/tier.json" <<'PY'
import json,sys; p=sys.argv[1]; T=json.load(open(p)); T.update(arm="e2e-spec",use_ideation_contract=True,topic_input="psydefdetect_topic.md (production spec) + ideation contract paragraph + hf_dataset_reference.py (loader v2, --add_dataset_ref)",data_mounted=True,stages_open="1-4 (20/6/6/2)",assembly="host deterministic (assemble_psydef.py)"); json.dump(T,open(p,"w"),ensure_ascii=False,indent=1)
PY
PROVIDER_ENV=$PUB/real_eval/runs/fullrun_arc_02_luna_20260917_085638/provider.env
BASE_URL="$(grep -E '^OPENAI_BASE_URL=' "$PROVIDER_ENV" | cut -d= -f2-)"
python3 "$PUB/automation/scripts/generate_psydefdetect_native_inputs.py" --output-root "$INP" --dataset-root "$PUB/data/psydefdetect" --contract-file "$PUB/automation/psydefdetect_contract.md" --provider-base-url "$BASE_URL" --primary-model gpt-5.6-luna >/dev/null
rsync -a "$INP/automation/" "$WS/automation/"; cp "$PUB/automation/psydefdetect_contract.md" "$WS/automation/psydefdetect_contract.md"; ln -sfn /data/psydefdetect "$WS/data/psydefdetect"
cp "$INP/AI-Scientist-v2/ai_scientist/ideas/psydefdetect_topic.md" "$WS/ai_scientist/ideas/psydefdetect_topic.md"
cp "$SP/staged/psydefdetect_native_v2.py" "$WS/hf_dataset_reference.py"
cp "$SP/staged/launch_e2e_spec.sh" "$SP/staged/assemble_psydef.py" "$SP/staged/psydef_host_validate.py" "$SP/staged/psydefdetect_native_v2.py" "$WS/ai_scientist/ideas/psydefdetect_topic.md" "$SP/tier/tier_apply.py" "$RUN/"
echo "$RUN" > "$SP/current_e2espec"; NAME=control_e2espec_rep${REP}_${TS}; echo "$NAME" > "$SP/current_e2espec_container"
python3 - "$RUN/state.json" "$REP" <<'PY'
import json,sys,datetime
json.dump({"project_id":"control_e2espec_psydef02_luna","phase":"diagnostic","status":"running","summary":f"end-to-end SPEC arm rep {sys.argv[2]}: production spec topic + ideation contract, loader v2 via dataset-reference slot, stages 1-4, host deterministic assembly + validation","updated_at":datetime.datetime.now(datetime.UTC).isoformat()},open(sys.argv[1],"w"),indent=2)
PY
set +e
timeout 14400s docker run --rm --name "$NAME" --cpus 8 --shm-size 8g \
  -v "$WS":/workspace -w /workspace -v "$PUB/data/psydefdetect:/data/psydefdetect:ro" --env-file "$PROVIDER_ENV" \
  -e HF_ENDPOINT=https://hf-mirror.com -e PYTHONUNBUFFERED=1 -e CUDA_VISIBLE_DEVICES= -e PROMPT_LOG_DIR=/workspace/prompt_logs \
  ai-scientist-v2:runtime-ready bash -lc '
set -euo pipefail
echo "CONTROL_E2E_SPEC model=$OPENAI_MODEL"
python3 tier/tier_apply.py
python3 - <<PY
import yaml
p="bfts_config.yaml"; c=yaml.safe_load(open(p))
c["agent"]["stages"].update({"stage1_max_iters":20,"stage2_max_iters":6,"stage3_max_iters":6,"stage4_max_iters":2})
c["agent"]["multi_seed_eval"]["num_seeds"]=1
yaml.safe_dump(c,open(p,"w"),sort_keys=False); print("stage iters 20/6/6/2, num_seeds 1, generate_report", c.get("generate_report"))
PY
rm -f ai_scientist/ideas/psydefdetect_topic.json
timeout 1800s python ai_scientist/perform_ideation_temp_free.py --workshop-file ai_scientist/ideas/psydefdetect_topic.md --model "$OPENAI_MODEL" --max-num-generations 2 --num-reflections 5
python3 - <<PY
import json
ideas=json.load(open("ai_scientist/ideas/psydefdetect_topic.json")); print("NATIVE_IDEAS",len(ideas)); [print(" idea",i,":",x["Title"]) for i,x in enumerate(ideas)]
idea=ideas[0]
ri={"framework":"AI-Scientist-v2","source_artifact":"ai_scientist/ideas/psydefdetect_topic.json","hypothesis":idea.get("Short Hypothesis") or idea.get("Abstract",""),"method_rationale":idea.get("Experiments",""),"expected_failure_modes":idea.get("Risk Factors and Limitations") or "","comparison_logic":idea.get("Experiments",""),"native_idea":idea}
json.dump(ri,open("/workspace/research_idea.json","w"),ensure_ascii=False,indent=2); print("RESEARCH_IDEA_LOCKED (mapped from the framework idea before BFTS)")
PY
echo "NATIVE_BFTS_START"
python launch_scientist_bfts.py --load_ideas ai_scientist/ideas/psydefdetect_topic.json --idea_idx 0 --add_dataset_ref \
  --model_writeup "$OPENAI_MODEL" --model_citation "$OPENAI_MODEL" --model_review "$OPENAI_MODEL" --model_agg_plots "$OPENAI_MODEL" --num_cite_rounds 0 --skip_writeup --skip_review
echo "NATIVE_BFTS_END"
' 2>&1 | tee "$RUN/logs/native.log" "$SP/e2espec_rep${REP}_${TS}.log"
native_rc=${PIPESTATUS[0]}
echo "[e2e] native exit code: $native_rc"
echo "[e2e] host assembly ..."
python3 "$SP/staged/assemble_psydef.py" --workspace "$WS" --out "$WS" --model gpt-5.6-luna --base-url "$BASE_URL" 2>&1 | tee "$RUN/logs/assembly.log"
asm_rc=${PIPESTATUS[0]}
echo "[e2e] assembly exit code: $asm_rc"
echo "[e2e] host validation ..."
python3 "$SP/staged/psydef_host_validate.py" "$WS" gpt-5.6-luna 2>&1 | tee "$RUN/logs/host_validation.log"
val_rc=${PIPESTATUS[0]}
echo "[e2e] validation exit code: $val_rc"
python3 - "$RUN/state.json" "$native_rc" "$asm_rc" "$val_rc" <<'PY'
import json,sys,datetime
d=json.load(open(sys.argv[1])); n,a,v=map(int,sys.argv[2:5])
d.update(status=("finished" if (a==0 and v==0) else "failed"),native_exit_code=n,assembly_exit_code=a,validation_exit_code=v,summary=d["summary"]+f" | ended: native={n} assembly={a} validation={v}",updated_at=datetime.datetime.now(datetime.UTC).isoformat()); json.dump(d,open(sys.argv[1],"w"),indent=2)
print("E2E_DONE native=%d assembly=%d validation=%d"%(n,a,v))
PY
