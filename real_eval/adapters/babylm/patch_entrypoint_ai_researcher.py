#!/usr/bin/env python3
"""01 x BabyLM entrypoint fixes (host-side, applied to the run's source copy before launch).

Upstream ships research_agent/constant.py without PLATFORM, so every tool module that imports it
fails during the tools package's recursive import and run_infer_idea.py dies with "cannot import
name 'gen_code_tree_structure'". The ARC wrapper already patches this; BabyLM never did. Same minimal
fix: define PLATFORM and register the tool modules explicitly. Also: main() takes (args, references)
but the module-level call passes only args; and the GitHub code search needs a token the public
setup does not ship (401 kills the run) -- skipped for the babylm category, as ARC does for its own.

argv: <constant.py> <inno/tools/__init__.py> <run_infer_idea.py>
"""
from pathlib import Path
import sys

entrypoint = Path(sys.argv[3])
text = entrypoint.read_text(encoding="utf-8")
# Upstream's main() takes (args, references); the module-level call passes only
# args. The ARC wrapper already patches this; BabyLM never did.
if '    main(args)\n' in text:
    text = text.replace('    main(args)\n', '    main(args, references="")\n', 1)
# GitHub code search needs a token the public setup does not ship (401 kills the
# run). ARC bypasses it for its category; do the same for babylm.
old_gh = '        github_result = self.git_search({"metadata": metadata})'
new_gh = '        github_result = "" if category == "babylm" else self.git_search({"metadata": metadata})'
if old_gh in text:
    text = text.replace(old_gh, new_gh, 1)
else:
    print("SKIP: GitHub-search insertion point not found")
entrypoint.write_text(text, encoding="utf-8")

constants = Path(sys.argv[1])
text = constants.read_text(encoding="utf-8")
if "PLATFORM =" not in text:
    constants.write_text(text + "\nPLATFORM = 'linux/amd64'\n", encoding="utf-8")

tools = Path(sys.argv[2])
text = tools.read_text(encoding="utf-8")
old = "import_tools_recursively(current_dir, 'inno.tools')"
new = '''for module_name in (
    "terminal_tools",
    "inner",
    "inno_tools.planning_tools",
    "inno_tools.web_tools",
):
    importlib.import_module(f"research_agent.inno.tools.{module_name}")'''
if old in text:
    tools.write_text(text.replace(old, new), encoding="utf-8")
else:
    print("SKIP: tool registration insertion point not found")
