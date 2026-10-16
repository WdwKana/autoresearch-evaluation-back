#!/usr/bin/env python3
"""01 x BabyLM: route the paper-writing phase through the injected model; empty replies degrade to "" (host-side).

fullrun_babylm_01_20260828_130336 finished its research (EXIT_CODE=0) and then lost the whole writeup:
SectionComposer defaults gpt_model to 'gpt-4o-mini-2024-07-18' and MethodologyComposer never overrides
it, so all 22 writing-phase calls got 403. chat() swallows the 403 and returns None, which crashes the
first consumer that assumes text. Two source-level fixes: every GPTClient uses OPENAI_MODEL, and chat()
returns "" instead of None on failure.

argv: <benchmark_collection/utils/openai_utils.py>
"""
from pathlib import Path
import sys

# Run fullrun_babylm_01_20260828_130336 finished its research (EXIT_CODE=0) and
# then lost the whole writeup: SectionComposer defaults gpt_model to
# 'gpt-4o-mini-2024-07-18' and MethodologyComposer never overrides it, so all
# 22 writing-phase calls hit the provider as gpt-4o-mini and got 403 (token has
# no access to that model). chat() swallows the 403 and returns None, which
# then crashes the first consumer that assumes text. Two source-level fixes:
# route every GPTClient through the injected OPENAI_MODEL, and make chat()
# degrade to "" instead of None so no consumer can crash on a failed call.
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

old = "        self.model = model"
new = '        self.model = os.environ.get("OPENAI_MODEL") or model'
if old in text:
    text = text.replace(old, new, 1)
else:
    print("SKIP: GPTClient model assignment not found")

old = """                    response = await self._get_response(messages, temperature, max_tokens)

                    # \u2705 Log the output
                    log_message("Assistant Message", datetime.datetime.now(), f"Paper Agent: {response.strip()}")

                    return response"""
new = """                    response = await self._get_response(messages, temperature, max_tokens)
                    if not isinstance(response, str):
                        print("Empty completion content; coercing to empty string")
                        response = ""
                    log_message("Assistant Message", datetime.datetime.now(), f"Paper Agent: {response.strip()}")

                    return response"""
if old in text:
    text = text.replace(old, new, 1)
else:
    print("SKIP: chat success path not found")

for prefix, indent in (
    ('            print("Warning: Input tokens exceed model\'s context window")', "            "),
    ('                        print(f"Final attempt failed: {str(e)}")', "                        "),
    ('                    print(f"Unexpected error: {str(e)}")', "                    "),
    ('            print(f"Error in chat method: {str(e)}")', "            "),
):
    old = prefix + "\n" + indent + "return None"
    new = prefix + "\n" + indent + 'return ""'
    if old in text:
        text = text.replace(old, new, 1)
    else:
        print(f"SKIP: return-None site not found after: {prefix.strip()[:40]}")

path.write_text(text, encoding="utf-8")
