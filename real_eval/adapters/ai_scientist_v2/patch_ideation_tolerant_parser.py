#!/usr/bin/env python3
"""Infrastructure fix: tolerant parsing of ideation replies (AI-Scientist-v2).

perform_ideation_temp_free.py expects exactly one ACTION/ARGUMENTS pair per reply and
parses ARGUMENTS with ``ARGUMENTS:\\s*(.*?)(?:$|\\nTHOUGHT:|\\n$)``, i.e. up to the end of
the reply. Two reply shapes that carry exactly the requested content break it:

  * several ACTION/ARGUMENTS blocks in one reply (kimi-k2.6: a few searches followed by
    FinalizeIdea): the first ARGUMENTS text swallows the rest of the reply and json.loads
    fails with "Extra data"; upstream then discards the whole proposal.
  * a FinalizeIdea payload nested one level too deep, {"idea": {"idea": {...}}}
    (deepseek-v4-flash): upstream stores {"idea": {...}} and the BFTS launcher later fails
    on idea["Name"].

This patch keeps the protocol and every upstream decision: blocks are executed in the
order the model wrote them (tool results of one reply are concatenated), a FinalizeIdea
block finalizes exactly as upstream does, trailing prose after a complete JSON object is
ignored, and a single-level surplus "idea" wrapper is unwrapped. Nothing is repaired or
invented: a block whose JSON is still invalid fails exactly as before.

Idempotent; fails loudly if the upstream anchors move. Run from the source root, after
patch_ideation_action_format.py if that one is used (either order of presence is handled).
"""
from pathlib import Path

TARGET = Path("ai_scientist/perform_ideation_temp_free.py")
MARK = "ideation-tolerant-parser"

HELPERS = '''
# ''' + MARK + ''': helpers (see real_eval/adapters/ai_scientist_v2/patch_ideation_tolerant_parser.py)
_TP_BLOCK = re.compile(
    r"ACTION:\\s*(.*?)\\s*ARGUMENTS:\\s*(.*?)(?=\\n[ \\t>#*_`]*ACTION[ \\t*_`]*:|\\nTHOUGHT:|\\Z)",
    re.DOTALL | re.IGNORECASE,
)


def _tp_trim_json(arguments_text):
    """Return the first complete JSON value at the start of the text (fenced or bare),
    ignoring anything after it; return the text unchanged if no JSON starts there."""
    text = arguments_text.strip()
    fenced = re.match(r"```(?:json)?\\s*(.*?)\\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    if text[:1] in "{[":
        try:
            _, end = json.JSONDecoder().raw_decode(text)
        except json.JSONDecodeError:
            return text
        if text[end:].strip():
            print(f"[tolerant-parser] ignoring {len(text) - end} trailing characters after the JSON arguments")
        return text[:end]
    return text


def _tp_action_blocks(text):
    """All (action, arguments_text) pairs of a reply, in order."""
    return [(m.group(1).strip().strip("*_` "), _tp_trim_json(m.group(2))) for m in _TP_BLOCK.finditer(text)]


def _tp_unwrap_idea(idea):
    """{"idea": {"idea": {...}}} -> the inner idea (only a surplus single-key wrapper)."""
    while isinstance(idea, dict) and list(idea.keys()) == ["idea"] and isinstance(idea["idea"], dict):
        print("[tolerant-parser] unwrapping a surplus 'idea' wrapper in FinalizeIdea arguments")
        idea = idea["idea"]
    return idea

'''

FUNC_ANCHOR = "\ndef generate_temp_free_idea(\n"

SEG_START_PATCHED = "                    action_match = re.search(\n                        action_pattern, _parse_text, re.DOTALL | re.IGNORECASE\n                    )\n"
SEG_START_PLAIN = "                    action_match = re.search(\n                        action_pattern, response_text, re.DOTALL | re.IGNORECASE\n                    )\n"
SEG_END = '                        print(f"Available actions are: {tool_names_str}")\n'

NEW_SEGMENT = '''                    # {mark}: several ACTION/ARGUMENTS blocks per reply are executed in order;
                    # trailing prose after the JSON is ignored; a surplus "idea" wrapper is unwrapped.
                    _tp_blocks = _tp_action_blocks({source})
                    if not _tp_blocks:
                        raise ValueError("Failed to parse the LLM response.")
                    if len(_tp_blocks) > 1:
                        print(f"[tolerant-parser] {{len(_tp_blocks)}} action blocks in one reply; executing in order")
                    _tp_reply_results = []
                    for action, arguments_text in _tp_blocks:
                        print(f"Action: {{action}}")
                        print(f"Arguments: {{arguments_text}}")

                        # Process the action and arguments
                        if action in tools_dict:
                            # It's a tool we have defined
                            tool = tools_dict[action]
                            # Parse arguments
                            try:
                                arguments_json = json.loads(arguments_text)
                            except json.JSONDecodeError:
                                raise ValueError(f"Invalid arguments JSON for {{action}}.")

                            # Use the tool
                            try:
                                # Assuming the arguments match the parameters of the tool
                                result = tool.use_tool(**arguments_json)
                                _tp_reply_results.append(str(result))
                            except Exception as e:
                                _tp_reply_results.append(f"Error using tool {{action}}: {{str(e)}}")
                        elif action == "FinalizeIdea":
                            # Parse arguments
                            try:
                                arguments_json = json.loads(arguments_text)
                                idea = _tp_unwrap_idea(arguments_json.get("idea"))
                                if not idea:
                                    raise ValueError("Missing 'idea' in arguments.")

                                # Append the idea to the archive
                                idea_str_archive.append(json.dumps(idea))
                                print(f"Proposal finalized: {{idea}}")
                                idea_finalized = True
                                break
                            except json.JSONDecodeError:
                                raise ValueError("Invalid arguments JSON for FinalizeIdea.")
                        else:
                            print(
                                "Invalid action. Please specify one of the available tools."
                            )
                            print(f"Available actions are: {{tool_names_str}}")
                    if _tp_reply_results:
                        last_tool_results = "\\n\\n".join(_tp_reply_results)
                    if idea_finalized:
                        break
'''


def main() -> None:
    if not TARGET.is_file():
        raise SystemExit("run from the AI-Scientist-v2 source root: ideation script not found")
    text = TARGET.read_text(encoding="utf-8")
    if MARK in text:
        print("ideation tolerant parser already applied")
        return
    if text.count(FUNC_ANCHOR) != 1:
        raise SystemExit("ideation parser anchor not found exactly once: generate_temp_free_idea")
    if text.count(SEG_START_PATCHED) == 1:
        start, source = SEG_START_PATCHED, "_parse_text"
    elif text.count(SEG_START_PLAIN) == 1:
        start, source = SEG_START_PLAIN, "response_text"
    else:
        raise SystemExit("ideation parser anchor not found exactly once: action_match = re.search(")
    if text.count(SEG_END) != 1:
        raise SystemExit("ideation parser anchor not found exactly once: Available actions are")
    i = text.index(start)
    j = text.index(SEG_END) + len(SEG_END)
    if j <= i:
        raise SystemExit("ideation parser anchors out of order")
    new = text[:i] + NEW_SEGMENT.format(mark=MARK, source=source) + text[j:]
    new = new.replace(FUNC_ANCHOR, HELPERS + FUNC_ANCHOR, 1)
    TARGET.write_text(new, encoding="utf-8")
    print("ideation tolerant parser applied")


if __name__ == "__main__":
    main()
