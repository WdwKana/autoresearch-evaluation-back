#!/usr/bin/env python3
"""AI-Scientist-v2: raise the ideation output cap MAX_NUM_TOKENS 4096 -> 16384.

A model that reasons before answering spends part of the cap on reasoning, and its FinalizeIdea JSON is
cut mid-string ("Unterminated string", 0 ideas: fullrun_psydef_02_ds_r5_20260919_212837). Same remedy
the maintainers' BabyLM wrapper applies. Run from the AI-Scientist-v2 source root.
"""
from pathlib import Path
llm = Path("ai_scientist/llm.py")
text = llm.read_text(encoding="utf-8")
if "MAX_NUM_TOKENS = 4096" not in text and "MAX_NUM_TOKENS = 16384" not in text:
    raise SystemExit("MAX_NUM_TOKENS anchor not found in ai_scientist/llm.py")
llm.write_text(text.replace("MAX_NUM_TOKENS = 4096", "MAX_NUM_TOKENS = 16384"), encoding="utf-8")
print("[psydef-wrapper] ideation MAX_NUM_TOKENS = 16384")
