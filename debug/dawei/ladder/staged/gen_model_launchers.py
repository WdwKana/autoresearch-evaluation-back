import sys,re; SP=sys.argv[1]
IDEATION_PATCH_BLOCK='''python3 real_eval/adapters/ai_scientist_v2/patch_ideation_action_format.py
python3 real_eval/adapters/ai_scientist_v2/patch_ideation_tolerant_parser.py
python3 - <<PY
from pathlib import Path
llm = Path("ai_scientist/llm.py"); text = llm.read_text(encoding="utf-8")
if "MAX_NUM_TOKENS = 4096" not in text and "MAX_NUM_TOKENS = 16384" not in text: raise SystemExit("MAX_NUM_TOKENS anchor not found")
llm.write_text(text.replace("MAX_NUM_TOKENS = 4096", "MAX_NUM_TOKENS = 16384"), encoding="utf-8"); print("ideation MAX_NUM_TOKENS = 16384")
PY
'''
VLM_YAML='import os\nif os.environ.get("VLM_MODEL"): c["agent"]["vlm_feedback"]["model"]=os.environ["VLM_MODEL"]; print("VLM (plot feedback) model override:", c["agent"]["vlm_feedback"]["model"])\n'
def generalize(src, dst, kind):
    s=open(src).read()
    s=s.replace('REP="${1:?rep}"\n','REP="${1:?rep}"; TAG="${2:?model tag}"; PROVIDER_ENV="${3:?provider env}"\nMODEL="$(grep -E \'^OPENAI_MODEL=\' "$PROVIDER_ENV" | cut -d= -f2-)"\nVLM_MODEL="${VLM_MODEL:-}"   # optional vision-capable model for the plot-feedback step only\n',1)
    old='PROVIDER_ENV=$PUB/real_eval/runs/fullrun_arc_02_luna_20260917_085638/provider.env\n'; assert s.count(old)==1; s=s.replace(old,'')
    s=s.replace('cp "$PUB/real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py"','cp "$PUB/real_eval/adapters/ai_scientist_v2/patch_ideation_action_format.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_ideation_tolerant_parser.py" "$PUB/real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py"',1)
    assert s.count('python3 tier/tier_apply.py\n')==1; s=s.replace('python3 tier/tier_apply.py\n','python3 tier/tier_apply.py\n'+IDEATION_PATCH_BLOCK,1)
    assert s.count('c["agent"]["multi_seed_eval"]["num_seeds"]=1\n')==1; s=s.replace('c["agent"]["multi_seed_eval"]["num_seeds"]=1\n','c["agent"]["multi_seed_eval"]["num_seeds"]=1\n'+VLM_YAML,1)
    m=re.search(r'rm -f (ai_scientist/ideas/\S+\.json)\ntimeout 1800s python ai_scientist/perform_ideation_temp_free\.py --workshop-file (\S+) --model "\$OPENAI_MODEL" --max-num-generations 2 --num-reflections 5\n', s); assert m
    js, md = m.group(1), m.group(2)
    retry=f'''for ideation_attempt in 1 2 3; do
  rm -f {js}
  timeout 1800s python ai_scientist/perform_ideation_temp_free.py --workshop-file {md} --model "$OPENAI_MODEL" --max-num-generations 2 --num-reflections 5 || true
  if python3 -c "import json,sys; d=json.load(open('{js}')); sys.exit(0 if isinstance(d, list) and d else 1)" 2>/dev/null; then echo "IDEATION_OK attempt $ideation_attempt"; break; fi
  echo "IDEATION_EMPTY attempt $ideation_attempt"
done
test -s {js}
'''
    s=s[:m.start()]+retry+s[m.end():]
    s=s.replace('-e PYTHONUNBUFFERED=1','-e VLM_MODEL="$VLM_MODEL" -e PYTHONUNBUFFERED=1',1)
    s=s.replace('--primary-model gpt-5.6-luna','--primary-model "$MODEL"').replace('--model gpt-5.6-luna','--model "$MODEL"').replace('arc_host_validate.py" "$WS" gpt-5.6-luna','arc_host_validate.py" "$WS" "$MODEL"')
    if kind=="arc":
        s=s.replace('RUN=$PUB/real_eval/runs/control_e2earc_rep${REP}_arc02_luna_${TS}','RUN=$PUB/real_eval/runs/control_e2earc_rep${REP}_arc02_${TAG}_${TS}')
        s=s.replace('echo "$RUN" > "$SP/current_e2earc"; NAME=control_e2earc_rep${REP}_${TS}; echo "$NAME" > "$SP/current_e2earc_container"; echo "$RUN" > "$SP/current_e2earc_v2"','echo "$RUN" > "$SP/current_e2earc_${TAG}"; NAME=control_e2earc_${TAG}_rep${REP}_${TS}; echo "$NAME" > "$SP/current_e2earc_${TAG}_container"')
        s=s.replace('tee "$RUN/logs/native.log" "$SP/e2earc_rep${REP}_${TS}.log"','tee "$RUN/logs/native.log" "$SP/e2earc_${TAG}_rep${REP}_${TS}.log"')
        s=s.replace('"project_id":"control_e2earc_arc02_luna"','"project_id":"control_e2earc_arc02_"+sys.argv[3]').replace('python3 - "$RUN/state.json" "$REP" <<\'PY\'','python3 - "$RUN/state.json" "$REP" "$TAG" "$VLM_MODEL" <<\'PY\'').replace('"summary":f"ARC end-to-end rep {sys.argv[2]}','"summary":f"ARC end-to-end rep {sys.argv[2]} model={sys.argv[3]} vlm_override={sys.argv[4] or \'none\'}')
        s=s.replace('-e HF_HUB_OFFLINE=1 -e HF_DATASETS_OFFLINE=1','-e HF_HUB_OFFLINE=1 -e HF_DATASETS_OFFLINE=1 -e OMP_NUM_THREADS=8 -e MKL_NUM_THREADS=8 -e OPENBLAS_NUM_THREADS=8 -e TORCH_NUM_THREADS=8',1)
        s=s.replace('T.update(arm="e2e-arc-v2",','T.update(arm="e2e-arc-v2",model_tag=sys.argv[2],vlm_model_override=(sys.argv[3] or None),ideation_patches="label normalization, tolerant parser, MAX_NUM_TOKENS 16384, retry x3",').replace('python3 - "$WS/tier/tier.json" <<\'PY\'','python3 - "$WS/tier/tier.json" "$TAG" "$VLM_MODEL" <<\'PY\'')
        s=s.replace('cp "$SP/staged/arc/launch_e2e_arc_v2.sh"','cp "$SP/staged/arc/launch_e2e_arc_model.sh"')
    else:
        s=s.replace('RUN=$PUB/real_eval/runs/control_e2etdcspec_rep${REP}_tdc02_luna_${TS}','RUN=$PUB/real_eval/runs/control_e2etdcspec_rep${REP}_tdc02_${TAG}_${TS}')
        s=s.replace('echo "$RUN" > "$SP/current_e2etdcspec"; NAME=control_e2etdcspec_rep${REP}_${TS}; echo "$NAME" > "$SP/current_e2etdcspec_container"','echo "$RUN" > "$SP/current_e2etdcspec_${TAG}"; NAME=control_e2etdcspec_${TAG}_rep${REP}_${TS}; echo "$NAME" > "$SP/current_e2etdcspec_${TAG}_container"')
        s=s.replace('tee "$RUN/logs/native.log" "$SP/e2etdc_rep${REP}_${TS}.log"','tee "$RUN/logs/native.log" "$SP/e2etdcspec_${TAG}_rep${REP}_${TS}.log"')
        s=s.replace('"project_id":"control_e2etdcspec_tdc02_luna"','"project_id":"control_e2etdcspec_tdc02_"+sys.argv[3]').replace('python3 - "$RUN/state.json" "$REP" <<\'PY\'','python3 - "$RUN/state.json" "$REP" "$TAG" "$VLM_MODEL" <<\'PY\'').replace('"summary":f"TDC end-to-end SPEC arm rep {sys.argv[2]}','"summary":f"TDC end-to-end SPEC arm rep {sys.argv[2]} model={sys.argv[3]} vlm_override={sys.argv[4] or \'none\'}')
        s=s.replace('T.update(arm="e2e-tdc-spec",','T.update(arm="e2e-tdc-spec",model_tag=sys.argv[2],vlm_model_override=(sys.argv[3] or None),ideation_patches="label normalization, tolerant parser, MAX_NUM_TOKENS 16384, retry x3",').replace('python3 - "$WS/tier/tier.json" <<\'PY\'','python3 - "$WS/tier/tier.json" "$TAG" "$VLM_MODEL" <<\'PY\'')
        s=s.replace('cp "$SP/staged/tdc/launch_e2e_tdc_spec.sh"','cp "$SP/staged/tdc/launch_e2e_tdc_model.sh"')
    bad=[l for l in s.splitlines() if "gpt-5.6-luna" in l]; assert not bad, bad
    open(dst,"w").write(s); print("written", dst.split("/")[-1])
generalize(f"{SP}/staged/arc/launch_e2e_arc_v2.sh", f"{SP}/staged/arc/launch_e2e_arc_model.sh", "arc")
generalize(f"{SP}/staged/tdc/launch_e2e_tdc_spec.sh", f"{SP}/staged/tdc/launch_e2e_tdc_model.sh", "tdc")
