#!/usr/bin/env python3
"""In-container applier for the native->contract ablation ladder (psydef, 02 x luna).

Reads /workspace/tier/tier.json and applies, cumulatively:
  tier 0: model adapter (provider routing, chat shim, token-tracker None safety,
          model names + num_workers=1), S2 bounded/timeout, common transport shim,
          prompt-logging diagnostic.                                  (native baseline)
  tier 1: + our psydef topic file is used by ideation (staged by the launcher)
          + the psydef wrapper's ideation contract paragraph (verbatim) into the
            ideation system prompt.
  tier 2: + real data / split / scorer facts APPENDED to the native impl guideline
            (native lines untouched).
  tier 3: + whole-study + deliverables lines APPENDED to the native impl guideline.
  tier 4: + upstream psydef wrapper control flow: stage-1 completion gate, stage
            stop, multi-seed skip (agent_manager.py) and its bfts search config.
Every text block is copied from real_eval/scripts/02_ai_scientist_v2_psydefdetect_fullrun.sh
by the launcher (tier.json carries the exact strings + sha256), so the ladder
uses the same words as the production wrapper. Run from /workspace.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

T = json.load(open("tier/tier.json", encoding="utf-8"))
tier = int(T["tier"])
print(f"[tier-apply] tier={tier}{T.get('arm','a')} rep={T['rep']} contract={T.get('use_ideation_contract', tier>=1)} facts={T.get('use_guideline_tier2', tier>=2)} load_code={T.get('use_load_code', False)}")


def run(cmd):
    print("[tier-apply] $", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


# ---- tier 0: model adapter + transport + logging (identical for every tier) ----
run([sys.executable, "real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py"])
run([sys.executable, "real_eval/adapters/ai_scientist_v2/patch_semantic_scholar_bounded.py"])
spec = importlib.util.spec_from_file_location("adapter", "real_eval/adapters/tdc_admet_tox/patch_ai_scientist_v2.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.patch_llm(); m.patch_chat_create(); m.patch_token_tracker(); m.patch_bfts_config()
print("[tier-apply] model adapter applied (llm routing, chat shim, token tracker, model names, num_workers=1)")
run([sys.executable, "real_eval/adapters/ai_scientist_v2/patch_prompt_logging.py"])

# ---- tier 1: ideation contract paragraph (verbatim from the psydef wrapper) ----
if T.get("use_ideation_contract", tier >= 1):
    p = Path("ai_scientist/perform_ideation_temp_free.py")
    text = p.read_text(encoding="utf-8")
    marker = "# Define the initial idea generation prompt"
    if T["ideation_contract"] not in text:
        if marker not in text:
            raise SystemExit("ideation system-prompt insertion point not found")
        text = text.replace(marker, 'system_prompt += """\n\n' + T["ideation_contract"] + '\n"""\n\n' + marker, 1)
        p.write_text(text, encoding="utf-8")
    print("[tier-apply] tier1: ideation contract paragraph inserted")

# ---- tier 2 / 3: guideline lines APPENDED to the native guideline ----
lines = []
if T.get("use_guideline_tier2", tier >= 2):
    lines += T["guideline_tier2"]
if tier >= 3:
    lines += T["guideline_tier3"]
if lines:
    p = Path("ai_scientist/treesearch/parallel_agent.py")
    text = p.read_text(encoding="utf-8")
    anchor = '        return {"Implementation guideline": impl_guideline}'
    mark = "tier-ladder-guideline-append"
    if mark not in text:
        if text.count(anchor) != 1:
            raise SystemExit("impl_guideline return anchor not found exactly once")
        block = "        # " + mark + "\n        impl_guideline.extend(" + repr(lines) + ")\n" + anchor
        p.write_text(text.replace(anchor, block, 1), encoding="utf-8")
    print(f"[tier-apply] tier{tier}: {len(lines)} guideline lines appended to the NATIVE guideline")

# ---- tier 4: upstream psydef wrapper control flow + search config ----
if tier >= 4:
    os.environ["AI_SCIENTIST_PSYDEFDETECT_TWO_EXPERIMENTS"] = "1"
    p = Path("ai_scientist/treesearch/agent_manager.py")
    text = p.read_text(encoding="utf-8")
    if "import os\n" not in text:
        text = "import os\n" + text
    for old, new in T["manager_patch_pairs"]:
        if old not in text:
            raise SystemExit("manager patch anchor not found: " + old[:60])
        text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    import yaml
    cfgp = Path("bfts_config.yaml")
    cfg = yaml.safe_load(cfgp.read_text(encoding="utf-8"))
    for dotted, value in T["config_tier4"].items():
        node = cfg
        keys = dotted.split(".")
        for k in keys[:-1]:
            node = node.setdefault(k, {})
        node[keys[-1]] = value
    cfgp.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    print("[tier-apply] tier4: upstream psydef control flow + search config applied")

print("[tier-apply] done")
