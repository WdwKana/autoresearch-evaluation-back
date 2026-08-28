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
   call (upstream's signature takes two arguments);
4. run experiments inside this container instead of spawning a nested one.
   The TDC wrapper states its contract explicitly -- "experiments execute inside
   the framework container without a host Docker socket" -- and mounts no
   /var/run/docker.sock, but DockerEnv.init_container() always shells out to
   `docker run`, so the run dies with "failed to connect to the docker API".
   Make init_container a no-op and route run_command through a local subprocess
   with the same return shape the caller expects.

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

    docker_env = Path("research_agent/inno/environment/docker_env.py")
    text = docker_env.read_text(encoding="utf-8")
    if "_TDC_LOCAL_EXEC" not in text:
        old_init = "    def init_container(self):"
        new_init = """    _TDC_LOCAL_EXEC = True

    def init_container(self):
        # TDC runs experiments in this container; no nested docker, no socket.
        os.makedirs(self.local_workplace, exist_ok=True)
        return

    def _tdc_unused_init_container(self):"""
        if old_init not in text:
            raise SystemExit("init_container anchor not found in docker_env.py")
        text = text.replace(old_init, new_init, 1)

        old_run = "    def run_command(self, command, stream_callback=None):"
        new_run = """    def run_command(self, command, stream_callback=None):
        # Local execution path for TDC (no nested container / socket).
        completed = subprocess.run(
            command, shell=True, cwd=self.local_workplace,
            capture_output=True, text=True,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        if stream_callback is not None and output:
            stream_callback(output)
        return {"status": completed.returncode, "result": output}

    def _tdc_unused_run_command(self, command, stream_callback=None):"""
        if old_run not in text:
            raise SystemExit("run_command anchor not found in docker_env.py")
        text = text.replace(old_run, new_run, 1)

        old_wait = "    def wait_for_container_ready(self, timeout=30):"
        new_wait = """    def wait_for_container_ready(self, timeout=30):
        return True

    def _tdc_unused_wait_for_container_ready(self, timeout=30):"""
        if old_wait in text:
            text = text.replace(old_wait, new_wait, 1)
        docker_env.write_text(text, encoding="utf-8")

    text = ENTRYPOINT.read_text(encoding="utf-8")
    if "    main(args)\n" in text:
        ENTRYPOINT.write_text(
            text.replace("    main(args)\n", '    main(args, references="")\n', 1),
            encoding="utf-8",
        )

    print("tdc_admet_tox AI-Researcher adapter applied")


if __name__ == "__main__":
    main()
