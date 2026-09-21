import json, os, sys
sys.path.insert(0, "/workspace")
import ai_scientist.perform_ideation_temp_free as M

IDEA = {"Name": "n1", "Title": "T", "Short Hypothesis": "h", "Related Work": "r", "Abstract": "a", "Experiments": "e", "Risk Factors and Limitations": "l"}
calls, prompts = [], []
class StubTool:
    name = "SearchSemanticScholar"
    def use_tool(self, query): calls.append(query); return f"RESULT<{query}>"
M.tools_dict = {"SearchSemanticScholar": StubTool()}
M.tool_names_str = "SearchSemanticScholar, FinalizeIdea"

def run(replies, num_reflections=5, gens=1):
    calls.clear(); prompts.clear(); it = iter(replies)
    def fake(prompt, client, model, system_message, msg_history):
        prompts.append(prompt); return next(it), msg_history
    M.get_response_from_llm = fake
    fn = "/tmp/ideas_test.json"
    if os.path.exists(fn): os.remove(fn)
    return M.generate_temp_free_idea(fn, None, "stub", "desc", max_num_generations=gens, num_reflections=num_reflections, reload_ideas=False)

kimi = ("I'll search first.\n\nACTION:\nSearchSemanticScholar\n\nARGUMENTS:\n{\"query\": \"q1\"}\n\nACTION:\nSearchSemanticScholar\n\nARGUMENTS:\n{\"query\": \"q2\"}\n\n"
        "Now let me finalize my research idea based on the literature search.\n\nACTION:\nFinalizeIdea\n\nARGUMENTS:\n" + json.dumps({"idea": IDEA}) + "\n")
r = run([kimi]); assert calls == ["q1", "q2"] and r == [IDEA], (calls, r); print("1 kimi batched (2 searches + prose + finalize): OK")

ds = "ACTION: FinalizeIdea\nARGUMENTS: " + json.dumps({"idea": {"idea": IDEA}}, indent=2)
r = run([ds]); assert r == [IDEA], r; print("2 ds nested idea unwrapped: OK")

single = ["ACTION:\nSearchSemanticScholar\n\nARGUMENTS:\n{\"query\": \"only\"}\n", "ACTION:\nFinalizeIdea\n\nARGUMENTS:\n```json\n" + json.dumps({"idea": IDEA}) + "\n```\n"]
r = run(single); assert calls == ["only"] and r == [IDEA] and "RESULT<only>" in prompts[1], (calls, r, prompts[1][-200:]); print("3 single-action rounds + fenced json, tool result fed back: OK")

labeled = "**Action**: SearchSemanticScholar\n**Arguments**: {\"query\": \"a\"}\n\n**Action**: FinalizeIdea\n**Arguments**:\n" + json.dumps({"idea": IDEA})
r = run([labeled]); assert calls == ["a"] and r == [IDEA], (calls, r); print("4 markdown labels + batched (composes with label patch): OK")

broken = "ACTION:\nSearchSemanticScholar\n\nARGUMENTS:\n{\"query\": \"unterminated}\n"
r = run([broken, "ACTION: FinalizeIdea\nARGUMENTS: " + json.dumps({"idea": IDEA})]); assert r == [] and len(prompts) == 1, (r, len(prompts)); print("5 invalid JSON still aborts the proposal as upstream: OK")

r = run(["ACTION:\nSearchSemanticScholar\n\nARGUMENTS:\n{\"query\": \"s%d\"}\n" % i for i in range(5)]); assert r == [] and calls == ["s0","s1","s2","s3","s4"], (r, calls); print("6 five search-only rounds -> nothing stored (unchanged): OK")

r = run(["ACTION: FinalizeIdea\nARGUMENTS: {\"idea\": {}}", "x"]); assert r == [] and len(prompts) == 1; print("7 empty idea still rejected: OK")
print("ALL_PARSER_TESTS_PASSED")
