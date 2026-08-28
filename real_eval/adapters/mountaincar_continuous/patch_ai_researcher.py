#!/usr/bin/env python3
"""AI-Researcher runtime adapter for MountainCar-Continuous.

Derived from real_eval/adapters/tdc_admet_tox/patch_ai_researcher.py, which
carries the same duties for TDC. The MountainCar topic never had one: its
wrapper was scaffolding that pointed at /workspace/AI-Researcher (the framework
is rsynced to /workspace itself), passed no --instance_path (defaulting to
benchmark/gnn.json, an unrelated topic), no --model (defaulting to
gpt-4o-2024-08-06, which 403s against the injected provider), and mounted no
Docker socket although AI-Researcher spawns a nested container by default. Run
fullrun_mcar_01_20260828_141535 (retained) failed three seconds in with
"can't open file '/workspace/AI-Researcher/research_agent/run_infer_idea.py'".

Duties, all of them upstream gaps the ARC/BabyLM/TDC wrappers already patch:

1. define PLATFORM in research_agent/constant.py, without which every tool
   module fails during the tools package's recursive import;
2. register the tool modules explicitly instead of the recursive walk;
3. pass the `references` argument in run_infer_idea.py's module-level main()
   call (upstream's signature takes two arguments);
4. resolve the dataset_candidate source with an absolute path (upstream's
   relative "../benchmark/..." does not exist under this workdir);
5. run experiments inside this container instead of spawning a nested one,
   since no host Docker socket is mounted;
6. skip the GitHub code search, which needs a token the public setup does not
   ship and 401s the run.

Idempotent; fails loudly if an upstream anchor moves. Run from the
AI-Researcher source root.
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

    utils = Path("research_agent/inno/environment/utils.py")
    text = utils.read_text(encoding="utf-8")
    if "_MCAR_DATASET_SETUP" not in text:
        old_src = '    source_path = f"../benchmark/process/dataset_candidate/{category}"'
        new_src = (
            "    _MCAR_DATASET_SETUP = True\n"
            "    _repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))\n"
            "    source_path = os.path.join(_repo_root, 'benchmark', 'process', 'dataset_candidate', category)\n"
            "    if not os.path.exists(source_path):\n"
            + old_src.replace("    source_path", "        source_path")
        )
        if old_src not in text:
            raise SystemExit("setup_dataset source_path anchor not found")
        text = text.replace(old_src, new_src, 1)
        old_copy = "        shutil.copytree(source_path, dataset_candidate_path)"
        new_copy = (
            old_copy + "\n"
            "        if category == 'mountaincar_continuous':\n"
            "            # The metaprompt addresses /workspace/src, /workspace/evaluate.py and\n"
            "            # /workspace/checkpoints, but the agent works inside its own workplace.\n"
            "            # Project the frozen starter code and the protected evaluator in, so the\n"
            "            # agent edits a copy and never the originals.\n"
            "            for _name in ('src', 'evaluate.py', 'evaluate.py.sha256'):\n"
            "                _s = os.path.join('/workspace', _name)\n"
            "                _t = os.path.join(local_workplace, _name)\n"
            "                if os.path.exists(_s) and not os.path.exists(_t):\n"
            "                    if os.path.isdir(_s):\n"
            "                        shutil.copytree(_s, _t)\n"
            "                    else:\n"
            "                        shutil.copy2(_s, _t)\n"
            "            os.makedirs(os.path.join(local_workplace, 'checkpoints'), exist_ok=True)\n"
        )
        if old_copy in text:
            text = text.replace(old_copy, new_copy, 1)
        utils.write_text(text, encoding="utf-8")

    docker_env = Path("research_agent/inno/environment/docker_env.py")
    text = docker_env.read_text(encoding="utf-8")
    if "_MCAR_LOCAL_EXEC" not in text:
        old_init = "    def init_container(self):"
        new_init = """    _MCAR_LOCAL_EXEC = True

    def init_container(self):
        # MountainCar runs experiments in this container; no nested docker, no socket.
        os.makedirs(self.local_workplace, exist_ok=True)
        return

    def _mcar_unused_init_container(self):"""
        if old_init not in text:
            raise SystemExit("init_container anchor not found in docker_env.py")
        text = text.replace(old_init, new_init, 1)

        old_run = "    def run_command(self, command, stream_callback=None):"
        new_run = """    def run_command(self, command, stream_callback=None):
        # Local execution path for MountainCar (no nested container / socket).
        completed = subprocess.run(
            command, shell=True, cwd=self.local_workplace,
            capture_output=True, text=True,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        if stream_callback is not None and output:
            stream_callback(output)
        return {"status": completed.returncode, "result": output}

    def _mcar_unused_run_command(self, command, stream_callback=None):"""
        if old_run not in text:
            raise SystemExit("run_command anchor not found in docker_env.py")
        text = text.replace(old_run, new_run, 1)

        old_wait = "    def wait_for_container_ready(self, timeout=30):"
        new_wait = """    def wait_for_container_ready(self, timeout=30):
        return True

    def _mcar_unused_wait_for_container_ready(self, timeout=30):"""
        if old_wait in text:
            text = text.replace(old_wait, new_wait, 1)
        docker_env.write_text(text, encoding="utf-8")

    text = ENTRYPOINT.read_text(encoding="utf-8")
    old_gh = '        github_result = self.git_search({"metadata": metadata})'
    new_gh = '        github_result = "" if category == "mountaincar_continuous" else self.git_search({"metadata": metadata})'
    if old_gh in text:
        text = text.replace(old_gh, new_gh, 1)

    if "    main(args)\n" in text:
        ENTRYPOINT.write_text(
            text.replace("    main(args)\n", '    main(args, references="")\n', 1),
            encoding="utf-8",
        )

    print("mountaincar_continuous AI-Researcher adapter applied")


if __name__ == "__main__":
    main()
