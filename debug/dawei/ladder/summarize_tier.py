#!/usr/bin/env python3
"""Summarize one ladder run: pass?, node index of pass, crash rate, whether judge
analyses reached later drafts through the Memory summaries (prompt_logs)."""
import glob
import json
import os
import re
import sys

run = sys.argv[1]
reason = sys.argv[2] if len(sys.argv) > 2 else ""
T = json.load(open(os.path.join(run, "workspace/tier/tier.json")))
log = open(os.path.join(run, "logs/native.log"), encoding="utf-8", errors="replace").read()
print(f"RUN {os.path.basename(run)}  tier={T['tier']} rep={T['rep']} | {reason}")
ideas = re.findall(r"^ idea (\d) : (.*)$", log, re.M)
print("ideas:", "; ".join(f"{i}:{t[:70]}" for i, t in ideas) or "(none)")
m = re.search(r"Defined eval metrics:.*?name:\s*([^\n]+)", log, re.S)
print("auto metric:", m.group(1).strip() if m else "?")
J = glob.glob(os.path.join(run, "workspace/experiments/*/logs/*/stage_1*/journal.json"))
if not J:
    print("no stage-1 journal"); sys.exit(0)
ns = json.load(open(J[0]))["nodes"]
ran = [n for n in ns if not n.get("exc_type")]
passed = [k for k, n in enumerate(ns, 1) if n.get("is_buggy") is False]
print(f"nodes={len(ns)} ran={len(ran)} crashed={len(ns)-len(ran)} ({(len(ns)-len(ran))*100//max(1,len(ns))}%) judged_non_buggy={len(passed)} pass_at_node={passed[0] if passed else '-'}")
for k, n in enumerate(ns, 1):
    plan = re.sub(r"\s+", " ", n.get("plan") or "")
    ref = bool(re.search(r"\b(earlier|previous|prior|avoid\w*|main (fix|correction)|fix\w* the|correct\w*|address\w*|instead of|rather than|no longer)\b", plan, re.I))
    print(f" {k:2d} {'PASS ' if n.get('is_buggy') is False else 'buggy'} {'crash' if n.get('exc_type') else 'ran  '} t={round(n.get('exec_time') or 0):4d}s lines={n['code'].count(chr(10)):4d} plan_refs_past={'y' if ref else 'n'} | {re.sub(r'\s+',' ',str(n.get('analysis')))[:150]}")
# memory logs: did the judge's analysis text survive into the summaries?
mems = sorted(glob.glob(os.path.join(run, "workspace/**/prompt_logs/step_*_memory.md"), recursive=True))
qs = [q for q in glob.glob(os.path.join(run, "workspace/**/prompt_logs/q_*_draft_*.md"), recursive=True) if not q.endswith(".reply.md")]
print(f"prompt_logs: memory files={len(mems)} draft prompts={len(qs)}")
if mems:
    last = open(mems[-1], encoding="utf-8", errors="replace").read()
    print(f" last memory summary: {len(last)} chars; head: {re.sub(r'\s+',' ',last)[:300]}")
if qs:
    sizes = [len(open(q, encoding="utf-8", errors="replace").read()) for q in qs]
    print(f" draft prompt sizes (chars): min={min(sizes)} max={max(sizes)} mean={sum(sizes)//len(sizes)}")
