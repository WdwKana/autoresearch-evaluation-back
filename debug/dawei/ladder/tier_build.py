#!/usr/bin/env python3
"""Host-side builder: extracts the exact text blocks from the production psydef
wrapper and writes <workspace>/tier/tier.json for a given tier.
Usage: tier_build.py <tier> <rep> <workspace> <pub_root>
"""
import hashlib
import json
import re
import sys
from pathlib import Path

tier_arg, rep, ws, pub = sys.argv[1], sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
arm = tier_arg[-1] if tier_arg[-1] in "ab" else "a"
tier = int(tier_arg.rstrip("ab"))
w = (pub / "real_eval/scripts/02_ai_scientist_v2_psydefdetect_fullrun.sh").read_text(encoding="utf-8")

# ideation contract paragraph (verbatim)
m = re.search(r'mandatory = \'\'\'system_prompt \+= """(.*?)"""', w, re.S)
ideation_contract = m.group(1).strip()

# guideline lines (verbatim, in wrapper order)
m = re.search(r'"Implementation guideline": \[(.*?)\n                \]\n            \}', w, re.S)
raw = re.findall(r'^\s*"((?:[^"\\]|\\.)*)",?\s*$', m.group(1), re.M)
lines = [json.loads('"' + s + '"') for s in raw]
assert len(lines) == 16, len(lines)
# tier 2 = task facts & constraints (deps policy, data path/schema, target text, scorer CLI + row schema, scorer rc check)
TIER2_IDX = [0, 1, 2, 3, 4, 5, 7, 8]
# tier 3 = whole study + deliverables (two configs, selection + root files, trace schema, verification block, metric print, no plots/synthetic)
TIER3_IDX = [6, 9, 10, 11, 12, 15]
# 13, 14 restate native rules (no __main__, npy saving) that the native guideline already carries -> not appended.

# manager patch pairs (verbatim from the wrapper's inline python)
pairs = []
for old, new in re.findall(r"old = '''(.*?)'''\nnew = '''(.*?)'''", w, re.S):
    if "journals[stage.name]" in old or "parse_stage_names" in old:
        pairs.append([old, new])
old2 = "                            if current_substage.stage_number in [1, 2, 3, 4]:"
m2 = re.search(r"old = '" + re.escape(old2) + r"'\nnew = '''(.*?)'''", w, re.S)
pairs.append([old2, m2.group(1)])
assert len(pairs) == 3, len(pairs)

config_tier4 = {
    "exp_name": "psydefdetect",
    "generate_report": False,
    "agent.num_workers": 1,
    "agent.steps": 3,
    "agent.stages.stage1_max_iters": 8,
    "agent.stages.stage2_max_iters": 3,
    "agent.stages.stage3_max_iters": 3,
    "agent.stages.stage4_max_iters": 3,
    "agent.search.num_drafts": 1,
    "agent.search.debug_prob": 1.0,
    "agent.search.max_debug_depth": 2,
    "agent.multi_seed_eval.num_seeds": 1,
    "agent.expose_prediction": True,
    "exec.timeout": 900,
}

native_input = (tier == 2 and arm == "b")
T = {
    "tier": tier, "arm": arm, "rep": rep,
    "use_ideation_contract": tier >= 1 and not native_input,
    "use_guideline_tier2": tier >= 2 and not native_input,
    "use_load_code": native_input,
    "ideation_contract": ideation_contract,
    "guideline_tier2": [lines[i] for i in TIER2_IDX],
    "guideline_tier3": [lines[i] for i in TIER3_IDX],
    "manager_patch_pairs": pairs,
    "config_tier4": config_tier4,
    "source_wrapper_sha256": hashlib.sha256(w.encode()).hexdigest(),
    "topic_input": "upstream i_cant_believe_its_not_better.md" if tier == 0 else ("psydefdetect_native.md (theme-style) + psydefdetect_native.py via --load_code" if native_input else "psydefdetect_topic.md (generate_psydefdetect_native_inputs.py)"),
    "data_mounted": tier >= 1,
}
(ws / "tier").mkdir(parents=True, exist_ok=True)
(ws / "tier/tier.json").write_text(json.dumps(T, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"tier.json written: tier={tier}{arm} rep={rep} guideline_tier2={len(T['guideline_tier2'])} guideline_tier3={len(T['guideline_tier3'])} manager_pairs={len(pairs)}")
