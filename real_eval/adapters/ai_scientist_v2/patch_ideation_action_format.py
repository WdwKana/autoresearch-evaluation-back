#!/usr/bin/env python3
"""Infrastructure fix: tolerate markdown emphasis around the ideation action labels.

perform_ideation_temp_free.py extracts the agent's step with the literal regexes
``ACTION:\\s*(.*?)\\s*ARGUMENTS:`` / ``ARGUMENTS:\\s*(...)``. A reply that carries
exactly the requested content but decorates the labels -- e.g. deepseek-v4-flash's

    **Action**: FinalizeIdea
    **Arguments**:
    ```json
    {"idea": {...}}
    ```

does not match (the ``**`` sits between the word and the colon), the parser raises
"Failed to parse the LLM response", and upstream then BREAKS out of the whole
reflection loop: a complete, valid idea is discarded and ideation ends with
"Stored 0 ideas" (run fullrun_psydef_02_ds_r5_20260919_212250).

This patch only normalizes the three labels (ACTION / ARGUMENTS / THOUGHT) when
they are wrapped in markdown emphasis, heading or quote markers, and strips the
same decoration from the action name. The prompt, the tools, the idea content and
every decision stay the framework's and the model's. A reply already in the
literal format is left byte-identical (no-op for models that comply).
Idempotent; fails loudly if the upstream anchors move. Run from the source root.
"""
from __future__ import annotations

from pathlib import Path

TARGET = Path("ai_scientist/perform_ideation_temp_free.py")
MARK = "ideation-action-label-normalization"

OLD_PATTERN = '                    action_pattern = r"ACTION:\\s*(.*?)\\s*ARGUMENTS:"\n'
NEW_PATTERN = (
    "                    # " + MARK + ": accept **Action**: / ### ARGUMENTS: etc.\n"
    "                    _parse_text = re.sub(\n"
    "                        r\"(?im)^[ \\t>#*_`]*(ACTION|ARGUMENTS|THOUGHT)[ \\t*_`]*:[ \\t*_`]*\",\n"
    "                        lambda m: m.group(0) if m.group(0).strip() == m.group(1) + \":\" and m.group(1).isupper() else m.group(1).upper() + \": \",\n"
    "                        response_text,\n"
    "                    )\n"
    + OLD_PATTERN
)
OLD_ACTION_SEARCH = (
    "                    action_match = re.search(\n"
    "                        action_pattern, response_text, re.DOTALL | re.IGNORECASE\n"
    "                    )\n"
)
NEW_ACTION_SEARCH = OLD_ACTION_SEARCH.replace("response_text", "_parse_text")
OLD_ARGS_SEARCH = (
    "                    arguments_match = re.search(\n"
    "                        arguments_pattern, response_text, re.DOTALL | re.IGNORECASE\n"
    "                    )\n"
)
NEW_ARGS_SEARCH = OLD_ARGS_SEARCH.replace("response_text", "_parse_text")
OLD_ACTION_VALUE = "                    action = action_match.group(1).strip()\n"
NEW_ACTION_VALUE = "                    action = action_match.group(1).strip().strip(\"*_` \")\n"


def main() -> None:
    if not TARGET.is_file():
        raise SystemExit("run from the AI-Scientist-v2 source root: ideation script not found")
    text = TARGET.read_text(encoding="utf-8")
    if MARK in text:
        print("ideation action-label normalization already applied")
        return
    for old in (OLD_PATTERN, OLD_ACTION_SEARCH, OLD_ARGS_SEARCH, OLD_ACTION_VALUE):
        if text.count(old) != 1:
            raise SystemExit(f"ideation parser anchor not found exactly once: {old.strip()[:60]!r}")
    text = (
        text.replace(OLD_PATTERN, NEW_PATTERN, 1)
        .replace(OLD_ACTION_SEARCH, NEW_ACTION_SEARCH, 1)
        .replace(OLD_ARGS_SEARCH, NEW_ARGS_SEARCH, 1)
        .replace(OLD_ACTION_VALUE, NEW_ACTION_VALUE, 1)
    )
    TARGET.write_text(text, encoding="utf-8")
    print("ideation action-label normalization applied")


if __name__ == "__main__":
    main()
