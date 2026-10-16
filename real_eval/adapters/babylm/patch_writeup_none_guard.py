#!/usr/bin/env python3
"""01 x BabyLM: a None LLM reply must not kill the writeup (host-side).

write_temp_log() writes whatever the structure generator returned; when an LLM call yields nothing it is
None and the writeup dies with "write() argument must be str, not None" (fullrun_babylm_01_20260828_055119);
generate_or_revise_structure propagates the same None into structure.split (_121236). Coerce at both
sites so an empty reply degrades to an empty structure.

argv: <paper_agent/section_composer.py>
"""
from pathlib import Path
import sys

# write_temp_log() writes whatever the structure generator returned; when an LLM
# call yields nothing it is None and the writeup dies with
# "write() argument must be str, not None" after the research is complete
# (run fullrun_babylm_01_20260828_055119). Coerce to text.
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

# Root cause of the same family: generate_or_revise_structure returns whatever
# gpt_client.chat() gives back, and a None answer then propagates into
# write_temp_log / structure.split (run fullrun_babylm_01_20260828_121236 died
# on "'NoneType' object has no attribute 'split'"). Coerce at the source so an
# empty LLM reply degrades to an empty structure instead of killing the writeup.
comp = path.parent / "methodology_composing_using_template.py"
if comp.is_file():
    ctext = comp.read_text(encoding="utf-8")
    old_ret = "        return await self.gpt_client.chat(prompt=prompt)"
    new_ret = ("        _arc_result = await self.gpt_client.chat(prompt=prompt)\n"
               "        return _arc_result if isinstance(_arc_result, str) else (current_structure or \"\")")
    if old_ret in ctext and "_arc_result" not in ctext:
        comp.write_text(ctext.replace(old_ret, new_ret, 1), encoding="utf-8")
    elif old_ret not in ctext and "_arc_result" not in ctext:
        print("SKIP: structure generator return anchor not found")
old = "        with open(filename, 'w', encoding='utf-8') as f:\n            f.write(content)"
new = "        with open(filename, 'w', encoding='utf-8') as f:\n            f.write(content if isinstance(content, str) else ('' if content is None else str(content)))"
if old in text:
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
else:
    print("SKIP: write_temp_log insertion point not found")
