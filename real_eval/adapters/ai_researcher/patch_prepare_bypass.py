#!/usr/bin/env python3
"""Bypass the Prepare Agent when its input is provably empty.

The Prepare Agent's mission is "go through the GitHub searching results ...
choose at least 5 repositories", with case_resolved as the only exit and
tool_choice="required" forcing a tool call every turn. Custom topics carry
source_papers = [], so github_result is the empty string: the agent is asked
to pick five repositories from a candidate pool of zero. Conversation
archives show the three models resolving this differently -- gpt-5.6-luna
submits an empty case_resolved after 14 messages, deepseek-v4-flash after 31,
while kimi-k2.6 refuses to hand in an empty result and manufactures its own
search (505 messages) until the request exceeds the model's 262,144-token
window and the run dies.

This adapter synthesises exactly the Result text case_resolved produces for
empty lists -- byte-identical in structure to what the successful runs fed
downstream -- and skips the agent call. It triggers ONLY when github_result
is blank, so upstream's own benchmark instances (which ship source papers)
run the Prepare Agent unchanged even with the flag on. Gated by
AI_RESEARCHER_PREPARE_BYPASS=1; default off at this layer, wrappers opt in.

Idempotent; fails loudly if the upstream anchor moves. Run from the
AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

ENTRYPOINT = Path("research_agent/run_infer_idea.py")

OLD = '''        messages = [{"role": "user", "content": query}]
        prepare_messages, context_variables = await self.prepare_agent(messages, context_variables)
        prepare_res = prepare_messages[-1]["content"]
        prepare_dict = extract_json_from_output(prepare_res)'''

NEW = '''        messages = [{"role": "user", "content": query}]
        if os.getenv("AI_RESEARCHER_PREPARE_BYPASS", "0") == "1" and not github_result.strip():
            # No GitHub search results were provided (source_papers is empty),
            # so "choose at least 5 repositories" has no satisfiable answer.
            # Hand downstream the same empty case_resolved result the
            # successful runs produced, without asking a model to arrive at it.
            _empty_prepare = {"reference_codebases": [], "reference_paths": [], "reference_papers": []}
            prepare_res = (
                "I have determined the reference codebases and paths according to the existing resources and the innovative ideas.\\n"
                + json.dumps(_empty_prepare, ensure_ascii=False, indent=4)
            )
            context_variables["prepare_result"] = _empty_prepare
            prepare_dict = _empty_prepare
        else:
            prepare_messages, context_variables = await self.prepare_agent(messages, context_variables)
            prepare_res = prepare_messages[-1]["content"]
            prepare_dict = extract_json_from_output(prepare_res)'''


def main() -> None:
    if not ENTRYPOINT.is_file():
        raise SystemExit("prepare-bypass: run from the AI-Researcher source root")
    text = ENTRYPOINT.read_text(encoding="utf-8")
    if "AI_RESEARCHER_PREPARE_BYPASS" in text:
        print("[prepare-bypass] already applied")
        return
    if OLD not in text:
        raise SystemExit("prepare-bypass: prepare_agent call-site anchor not found")
    for needed in ("import os", "import json"):
        if needed not in text:
            raise SystemExit(f"prepare-bypass: entrypoint lacks '{needed}'")
    ENTRYPOINT.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("[prepare-bypass] applied (active only when AI_RESEARCHER_PREPARE_BYPASS=1 and github_result is empty)")


if __name__ == "__main__":
    main()
