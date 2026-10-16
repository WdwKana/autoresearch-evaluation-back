#!/usr/bin/env python3
"""01 x BabyLM: count tokens of corpus text that contains tiktoken special tokens (host-side).

count_tokens() calls tiktoken encode() with default args, which raises on any text containing a special
token such as <|endoftext|>. BabyLM corpora are GPT-2-style text and contain that literal, so paper
composition dies after the research work is already done (fullrun_babylm_01_20260827_092535 lost 8.5
hours of completed training to this). Count them as ordinary text.

argv: <benchmark_collection/utils/openai_utils.py>
"""
from pathlib import Path
import sys

# count_tokens() calls tiktoken encode() with default args, which raises on any
# text containing a special token such as <|endoftext|>. BabyLM corpora are
# GPT-2-style text and contain that literal, so paper composition dies after the
# research work is already done (run fullrun_babylm_01_20260827_092535 lost 8.5
# hours of completed training to this). Count them as ordinary text.
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
old = "    return len(encoding.encode(text))"
new = "    return len(encoding.encode(text, disallowed_special=()))"
if old in text:
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
else:
    print("SKIP: count_tokens insertion point not found")
