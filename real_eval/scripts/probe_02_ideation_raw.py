"""Replay the 02 ideation first-round request against the current provider and dump
the RAW chat.completions response (content / tool_calls / finish_reason / usage),
bypassing the parser. Read-only on the run workspace; nothing is written there.
Run inside the 02 runtime image with the run workspace mounted at /workspace."""
import json, os, sys, types
sys.path.insert(0, "/workspace")
os.chdir("/workspace")

import openai
from ai_scientist import llm as llm_mod

raw_dump = []
_orig = llm_mod.chat_create

EXTRA = json.loads(os.environ.get("EXTRA_KWARGS", "{}"))

def spy_chat_create(client, **kwargs):
    if EXTRA:
        kwargs = dict(kwargs)
        if "max_completion_tokens" in EXTRA:
            kwargs.pop("max_tokens", None)
        kwargs.update(EXTRA)
    resp = _orig(client, **kwargs)
    try:
        ch = resp.choices
        raw_dump.append({
            "n_requested": kwargs.get("n"), "n_choices": len(ch),
            "finish": [c.finish_reason for c in ch],
            "content_head": [((c.message.content or "")[:300]) for c in ch],
            "content_is_none": [c.message.content is None for c in ch],
            "tool_calls": [str(getattr(c.message, "tool_calls", None))[:300] for c in ch],
            "extra_fields": [sorted(k for k in c.message.model_dump().keys() if k not in ("content", "role", "tool_calls", "function_call"))
                             for c in ch],
            "usage": resp.usage.model_dump() if resp.usage else None,
        })
    except Exception as e:  # noqa: BLE001
        raw_dump.append({"spy_error": repr(e)[:200]})
    return resp

llm_mod.chat_create = spy_chat_create
import ai_scientist.perform_ideation_temp_free as pit
pit.chat_create = spy_chat_create if hasattr(pit, "chat_create") else None

model = os.environ["OPENAI_MODEL"]
client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url=os.environ["OPENAI_BASE_URL"])
topic = open("ai_scientist/ideas/babylm_topic.md", encoding="utf-8").read()
if os.environ.get("TOPIC_TRUNC"):
    topic = topic[: int(os.environ["TOPIC_TRUNC"])]
    print(f"[probe] topic truncated to {len(topic)} chars (diagnostic only)")
sys_prompt = pit.system_prompt
# first-round user message exactly as generate_temp_free_idea builds it
tmpl = getattr(pit, "idea_generation_prompt", None)
user_msg = tmpl.format(workshop_description=topic, prev_ideas_string="", **({"num_reflections": 3} if "{num_reflections}" in tmpl else {})) if tmpl else topic
text, hist = llm_mod.get_response_from_llm(user_msg, client=client, model=model, system_message=sys_prompt, print_debug=False, msg_history=[], temperature=0.7)
print("=== RAW RESPONSE DUMP ===")
print(json.dumps(raw_dump, ensure_ascii=False, indent=1)[:3000])
print("=== PARSED TEXT HEAD ===")
print(repr((text or "")[:400]))
if os.environ.get("CONTINUE_TEST") == "1" and "ACTION" not in (text or "").upper():
    # Second turn: does the model emit the protocol block once told to proceed?
    nudge = os.environ.get("CONTINUE_MSG", "Proceed now. Respond with the protocol: THOUGHT, ACTION, ARGUMENTS.")
    text2, hist2 = llm_mod.get_response_from_llm(nudge, client=client, model=model, system_message=sys_prompt, print_debug=False, msg_history=hist, temperature=0.7)
    print("=== SECOND TURN ===")
    print("has_ACTION=", "ACTION" in (text2 or "").upper(), "| len=", len(text2 or ""), "| head=", repr((text2 or "")[:300]))
