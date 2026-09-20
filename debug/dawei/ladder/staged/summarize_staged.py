#!/usr/bin/env python3
"""Per-stage summary for the staged-injection arm: nodes, passes, crashes, real-data + scorer use, time."""
import glob, json, os, re, sys
run=sys.argv[1]; reason=sys.argv[2] if len(sys.argv)>2 else ""
log=open(os.path.join(run,"logs/native.log"),encoding="utf-8",errors="replace").read()
print(f"RUN {os.path.basename(run)} | {reason}")
print("ideas:","; ".join(f"{i}:{t[:70]}" for i,t in re.findall(r"^ idea (\d) : (.*)$",log,re.M)) or "(none)")
m=re.search(r"Defined eval metrics:.*?name:\s*([^\n]+)",log,re.S); print("auto metric:",m.group(1).strip() if m else "?")
for J in sorted(glob.glob(os.path.join(run,"workspace/experiments/*/logs/*/stage_*/journal.json"))):
    stage=re.search(r"/(stage_[^/]+)/journal.json",J).group(1)
    ns=json.load(open(J))["nodes"]
    if not ns: print(f"[{stage}] 0 nodes"); continue
    ran=[n for n in ns if not n.get("exc_type")]; good=[k for k,n in enumerate(ns,1) if n.get("is_buggy") is False]
    real=sum(1 for n in ns if re.search(r"PsyDefConv|/data/psydefdetect|psydefdetect_split|load_corpus\(|official_score\(",n["code"]))
    sc=sum(1 for n in ns if re.search(r"run_psydefdetect_local_score|official_score\(",n["code"]))
    syn=sum(1 for n in ns if re.search(r"synthetic",("".join(n.get("_term_out") or [])),re.I))
    t=sum(n.get("exec_time") or 0 for n in ns)
    print(f"[{stage}] nodes={len(ns)} ran={len(ran)} crashed={len(ns)-len(ran)} passes={len(good)} first_pass_at={good[0] if good else '-'} | real_data_code={real}/{len(ns)} scorer_code={sc}/{len(ns)} synthetic_in_output={syn}/{len(ns)} | exec_time_total={int(t)}s")
    for k,n in enumerate(ns,1):
        print(f"   {k:2d} {'PASS ' if n.get('is_buggy') is False else 'buggy'} {'crash' if n.get('exc_type') else 'ran  '} t={round(n.get('exec_time') or 0):4d}s | {re.sub(r'\s+',' ',str(n.get('analysis')))[:110]}")
