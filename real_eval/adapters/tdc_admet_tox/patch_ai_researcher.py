#!/usr/bin/env python3
"""AI-Researcher runtime adapter for TDC-ADMET-Tox (reconstructed).

The public release references this file from
`real_eval/scripts/01_ai_researcher_tdc_admet_tox_fullrun.sh` but does not ship
it, so the full run stops at "missing required native input". This is a minimal
reconstruction of the duties the wrapper's own import gate implies: right after
running this script it imports execute_command, gen_code_tree_structure,
plan_dataset, plan_testing, plan_training, read_file and run_python from
research_agent.inno.tools and asserts they are callable.

Those symbols are unavailable in a stock checkout because
research_agent/constant.py defines no PLATFORM, so every tool module that
imports it fails during the tools package's recursive import. The ARC and
BabyLM wrappers already carry the same three fixes inline; this file applies
them for TDC:

1. define PLATFORM in research_agent/constant.py;
2. register the tool modules explicitly instead of the recursive walk;
3. pass the `references` argument in run_infer_idea.py's module-level main()
   call (upstream's signature takes two arguments).

It is idempotent and fails loudly if an upstream anchor moves. If the
maintainers' original version becomes available, diff and replace this file.
Run from the AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

CONSTANTS = Path("research_agent/constant.py")
TOOLS_INIT = Path("research_agent/inno/tools/__init__.py")
ENTRYPOINT = Path("research_agent/run_infer_idea.py")

OLD_REGISTRATION = "import_tools_recursively(current_dir, 'inno.tools')"
NEW_REGISTRATION = '''for module_name in (
    "terminal_tools",
    "inner",
    "inno_tools.planning_tools",
    "inno_tools.web_tools",
):
    importlib.import_module(f"research_agent.inno.tools.{module_name}")'''


def main() -> None:
    if not CONSTANTS.is_file():
        raise SystemExit("run from the AI-Researcher source root: research_agent/ not found")

    text = CONSTANTS.read_text(encoding="utf-8")
    if "PLATFORM =" not in text:
        CONSTANTS.write_text(text + "\nPLATFORM = 'linux/amd64'\n", encoding="utf-8")

    text = TOOLS_INIT.read_text(encoding="utf-8")
    if OLD_REGISTRATION in text:
        TOOLS_INIT.write_text(text.replace(OLD_REGISTRATION, NEW_REGISTRATION), encoding="utf-8")
    elif "importlib.import_module(f\"research_agent.inno.tools." not in text:
        raise SystemExit("tool registration anchor not found in research_agent/inno/tools/__init__.py")

    text = ENTRYPOINT.read_text(encoding="utf-8")
    if "    main(args)\n" in text:
        ENTRYPOINT.write_text(
            text.replace("    main(args)\n", '    main(args, references="")\n', 1),
            encoding="utf-8",
        )

    print("tdc_admet_tox AI-Researcher adapter applied")


if __name__ == "__main__":
    main()
