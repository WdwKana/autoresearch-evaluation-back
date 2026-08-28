#!/usr/bin/env python3
"""AI-Scientist-v2 runtime adapter for TDC-ADMET-Tox (reconstructed).

Referenced by real_eval/scripts/02_ai_scientist_v2_tdc_admet_tox_fullrun.sh but
not shipped in the public release. That wrapper carries none of the inline
patches the ARC wrapper applies, so this file must perform them. All logic is
ported verbatim from the working 02xARC wrapper blocks:

1. register OPENAI_MODEL in AVAILABLE_LLMS and route the OpenAI client through
   the injected OPENAI_API_KEY / OPENAI_BASE_URL;
2. rewrite chat completion call sites to the gpt_responses_compat shim
   (created by patch_ai_scientist_v2_common.py, which runs before this);
3. guard token_tracker against providers that return None token details;
4. route every model reference in bfts_config.yaml onto OPENAI_MODEL
   (materializing agent.summary / agent.select_node, whose absence makes
   treesearch/journal.py fall back to a hardcoded gpt-4o).

Idempotent; fails loudly when an upstream anchor is missing. Replace with the
maintainers' original when available. Run from the AI-Scientist-v2 source root.
"""
from __future__ import annotations

import os
from pathlib import Path

MODEL = os.environ.get("OPENAI_MODEL", "")


def patch_llm() -> None:
    path = Path("ai_scientist/llm.py")
    text = path.read_text(encoding="utf-8")
    if MODEL and f'"{MODEL}"' not in text:
        text = text.replace("AVAILABLE_LLMS = [", f'AVAILABLE_LLMS = [\n    "{MODEL}",', 1)
    text = text.replace(
        'elif "gpt" in model:', 'elif "gpt" in model or model == "' + MODEL + '":'
    )
    text = text.replace(
        "return openai.OpenAI(), model",
        'return openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"], '
        'base_url=os.environ["OPENAI_BASE_URL"]), model',
    )
    path.write_text(text, encoding="utf-8")


def patch_chat_create() -> None:
    for raw in ("ai_scientist/llm.py", "ai_scientist/treesearch/backend/backend_openai.py"):
        path = Path(raw)
        text = path.read_text(encoding="utf-8")
        if "from ai_scientist.gpt_responses_compat import chat_create" not in text:
            text = "from ai_scientist.gpt_responses_compat import chat_create\n" + text
        text = text.replace("client.chat.completions.create(", "chat_create(client,")
        path.write_text(text, encoding="utf-8")


def patch_token_tracker() -> None:
    path = Path("ai_scientist/utils/token_tracker.py")
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "result.usage.completion_tokens_details.reasoning_tokens,",
        "result.usage.completion_tokens_details.reasoning_tokens or 0,",
    )
    text = text.replace(
        "result.usage.prompt_tokens_details.cached_tokens\n",
        "result.usage.prompt_tokens_details.cached_tokens or 0\n",
    )
    path.write_text(text, encoding="utf-8")


def patch_bfts_config() -> None:
    path = Path("bfts_config.yaml")
    if not path.is_file() or not MODEL:
        return
    import yaml

    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    for section in ("summary", "select_node"):
        entry = dict(config["agent"].get(section) or {})
        entry["model"] = MODEL
        entry.setdefault("temp", 0.3)
        config["agent"][section] = entry

    def set_models(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "model" and isinstance(value, str):
                    node[key] = MODEL
                else:
                    set_models(value)
        elif isinstance(node, list):
            for item in node:
                set_models(item)

    set_models(config)
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


def main() -> None:
    if not Path("ai_scientist").is_dir():
        raise SystemExit("run from the AI-Scientist-v2 source root: ai_scientist/ not found")
    patch_llm()
    patch_chat_create()
    patch_token_tracker()
    patch_bfts_config()
    print("tdc_admet_tox AI-Scientist-v2 adapter applied")


if __name__ == "__main__":
    main()
