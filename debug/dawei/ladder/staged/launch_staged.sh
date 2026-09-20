#!/usr/bin/env bash
# 分阶段注入臂(诊断,不进计分板):psydef × 02 × luna。
#   ideation: 主题体主题文件(psydefdetect_native.md),原生系统 prompt。
#   数据:参考代码只走框架自带的数据集参考槽位(--add_dataset_ref 读取 workspace 根目录的 hf_dataset_reference.py),
#        进入 task_desc 的 "Code To Use",所有阶段可见。不再同时用 --load_code,避免同一段代码出现两次。
#   阶段:放开 stage 1-3(stage 4 仅 2 步),不做 stage 停止、不改指南、不改阶段目标;
#        多种子复评按 README 设为 num_seeds=1(num_workers=1 时)。
#   看护:stage 3 结束或 4 小时上限即停容器。
# 用法: launch_staged.sh <rep>
set -euo pipefail
REP="${1:?rep}"
PUB=/data/daweiwang/claude-home/researchclaweval-public
SP=/tmp/claude-0/-root-researchclaweval-public/51dbc20a-062b-4219-ba2a-1b69cde17c93/scratchpad
TS=$(date +%Y%m%d_%H%M%S)
RUN=$PUB/real_eval/runs/control_staged_rep${REP}_psydef02_luna_${TS}
WS=$RUN/workspace; INP=$RUN/inputs
mkdir -p "$WS" "$RUN/logs" "$INP"
rsync -a --exclude .git --exclude experiments --exclude "ai_scientist/ideas/my_research_topic.md" --exclude "ai_scientist/ideas/topic2_topic.md" "$PUB/AI-Scientist-v2/" "$WS/"
mkdir -p "$WS/real_eval/adapters/ai_scientist_v2" "$WS/real_eval/adapters/tdc_admet_tox" "$WS/tier" "$WS/automation" "$WS/data"
cp "$PUB/real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_semantic_scholar_bounded.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_prompt_logging.py" "$WS/real_eval/adapters/ai_scientist_v2/"
cp "$PUB/real_eval/adapters/tdc_admet_tox/patch_ai_scientist_v2.py" "$WS/real_eval/adapters/tdc_admet_tox/"
cp "$SP/tier/tier_apply.py" "$WS/tier/"
python3 "$SP/tier/tier_build.py" 0 "$REP" "$WS" "$PUB" >/dev/null      # tier 0 switches = model adapter + logging only
python3 - "$WS/tier/tier.json" <<'PY'
import json,sys; p=sys.argv[1]; T=json.load(open(p)); T.update(arm="staged",topic_input="psydefdetect_native.md + hf_dataset_reference.py (--add_dataset_ref)",data_mounted=True,stages_open="1-3 (+stage 4 max 2 iters)"); json.dump(T,open(p,"w"),ensure_ascii=False,indent=1)
PY
# inputs: theme-style topic + host loader in BOTH native code slots; data/split/scorer mounted like the production runner
PROVIDER_ENV=$PUB/real_eval/runs/fullrun_arc_02_luna_20260917_085638/provider.env
python3 "$PUB/automation/scripts/generate_psydefdetect_native_inputs.py" --output-root "$INP" --dataset-root "$PUB/data/psydefdetect" --contract-file "$PUB/automation/psydefdetect_contract.md" --provider-base-url "$(grep -E '^OPENAI_BASE_URL=' "$PROVIDER_ENV" | cut -d= -f2-)" --primary-model gpt-5.6-luna >/dev/null
rsync -a "$INP/automation/" "$WS/automation/"; cp "$PUB/automation/psydefdetect_contract.md" "$WS/automation/psydefdetect_contract.md"; ln -sfn /data/psydefdetect "$WS/data/psydefdetect"
cp "$SP/tier/psydefdetect_native.md" "$WS/ai_scientist/ideas/psydefdetect_native.md"
cp "$SP/tier/psydefdetect_native.py" "$WS/hf_dataset_reference.py"
cp "$SP/staged/launch_staged.sh" "$SP/tier/tier_apply.py" "$SP/tier/psydefdetect_native.md" "$SP/tier/psydefdetect_native.py" "$RUN/"
echo "$RUN" > "$SP/current_staged"; NAME=control_staged_rep${REP}_${TS}; echo "$NAME" > "$SP/current_staged_container"
python3 - "$RUN/state.json" "$REP" <<'PY'
import json,sys,datetime
json.dump({"project_id":"control_staged_psydef02_luna","phase":"diagnostic","status":"running","summary":f"staged-injection arm rep {sys.argv[2]}: theme topic, loader via native code slots, stages 1-3 open","updated_at":datetime.datetime.now(datetime.UTC).isoformat()},open(sys.argv[1],"w"),indent=2)
PY
docker run --rm --name "$NAME" --cpus 8 --shm-size 8g \
  -v "$WS":/workspace -w /workspace -v "$PUB/data/psydefdetect:/data/psydefdetect:ro" --env-file "$PROVIDER_ENV" \
  -e HF_ENDPOINT=https://hf-mirror.com -e PYTHONUNBUFFERED=1 -e CUDA_VISIBLE_DEVICES= -e PROMPT_LOG_DIR=/workspace/prompt_logs \
  ai-scientist-v2:runtime-ready bash -lc '
set -euo pipefail
echo "CONTROL_STAGED model=$OPENAI_MODEL"
python3 tier/tier_apply.py
python3 - <<PY
import yaml
p="bfts_config.yaml"; c=yaml.safe_load(open(p))
c["agent"]["stages"].update({"stage1_max_iters":20,"stage2_max_iters":6,"stage3_max_iters":6,"stage4_max_iters":2})
c["agent"]["multi_seed_eval"]["num_seeds"]=1   # README: equal to num_workers when num_workers < 3
yaml.safe_dump(c,open(p,"w"),sort_keys=False); print("stage iters 20/6/6/2, num_seeds 1, num_workers", c["agent"]["num_workers"])
PY
rm -f ai_scientist/ideas/psydefdetect_native.json
timeout 1800s python ai_scientist/perform_ideation_temp_free.py --workshop-file ai_scientist/ideas/psydefdetect_native.md --model "$OPENAI_MODEL" --max-num-generations 2 --num-reflections 5
python3 -c "import json;d=json.load(open(\"ai_scientist/ideas/psydefdetect_native.json\"));print(\"NATIVE_IDEAS\",len(d));[print(\" idea\",i,\":\",x[\"Title\"]) for i,x in enumerate(d)]"
echo "NATIVE_BFTS_START"
python launch_scientist_bfts.py --load_ideas ai_scientist/ideas/psydefdetect_native.json --idea_idx 0 --add_dataset_ref \
  --model_writeup "$OPENAI_MODEL" --model_citation "$OPENAI_MODEL" --model_review "$OPENAI_MODEL" --model_agg_plots "$OPENAI_MODEL" --num_cite_rounds 0 --skip_writeup --skip_review
' 2>&1 | tee "$RUN/logs/native.log" "$SP/staged_rep${REP}_${TS}.log"
